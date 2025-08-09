# -*- coding: utf-8 -*-
"""
Minimal OpenAI HTTPS client via urllib (no httpx). Works with Python stdlib.
Env:
  OPENAI_API_KEY
  OPENAI_BASE_URL (default https://api.openai.com/v1)
"""
import os, json, ssl, uuid
from urllib import request, error

BASE = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
KEY = os.getenv("OPENAI_API_KEY") or ""

def _headers(extra=None, content_type="application/json"):
    h = {
        "Authorization": f"Bearer {KEY}",
    }
    if content_type:
        h["Content-Type"] = content_type
    if extra:
        h.update(extra)
    return h

def _ctx():
    return ssl.create_default_context()

def chat_completions(model: str, messages):
    if not KEY:
        raise RuntimeError("OPENAI_API_KEY не задан.")
    url = BASE + "/chat/completions"
    data = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 800
    }).encode("utf-8")
    req = request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with request.urlopen(req, context=_ctx(), timeout=30) as r:
            body = r.read()
            obj = json.loads(body.decode("utf-8"))
            return obj["choices"][0]["message"]["content"].strip()
    except error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {err_body[:400]}")
    except Exception as e:
        raise RuntimeError(f"Network error: {type(e).__name__}: {e}")

def transcribe_whisper(file_path: str, model: str = "whisper-1"):
    if not KEY:
        raise RuntimeError("OPENAI_API_KEY не задан.")
    url = BASE + "/audio/transcriptions"
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    def part(name, value):
        return (f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n").encode("utf-8")
    def file_part(field, filename, content_type, data_bytes):
        head = (f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {content_type}\r\n\r\n").encode("utf-8")
        tail = b"\r\n"
        return head + data_bytes + tail
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    body = b"".join([
        part("model", model),
        file_part("file", "audio.wav", "audio/wav", file_bytes),
        (f"--{boundary}--\r\n").encode("utf-8")
    ])
    headers = _headers(content_type=f"multipart/form-data; boundary={boundary}")
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, context=_ctx(), timeout=60) as r:
            resp = r.read()
            obj = json.loads(resp.decode("utf-8"))
            # Some responses: {"text":"..."}
            return obj.get("text") or obj.get("data", [{}])[0].get("text") or ""
    except error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {err_body[:400]}")
    except Exception as e:
        raise RuntimeError(f"Network error: {type(e).__name__}: {e}")
