# -*- coding: utf-8 -*-
import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

def load_system_prompt() -> str:
    p = ROOT / "prompts" / "system_prompt.txt"
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return "You are Red. Be concise and directive. Address the user as 'Владыка'."

def get(key: str, default=None):
    return os.getenv(key, default)

def chat_model() -> str:
    env = get("OPENAI_MODEL")
    if env:
        return env
    cfg = ROOT / "config.json"
    if cfg.exists():
        try:
            return json.loads(cfg.read_text(encoding="utf-8")).get("model", "gpt-4o-mini")
        except Exception:
            pass
    return "gpt-4o-mini"

def stt_model() -> str:
    return get("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

def base_url() -> str | None:
    v = get("OPENAI_BASE_URL", "").strip()
    return v or None

def api_key() -> str | None:
    return get("OPENAI_API_KEY")

def vosk_model_path() -> str | None:
    p = get("VOSK_MODEL_PATH", "").strip()
    return p or None
