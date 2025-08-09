# -*- coding: utf-8 -*-
import pyttsx3

class TTS:
    def __init__(self, rate: int = 175):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', 0.9)

    def say(self, text: str):
        try:
            self.engine.stop()
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            pass

    def stop(self):
        try:
            self.engine.stop()
        except Exception:
            pass
