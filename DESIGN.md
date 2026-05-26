---
name: Galgame Translater
description: 将小说转化为可玩的 Galgame。AI 解析 + Web 播放器 + 在线编辑 + Ren'Py 导出
colors:
  sakura-pink: "#ff8ba0"
  sakura-deep: "#e6758b"
  sakura-glow: "#ffb3c1"
  night-deep: "#0a0a10"
  night-panel: "#16161e"
  night-card: "#1e1e2a"
  night-border: "#2e2e3e"
  text-primary: "#ececf4"
  text-secondary: "#9090a8"
  text-muted: "#58587a"
  warm-gold: "#d4a86a"
  warm-gold-hover: "#c49555"
  success-green: "#6bcb9e"
  error-red: "#e86868"
  # Light mode
  light-bg: "#faf5f0"
  light-panel: "#f5efe8"
  light-card: "#ffffff"
  light-border: "#e0dbd4"
  light-text-primary: "#1c1c2a"
  light-text-secondary: "#6a6a7e"
  light-text-muted: "#a8a4b8"
typography:
  display:
    fontFamily: "'Noto Serif SC', 'Noto Serif', Georgia, serif"
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.02em"
  headline:
    fontFamily: "'Noto Serif SC', 'Noto Serif', Georgia, serif"
    fontSize: "clamp(1.25rem, 3vw, 2rem)"
    fontWeight: 600
    lineHeight: 1.3
  title:
    fontFamily: "'Noto Sans SC', 'Hiragino Sans GB', sans-serif"
    fontSize: "clamp(1rem, 2vw, 1.25rem)"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "'Noto Sans SC', 'Hiragino Sans GB', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "0.01em"
  label:
    fontFamily: "'Noto Sans SC', 'Hiragino Sans GB', sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.03em"
  mono:
    fontFamily: "'JetBrains Mono', 'Geist Mono', monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
components:
  button-primary:
    backgroundColor: "{colors.sakura-pink}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "12px 28px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.sakura-deep}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "12px 28px"
    border: "1px solid {colors.night-border}"
    typography: "{typography.label}"
  button-secondary-hover:
    borderColor: "{colors.sakura-pink}"
    textColor: "{colors.sakura-pink}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-ghost-hover:
    backgroundColor: "{colors.night-card}"
    textColor: "{colors.text-primary}"
  card-default:
    backgroundColor: "{colors.night-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  card-panel:
    backgroundColor: "{colors.night-panel}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  input-default:
    backgroundColor: "{colors.night-deep}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    border: "1px solid {colors.night-border}"
  input-focus:
    borderColor: "{colors.sakura-pink}"
    ring: "0 0 0 2px {colors.sakura-glow}30"
---

# Design System: Galgame Translater — 夜樱工坊

## 1. Overview

**Creative North Star: "夜樱工坊 — 在夜色与樱花环绕中创造故事"**

夜色为纸，樱花为墨。这个设计系统融合了深夜的静谧与樱花的温柔，为一个将小说转化为 Galgame 的创作平台提供视觉语言。它不像工具，更像一个让人愿意停留的空间 — 打开页面就像推开一间夜色中的工坊，暖光笼罩，樱花飘落。

系统以**暗色模式为默认品牌体验**（夜樱），同时提供**亮色模式**（朝樱）作为可切换选项。两套主题共享樱花粉情感锚点和金色点缀，仅在基底色和光影方向上发生翻转 — 就像从深夜到黎明的自然过渡。切换主题时，樱花粉不改变色相，只是它在不同背景上的表达方式随之调整。

**Key Characteristics:**
- 暗/亮双主题，共享樱花粉 + 金色点缀的视觉主轴
- 排版优先：衬线字体用于标题和角色名，无衬线用于正文，形成情感与信息的清晰分层
- 动效编排：粒子系统（樱花、雪花）、光影扫过、模糊过渡、呼吸感缩放，所有动效服务于"治愈·唯美"的感受
- 沉浸优先：内容即装饰，背景画布和角色立绘本身就是界面
- 克制的信息密度：工具功能被优雅地隐藏在体验之后

