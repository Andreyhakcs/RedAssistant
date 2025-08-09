# -*- coding: utf-8 -*-
from typing import List, Dict
from . import config

try:
    from openai import OpenAI
    _client = OpenAI(api_key=config.api_key(), base_url=config.base_url())
    _init_err = None
except Exception as e:
    _client, _init_err = None, e

def init_error():
    return _init_err

def chat(messages: List[Dict[str,str]], model: str | None = None) -> str:
    if _client is None:
        raise RuntimeError(f"OpenAI init error: {init_error()}")
    model = model or config.chat_model()
    r = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=800,
    )
    return r.choices[0].message.content.strip()
