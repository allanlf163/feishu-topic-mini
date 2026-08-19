# 部署到 Cloudflare Workers（无信用卡方案）

> 适合：不想绑信用卡、又想要一个**固定不变**的手机提交地址。
> 优点：注册只需邮箱，**不用信用卡**；自动给固定子域 `https://你的名字.workers.dev`；免费额度每日 10 万次请求；零冷启动。
> 缺点：Cloudflare 国内访问偶尔偏慢（比临时隧道稳定得多，但偶尔要等一两秒）。

本项目有两套部署方案：
- `DEPLOY-RENDER.md`：Render 云（需要信用卡 $1 验证，会退还）
- 本文件：Cloudflare Workers（**无信用卡**，推荐）

---

## 第 1 步：注册 Cloudflare（免费，只需邮箱）

1. 浏览器打开 👉 https://workers.cloudflare.com （或 https://dash.cloudflare.com/sign-up）
2. 点 **Sign Up**，用你的邮箱 + 设密码注册
3. 去邮箱点验证链接激活账号

> 全程不需要填任何卡号。

## 第 2 步：设置你的 workers.dev 子域

1. 登录后进入控制台，左侧点 **Workers & Pages**
2. 第一次会让你设一个**子域名前缀**（比如你填 `my-topic`，以后地址就是 `my-topic.workers.dev`）
3. 这个前缀只能设一次，想好再填（英文/数字/横线）

## 第 3 步：新建 Worker 并粘贴代码

1. 在 **Workers & Pages** 页面点 **Create** → 选 **Worker**
2. 起个名字（比如 `feishu-topic-mini`），点 **Deploy** 先建一个空 Worker
3. 建好后点 **Edit code**（或 **Quick Edit**）
4. 把左边编辑器里的默认代码**全部删掉**，把本项目 `worker.js` 的**全部内容**粘贴进去
5. 点右上角 **Deploy** 保存

## 第 4 步：填入 4 个飞书密钥（关键）

1. 在 Worker 详情页点 **Settings** → **Variables**
2. 在 **Variables and Secrets** 区域点 **Add variable**，逐个添加下面 4 个：
   - `FEISHU_APP_TOKEN` ＝ `FlJ6b8dCtaZcdzssMLycOTcynEW`
   - `FEISHU_TABLE_ID` ＝ `tbl7pKnANtwTRvzV`
   - `FEISHU_PBT` ＝ `pt-TBp4rDbvvMhTT69ndabTz08xdWJfFMVEZJKrgWqgAQAAAkDBU-RLwPmTPpUK`
     （建议选 **Secret / 加密** 类型，更安全）
   - `PHONE_TOKEN` ＝ `V5ZHTeSpftmKdK88Bzij7pgf`
     （建议选 **Secret / 加密** 类型）
3. 每加一个就 **Save**
4. **改完变量后，回到代码页再点一次 Deploy**，让变量生效

> 这 4 个值也可以从你电脑上的 `feishu-topic-mini/.env` 文件里复制（用记事本打开）。

## 第 5 步：手机打开固定地址

部署完成后，你的固定地址就是：

```
https://<你第2步设的前缀>.workers.dev/submit
```

把这个地址在手机浏览器打开，按页面提示操作即可：
1. 小红书/抖音点「分享」→「复制链接」
2. 回到该页面，**长按输入框** → 选「粘贴」
3. 点「发送」
4. 看到「✓ 收录成功」就完成，去飞书表刷新即可看到

> 建议：手机浏览器把 `/submit` 页面「添加到主屏幕」，以后像 App 一样点开。

---

## 想用 Git 部署（进阶，可选）

如果你习惯用 GitHub 管理代码，也可以：
1. 把本项目的 `worker.js` 推到 GitHub（参考 `DEPLOY-RENDER.md` 里的仓库 `allanlf163/feishu-topic-mini`）
2. 在 Cloudflare Workers 里 **Create** → 选 **Import from Git** → 连仓库 → 选 `worker.js`
3. 变量仍要在控制台 Settings → Variables 里填一次

## 常见问题

- **页面打不开 / 超时**：Cloudflare 节点偶尔被墙，多刷新几次；若长期不稳，可回到本地 `tunnel.bat` 临时隧道方案。
- **显示「授权失败」**：说明 `PHONE_TOKEN` 变量没填或填错，回去第 4 步核对。
- **显示「飞书写入失败」**：检查 `FEISHU_APP_TOKEN / FEISHU_TABLE_ID / FEISHU_PBT` 三个是否复制完整、无空格。
- **改了代码不生效**：每次改完都要点 **Deploy**；改了变量也要重新 Deploy 一次。
