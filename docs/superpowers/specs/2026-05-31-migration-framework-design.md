# 数据库迁移框架 · 规格（修订版）

## 背景

`feat/夜樱工坊-ui-redesign` 分支已经通过 `init_db()` 中的 `_migrate_add_idempotency_key()` 执行了部分增量 schema 变更（新增 `idempotency_key` 列和 `retry_count` 列）。但这是个临时方案，无法处理索引创建、数据清理、以及一致性校验。

需要一套可重复运行、幂等的迁移框架，同时需要对已经存在的列做兼容检测（而非重复添加）。

---

## 1. 迁移脚本定位

- 文件：`scripts/migrate_v1_to_v2.py`
- 入口：`python scripts/migrate_v1_to_v2.py [--dry-run] [--data-dir PATH]`
- 不依赖 SQLAlchemy ORM，直连 SQLite 以避免 import 循环
- 从 `GALGAME_DATABASE_URL` 环境变量或 `--data-dir` 推断数据库路径
- **幂等设计**：每个迁移项检查 `_migration_log` 表，已执行的跳过
- **兼容已部分迁移的数据库**：检测列是否存在，对已存在的列不做重复添加

## 2. `_migration_log` 表

```sql
CREATE TABLE IF NOT EXISTS _migration_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     TEXT    NOT NULL,       -- e.g. "V2", "V3"
    name        TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    checksum    TEXT    NOT NULL,        -- SHA256 of migration SQL
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    duration_ms INTEGER
);
```

每次迁移项执行前检查 `name` 是否已存在。已存在则跳过（幂等）。每条迁移项用 `BEGIN IMMEDIATE ... COMMIT` 包裹。

## 3. 迁移项（按 version 顺序）

### 兼容检测

由于 `feat/夜樱工坊-ui-redesign` 分支的 `_migrate_add_idempotency_key()` 可能已经在某些数据库上执行过，每个列级迁移项必须首先检测目标列是否存在：

```python
def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())
```

### 迁移项清单

| # | name | 前置条件 | 操作 | 幂等逻辑 |
|---|------|----------|------|----------|
| 1 | `add_idempotency_key_col` | 无 | `ALTER TABLE generation_jobs ADD COLUMN idempotency_key VARCHAR` | 检查列已存在则 skip |
| 2 | `add_idempotency_key_index` | 依赖 #1 | `CREATE INDEX IF NOT EXISTS idx_generation_jobs_idempotency ON generation_jobs(project_id, idempotency_key)` | `CREATE INDEX IF NOT EXISTS` 自身幂等 |
| 3 | `add_retry_count_col` | 无 | `ALTER TABLE generation_jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0` | 检查列已存在则 skip |
| 4 | `clean_duplicate_active_jobs` | 无 | 对同一 `(project_id, job_type, idempotency_key)` 有多个 pending/running 行的，保留 `created_at` 最早的，其余标记 `cancelled` | 用 `--apply-data-changes` 标志控制；dry-run 只报告 |
| 5 | `create_unique_active_job_index` | 依赖 #2、#4 | 创建部分唯一索引，只约束 active 状态行 | `CREATE UNIQUE INDEX IF NOT EXISTS idx_generation_jobs_active_unique ON generation_jobs(project_id, job_type, idempotency_key) WHERE status IN ('pending', 'running')` |
| 6 | `add_locked_until_col` | 无（按 P2 最终设计） | `ALTER TABLE generation_jobs ADD COLUMN locked_until TEXT` | 检查列已存在则 skip |
| 7 | `validate_status_values` | 无 | 将 `status` 列中不在 `pending/running/completed/failed/permanently_failed/cancelled` 中的值统一为 `failed`，记录修正数 | `--apply-data-changes` 标志控制；dry-run 报告非法值数量 |

### 关于历史 Job ID 的约定

**不重写已有 Job ID 格式**。当前 `job_id` 使用 `job_{project_id}_parse` 等格式。V2 迁移不改动已有行，只修改新任务生成策略：

