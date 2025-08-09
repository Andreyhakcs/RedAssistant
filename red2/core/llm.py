# -*- coding: utf-8 -*-
# Use urllib-based client to avoid httpx issues.
from typing import List, Dict
from . import config
from .http_openai import chat_completions

def init_error():
    return None

def chat(messages: List[Dict[str,str]], model: str | None = None) -> str:
    model = model or config.chat_model()
    return chat_completions(model, messages)
