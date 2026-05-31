# 原子素材合并接口 · 规格（修订版）

## 背景

当前 `handle_generate_asset()` 通过直连 SQLite 的 `_load_project_from_db()` → `_save_project_to_db_slim()` 实现读-改-写。当 `MAX_WORKERS=3` 时，两个线程可能同时读取同一项目、各自添加素材、写回，最后一个写回覆盖前一个。

需要一套原子化的素材合并接口消除竞争，同时确保非 `neutral` 表情等待基础图时不占住 Worker 线程。

---

## 1. 事务边界

### 设计原则

- **事务只包围数据库合并操作，不包含 ComfyUI 调用。**
- ComfyUI 调用（可能耗时 10-60s）必须在事务外完成。
- 读取最新 project JSON → Pydantic 合并 → 写回，三步在同一事务中。

### 接口签名

```python
def atomic_merge_asset(
    project_id: str,
    asset_resource: AssetResource,
    *,
    scene_id: str | None = None,
    character_id: str | None = None,
    emotion: Emotion | None = None,
    base_asset_id: str | None = None,
) -> bool:
    """
    在 BEGIN IMMEDIATE 事务中原子地：
    1. 读取 project（最新版）
    2. 合并一个 AssetResource 到 asset_resources
    3. 如果 scene_id 指定且是背景类型，绑定 scene.background_id
    4. 如果 character_id + emotion 指定且是角色类型，绑定 char.asset_ids[emotion]
    5. 更新 updated_at

    不包含 ComfyUI 生成逻辑。不持有长事务。

    返回 True 表示成功，False 表示 project 不存在。
    """
```

### 事务流程

```python
def atomic_merge_asset(...) -> bool:
    db_path = _resolve_db_path()
    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        conn.execute("BEGIN IMMEDIATE")

        # 1. 读取最新 project JSON
        row = conn.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            conn.rollback()
            return False

        project = AdaptationProject.model_validate_json(row[0])

        # 2. Merges: 合并一个素材
        project.asset_resources[asset_resource.id] = asset_resource

        # 3. 绑定背景
        if scene_id and asset_resource.asset_type == AssetType.background:
            if scene_id in project.scenes:
                project.scenes[scene_id].background_id = asset_resource.id

        # 4. 绑定角色表情
        if character_id and emotion and asset_resource.asset_type == AssetType.character_sprite:
            if character_id in project.characters:
                project.characters[character_id].asset_ids[emotion] = asset_resource.id

        # 5. 更新基础图关联
        if base_asset_id and asset_resource.base_asset_id is None:
            asset_resource.base_asset_id = base_asset_id

        # 6. 写回
        now = datetime.now(timezone.utc).isoformat()
        project.updated_at = now
        conn.execute(
            "UPDATE projects SET data = ?, updated_at = ? WHERE id = ?",
            (project.model_dump_json(), now, project_id),
        )

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**关键点**：`BEGIN IMMEDIATE` 获取写锁后，后续的 SELECT 和 UPDATE 在这个锁内原子完成。另一个线程的同类操作会排队等待当前事务结束——因为两个操作写的是**同一个 project 的整行**，SQLite 的写锁序列化后，第二个线程看到的是更新后的 `data`，不会覆盖。

### `json_set()` 作为后续优化

当前方案用 Pydantic `model_dump_json()` 写入整行，对于单素材写入是简洁、可验证的。如果将来遇到大量并发写入同一 project 时，可以用 `json_set()` 做字段级优化，但：

- `json_set()` 在 SQLite 3.38+ 可用
- JSON path 中的 `asset_id` 和 `emotion` 值可能包含特殊字符，需要 `json_valid()` 确认或 hex 化 key
- **P1 / P2 阶段暂不引入 json_set()，使用上述事务方案**

---

## 2. 基础图失败降级状态机

### 问题

feature 分支的 `handle_generate_asset()` 中，当 `target_type == "character_sprite"` 且角色已有素材时，遍历 `char.asset_ids` 找第一个已有文件路径。但如果那个素材是 failed 状态，系统仍尝试使用它。也找不到 `neutral` 的 `asset_ids` 条目。

更关键的问题：**等待基础图完成期间不能占住 Worker 线程。** `wait_for_base_asset()` 如果轮询 300s，这个 Worker 线程在 5 分钟内无法处理其他任何 job。

### 解决：不在线等待 → 延迟入队

```
非 neutral 表情到达
  ↓
