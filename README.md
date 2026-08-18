# 飞书选题库 · 精简版（手机快捷指令录入飞书素材库）

零依赖的 Python 小服务：手机复制分享链接 → 快捷指令 POST 到本服务 → 先把链接写进你的飞书多维表格 → 后台自动补全标题/作者/封面/类型。

对应教程《快捷指令&飞书选题库同步全流程制作教程》的核心链路，但用一份可自己跑的代码替代了教程里缺失的 `topic-table-service`。

> 说明：本精简版不含 Claude 文案精修、沉淀表同步。短视频 ASR 转写已内置（见「八、短视频转写」），默认关闭，配置 ASR_API_KEY 后启用。

---

## 一、准备飞书多维表格

1. 飞书里新建一个**多维表格**（也可新建一个表），命名如 `当前对标`。
2. 打开该表，从浏览器地址栏复制链接，形如：
   `https://xxx.feishu.cn/base/APP_TOKEN?table=tblXXXXXX&view=vewXXXXXX`
   - `APP_TOKEN` = `/base/` 之后、`?` 之前那段
   - `TABLE_ID` = `table=` 之后那段（`tbl` 开头）
3. 获取飞书 Personal Base Token：飞书 → 多维表格 → 右上「…」→ **获取 Personal Base Token（个性化令牌）**，复制 `t-`/`pt-` 开头的串。**该令牌持有者必须能编辑这张表。**

> 字段不用提前建。配置好 `.env` 后跑一次 `python app.py setup`，会自动建好：内容链接、标题、作者、封面、类型（多选）、整理情况（单选）。

## 二、配置 .env

```bash
cp .env.example .env      # Windows：复制 .env.example 改名为 .env
```

按注释填：`PHONE_TOKEN`（自设随机串）、`FEISHU_APP_TOKEN`、`FEISHU_TABLE_ID`、`FEISHU_PBT`。

## 三、运行

```bash
# 任选一个 Python（3.8+ 即可，无需安装任何第三方包）
python app.py             # 启动服务
python app.py setup       # 首次：连接飞书，自动补全标准字段
```

健康检查：浏览器/终端访问 `http://localhost:18182/health` → `{"ok":true,...}`

## 四、手机快捷指令

1. 新建快捷指令，命名「收录到选题表」。
2. 动作顺序：
   - `获取剪贴板`
   - `获取 URL 内容`
   - `显示通知`
3. 配置「获取 URL 内容」：
   - 方法：**POST**
   - URL：`https://你的域名或IP:18182/api/topic-link/submit`
   - 请求头：`Authorization: Bearer <PHONE_TOKEN>`、`Content-Type: application/json`
   - 请求体（JSON）：`{"content":"<剪贴板变量>"}`
4. 通知：成功显示「已成功收录到选题表」，失败显示「收录失败，请检查链接或授权」。

## 五、让手机能访问（公网/内网）

- 本机调试：手机和电脑同一 Wi-Fi，URL 用电脑局域网 IP（如 `http://192.168.x.x:18182/...`）。
- 真正常用：把服务部署到一台有公网域名的服务器，或用 `cloudflared` / `ngrok` 临时隧道把本地 18182 暴露成 https 域名，再把快捷指令 URL 换成该域名。一键隧道脚本见「七、公网隧道」。

## 六、一键启动 / 开机自启（Windows）

不想每次手动开终端，就用这两个脚本：

1. **双击 `start.bat`** —— 一键启动，崩溃/退出后 5 秒自动重启，日志写进 `service.log`。停止按 `Ctrl+C`。
2. **注册开机自启** —— 右键 `install_service.ps1` →「使用 PowerShell 运行」（或管理员 PowerShell 执行 `powershell -ExecutionPolicy Bypass -File install_service.ps1`）：
   - 用 `pythonw` 后台无窗口运行，登录后自动起，崩溃每分钟重试（最多 3 次）。
   - 任务名 `FeishuTopicMini`，在「任务计划程序 → 任务计划程序库」里可看到/管理。
   - 卸载运行 `uninstall_service.ps1`。

> 想“开机即起、不依赖登录”，把脚本里的 `New-ScheduledTaskTrigger -AtLogOn` 改成 `-AtStartup`，并以管理员身份注册即可。

## 七、公网隧道（让手机从外网访问）

双击 `tunnel.bat`：

- 自动探测本机 `cloudflared` 或 `ngrok`（谁在 PATH 里用谁），把 `http://localhost:18182` 暴露成 https。
- 窗口里会打印一个 `https://*.trycloudflare.com` 或 `https://*.ngrok.io` 地址，把它填进手机快捷指令的 URL。
- 两者都没装会给出下载链接。免费隧道域名每次重启会变，属正常。

> cloudflared 临时隧道免登录；ngrok 免费也能用（随机域名）。要固定域名需各自注册并配 token/命名隧道。

## 八、短视频转写（ASR，默认关闭）

对**抖音 / 小红书**链接，服务可后台下载音频并用语音识别转写成「短视频文案」写进飞书表（新增字段 `短视频文案`）。

配置 `.env`：

```bash
ENABLE_ASR=true
ASR_API_KEY=你的key
# 官方 OpenAI：https://api.openai.com/v1
# 火山方舟示例：https://ark.cn-beijing.volces.com/api/v3
# DeepSeek / 通义 等同理，填各自暴露 /v1/audio/transcriptions 的 base_url
ASR_BASE_URL=https://api.openai.com/v1
ASR_MODEL=whisper-1
```

要点：

- 接口走 OpenAI 兼容规范（`POST {base_url}/audio/transcriptions`），国内兼容服务填各自 `base_url` 即可。
- 抖音/小红书 音频下载依赖 `yt-dlp`（需另装并加入 PATH；部分平台需 `--cookies`）。`yt-dlp` 缺失或下载失败时，「整理情况」会标成「需手动提供视频音频」，不阻断主链路。
- 无 `ASR_API_KEY` 时整体禁用，不影响链接入库与标题/作者/封面补全。

## 九、排错

| 现象 | 排查 |
|---|---|
| 提交 401 | 快捷指令 Header 的 Bearer 值与 `.env` 的 `PHONE_TOKEN` 不一致 |
| 写表 502 | `FEISHU_PBT` 无效/无该表权限，或 `APP_TOKEN`/`TABLE_ID` 填错 |
| 飞书只有链接、没标题 | 后台补全是异步的，等几秒；或 `ENABLE_ENRICH=false` 关了；或链接被平台风控 |
| 启动警告缺配置 | 没填 `.env` 或没 `cp` 成功 |
| 抖音链接「整理情况」=需手动提供视频音频 | 没装 `yt-dlp`，或该平台需 `--cookies`，或下载被风控；可手动把音频喂给 ASR |
| 转写失败 | `ASR_API_KEY`/`ASR_BASE_URL` 错，或音频非语音；看 `service.log` 的 `[ASR]` 日志 |

## 十、一键验证（终端）

```bash
curl -X POST http://localhost:18182/api/topic-link/submit \
  -H "Authorization: Bearer 你的PHONE_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"content":"测试 https://example.com/demo"}'
```

期望：`{"ok":true,"message":"已成功收录到选题表","status":"created",...}`
