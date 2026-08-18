#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音转写客户端（可插拔，零依赖，仅用 Python 标准库）。

默认实现 OpenAI 兼容接口  POST {base_url}/audio/transcriptions ：
  - OpenAI 官方：  ASR_BASE_URL=https://api.openai.com/v1
  - 国内兼容服务（火山方舟 / DeepSeek / 通义 / 智谱 等暴露兼容 transcription 的）：
    填各自 base_url 即可，请求格式一致。

未配置 ASR_API_KEY 时整体禁用，transcribe_* 返回 None，不报错、不阻断主链路。
"""

import json
import urllib.request
import urllib.error


class ASRClient:
    """转写接口（可替换为其他实现）。"""

    def transcribe_file(self, path):
        raise NotImplementedError

    def transcribe_bytes(self, data, filename="audio.mp3"):
        raise NotImplementedError


class OpenAICompatibleASR(ASRClient):
    def __init__(self, api_key, base_url, model):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def transcribe_bytes(self, data, filename="audio.mp3"):
        if not self.api_key:
            return None
        url = self.base_url + "/audio/transcriptions"
        boundary = "----wbboundary7Qk9Xy"
        CRLF = b"\r\n"
        body = b""
        # 文本字段 model
        body += b"--" + boundary.encode() + CRLF
        body += b'Content-Disposition: form-data; name="model"' + CRLF + CRLF
        body += self.model.encode("utf-8") + CRLF
        # 文件字段
        body += b"--" + boundary.encode() + CRLF
        body += ('Content-Disposition: form-data; name="file"; filename="%s"'
                 % filename).encode("utf-8") + CRLF
        body += b"Content-Type: application/octet-stream" + CRLF + CRLF
        body += data + CRLF
        body += b"--" + boundary.encode() + b"--" + CRLF

        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
        req.add_header("Authorization", "Bearer %s" % self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read().decode("utf-8", "ignore"))
            return out.get("text") or None
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8", "ignore"))
                print("[ASR] HTTP %s: %s" % (e.code, err))
            except Exception:
                print("[ASR] HTTP %s" % e.code)
            return None
        except Exception as e:  # noqa: BLE001
            print("[ASR] 请求失败: %s" % e)
            return None

    def transcribe_file(self, path):
        with open(path, "rb") as f:
            data = f.read()
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else "mp3"
        ok = {"mp3", "m4a", "wav", "aac", "ogg", "flac", "mp4", "webm"}
        filename = ("audio.%s" % ext) if ext in ok else "audio.mp3"
        return self.transcribe_bytes(data, filename)
