# -*- coding: utf-8 -*-
import pyttsx3, threading

class TTS:
    def __init__(self, rate: int = 175, volume: float = 0.9):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        self._lock = threading.Lock()

    def speak(self, text: str, on_start=None, on_done=None):
        def run():
            if on_start: 
                try: on_start()
                except: pass
            try:
                with self._lock:
                    self.engine.stop()
                    self.engine.say(text)
                    self.engine.runAndWait()
            finally:
                if on_done:
                    try: on_done()
                    except: pass
        threading.Thread(target=run, daemon=True).start()