检查 char.asset_ids 中是否有 neutral
  ├─ 有 neutral 且文件存在 → 立即增量生成（当前逻辑正确）
  └─ 没有 neutral 或文件不存在
       ├─ 有 neutral 的 job 在 pending/running 中吗？
       │   ├─ 无 → 发起 neutral 全图生成
       │   │      ↓
       │   │      新 neutral job 入队后，当前 job 也重新入队
       │   │      保证 neutral 排在当前表情前面即可
       │   └─ 有 → 当前 job 重新入队（priority 低于 neutral, 高于其他）
       │
       ├─ 降级：如果 neutral job 的重试计数超过阈值，直接全图生成
       └─ 降级：检测队列中已有 neutral job 的尝试次数，如果它进入
                  permanently_failed，直接全图生成
```

### 重新入队机制

```python
def _re_enqueue_with_degraded(
    job_id: str,
    project_id: str,
    original_payload: dict,
    reason: str,
    *,
    degraded_base: bool = True,
) -> None:
    """将当前 job 重新入队，标记为 degrade 模式。当前 job 标记为 cancelled。"""
    db_path = DATA_DIR / "galgame.db"

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")

        # 1. 取消当前 job
        conn.execute(
            "UPDATE generation_jobs SET status = 'cancelled', updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), job_id),
        )

        # 2. 创建新 job（优先级更高：created_at 稍微提前）
        new_payload = {**original_payload, "degraded_base": True, "degraded_reason": reason}
        conn.execute(
            """INSERT INTO generation_jobs
               (id, project_id, job_type, status, payload, created_at, updated_at)
               VALUES (?, ?, 'generate_asset', 'pending', ?, ?, ?)""",
            (
                f"deferred_{uuid4().hex[:12]}",
                project_id,
                json.dumps(new_payload),
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

这样，一个等待 `neutral` 完成的 `happy` 表情 job 不会阻塞 Worker，而是：
1. 自己 cancelled
2. 一个新的 `happy` job 排在 `neutral` job 之后
3. `neutral` 完成后，`happy` 重试时可用的 `asset_ids` 中找到 `neutral` 的路径

### 降级触发条件

在 `handle_generate_asset()` 中，调用 `_resolve_base_for_emotion()` 判断：

```python
def _resolve_base_for_emotion(
    project: AdaptationProject,
    character_id: str,
    emotion: str,
) -> tuple[str | None, str | None]:
    """返回 (base_asset_id, base_image_path) 或 (None, None) 表示降级。"""
    char = project.characters.get(character_id)
    if not char or emotion == "neutral":
        return None, None

    # 查 neutral
    for target_emotion in ("neutral",):
        aid = char.asset_ids.get(Emotion(target_emotion))
        if aid and aid in project.asset_resources:
            res = project.asset_resources[aid]
            img_path = _comfyui_asset_url_to_path(res.url)
            if img_path and img_path.exists():
                return aid, str(img_path)

    # neutral 不存在
    # 检查是否有 neutral 的 job 在队列中
    pending_neutral = _count_pending_jobs(project_id, character_id=character_id, emotion="neutral")
    if pending_neutral > 0:
        # 有 neutral 在等待中 → 当前 job 重新入队（不阻塞）
        return "RE_ENQUEUE", None  # 哨兵值，上层处理

    # 检查 neutral 的失败历史
    failed_neutral_count = _count_failed_jobs(project_id, character_id=character_id, emotion="neutral")
    if failed_neutral_count >= 2:
        # neutral 多次失败 → 降级：直接全图生成
        return None, None  # degraded

    # neutral 尚未被调度 → 发起 neutral 生成
    _enqueue_neutral_generation(project_id, character_id, project.characters[character_id])
    return "RE_ENQUEUE", None
```

---

## 3. 修复 `base_asset_id` 未持久化的问题

feature 分支的 `generate_character_sprite()` 已生成基础图并缓存，且返回了 `cached_base_id`，但 `handle_generate_asset` 中没有将 `base_asset_id` 保存到 `asset_resource`。

### 修复点

在 `apps/worker/src/worker/tasks.py` 的 `handle_generate_asset()` 中，resource 创建后增加：

```python
# 持久化 base_asset_id（如果本次生成产出了新的基础图）
base_asset_id = result.get("base_asset_id") or base_asset_id
# 如果生成时没有传入 base_asset_id 但产出了缓存 ID，将其保存
if result.get("cached_base_id"):
    base_asset_id = result["cached_base_id"]
```

然后传入 `atomic_merge_asset(..., base_asset_id=base_asset_id)`。

---

## 4. 并发测试：`threading.Barrier`

测试文件：`apps/worker/tests/test_asset_concurrency.py`

### 测试设计

```python
import threading
from apps.worker.tasks import atomic_merge_asset
from project_model.schema import AssetResource, AssetType

N_THREADS = 10

def test_concurrent_asset_saves_retain_all_assets():
    """验证 N 个线程同时合并素材后，asset_resources 包含全部 N 项。"""
    project = _create_test_project()  # asset_resources = {}
    barrier = threading.Barrier(N_THREADS)

    results = []

    def _worker(asset: AssetResource):
        barrier.wait()  # 所有线程同时释放
        ok = atomic_merge_asset(project.project_id, asset)
        results.append(ok)

    assets = [
        AssetResource(id=f"ast_{i:04x}", url=f"/generated/{i}.png", asset_type="background")
        for i in range(N_THREADS)
    ]
    threads = [threading.Thread(target=_worker, args=(a,)) for a in assets]

    for t in threads: t.start()
    for t in threads: t.join()

    reloaded = _load_project(project.project_id)
    assert all(results)
    assert len(reloaded.asset_resources) == N_THREADS
    assert all(a.id in reloaded.asset_resources for a in assets)
```

### 可注入钩子

```python
# 在 atomic_merge_asset 的事务边界插入
_CONCURRENCY_BARRIER: threading.Barrier | None = None  # 用于测试

# 使用：测试中设置 barrier，所有线程在 SELECT 后、写入前同步
```

---

## 5. `handle_generate_asset` 重构调用链

```
handle_generate_asset(payload)
  │
  ├─ 1. 读取 project 元信息（角色、场景列表等）
  │
  ├─ 2. 幂等性检查（pre-gen check_asset_exists）→ 命中直接返回
  │
  ├─ 3. _resolve_base_for_emotion()
  │     ├─ → (id, path)    正常增量模式
  │     ├─ → RE_ENQUEUE    重新入队，return
  │     └─ → (None, None)  降级为全图生成（degraded）
  │
  ├─ 4. 调用 ComfyUI（耗时操作，无事务持有）
  │     generate_background() 或 generate_character_sprite()
  │
  ├─ 5. 原子合并素材
  │     atomic_merge_asset(project_id, resource, scene_id, character_id, emotion, base_asset_id)
  │
  └─ 6. 返回 result
```

---

## 6. 验收标准

- `python -m pytest apps/worker/tests/test_asset_concurrency.py -v` 通过（连续跑 3 轮）
- 10 个线程并发写入 10 个不同素材后，`asset_resources` 保留全部 10 项（零丢失）
- `base_asset_id` 在素材写入后持久化到 `AssetResource.base_asset_id`
- 非 `neutral` 表情的 character job 在 `neutral` 不存在时，不会阻塞 Worker 线程（通过 re-enqueue 验证：原始 job 状态为 `cancelled`，新 job 状态为 `pending`）
- `neutral` 连续失败 2 次后，后续表情降级为全图生成（`degraded_base=true`），不再重新入队
- 基准测试：100 次 `atomic_merge_asset` 调用总耗时 < 500ms（SQLite WAL 模式）
