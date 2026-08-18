#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短视频音频下载（尽力而为，可选依赖 yt-dlp，零强制依赖）。

- 优先用 yt-dlp 下载抖音 / 小红书 / B站 / YouTube 等平台的音频
  （部分平台需要登录态，可加 --cookies cookies.txt，本脚本不内置）。
- 直链（.mp3/.m4a/.mp4 等）直接下载。
- 任何一步失败都返回 None，由调用方把「整理情况」标记为“需手动提供视频音频”。
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request


def download_audio(url, workdir=None):
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="topic_asr_")
    os.makedirs(workdir, exist_ok=True)

    # 1) yt-dlp（支持抖音/小红书/B站/YouTube 等）
    ytdlp = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if ytdlp:
        out_tmpl = os.path.join(workdir, "vid_%(id)s.%(ext)s")
        try:
            subprocess.run(
                [ytdlp, "-x", "--audio-format", "mp3", "--no-progress",
                 "-o", out_tmpl, url],
                capture_output=True, text=True, timeout=180,
            )
        except Exception:  # noqa: BLE001
            pass
        mp3s = sorted(glob.glob(os.path.join(workdir, "*.mp3")),
                      key=os.path.getmtime, reverse=True)
        if mp3s:
            return mp3s[0]

    # 2) 直链兜底
    if re.search(r"\.(mp3|m4a|wav|aac|ogg|flac|mp4|webm)(\?|$)", url, re.I):
        try:
            dest = os.path.join(workdir, "direct_audio")
            urllib.request.urlretrieve(url, dest)
            return dest
        except Exception:  # noqa: BLE001
            return None
    return None
