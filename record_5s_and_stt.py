# Record 5s from default mic and transcribe via configured STT
import time, os
from dotenv import load_dotenv; load_dotenv()
from red2.core import audio, stt

rec = audio.Recorder(samplerate=16000, channels=1)
print("Recording 5s...")
rec.start(); time.sleep(5); path = rec.stop()
print("Saved:", path)
txt = stt.stt_vosk_wav(path) or stt.stt_openai_wav(path)
print("Transcript:", txt)
