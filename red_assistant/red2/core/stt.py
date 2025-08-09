# -*- coding: utf-8 -*-
import os, tempfile
from typing import Optional
from . import config

# Online STT via OpenAI (Whisper API / 4o-mini-transcribe)
def stt_openai_wav(path_wav: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config.api_key(), base_url=config.base_url())
    model = config.stt_model()
    with open(path_wav, "rb") as f:
        try:
            # Prefer whisper-1 compatibility
            r = client.audio.transcriptions.create(model=model, file=f)
            return r.text.strip()
        except Exception as e:
            # Some SDKs return different shape
            raise e

# Optional offline STT via Vosk
def stt_vosk_wav(path_wav: str) -> Optional[str]:
    model_dir = config.vosk_model_path()
    if not model_dir:
        return None
    try:
        from vosk import Model, KaldiRecognizer
        import json, wave
        wf = wave.open(path_wav, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in (16000, 44100, 48000):
            # Vosk works best with 16k mono 16-bit. For brevity, assume it's OK if 16k mono 16-bit.
            pass
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
