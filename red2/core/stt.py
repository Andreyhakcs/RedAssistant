# -*- coding: utf-8 -*-
# Use urllib-based client to avoid httpx issues.
from typing import Optional
from .http_openai import transcribe_whisper
from . import config

def stt_openai_wav(path_wav: str) -> str:
    return transcribe_whisper(path_wav, model=config.stt_model())

def stt_vosk_wav(path_wav: str) -> Optional[str]:
    model_dir = config.vosk_model_path()
    if not model_dir:
        return None
    try:
        from vosk import Model, KaldiRecognizer
        import json, wave
        wf = wave.open(path_wav, "rb")
        rec = KaldiRecognizer(Model(model_dir), wf.getframerate())
        rec.SetWords(True)
        text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text += " " + res.get("text","")
        final = json.loads(rec.FinalResult())
        text += " " + final.get("text","")
        return text.strip()
    except Exception:
        return None
