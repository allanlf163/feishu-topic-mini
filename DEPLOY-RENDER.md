# 部署到 Render 免费云（固定地址，电脑可关机）

目标：把本项目部署到 Render 免费云，得到一个**永远不变**的网址
`https://feishu-topic-mini.onrender.com`（名字可自定义），手机随时打开 `/submit` 就能用，
**不需要你电脑一直开着**，也不用买域名。

---

## 第 1 步：把代码放进一个 GitHub 仓库（不用装 git）

1. 打开 https://github.com ，注册一个免费账号（Sign up）。
2. 右上角 `+` → `New repository`：
   - Repository name 填 `feishu-topic-mini`（随意）
   - 选 `Public` 或 `Private` 都行
   - 点 `Create repository`
3. 在空仓库页面点 `Add file` → `Upload files`，把**下面这些文件**从你电脑拖进去上传
   （文件在你电脑这个目录：`C:\Users\allan\WorkBuddy\2026-08-16-19-18-05\feishu-topic-mini\`）：

   必须上传：
   - `app.py`
   - `asr.py`
   - `media.py`
   - `requirements.txt`
   - `runtime.txt`
   - `Procfile`
   - `render.yaml`

   可选上传：
   - `.env.example`（模板，不含真实密钥）
   - `README.md`

   ⚠️ **千万不要上传 `.env` 文件**（里面是你的飞书密钥和手机令牌）！

4. 拉到最下面点 `Commit changes`。

---

## 第 2 步：用 Render 一键部署

1. 打开 https://render.com ，用 GitHub 账号直接登录（Sign up with GitHub 最方便）。
2. 登录后点 `New` → `Blueprint`（因为仓库里有 `render.yaml`，Render 会自动读懂配置）。
3. 连接你的 GitHub，选中刚才建的 `feishu-topic-mini` 仓库 → 确认创建。
4. 创建好后进入该服务，点 `Environment`（环境变量）：
   把下面 4 项**手动填好**（值从你电脑上的 `.env` 文件里复制，别填错）：

   | Render 变量名        | 填什么（去 `.env` 里找对应的值）        |
   |---------------------|----------------------------------------|
   | `FEISHU_APP_TOKEN`  | `.env` 里的 `FEISHU_APP_TOKEN=` 后面那串 |
   | `FEISHU_TABLE_ID`   | `.env` 里的 `FEISHU_TABLE_ID=` 后面那串  |
   | `FEISHU_PBT`        | `.env` 里的 `FEISHU_PBT=` 后面那串（pt- 开头） |
   | `PHONE_TOKEN`       | `.env` 里的 `PHONE_TOKEN=` 后面那串      |

   > `FEISHU_DOMAIN` / `ENABLE_ENRICH` / `ENABLE_ASR` 已经在 `render.yaml` 里设好了，不用动。
   > `PORT` 由 Render 自动给，也不用管。

5. 填完点 `Save Changes`，然后点 `Deploy` / `Manual Deploy`。
6. 等 1～2 分钟，状态变成 `Live`，页面右上角会显示一个网址，形如
   `https://feishu-topic-mini.onrender.com` —— **这就是你的固定地址**。

---

## 第 3 步：手机上用

- 打开 `https://你的服务名.onrender.com/submit`（把 `你的服务名` 换成实际名字）。
- 以后这个地址**永远不变**。安卓可把它「添加到主屏幕」，像 App 一样点开。
- 用法不变：小红书/抖音「分享→复制链接」→ 长按框「粘贴」→ 点「发送」→ 看「✓ 收录成功」。

---

## 注意事项

- **免费档会休眠**：超过约 15 分钟没人访问，Render 会把它暂停以省资源；下次打开时第一次会慢几秒（自动唤醒），之后正常。这是免费的代价，属正常。
- 如果以后想改代码：在 GitHub 里改文件并 `Commit`，Render 会自动重新部署。
- 想彻底不用电脑、又不要休眠？需要升级 Render 付费档（约 $7/月），非必需。
- 不想用云了？本地仍可用 `start.bat` + `tunnel.bat` 临时隧道方案。
