#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书选题库 · 精简版服务（零依赖，仅用 Python 标准库）

链路：手机快捷指令 POST -> 本服务先把"链接"写入飞书多维表格 -> 后台线程异步补全 标题/作者/封面/类型

运行：
    python app.py              # 启动服务（默认 0.0.0.0:18182）
    python app.py setup        # 连接飞书，自动补全标准字段（内容链接/标题/作者/封面/类型/整理情况）
"""

import os
import sys
import json
import re
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 短视频转写相关（无 key 时整体禁用，不影响主链路）
import asr as _asr
import media as _media

# ----------------------------------------------------------------------------
# 配置：优先读环境变量，其次读同目录 .env
# ----------------------------------------------------------------------------
def load_env(path=".env"):
    cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


_ENV = load_env()


def cfg(key, default=""):
    return os.environ.get(key, _ENV.get(key, default))


PORT = int(cfg("PORT", "18182"))
PHONE_TOKEN = cfg("PHONE_TOKEN", "")          # 手机快捷指令鉴权用（自己设的一串随机字符）
FEISHU_APP_TOKEN = cfg("FEISHU_APP_TOKEN", "")  # 飞书表链接里的 app_token
FEISHU_TABLE_ID = cfg("FEISHU_TABLE_ID", "")    # 飞书表链接里的 table_id
FEISHU_PBT = cfg("FEISHU_PBT", "")            # 飞书 Personal Base Token（t-/pt- 开头）
FEISHU_DOMAIN = cfg("FEISHU_DOMAIN", "base-api.feishu.cn")  # 海外填 base-api.larksuite.com
ENABLE_ENRICH = cfg("ENABLE_ENRICH", "true").lower() in ("1", "true", "yes", "on")

# 短视频转写（ASR）：默认关闭，需配置 ASR_API_KEY 才启用
ENABLE_ASR = cfg("ENABLE_ASR", "false").lower() in ("1", "true", "yes", "on")
ASR_API_KEY = cfg("ASR_API_KEY", "")
ASR_BASE_URL = cfg("ASR_BASE_URL", "https://api.openai.com/v1")
ASR_MODEL = cfg("ASR_MODEL", "whisper-1")
asr_client = None
if ENABLE_ASR and ASR_API_KEY:
    asr_client = _asr.OpenAICompatibleASR(ASR_API_KEY, ASR_BASE_URL, ASR_MODEL)


# ----------------------------------------------------------------------------
# 飞书多维表格客户端
# ----------------------------------------------------------------------------
def _feishu_req(method, path, body=None):
    url = "https://%s/open-apis/bitable/v1%s" % (FEISHU_DOMAIN, path)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer %s" % FEISHU_PBT)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"code": -1, "msg": "HTTP %s" % e.code}
    except Exception as e:  # noqa: BLE001
        return {"code": -1, "msg": str(e)}


def feishu_create_record(content_link):
    path = "/apps/%s/tables/%s/records" % (FEISHU_APP_TOKEN, FEISHU_TABLE_ID)
    body = {"fields": {"内容链接": content_link, "整理情况": "空"}}
    return _feishu_req("POST", path, body)


def feishu_update_record(record_id, fields):
    path = "/apps/%s/tables/%s/records/%s" % (FEISHU_APP_TOKEN, FEISHU_TABLE_ID, record_id)
    return _feishu_req("PUT", path, {"fields": fields})


def feishu_ensure_fields():
    """确保标准字段存在。仅创建有把握的类型：1=文本 3=单选 4=多选。"""
    path = "/apps/%s/tables/%s/fields" % (FEISHU_APP_TOKEN, FEISHU_TABLE_ID)
    resp = _feishu_req("GET", path)
    existing = {f.get("field_name") for f in resp.get("data", {}).get("items", [])}
    want = [
        ("内容链接", 1, None),
        ("标题", 1, None),
        ("作者", 1, None),
        ("封面", 1, None),  # 以链接文本存储，规避附件类型号不确定性
        ("类型", 4, ["小红书", "抖音", "公众号", "X", "图文", "短视频", "其他"]),
        ("短视频文案", 1, None),
        ("整理情况", 3, ["空", "已整理", "已完成", "需手动提供视频音频", "转写失败"]),
    ]
    created = []
    for name, ftype, options in want:
        if name in existing:
            continue
        body = {"field_name": name, "type": ftype}
        if options:
            body["property"] = {"options": [{"name": o} for o in options]}
        r = _feishu_req("POST", path, body)
        if r.get("code") == 0:
            created.append(name)
        else:
            print("  ! 创建字段 [%s] 失败: %s" % (name, r.get("msg", r)))
    return created


# ----------------------------------------------------------------------------
# 内容采集（尽力而为，失败不影响链接入库）
# ----------------------------------------------------------------------------
_PRIVATE = re.compile(r"(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.)", re.I)


def extract_url(text):
    m = re.search(r"https?://[^\s\"'<>]+", text or "")
    return m.group(0).rstrip(")") if m else None


def _safe_url(u):
    if _PRIVATE.search(u.split("/")[2] if "//" in u else u):
        return False
    return True


def fetch_meta(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent",
                   "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read(2000000).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return {}

    def og(prop):
        m = re.search(r'<meta[^>]+property=["\']og:%s["\'][^>]+content=["\']([^"\']+)' % prop,
                      html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:%s["\']'
                          % prop, html, re.I)
        return m.group(1).strip() if m else ""

    title = og("title")
    if not title:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        title = m.group(1).strip() if m else ""
    author = og("author") or og("site_name")
    cover = og("image") or og("image:secure_url")
    return {"title": title, "author": author, "cover": cover}


def detect_platform(url):
    u = url.lower()
    if "xiaohongshu.com" in u or "xhslink.com" in u:
        return "小红书"
    if "douyin.com" in u or "iesdouyin.com" in u:
        return "抖音"
    if "mp.weixin.qq.com" in u:
        return "公众号"
    if "x.com" in u or "twitter.com" in u:
        return "X"
    return "其他"


def enrich(record_id, url):
    try:
        if not _safe_url(url):
            return
        info = fetch_meta(url)
        fields = {}
        if info.get("title"):
            fields["标题"] = info["title"][:200]
        if info.get("author"):
            fields["作者"] = info["author"][:100]
        if info.get("cover"):
            fields["封面"] = info["cover"]
        ptype = detect_platform(url)
        if ptype:
            fields["类型"] = [ptype]

        # 短视频转写（抖音/小红书）：下载音频 -> ASR -> 写「短视频文案」
        if asr_client and ptype in ("抖音", "小红书"):
            try:
                audio_path = _media.download_audio(url)
                if audio_path:
                    text = asr_client.transcribe_file(audio_path)
                    if text:
                        fields["短视频文案"] = text[:4000]
                        fields["整理情况"] = "已整理"
                    else:
                        fields["整理情况"] = "转写失败"
                else:
                    fields["整理情况"] = "需手动提供视频音频"
            except Exception:  # noqa: BLE001
                fields["整理情况"] = "转写失败"

        if fields:
            fields.setdefault("整理情况", "已整理")
            feishu_update_record(record_id, fields)
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------------
# HTTP 处理
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code, html):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p == "/health":
            return self._send(200, {"ok": True, "service": "feishu-topic-mini",
                                    "version": "0.2.0",
                                    "features": {"enrich": ENABLE_ENRICH,
                                                 "asr": asr_client is not None}})
        if p == "/submit":
            return self._send_html(200, SUBMIT_HTML)
        if p in ("", "/"):
            return self._send_html(200, ROOT_HTML)
        self._send(404, {"ok": False, "message": "not found"})



    def do_POST(self):
        if self.path.split("?")[0].rstrip("/") != "/api/topic-link/submit":
            return self._send(404, {"ok": False, "message": "not found"})

        # 1) 读正文（支持 application/json / form-urlencoded / text/plain）
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = (self.headers.get("Content-Type", "") or "").lower()
        form_wants_html = False
        token = ""
        content = ""
        if "application/json" in ctype:
            try:
                data = json.loads(raw.decode("utf-8", "ignore"))
                content = data.get("content") if isinstance(data, dict) else str(data)
                token = (data.get("token") or "") if isinstance(data, dict) else ""
            except Exception:
                content = raw.decode("utf-8", "ignore")
        elif "application/x-www-form-urlencoded" in ctype:
            from urllib.parse import parse_qs
            form_wants_html = True
            try:
                parsed = parse_qs(raw.decode("utf-8", "ignore"))
                content = (parsed.get("content") or [""])[0]
                token = (parsed.get("token") or [""])[0]
            except Exception:
                content = raw.decode("utf-8", "ignore")
        else:
            content = raw.decode("utf-8", "ignore")

        # 2) 鉴权：优先 Bearer，其次表单 token，再次 GET ?token=
        auth = self.headers.get("Authorization", "")
        m = re.match(r"Bearer\s+(.+)", auth)
        if m:
            token = m.group(1).strip()
        else:
            import urllib.parse as _up
            qs = _up.urlparse(self.path).query
            token = (dict(_up.parse_qsl(qs)).get("token") or token or "").strip()
        if not PHONE_TOKEN or token != PHONE_TOKEN:
            if form_wants_html:
                return self._send_html(401, self._result_page(False, "授权失败：手机授权码无效"))
            return self._send(401, {"ok": False, "message": "授权失败：手机授权码无效"})

        if not content:
            msg = "没收到内容：请先把链接长按粘贴到框里，再点发送"
            if form_wants_html:
                return self._send_html(400, self._result_page(False, msg))
            return self._send(400, {"ok": False, "message": msg})

        # 3) 提取链接
        url = extract_url(content)
        if not url:
            msg = "没识别到链接：请把小红书/抖音的分享链接粘贴到框里再发送"
            if form_wants_html:
                return self._send_html(400, self._result_page(False, msg))
            return self._send(400, {"ok": False, "message": msg})
        if not _safe_url(url):
            msg = "不支持内部/本地链接"
            if form_wants_html:
                return self._send_html(400, self._result_page(False, msg))
            return self._send(400, {"ok": False, "message": msg})

        # 4) 先写飞书（秒回，不等采集）
        resp = feishu_create_record(url)
        if resp.get("code") != 0:
            msg = "飞书写入失败：" + str(resp.get("msg", resp))
            if form_wants_html:
                return self._send_html(502, self._result_page(False, msg))
            return self._send(502, {"ok": False,
                                    "message": msg})
        rec = resp.get("data", {}).get("record") or {}
        rid = rec.get("record_id")

        # 5) 后台异步补全
        if ENABLE_ENRICH and rid:
            threading.Thread(target=enrich, args=(rid, url), daemon=True).start()

        if form_wants_html:
            return self._send_html(200, self._result_page(
                True, "已成功收录到选题表", rid))
        self._send(200, {"ok": True, "message": "已成功收录到选题表",
                         "status": "created", "record_id": rid})

        if not content:
            return self._send(400, {"ok": False, "message": "未识别到内容"})

        # 3) 提取链接
        url = extract_url(content)
        if not url:
            return self._send(400, {"ok": False, "message": "未识别到链接，请复制分享内容"})
        if not _safe_url(url):
            return self._send(400, {"ok": False, "message": "不支持内部/本地链接"})

        # 4) 先写飞书（秒回，不等采集）
        resp = feishu_create_record(url)
        if resp.get("code") != 0:
            return self._send(502, {"ok": False,
                                    "message": "飞书写入失败：" + str(resp.get("msg", resp))})
        rec = resp.get("data", {}).get("record") or {}
        rid = rec.get("record_id")

        # 5) 后台异步补全
        if ENABLE_ENRICH and rid:
            threading.Thread(target=enrich, args=(rid, url), daemon=True).start()

        self._send(200, {"ok": True, "message": "已成功收录到选题表",
                         "status": "created", "record_id": rid})

    def log_message(self, *a):  # 静默访问日志
        pass

    @staticmethod
    def _result_page(ok, message, record_id=None):
        title = "✓ 收录成功" if ok else "✗ 收录失败"
        color = "#1a9d4b" if ok else "#d23"
        rid_line = ('<p>记录ID：<code>%s</code></p>' % record_id) if (ok and record_id) else ""
        back = '<p><a href="/submit">← 再收录一条</a></p>'
        return '''<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title><style>
body{font-family:-apple-system,system-ui,"PingFang SC",sans-serif;background:#f7f5f2;margin:0;padding:24px;color:#2b2b2b}
.card{background:#fff;border-radius:16px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08);max-width:480px;margin:40px auto;text-align:center}
h1{color:%s;font-size:24px;margin:0 0 12px}
p{font-size:15px;line-height:1.7;word-break:break-all}
code{background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:13px}
a{color:#ff7a45;font-weight:600;text-decoration:none}
</style></head>
<body><div class="card"><h1>%s</h1><p>%s</p>%s%s</div></body></html>''' % (
            title, color, title, message, rid_line, back)



# 首页（Render 等平台健康检查用，也方便人直接访问根路径）
ROOT_HTML = '''<!DOCTYPE html>
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
</div></body></html>'''

# 手机网页版提交器（安卓/iPhone 通用，浏览器打开即用，无需装 App）
# v5: 先粘贴、再发送 —— 不承诺"自动读剪贴板"（多数安卓浏览器出于隐私会拦截），
#     以手动粘贴为唯一可靠路径；原生表单兜底，JS 仅做"框空时提示"增强，不阻断提交。
SUBMIT_HTML = '''<!DOCTYPE html>
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
    <input type="hidden" name="token" value="__TOKEN__">
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
// 仅在 JS 可用时增强：框为空时提示手动粘贴；若浏览器允许读剪贴板则自动填入。
// 核心提交由原生表单完成，JS 失效也不影响（此时靠服务器端校验给出清晰提示）。
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
</html>'''
SUBMIT_HTML = SUBMIT_HTML.replace("__TOKEN__", PHONE_TOKEN)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        if not (FEISHU_APP_TOKEN and FEISHU_TABLE_ID and FEISHU_PBT):
            print("缺少飞书配置，请先填写 .env：FEISHU_APP_TOKEN / FEISHU_TABLE_ID / FEISHU_PBT")
            sys.exit(1)
        print("正在连接飞书并补全标准字段 ...")
        created = feishu_ensure_fields()
        print("完成。新建字段：%s" % (created or "无（均已存在）"))
        return

    if not (FEISHU_APP_TOKEN and FEISHU_TABLE_ID and FEISHU_PBT):
        print("[警告] 飞书配置未填全（FEISHU_APP_TOKEN/FEISHU_TABLE_ID/FEISHU_PBT），"
              "写表会失败。请先配置 .env")
    if not PHONE_TOKEN:
        print("[警告] PHONE_TOKEN 未设置，所有提交会被 401 拒绝。请在 .env 设一个随机字符串。")
    print("feishu-topic-mini 启动： http://0.0.0.0:%d  (Ctrl+C 停止)" % PORT)
    print("功能开关： 后台补全=%s  短视频转写=%s"
          % (ENABLE_ENRICH, "开启" if asr_client else "关闭(未配 ASR_API_KEY)"))
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
