# -*- coding: utf-8 -*-
import re
from PySide6.QtCore import QThread, Signal

# --- Additions to existing app.py ---

# 1) Replace previous import in app.py:
# from .core import vision as redvision
# with the same line — API changed to quick_screen_context_ultra_brief()

# 2) In VisionWorker use new call:
class VisionWorker(QThread):
    finished = Signal(str, str, str)   # desc, ocr, title
    failed = Signal(str)
    def run(self):
        try:
            from .core import vision as redvision
            desc, ocr, title = redvision.quick_screen_context_ultra_brief()
            self.finished.emit(desc, ocr, title)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")

# 3) In MainWindow._on_vision_ready accept three args and speak only short desc:
def _on_vision_ready(self, desc, ocr, title):
    self.last_screen_desc = desc or ""
    self.last_screen_ocr = (ocr or "")[:2000]
    self.last_screen_title = title or ""
    if self.last_screen_desc:
        if hasattr(self, "anim") and self.anim: self.anim.set_state("speaking")
        self.tts.speak(self.last_screen_desc, on_done=lambda: (hasattr(self,'anim') and self.anim and self.anim.set_state('idle')))
        self._append("assistant", f"Экран: {self.last_screen_desc}")

# 4) Add helper: detect translate intent (RU/EN keywords)
def _is_translate_request(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["переведи", "перевод", "translate", "переведи текст", "переведи с", "переведи на"])

# 5) In _on_stt_text and _send_text: if translate intent -> build translation prompt using last_screen_ocr
# Example for _on_stt_text (same idea for _send_text):
def _on_stt_text(self, text):
    if not text:
        self.state_lbl.setText("State: Idle  |  Ctrl+3 = Vision+PTT"); return
    self._append("user", text); self.state_lbl.setText("State: Thinking…  |  Ctrl+3 = Vision+PTT")
    msgs = self.messages[:]

    if _is_translate_request(text):
        ocr_text = getattr(self, 'last_screen_ocr', '') or ""
        if not ocr_text:
            try:
                from .core import vision as redvision
                _, ocr_text, _ = redvision.quick_screen_context_ultra_brief()
            except Exception:
                pass
        if not ocr_text:
            msgs.append({"role":"system","content":"На экране текста не найдено. Скажи об этом кратко."})
            msgs.append({"role":"user","content":"Переведи текст с экрана на русский."})
        else:
            msgs.append({"role":"system","content":"Ты переводчик. Переводи максимально кратко и точно. Без лишних слов."})
            msgs.append({"role":"user","content":f"Переведи на русский этот текст с экрана:\n{ocr_text}"})
    else:
        if getattr(self, 'last_screen_desc', ''):
            msgs.append({"role":"system","content": f"Контекст экрана: {self.last_screen_desc}"})
        if getattr(self, 'last_screen_title', ''):
            msgs.append({"role":"system","content": f"Активное окно: {self.last_screen_title}"})
        if getattr(self, 'last_screen_ocr', ''):
            msgs.append({"role":"system","content": f"OCR: {self.last_screen_ocr[:800]}"})
        msgs.append({"role":"user","content": text})

    self._llm = LLMWorker(msgs); self._llm.finished.connect(self._on_llm_reply); self._llm.failed.connect(self._on_llm_err); self._llm.start()
