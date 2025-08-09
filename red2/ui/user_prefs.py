
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Any

APP_NAME = "RedAssistant"

DEFAULTS: Dict[str, Any] = {
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "tts_engine": "edge",          # 'edge' | 'system'
    "tts_rate": 175,
    "tts_volume": 0.9,
    "tts_voice": "ru-RU-SvetlanaNeural",  # online голос по умолчанию
    "show_splash": True,
    "ocr_lang": "auto",
    "ptt_key": "ctrl+3",
    "vision_key": "ctrl+4",
}

def _pref_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / APP_NAME
    else:
        base = Path.home() / ".config" / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base / "user_prefs.json"

def load() -> Dict[str, Any]:
    p = _pref_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            merged = {**DEFAULTS, **(data or {})}
            return merged
        except Exception:
            pass
    return DEFAULTS.copy()

def save(data: Dict[str, Any]) -> None:
    p = _pref_path()
    try:
        p.write_text(json.dumps({**DEFAULTS, **data}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
