// feishu-topic-mini · Cloudflare Workers 版（无卡 / 固定地址 / 零冷启动）
//
// 功能与本地 Python 版完全一致：手机浏览器打开 /submit → 粘贴小红书/抖音链接 →
// 点发送 → 本 Worker 直接把链接写进你的飞书多维表格。
//
// 为什么用 Cloudflare Workers：
//   - 注册只需邮箱，【无需信用卡】
//   - 自动给固定子域 https://<你的子域>.workers.dev（永久不变）
//   - 免费额度每日 10 万次请求，足够个人使用；零冷启动
//   - 能自由访问飞书 API（base-api.feishu.cn），不受白名单限制
//
// 部署见 DEPLOY-CLOUDFLARE-WORKERS.md。4 个密钥在 Cloudflare 控制台
// 「Workers → 你的 Worker → Settings → Variables」里填：
//   FEISHU_APP_TOKEN / FEISHU_TABLE_ID / FEISHU_PBT / PHONE_TOKEN

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    try {
      if (request.method === "GET") {
        if (path === "/submit" || path === "/submit/") {
          return html(submitPage(env.PHONE_TOKEN));
        }
        if (path === "/" || path === "") {
          return html(rootPage());
        }
        if (path === "/health") {
          return json({ ok: true, service: "feishu-topic-mini", runtime: "cloudflare-workers" });
        }
        return json({ ok: false, message: "not found" }, 404);
      }

      if (request.method === "POST" && path === "/api/topic-link/submit") {
        return await handleSubmit(request, env);
      }

      return json({ ok: false, message: "method not allowed" }, 405);
    } catch (e) {
      return json({ ok: false, message: "server error: " + e.message }, 500);
    }
  }
};

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate"
    }
  });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" }
  });
}

async function handleSubmit(request, env) {
  // 1) 读表单：支持 form-urlencoded（手机原生表单）与 JSON
  let content = "";
  let token = "";
  const ctype = (request.headers.get("Content-Type") || "").toLowerCase();
  if (ctype.includes("application/json")) {
    try {
      const data = await request.json();
      content = data.content || "";
      token = data.token || "";
    } catch (_) { /* ignore */ }
  } else {
    try {
      const form = await request.formData();
      content = form.get("content") || "";
      token = form.get("token") || "";
    } catch (_) {
      content = await request.text();
    }
  }

  // 2) 鉴权
  if (env.PHONE_TOKEN && token !== env.PHONE_TOKEN) {
    return html(resultPage(false, "授权失败：手机授权码无效"), 401);
  }

  // 3) 校验内容
  content = (content || "").trim();
  if (!content) {
    return html(resultPage(false, "没收到内容：请先把链接长按粘贴到框里，再点发送"), 400);
  }

  // 4) 提取链接
  const link = extractUrl(content);
  if (!link) {
    return html(resultPage(false, "没识别到链接：请把小红书/抖音的分享链接粘贴到框里再发送"), 400);
  }
  if (!isSafe(link)) {
    return html(resultPage(false, "不支持内部/本地链接"), 400);
  }

  // 5) 写飞书（秒回，不卡采集）
  let recId = null;
  try {
    const api = "https://base-api.feishu.cn/open-apis/bitable/v1/apps/" +
      env.FEISHU_APP_TOKEN + "/tables/" + env.FEISHU_TABLE_ID + "/records";
    const resp = await fetch(api, {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + env.FEISHU_PBT,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ fields: { "内容链接": link, "整理情况": "空" } })
    });
    const data = await resp.json();
    if (data.code !== 0) {
      return html(resultPage(false, "飞书写入失败：" + (data.msg || JSON.stringify(data))), 502);
    }
    recId = (data.data && data.data.record && data.data.record.record_id) || null;
  } catch (e) {
    return html(resultPage(false, "飞书请求异常：" + e.message), 502);
  }

  return html(resultPage(true, "已成功收录到选题表", recId), 200);
}

function extractUrl(text) {
  const m = (text || "").match(/https?:\/\/[^\s"'<>]+/);
  if (!m) return null;
  return m[0].replace(/[)\]]+$/, "");
}