**明确拒绝的：** SaaS Dashboard 风格、卡片矩阵布局、企业蓝/灰色调、玻璃拟态作为默认样式、大数字指标模板。

## 2. Colors: 夜樱 Palette

夜色为幕，樱花为笔。整个调色板围绕"深夜"（冷黑基底）与"樱花"（暖粉情感）的对偶关系展开。

### Primary
- **Sakura Pink** (`#ff8ba0`): 主色调。用于按钮、链接、选中态、关键高亮。使用面积控制在 10-20% 的屏幕上。
- **Sakura Deep** (`#e6758b`): Primary hover 态。略深一层的粉色，保持温暖感。
- **Sakura Glow** (`#ffb3c1`): 用于发光效果、背景光晕、选中态的 ring 光晕。

### Secondary
- **Warm Gold** (`#d4a86a`): 次色调。用于星标、特殊成就、角色稀有度标识、暖光点缀。
- **Warm Gold Hover** (`#c49555`): Gold 的 hover 态。

### Neutral
- **Night Deep** (`#0a0a10`): 最深底色。页面背景、全屏画布。非常接近黑色但带有微暖色相（避免冷峻感）。
- **Night Panel** (`#16161e`): 面板色。侧边栏、属性面板、容器背景。
- **Night Card** (`#1e1e2a`): 卡片色。节点卡片、选项卡片、组件表面。
- **Night Border** (`#2e2e3e`): 边框色。分割线、描边、未选中态的边框。
- **Text Primary** (`#ececf4`): 主文字色。标题、正文、高优先级信息。
- **Text Secondary** (`#9090a8`): 次文字色。说明文字、标签、元信息。
- **Text Muted** (`#58587a`): 弱化文字色。占位符、禁用态、辅助信息。

### Semantic
- **Success Green** (`#6bcb9e`): 成功状态。解析完成、保存成功、导出成功。
- **Error Red** (`#e86868`): 错误状态。上传失败、解析错误、必填字段。

### Light Mode: 朝樱 Palette

亮色模式是暗色模式的镜像反转 — 基底从深夜变为暖白，层级关系反转（暗色中卡片比背景亮，亮色中卡片比背景更白），但樱花粉和金色的角色保持不变。

#### Light Neutral
- **Light BG** (`#faf5f0`): 页面背景。温暖的白，像和纸或樱花色的极浅底色。色相偏向暖黄，避免冷白。
- **Light Panel** (`#f5efe8`): 面板色。侧边栏、属性面板、容器背景。比背景略深几度，形成层次。
- **Light Card** (`#ffffff`): 卡片色。纯白底，与暖色背景形成清晰区隔。
- **Light Border** (`#e0dbd4`): 边框色。分割线、描边。暖灰，不刺眼。
- **Light Text Primary** (`#1c1c2a`): 主文字色。深暖黑，接近但不等于纯黑。
- **Light Text Secondary** (`#6a6a7e`): 次文字色。中灰色。
- **Light Text Muted** (`#a8a4b8`): 弱化文字色。占位符、辅助信息。

#### 主题对应关系

| 角色 | 暗色模式 | 亮色模式 |
|---|---|---|
| 背景 | Night Deep `#0a0a10` | Light BG `#faf5f0` |
| 面板 | Night Panel `#16161e` | Light Panel `#f5efe8` |
| 卡片 | Night Card `#1e1e2a` | Light Card `#ffffff` |
| 边框 | Night Border `#2e2e3e` | Light Border `#e0dbd4` |
| 主文字 | `#ececf4` | `#1c1c2a` |
| 次文字 | `#9090a8` | `#6a6a7e` |
| 弱化文字 | `#58587a` | `#a8a4b8` |

樱花粉（primary）和金色（secondary）在两套模式下完全共享，不需要调整 — 樱花粉在深色上发光，在浅色上成为视觉焦点，两种表达都是对的。

### Named Rules

**The 夜樱 Rule.** Sakura Pink 是唯一的情感色锚点。不使用第二种高饱和度色与其竞争。金色是温暖的辅助，不是第二主角。

