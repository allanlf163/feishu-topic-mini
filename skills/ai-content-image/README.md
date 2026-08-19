# AI 配图 Skill

面向内容创作者和学员的 AI 配图 skill。它帮助 AI 在生成公众号、小红书、文章插图、封面图和笔记本风格配图时，先理解业务和平台，再规划画面与文字，最后调用 AI 生图工具生成图片。

这个 skill 只做 AI 生图流程：

- 不做网络搜图。
- 不下载图片。
- 不判断版权授权。
- 不用 HTML/CSS/SVG/canvas/PIL 生成最终图片。
- 最终图片必须由 AI 生图工具生成。

文档面向中国区学员，主体说明使用中文表达；少量英文只作为 prompt 中的视觉关键词辅助使用。

## 适合谁

- 想用 AI 生成公众号头图、正文插图的创作者。
- 想把文章转成小红书封面和图文轮播的运营者。
- 想把课程、复盘、方法论做成笔记风格配图的学员。
- 想让 AI 记住自己业务、审美和平台偏好的内容团队。
- 想基于一个标准范式继续扩展自定义配图风格的用户。

## 支持入口

| 入口 | 用途 |
|---|---|
| `/AI生图` | 通用 AI 生图 |
| `/公众号配图` | 公众号头图、正文插图、一组文章配图 |
| `/小红书配图` | 小红书封面、图文卡片、轮播组图 |
| `/AI文章插图` | 文章正文解释图、概念图、流程图感插图 |
| `/AI封面图` | 公众号、小红书或通用封面图 |
| `/笔记本风格` | 内置示例风格，可叠加到公众号、小红书和通用文章配图 |

组合示例：

```text
/小红书配图 笔记本风格
```

```text
/公众号配图 笔记本风格
```

## 核心能力

- 先读长期记忆，再判断用户业务、平台和审美偏好。
- 先输出配图规划，再调用 AI 生图。
- 内置完整 AI 生图规范：prompt 结构、文字策略、风格锁、失败重试、QA 检查。
- 适配公众号和小红书的比例、文字密度和平台感。
- 支持品牌一致性、参考图使用、真实性和隐私边界。
- 支持通过 `memory.md` 沉淀用户长期偏好。
- 支持继续扩展自定义风格，例如黑板报风格、课程讲义风格、手账风格。

## 标准流程

AI 使用这个 skill 时，会按下面流程执行：

1. 读取 `memory.md`，了解用户业务和偏好。
2. 判断平台：公众号、小红书、通用文章或其他用途。
3. 判断产物：头图、正文插图、封面、单张图、轮播图或多张系列图。
4. 判断风格：默认平台风格、`/笔记本风格` 或其他自定义风格。
5. 先给配图规划表，写清每张图的用途、画面文字、视觉方案和尺寸。
6. 用户确认后调用 AI 生图工具。
7. 按 QA 清单检查比例、文字、平台感、风格一致性和安全边界。
8. 展示成功图片，并在必要时更新长期记忆。

## 仓库结构

仓库根目录就是 skill 根目录。安装时不要再额外套一层文件夹。

```text
ai-content-image/
├── SKILL.md
├── README.md
├── memory.md
├── agents/
│   └── openai.yaml
└── references/
    ├── workflow.md
    ├── imagegen-spec.md
    ├── platform-wechat.md
    ├── platform-xiaohongshu.md
    ├── prompt-presets.md
    ├── custom-styles.md
    └── qa-checklist.md
```

## 文件说明

- `SKILL.md`：AI 调用这个 skill 时首先读取的入口。
- `memory.md`：长期记忆模板，用来记录用户业务、平台偏好和配图审美。
- `agents/openai.yaml`：Codex UI 展示信息。
- `references/workflow.md`：标准执行流程。
- `references/imagegen-spec.md`：完整 AI 生图规范，包含 prompt 契约、文字策略、风格锁、失败重试和生成记录。
- `references/platform-wechat.md`：公众号头图和正文插图规则。
- `references/platform-xiaohongshu.md`：小红书封面和图文轮播规则。
- `references/prompt-presets.md`：公众号、小红书、笔记本风格等 prompt 预设。
- `references/custom-styles.md`：自定义风格注册方式，内置 `/笔记本风格` 示例。
- `references/qa-checklist.md`：出图后的检查清单。