function isSafe(u) {
  try {
    const host = new URL(u).hostname;
    return !/^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.)/.test(host);
  } catch (_) {
    return false;
  }
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function rootPage() {
  return `<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>飞书选题库服务</title><style>
body{font-family:-apple-system,system-ui,"PingFang SC",sans-serif;background:#f7f5f2;margin:0;padding:40px 24px;color:#2b2b2b;text-align:center}
.card{background:#fff;border-radius:16px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:480px;margin:0 auto}
h1{font-size:20px;margin:0 0 8px}
p{font-size:14px;color:#666;line-height:1.7}
a{color:#ff7a45;font-weight:600;text-decoration:none}
code{background:#f0f0f0;padding:2px 6px;border-radius:4px}
</style></head>
<body><div class="card">
<h1>飞书选题库服务运行中</h1>
<p>手机端请打开：<a href="/submit">/submit 收录页面</a></p>
<p>接口：<code>POST /api/topic-link/submit</code></p>
</div></body></html>`;
}

function submitPage(token) {
  return `<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>收录到选题表</title>
<style>
  body{font-family:-apple-system,system-ui,"PingFang SC","Microsoft YaHei",sans-serif;background:#f7f5f2;margin:0;padding:24px;color:#2b2b2b}
  .card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:480px;margin:0 auto}
  h1{font-size:20px;margin:0 0 4px}
  .sub{color:#888;font-size:13px;margin:0 0 16px}
  textarea{width:100%;height:130px;box-sizing:border-box;border:1px solid #ddd;border-radius:10px;padding:12px;font-size:15px;resize:vertical}
  button{width:100%;margin-top:12px;padding:14px;border:0;border-radius:10px;background:#ff7a45;color:#fff;font-size:16px;font-weight:600;cursor:pointer}
  button:active{opacity:.85}
  .steps{font-size:13px;color:#555;line-height:1.9;margin:16px 0 0;padding-left:20px}
  .steps b{color:#ff7a45}
  #hint{margin-top:12px;font-size:13px;color:#b86b00;min-height:18px}
  .ok{color:#1a9d4b;font-weight:600}
</style>
</head>
<body>
<div class="card">
  <h1>收录到选题表</h1>
  <p class="sub">先把链接粘贴到下面框里，再点「发送」</p>
  <form id="f" method="POST" action="/api/topic-link/submit">
    <input type="hidden" name="token" value="${token}">
    <textarea name="content" id="content" placeholder="长按这里 → 粘贴，把小红书/抖音链接贴进来"></textarea>
    <button type="submit" id="sendBtn">发送</button>
  </form>
  <div id="hint"></div>
  <ol class="steps">
    <li>在小红书/抖音点「分享」→「复制链接」</li>
    <li>回到本页，<b>长按上面的框</b>，选「粘贴」</li>
    <li>点「发送」</li>
    <li>看到「✓ 收录成功」就完成，去飞书表里看</li>
  </ol>
</div>
<script>
(function(){
  var box = document.getElementById("content");
  var btn = document.getElementById("sendBtn");
  var hint = document.getElementById("hint");
  if(navigator.clipboard && navigator.clipboard.readText){
    navigator.clipboard.readText().then(function(t){
      if(t && t.trim()){ box.value = t.trim(); hint.innerHTML = '<span class="ok">已从剪贴板自动填入，点发送即可</span>'; }
    }).catch(function(){});
  }
  btn.addEventListener("click", function(e){
    if(!box.value.trim()){
      e.preventDefault();
      hint.textContent = "框里是空的，请先长按框 → 粘贴链接，再点发送";
    }
  });
})();
</script>
</body>
</html>`;
}

function resultPage(ok, message, recId) {
  const title = ok ? "✓ 收录成功" : "✗ 收录失败";
  const color = ok ? "#1a9d4b" : "#d23";
  const ridLine = (ok && recId) ? `<p>记录ID：<code>${esc(recId)}</code></p>` : "";
  return `<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title><style>
body{font-family:-apple-system,system-ui,"PingFang SC",sans-serif;background:#f7f5f2;margin:0;padding:24px;color:#2b2b2b}
.card{background:#fff;border-radius:16px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:480px;margin:40px auto;text-align:center}
h1{color:${color};font-size:24px;margin:0 0 12px}
p{font-size:15px;line-height:1.7;word-break:break-all}
code{background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:13px}
a{color:#ff7a45;font-weight:600;text-decoration:none}
</style></head>
<body><div class="card"><h1>${esc(title)}</h1><p>${esc(message)}</p>${ridLine}<p><a href="/submit">← 再收录一条</a></p></div></body></html>`;
}