**The 昼夜 Rule.** 暗色模式是品牌默认体验，亮色模式是尊重用户环境的可选项。切换不是"换肤"而是"翻转"：基底从 Night Deep → Light BG，层级方向反转，但樱花粉和金色的色值不变。用户无论在哪一个模式下，都认得出这是同一个设计系统。

**The Night Rule (Dark).** 暗色模式中，所有表面以深夜色为基底。樱花粉出现在交互元素和高亮上，从不作为大面积背景色。

**The Dawn Rule (Light).** 亮色模式中，所有表面以暖白色为基底。樱花粉仍然作为交互色，在浅色背景上使用略深版本 (`sakura-deep`) 确保对比度达标。

**The One-Glow Rule.** 每个页面最多只有一个主动发光源（光晕/粒子/扫光）。亮色模式将"发光"替换为"阴影" — 粒子不再发光，而是轻微投射。

## 3. Typography

**Display Font:** Noto Serif SC (衬线，用于标题和角色名)
**Body Font:** Noto Sans SC (无衬线，用于正文和 UI 文字)
**Mono Font:** JetBrains Mono / Geist Mono (用于代码、ID 显示、技术信息)

**Character:** 衬线的古典温度与无衬线的清晰可读形成对话。标题和角色名使用衬线，传递故事感和情感重量；正文和 UI 使用无衬线，保证长时间阅读的舒适度。这对组合天然适合"故事类工具产品"的定位。

### Hierarchy

- **Display** (700, `clamp(2rem, 5vw, 3.5rem)`, 1.2): 首页大标题、品牌标语。仅出现在品牌/营销场景，不在应用 UI 中使用。
- **Headline** (600, `clamp(1.25rem, 3vw, 2rem)`, 1.3): 页面标题、场景标题、章节名称。
- **Title** (600, `clamp(1rem, 2vw, 1.25rem)`, 1.4): 卡片标题、对话框角色名、面板标题。
- **Body** (400, 1rem, 1.7): 正文阅读文本。对话文本、旁白、描述。行长限制 65-75ch。
- **Label** (500, 0.8125rem, 1.4, 0.03em letter-spacing): 按钮文字、标签、导航项、元信息。
- **Mono** (400, 0.875rem, 1.5): 节点 ID、代码片段、技术信息。

### Named Rules

**The 物语 Rule.** 角色名永远使用衬线字体（Display 或 Headline 级别），与正文的无衬线形成视觉区隔。角色的声音通过字体切换就能被感知。

## 4. Elevation

系统采用**分层而不抬升**的深度策略。层级通过颜色明度（从暗色模式的 Night Deep → Night Panel → Night Card 或亮色模式的 Light BG → Light Panel → Light Card 的递进）来区分，而不是通过投影。这种"平层堆叠"的方式更符合二次元插画的视觉逻辑 — 画面是层叠的，而不是悬浮的。

投影极少使用。在需要区分浮动元素时（下拉菜单、弹出层、Toast），使用柔和的小投影：

### 阴影词汇
- **Float Low** (`0 4px 12px rgba(0,0,0,0.3)` / 亮色: `0 2px 8px rgba(0,0,0,0.08)`): 下拉菜单、Tooltip、轻微浮动元素。
- **Float High** (`0 8px 32px rgba(0,0,0,0.4)` / 亮色: `0 8px 24px rgba(0,0,0,0.1)`): Modal、Dialog、全屏覆盖层。

亮色模式中阴影更浅、更柔和，因为浅色背景本身已经明亮，不需要深阴影来制造对比。暗色模式中的"发光效果"在亮色模式中替换为"外围阴影"。

### Named Rules

**The Flat-By-Default Rule.** 表面在静止状态下是平的。阴影仅作为状态响应（hover、聚焦、浮动）出现。面板之间的层级关系通过颜色深度表达，而非投影。

## 5. Components

