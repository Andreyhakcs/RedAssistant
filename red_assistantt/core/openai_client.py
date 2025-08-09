# -*- coding: utf-8 -*-
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    _CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL") or None)
except Exception as e:
    _CLIENT = None
    _INIT_ERROR = e
else:
    _INIT_ERROR = None

def is_ready() -> bool:
    return _CLIENT is not None and _INIT_ERROR is None

def init_error() -> Optional[Exception]:
    return _INIT_ERROR

def chat(model: str, messages: List[Dict[str, str]]) -> str:
    if not is_ready():
        raise RuntimeError(f"OpenAI client not initialized: {init_error()}")
    resp = _CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=600
    )
    return resp.choices[0].message.content.strip()