## 安装位置

如果没有设置 `CODEX_HOME`，最终路径应该是：

```text
~/.codex/skills/ai-content-image/SKILL.md
```

如果设置了 `CODEX_HOME`，最终路径应该是：

```text
$CODEX_HOME/skills/ai-content-image/SKILL.md
```

不要安装成下面这些嵌套结构：

```text
~/.codex/skills/ai-content-image/ai-content-image/SKILL.md
~/.codex/skills/ai-content-image-main/ai-content-image/SKILL.md
~/.codex/skills/配图/ai-content-image/SKILL.md
```

## 让 AI 帮你安装

把下面这段发给你的本地 AI 工具：

```text
请帮我把这个 GitHub 仓库安装为 Codex skill。

要求：
1. 最终 skill 路径必须是 ~/.codex/skills/ai-content-image/SKILL.md
2. 如果 CODEX_HOME 已设置，则安装到 $CODEX_HOME/skills/ai-content-image/SKILL.md
3. 不要嵌套文件夹，不要出现 ai-content-image/ai-content-image/SKILL.md
4. 如果下载的是 zip，解压后只复制仓库根目录里的内容到目标 skill 目录
5. 安装后检查 SKILL.md、memory.md、references/ 是否都在 ai-content-image 目录第一层
6. 安装完成后告诉我最终路径
```

## 手动安装

在仓库根目录，也就是能看到 `SKILL.md` 的目录中执行：

```bash
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILLS_DIR/ai-content-image"
rsync -av --exclude ".git" ./ "$SKILLS_DIR/ai-content-image/"
test -f "$SKILLS_DIR/ai-content-image/SKILL.md"
test -f "$SKILLS_DIR/ai-content-image/memory.md"
test -d "$SKILLS_DIR/ai-content-image/references"
```

如果最后三个 `test` 命令没有报错，说明安装位置正确。

## 使用示例

### 公众号配图

```text
/公众号配图
请根据这篇文章，先规划一张公众号头图和两张正文插图。
```

### 小红书图文

```text
/小红书配图
把这篇文章转成 5 张小红书图文卡片，先给我规划。
```

### 笔记本风格

```text
/笔记本风格
把这个知识点做成一张小红书 3:4 手写笔记图。
```

### 封面图

```text
/AI封面图
为这个课程主题生成一张适合小红书的封面，先给我 3 个方向。
```

## 长期记忆

`memory.md` 用来记录用户的业务情况和配图偏好。建议只记录长期稳定的信息，例如：

- 用户做什么业务。
- 内容主要发在哪些平台。
- 喜欢什么风格、颜色、文字密度。
- 公众号和小红书分别偏好的图像气质。
- 是否允许使用 logo、人物或产品参考图。
- 自定义风格入口和固定规则。

不要把 API key、账号密码、私密链接、客户资料或临时需求写入长期记忆。

## 使用边界

这个 skill 会避免生成容易误导读者的图片，例如：

- 假聊天记录。
- 假转账截图。
- 假后台数据。
- 假平台通知。
- 假媒体报道。
- 假证书、假奖项、假认证。
- 未授权的真实人物背书。

如果需要表达类似场景，应该改成示意图、流程图、抽象图、虚构样例或脱敏表达。

## 验证安装

安装后，可以让 AI 执行一次：

```text
请使用 $ai-content-image，根据一个关于“知识付费课程复盘”的主题，先规划一张公众号头图，不要生成图片。
```

如果 AI 能读取 skill、先做规划、并体现公众号头图规则，说明安装基本成功。
