# 夜樱工坊 — Galgame 转译器

上传小说 → AI 自动解析 → 生成可播放的 Galgame 演示版 → 在线编辑 → 导出 Ren'Py 项目

## 项目简介

「夜樱工坊」是一个将小说自动转化为视觉小说（Galgame）的工具。你只需要上传 `.txt` 或 `.md` 格式的小说文件，AI 会自动将其解析为场景、角色、对话和选择支，生成可在浏览器中直接播放的 Galgame 演示版。

## 架构

```
apps/
  web/       Next.js 前端（播放器 + 编辑器）
  api/       FastAPI 后端（项目管理和任务调度）
  worker/    后台任务处理器（AI 解析流水线）
packages/
  project-model/    共享 Pydantic 数据模型
  prompt-templates/ LLM 提示词模板
```

## 核心流程

```
上传小说 (.txt/.md)
  → AI 多步解析（摘要 → 角色 → 场景 → VN 适配）
    → 验证并生成规范化项目模型
      → Web 播放器（实时预览）
      → 在线编辑器（调整剧本）
      → Ren'Py 导出（待实现）
```

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- LLM API Key（支持 DeepSeek / Anthropic Claude / OpenAI 兼容接口）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd galgame_translater

# 安装 Python 依赖
pip install -e packages/project-model
pip install -e packages/prompt-templates
pip install -e apps/api
pip install -e apps/worker

# 安装前端依赖
cd apps/web && npm install && cd ../..
```

### 配置 LLM

在项目根目录创建 `.env` 文件：

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key-here
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
MAX_TOKENS=8192
```

也支持 Anthropic Claude：

```env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-sonnet-4-20250514
```

### 启动服务

需要同时运行三个服务：

```bash
# 终端 1：API 服务（端口 8001）
uvicorn apps.api.src.api.main:app --host 127.0.0.1 --port 8001

# 终端 2：Worker（AI 解析后台进程）
python -m apps.worker.src.worker.main

# 终端 3：前端（端口 3001）
cd apps/web && npx next dev -p 3001
```

打开浏览器访问 `http://localhost:3001` 即可使用。

### 可选：启动 Worker 脚本

项目根目录提供了 `start_worker.bat`（Windows），双击即可启动 Worker。

## 功能状态

| 功能 | 状态 |
|------|------|
| 上传 .txt/.md 小说 | ✅ 已完成 |
| AI 解析为场景、角色、对话、选择支 | ✅ 已完成（4 步 LLM 流水线） |
| Web 播放器预览 | ✅ 已完成 |
| 在线编辑器（单场景编辑） | ✅ 已完成 |
| 角色/背景图自动生成（AI 绘图） | ❌ 待实现（Phase 6） |
| Ren'Py 项目导出 | ❌ 待实现（Phase 5） |
| 暗色/亮色主题 | ✅ 已完成 |
| DeepSeek / Claude / OpenAI 多模型支持 | ✅ 已完成 |

## 项目模型

- **ParseDraft** — LLM 解析后的原始草稿（含角色、场景、资产线索）
- **AdaptationProject** — 验证后的规范化项目模型（播放器和编辑器使用的标准格式）

## 开发

```bash
# 运行测试
python -m pytest -q

# 构建前端
cd apps/web && npm run build
```

## 设计理念

参见 [DESIGN.md](DESIGN.md) 和 [PRODUCT.md](PRODUCT.md)。

- **第一秒即沉浸** — 进入网站如同翻开一部 Galgame 的标题画面
- **氛围优先，功能次之** — 暗色主题默认，柔和的发光效果，治愈系美学
- **为独处而设计** — 适合深夜打开，不刺眼，不喧哗