### Buttons
- **Shape:** 圆润的直角，12px 圆角。大按钮用更大圆角，小按钮稍小。
- **Primary (Sakura):** 樱花粉背景 + 白色文字。Hover 时变深 (`#e6758b`)，带轻微上移 (`translateY(-1px)`) 和 glow 扩散。过渡 0.2s ease-out。
- **Secondary (Outlined):** 透明背景 + 1px 边框（暗色: `night-border` / 亮色: `light-border`）。Hover 时边框和文字变为樱花粉。
- **Ghost:** 无背景无边框。Hover 时出现卡片色背景（暗色: `night-card` / 亮色: `light-panel`）。
- **Disabled:** 不透明度 40%，不触发任何交互态。
- **Light mode 注意:** Primary 按钮保持樱花粉 + 白色文字不变。Glow 效果在亮色模式中减弱（小一号的光晕），避免显得过度。

### Inputs / Fields
- **Style:** `night-deep` 背景 + 1px `night-border` 描边（暗色）/ `light-bg` 背景 + 1px `light-border` 描边（亮色）。8px 圆角。内部 10px 14px 内边距。
- **Focus:** 边框变为樱花粉 + 外围 2px 半透明樱花粉光晕（暗色: `rgba(255,139,160,0.19)` / 亮色: `rgba(255,139,160,0.25)`）。出框即失。
- **Placeholder:** `text-muted` 色（暗色: `#58587a` / 亮色: `#a8a4b8`）。
- **Error:** 边框变为 `error-red`，下方显示红色错误提示文字。
- **Disabled:** 不透明度 40%，`text-muted` 文字。

### Cards / Containers
- **Corner Style:** 12px 圆角 (`rounded.lg`)。
- **Background:** 暗色 `night-card` / 亮色 `light-card`（白色）。
- **Border:** 1px（暗色: `night-border` / 亮色: `light-border`）。选中态边框变为樱花粉。
- **Shadow Strategy:** 无默认阴影。需要浮动时使用 Float Low（亮色模式使用更柔和的阴影 `0 2px 8px rgba(0,0,0,0.08)`）。
- **Internal Padding:** 24px（大卡片）/ 16px（紧凑卡片）。

### Navigation
- **Style:** 透明背景，使用 label 字重。选中项以樱花粉文字 + 底部细线指示。
- **Hover:** 文字变为 `text-primary`。
- **Mobile:** 折叠式汉堡菜单，展开时半屏覆盖层 + 从右侧滑入。
- **Light mode:** 选中指示线保持樱花粉不变，背景微调为 `light-panel`。

### Dialogue Box (Player)
- **Position:** 固定在屏幕底部。暗色模式使用从底部向上的深色渐变；亮色模式使用向上的暖白渐变。
- **Dark:** 从底部向上渐变过渡 (gradient-to-top from `night-deep`/95 via `night-deep`/90 to transparent)，文字白色。
- **Light:** 从底部向上渐变过渡 (gradient-to-top from `light-bg`/95 via `light-bg`/90 to transparent)，文字为 `light-text-primary`。
- **Character Name:** 衬线字族，用角色专属色显示。两套模式下角色色值相同。
- **Text:** 正文体，1.7 行高，逐字打字机效果。未完成时右侧有闪烁光标 `▌`（樱花粉）。
- **Max Width:** 65-75ch，居中。
- **Continue Indicator:** 文字展示完成后，底部显示微弱的脉冲提示。

### Choice Panel (Player)
- **Style:** 选项以卡片背景 + 1px 边框显示，12px 圆角。每个选项独占一行。
- **Dark:** `night-card` 背景 + `night-border` 边框。
- **Light:** `light-card` 背景 + `light-border` 边框。
- **Hover:** 边框变为樱花粉，背景微亮。可点击整行。
- **Selected:** 选项被选中后（如果展示后选结果）变为樱花粉背景 + 白色文字（两套模式一致）。

### Node Card (Editor)
- **Style:** 面板背景（暗色: `night-panel` / 亮色: `light-panel`），左侧 4px 彩色边框表示节点类型（对话=粉、旁白=绿、选项=橙、过渡=黄、结局=红）。
- **Header:** 行内显示节点类型标签和 ID，右侧有上下移动和删除按钮。
- **Expanded:** 展开后显示详情编辑区，以 1px 边框分隔（暗色: `night-border` / 亮色: `light-border`）。
- **Selected:** 外围 1px 樱花粉 ring 光晕。

