# -*- coding: utf-8 -*-
"""
Префлайт‑проверки на старте: ключ, сеть, tesseract, каталоги.
Ничего не ломает, просто даёт быстрый фидбек, пока крутится сплэш.
"""
from __future__ import annotations
import os, json, socket, time, urllib.request
from dataclasses import dataclass

API_URL_DEFAULT = "https://api.openai.com/v1"

@dataclass
class PreflightResult:
    ok: bool
    notes: list[str]

def has_net(host="api.openai.com", port=443, timeout=2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def http_head(url: str, timeout=3.0) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status < 400
    except Exception:
        return False

def run_preflight(env_path: str | None = None) -> PreflightResult:
    notes = []

    # 1) API key
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key and env_path and os.path.exists(env_path):
        # грубо подгружаем .env (одна строка OPENAI_API_KEY=...)
        try:
            for line in open(env_path, "r", encoding="utf-8", errors="ignore"):
                if line.strip().startswith("OPENAI_API_KEY="):
                    api_key = line.split("=",1)[1].strip()
                    break
        except Exception:
            pass
    notes.append("Ключ: " + ("найден" if api_key else "не найден"))

    # 2) сеть
    notes.append("Сеть: ping api.openai.com " + ("ОК" if has_net() else "нет"))
    base = os.getenv("OPENAI_BASE_URL", API_URL_DEFAULT)
    notes.append(f"BASE_URL: {base}")
    notes.append("HEAD /v1: " + ("ОК" if http_head(base) else "ошибка/блок"))

    # 3) tesseract
    try:
        import pytesseract
        ver = pytesseract.get_tesseract_version()
        notes.append(f"Tesseract: {ver}")
    except Exception as e:
        notes.append(f"Tesseract: недоступен ({type(e).__name__})")

    # 4) temp dirs
    try:
        import pathlib
        tmp = pathlib.Path.cwd() / "tmp_audio"
        tmp.mkdir(exist_ok=True)
        notes.append("tmp_audio: есть")
    except Exception:
        notes.append("tmp_audio: ошибка")

    ok = any("ОК" in n for n in notes) or api_key != ""
    return PreflightResult(ok=ok, notes=notes)