- 新任务生成时，`job_id` 使用 `uuid4().hex` 格式
- 历史行的 `job_id` 保持不变
- API 的 schema 中 `job_id` 字段类型保持 `str`，不做格式校验

### 服务启动时的 schema 版本校验

```python
def check_schema_version(db_path: str) -> None:
    """
    检查数据库当前 schema 版本。
    如果版本低于预期，打印明确错误信息并退出。
    不自动执行迁移。
    """
    log_exists = _table_exists("_migration_log")
    if not log_exists:
        print("FATAL: Database schema is V1. Run `python scripts/migrate_v1_to_v2.py` before starting services.")
        sys.exit(1)

    # 检查关键迁移项是否存在
    required = ["add_idempotency_key_col", "create_unique_active_job_index", "add_locked_until_col"]
    missing = [name for name in required if not _migration_applied(name)]
    if missing:
        print(f"FATAL: Missing migrations: {', '.join(missing)}")
        print("Run `python scripts/migrate_v1_to_v2.py --apply-data-changes`")
        sys.exit(1)
```

在 `apps/api/src/api/main.py` 和 `apps/worker/src/worker/main.py` 的启动入口中调用 `check_schema_version()`。

---

## 4. Dry-run 模式

```python
def dry_run(db_path: str) -> int:
    """报告哪些迁移项待执行、每项会做什么、数据影响预估。返回待执行项数。"""
```

输出示例：
```
Migration plan for <galgame.db>
  _migration_log: 3 entries (schema partially migrated)
  Pending migrations:
    [V2] clean_duplicate_active_jobs    — DATA CHANGE: 2 duplicate rows will be cancelled
    [V2] create_unique_active_job_index — add partial unique index
    [V2] add_locked_until_col           — add column (non-destructive)
    [V2] validate_status_values         — DATA CHANGE: 0 rows affected

Use --apply-data-changes to allow data cleanup.
Use --dry-run (default) to only report.
```

已执行的迁移项（`add_idempotency_key_col`、`add_retry_count_col` 等）不会出现在待执行列表中。

---

## 5. 备份与回退

### 在线备份

使用 SQLite 的 `backup()` API，非文件复制，确保一致性：

```python
def backup_database(db_path: Path) -> Path:
    """使用 SQLite backup API 创建数据库一致性快照。不需要停止服务。"""
    backup_path = db_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}.db")
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(backup_path))
    src.backup(dst, pages=1024)  # 增量复制，不锁全库
    dst.close()
    src.close()
    return backup_path
```

在 `--apply-data-changes` 执行前自动调用备份。

### 恢复

**恢复时必须停止 API 和 Worker 进程**（因为涉及替换正在使用的数据库文件）：

```bash
# 停止服务后执行
python scripts/restore_from_backup.py <backup_path>
```

`restore_from_backup.py` 脚本：
1. 检查源数据库是否被 SQLite 锁定（如有活动连接则拒绝）
2. 用 `sqlite3.backup()` 将备份恢复到原始路径
3. 校验恢复后的完整性：`. integrity_check`

### 回退演练（每批次验证门槛之一）

```bash
# 1. dry-run 确认影响
python scripts/migrate_v1_to_v2.py --dry-run

# 2. 执行迁移
python scripts/migrate_v1_to_v2.py --apply-data-changes

# 3. 验证迁移日志
sqlite3 data/galgame.db "SELECT name, duration_ms FROM _migration_log"

# 4. 回退
python scripts/restore_from_backup.py data/galgame.db.bak.20260531120000.db

# 5. 验证回退后完整性
python -c "from scripts.migrate_v1_to_v2 import dry_run; assert dry_run('data/galgame.db') > 0"
```

---

## 6. 交付物

- `scripts/migrate_v1_to_v2.py` — 完整迁移入口
- `scripts/restore_from_backup.py` — 备份恢复入口
- `apps/api/src/api/main.py` — 添加 `check_schema_version()` 调用
- `apps/worker/src/worker/main.py` — 添加 `check_schema_version()` 调用