### Progress Bar
- **Style:** 全宽 track（暗色: `night-deep` / 亮色: `light-panel`），8px 圆角，4px 高度。
- **Fill:** 樱花粉渐变，圆角与 track 一致。
- **Indeterminate:** 解析进行中时，fill 宽度 2/3 并带脉冲动画。
- **Label:** 上方左对齐显示状态文字，右对齐可选附加信息（"Processing..."）。

### Scene Tree (Editor)
- **Style:** 简单列表，场景标题为 `text-primary`，行高 36px。选中场景以卡片背景 + 左侧 2px 樱花粉竖条指示（暗色: `night-card` / 亮色: `light-card`）。
- **Count Badge:** 场景数量以 `text-muted` 小字显示在标题旁。

### Theme Toggle
- **Position:** 固定在页面右上角或导航栏末端。
- **Visual:** 使用图标按钮，暗色模式显示太阳图标（点击切换到亮色），亮色模式显示月亮图标（点击切换到暗色）。
- **Style:** Ghost 按钮样式，hover 时出现背景。
- **Transition:** 主题切换时使用 `300ms ease-out-expo` 过渡，所有可过渡属性（背景、文字色、边框色）平滑变化。
- **Persistence:** 用户选择存入 localStorage，新会话自动恢复。

## 6. Do's and Don'ts

### Do:
- **Do** 使用樱花粉作为唯一的情感色锚点，金色只作为极少量点缀。
- **Do** 使用衬线字体（Noto Serif SC）展示角色名和标题，无衬线字体展示正文。
- **Do** 在深色背景上使用半透明渐变叠加层确保文字可读性。
- **Do** 为每个页面编排一个有节制的动效：页面入场渐入、元素依次出现、粒子系统作为背景层。
- **Do** 在工具 UI（编辑器、上传页）中保持樱花粉的克制使用，避免干扰功能性。
- **Do** 在播放器全屏模式下最大化沉浸感 — 隐藏所有非必要 UI 元素。
- **Do** 使用颜色明度分层（暗色: night-deep → night-panel → night-card / 亮色: light-bg → light-panel → light-card）来表达层级，而非投影。
- **Do** 在亮色模式中减弱发光效果（glow/sakura-glow），替换为柔和的阴影或减小 glow 半径。
- **Do** 提供主题切换动画：使用 300ms ease-out-expo 过渡所有颜色属性，用户切换时看到平滑的暗→亮过渡。可以考虑在切换瞬间添加一个微妙的圆形扩散遮罩动效。
- **Do** 将用户主题选择持久化到 localStorage，新会话自动恢复。

### Don't:
- **Don't** 使用纯白色 (`#ffffff`) 或纯黑色 (`#000000`) — 暗色模式基底是 `#0a0a10`，亮色模式基底是 `#faf5f0`。
- **Don't** 使用玻璃拟态（backdrop-blur 作为默认样式）。
- **Don't** 使用渐变文字（background-clip: text + gradient）。
- **Don't** 在卡片左侧使用超过 1px 的彩色竖条作为装饰性边框 — NodeCard 的 4px 彩色边框是功能性的类型标识，不是装饰。
- **Don't** SaaS Dashboard 风格 — 没有大数字指标、没有数据表格作为主页、没有侧边栏导航图表。
- **Don't** 在同一页面使用多个发光源 — 遵循 One-Glow 规则。亮色模式中，glow 应减弱而非增强。
- **Don't** 使用弹跳动画或弹性缓动 — 所有动效使用 exponential ease-out。
- **Don't** 嵌套卡片 — 卡片不应该嵌套在其他卡片中。
- **Don't** 在编辑器中使用模态框作为第一选择 — 优先使用行内展开编辑。
- **Don't** 在亮色模式中使用暗色模式的粒子/发光效果 — 亮色将发光粒子替换为轻微投射阴影的普通粒子。
- **Don't** 主题切换时只切换背景色而不切换文字色 — 所有 color token 必须成对切换。
