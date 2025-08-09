
# -*- coding: utf-8 -*-
import sys, os, time as _time
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QObject
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QPushButton, QLineEdit, QListWidget, QSystemTrayIcon, QMenu
)

from .core import config, llm, stt, audio, tts
from .core import vision as redvision
from .splash import SplashWindow
from .preflight import run_preflight
from .ui.neon_widgets import NeonSideBar
from .ui.settings_dialog import SettingsDialog
from .ui import user_prefs

APP_TITLE = "Red Assistant — Voice MVP (Minimal)"
MIN_RECORD_SEC = 0.20

def log(*a):
    try: print(*a, flush=True)
    except: pass

# ------------ Tray animator --------------
class TrayAnimator(QObject):
    def __init__(self, tray: QSystemTrayIcon):
        super().__init__()
        self.tray=tray; self.state="idle"; self.level=0.0; self._t=0
        self.timer=QTimer(self); self.timer.setInterval(80); self.timer.timeout.connect(self._tick); self.timer.start()
    def initial_icon(self)->QIcon: return self._build_icon()
    def set_state(self,s): self.state=s
    def set_level(self,v): self.level=max(0.0,min(1.0,float(v)))
    def _tick(self): self._t=(self._t+1)%10000; self.tray.setIcon(self._build_icon())
    def _build_icon(self)->QIcon:
        size=128; pm=QPixmap(size,size); pm.fill(Qt.transparent); p=QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing,True); p.setBrush(QColor(16,18,22)); p.setPen(Qt.NoPen); p.drawEllipse(2,2,size-4,size-4)
            bars=6
            for i in range(bars):
                import math as _m
                phase=self._t*0.18+i*0.9
                if self.state=="idle": amp=0.15+0.05*_m.sin(phase)
                elif self.state=="listening": amp=0.25+0.6*self.level+0.12*_m.sin(phase*1.3)
                elif self.state=="speaking": amp=0.5+0.25*_m.sin(phase*2.2)
                else: amp=0.08
                amp=max(0.05,min(1.0,amp)); w=(size-28)//bars; x=14+i*w; h=int((size-28)*amp); y=size-14-h
                grad=QLinearGradient(x,y,x+w,y); grad.setColorAt(0.0,QColor("#FF0033")); grad.setColorAt(1.0,QColor("#FF1A8A"))
                p.fillRect(x+2,y,w-4,h,QBrush(grad))
            p.setPen(QColor(255,0,51,180)); p.setBrush(Qt.NoBrush); p.drawEllipse(2,2,size-4,size-4)
        finally: p.end()
        return QIcon(pm)

# ------------ Workers ------------
class VisionWorker(QThread):
    finished = Signal(str,str,str)   # desc, ocr, title
    failed = Signal(str)
    def __init__(self, lang="auto"):
        super().__init__()
        self.lang = lang
    def run(self):
        try:
            # если redvision поддерживает язык — пробуем передать, иначе просто игнор
            try:
                desc, ocr, title = redvision.quick_screen_context_ultra_brief(lang=self.lang)
            except TypeError:
                desc, ocr, title = redvision.quick_screen_context_ultra_brief()
            self.finished.emit(desc, ocr, title)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")

class STTWorker(QThread):
    finished = Signal(str); failed = Signal(str)
    def __init__(self, wav): super().__init__(); self.wav=wav
    def run(self):
        try:
            text = stt.stt_vosk_wav(self.wav) or stt.stt_openai_wav(self.wav)
            self.finished.emit((text or '').strip())
        except Exception as e: self.failed.emit(f"{type(e).__name__}: {e}")

class LLMWorker(QThread):
    finished = Signal(str); failed = Signal(str)
    def __init__(self, msgs, model:str):
        super().__init__(); self.msgs=msgs; self.model=model
    def run(self):
        try: self.finished.emit(llm.chat(self.msgs, model=self.model))
        except Exception as e: self.failed.emit(f"{type(e).__name__}: {e}")

# ------------ Main -------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE); self.resize(1000,720)
        self._vision=None; self._stt=None; self._llm=None
        self._llm_busy=False
        self._hotkey_setup_done=False
        self._kb_hooked=False
        self.last_screen_desc=""; self.last_screen_ocr=""; self.last_screen_title=""
        self._last_stt_text=""; self._last_stt_ts=0.0
        self.prefs = user_prefs.load()

        # left neon bar
        self.neon = NeonSideBar()

        # right layout
        right=QWidget(); v=QVBoxLayout(right); v.setContentsMargins(16,18,18,18); v.setSpacing(14)
        top=QFrame(objectName="Panel"); top.setFixedHeight(72)
        tl=QHBoxLayout(top); tl.setContentsMargins(16,12,16,12)
        self.title_lbl=QLabel("Red Assistant"); self.title_lbl.setObjectName("Title")
        self.state_lbl=QLabel("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); self.state_lbl.setObjectName("State")
        tl.addWidget(self.title_lbl); tl.addStretch(1); tl.addWidget(self.state_lbl)
        self.btn_talk=QPushButton("🎤 Hold to Talk"); self.btn_talk.setCheckable(True); tl.addWidget(self.btn_talk)
        self.btn_settings=QPushButton("⚙ Settings"); tl.addWidget(self.btn_settings)
        v.addWidget(top)

        chat=QFrame(objectName="Panel"); cl=QVBoxLayout(chat); cl.setContentsMargins(14,14,14,14)
        self.chat_list=QListWidget(); cl.addWidget(self.chat_list,1)
        il=QHBoxLayout(); self.inp=QLineEdit(); self.inp.setPlaceholderText("Владыка, введите запрос..."); self.send_btn=QPushButton("Send")
        il.addWidget(self.inp,1); il.addWidget(self.send_btn); cl.addLayout(il)
        v.addWidget(chat,1)

        central=QWidget(); h=QHBoxLayout(central); h.setContentsMargins(0,0,0,0); h.setSpacing(8)
        h.addWidget(self.neon); h.addWidget(right,1); self.setCentralWidget(central)

        # tray
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray=QSystemTrayIcon(self); self.anim=TrayAnimator(self.tray); self.tray.setIcon(self.anim.initial_icon())
            menu=QMenu(); a_open=menu.addAction("Open"); a_vis=menu.addAction("Describe Screen now (Ctrl+4)"); a_settings = menu.addAction("Settings…"); a_quit=menu.addAction("Quit")
            self.tray.setContextMenu(menu); self.tray.activated.connect(lambda r: self.showNormal() if r==QSystemTrayIcon.Trigger else None); self.tray.show()
            a_open.triggered.connect(self.show_window); a_quit.triggered.connect(QApplication.instance().quit); a_vis.triggered.connect(self.describe_screen_now); a_settings.triggered.connect(self.open_settings)
            self.hide(); self._append("assistant","Started to tray.")
        else: self.anim=None; self.show()

        self.messages=[{"role":"system","content":config.load_system_prompt()}]; 
        self.rec=audio.Recorder(); 
        self.tts=tts.TTS(rate=int(self.prefs.get("tts_rate",175)), volume=float(self.prefs.get("tts_volume",0.9)))

        self.btn_talk.pressed.connect(self._start_rec); self.btn_talk.released.connect(self._stop_rec_and_transcribe)
        self.inp.returnPressed.connect(self._send_text); self.send_btn.clicked.connect(self._send_text)
        self.btn_settings.clicked.connect(self.open_settings)

        self.level_timer=QTimer(self); self.level_timer.setInterval(90); self.level_timer.timeout.connect(self._update_level); self.level_timer.start()
        self._setup_hotkeys_split()

    # ----- Settings -----
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.changed.connect(self.apply_prefs)
        dlg.exec()

    def apply_prefs(self, prefs:dict):
        self.prefs = prefs
        # TTS
        try:
            self.tts.stop()
        except Exception:
            pass
        self.tts = tts.TTS(rate=int(self.prefs.get("tts_rate",175)), volume=float(self.prefs.get("tts_volume",0.9)))
        # state label could include model
        self._append("assistant", f"Настройки применены: модель={self.prefs.get('model')}, TTS={self.prefs.get('tts_rate')} / {self.prefs.get('tts_volume')}")

    # ----- speak helper (no overlaps) -----
    def _speak(self, text: str):
        try: self.tts.stop()
        except Exception: pass
        if hasattr(self,'anim') and self.anim: self.anim.set_state("speaking")
        self.neon.set_state("speaking")
        self.tts.speak(text, on_done=lambda: (hasattr(self,'anim') and self.anim and self.anim.set_state('idle'),
                                              self.neon.set_state("idle"),
                                              self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4")))

    # ----- hotkeys -----
    def _setup_hotkeys_split(self):
        if getattr(self, "_hotkey_setup_done", False):
            return
        self._hotkey_setup_done=True
        ok=False
        try:
            from qhotkey import QHotkey
            self.hk_ptt=QHotkey(self.prefs.get("ptt_key","ctrl+3"), parent=self)
            self.hk_vis=QHotkey(self.prefs.get("vision_key","ctrl+4"), parent=self)
            ok_ptt=self.hk_ptt.setRegistered(True); ok_vis=self.hk_vis.setRegistered(True)
            if ok_ptt:
                self.hk_ptt.activated.connect(self._hk_ptt_down)
                try: self.hk_ptt.released.connect(self._hk_ptt_up)
                except Exception: pass
            if ok_vis:
                self.hk_vis.activated.connect(self._hk_vision_once)
            ok = ok_ptt or ok_vis
            if ok:
                self._append("assistant","Hotkeys via QHotkey: PTT Ctrl+3 (hold), Vision Ctrl+4."); return
        except Exception as e:
            self._append("assistant", f"QHotkey недоступен: {e}. Пробую fallback.")
        try:
            import keyboard
            if not getattr(self, "_kb_hooked", False):
                self._kb_down=False
                def on_evt(e):
                    try:
                        if keyboard.is_pressed('ctrl'):
                            if e.name in ('3','num 3'):
                                if e.event_type=='down' and not self._kb_down:
                                    self._kb_down=True; self._hk_ptt_down()
                                elif e.event_type=='up' and self._kb_down:
                                    self._kb_down=False; self._hk_ptt_up()
                            elif e.name in ('4','num 4'):
                                if e.event_type=='down':
                                    self._hk_vision_once()
                    except Exception: pass
                keyboard.hook(on_evt); self._kb_hooked=True
            self._append("assistant","Hotkeys via keyboard: PTT Ctrl+3 (hold), Vision Ctrl+4. Если не срабатывает — запусти от администратора.")
        except Exception as e:
            self._append("assistant", f"keyboard недоступен: {e}. Горячие клавиши отключены.")

    def _hk_ptt_down(self): self._start_rec(from_hotkey=True)
    def _hk_ptt_up(self):   self._stop_rec_and_transcribe(from_hotkey=True)
    def _hk_vision_once(self): self.describe_screen_now()

    def describe_screen_now(self):
        if self._vision and self._vision.isRunning(): self._append("assistant","Vision уже выполняется…"); return
        self._vision=VisionWorker(lang=self.prefs.get("ocr_lang","auto")); self._vision.finished.connect(self._on_vision_ready)
        self._vision.failed.connect(lambda e: self._append("assistant", f"Vision ошибка: {e}"))
        self._vision.finished.connect(lambda *a: setattr(self, "_vision", None)); self._vision.start()

    def _on_vision_ready(self, desc, ocr, title):
        self.last_screen_desc=desc or ""; self.last_screen_ocr=(ocr or "")[:2000]; self.last_screen_title=title or ""
        if self.last_screen_desc:
            self._speak(self.last_screen_desc)
            self._append("assistant", f"Экран: {self.last_screen_desc}")

    def _update_level(self):
        lvl = self.rec.current_level() if self.rec else 0.0
        if hasattr(self,'anim') and self.anim: self.anim.set_level(lvl)
        self.neon.set_level(lvl)

    # ----- recording -----
    def _start_rec(self, from_hotkey=False):
        if getattr(self,"_recording",False): return
        self._recording=True
        if hasattr(self,'anim') and self.anim: self.anim.set_state("listening")
        self.neon.set_state("listening")
        self.state_lbl.setText("State: Listening  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); self.btn_talk.setChecked(True)
        try: self.rec.start()
        except Exception as e:
            self._append("assistant", f"Микрофон ошибка: {e}")
            if hasattr(self,'anim') and self.anim: self.anim.set_state("idle")
            self.neon.set_state("idle")
            self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); self.btn_talk.setChecked(False); self._recording=False

    def _stop_rec_and_transcribe(self, from_hotkey=False):
        if not getattr(self,"_recording",False): return
        self._recording=False; wav=""
        try: wav=self.rec.stop()
        except Exception as e: self._append("assistant", f"Запись ошибка: {e}")
        if not wav or float(getattr(self.rec,"last_duration",0.0)) < MIN_RECORD_SEC:
            if hasattr(self,'anim') and self.anim: self.anim.set_state("idle")
            self.neon.set_state("idle")
            self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); self.btn_talk.setChecked(False)
            if wav: self._append("assistant", f"Запись слишком короткая (<{MIN_RECORD_SEC:.2f}с)."); return
            return
        if hasattr(self,'anim') and self.anim: self.anim.set_state("idle")
        self.neon.set_state("idle")
        self.state_lbl.setText("State: Transcribing…  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); self.btn_talk.setChecked(False)
        self._stt=STTWorker(wav); self._stt.finished.connect(self._on_stt_text); self._stt.failed.connect(self._on_stt_err); self._stt.start()

    # ----- debounce STT and singleflight LLM -----
    def _start_llm(self, msgs):
        if self._llm_busy:
            return
        self._llm_busy=True
        model = self.prefs.get("model") or "gpt-4o-mini"
        self._llm=LLMWorker(msgs, model=model)
        self._llm.finished.connect(self._on_llm_reply)
        self._llm.failed.connect(self._on_llm_err)
        def _clear():
            self._llm_busy=False
        self._llm.finished.connect(_clear)
        self._llm.failed.connect(_clear)
        self._llm.start()

    def _on_stt_text(self, text):
        if not text:
            self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4"); return
        now=_time.time()
        if text == self._last_stt_text and (now - self._last_stt_ts) < 1.2:
            return
        self._last_stt_text, self._last_stt_ts = text, now

        self._append("user", text); self.state_lbl.setText("State: Thinking…  |  PTT: Ctrl+3  |  Vision: Ctrl+4")
        is_tr, target = self._is_translate_request(text); msgs=self._build_msgs(is_tr, target)
        self._start_llm(msgs)

    def _on_stt_err(self, err): self._append("assistant", f"STT ошибка: {err}"); self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4")

    def _send_text(self):
        txt=self.inp.text().strip()
        if not txt: return
        self.inp.clear(); self._append("user", txt); self.state_lbl.setText("State: Thinking…  |  PTT: Ctrl+3  |  Vision: Ctrl+4")
        is_tr, target = self._is_translate_request(txt); msgs=self._build_msgs(is_tr, target)
        self._start_llm(msgs)

    # ----- build messages helpers -----
    def _is_translate_request(self, text: str) -> tuple[bool, str]:
        t=(text or "").lower().strip()
        if not t: return False, ""
        if any(k in t for k in ["переведи","перевод","переведи текст","translate"]):
            import re as _re
            m=_re.search(r"на\s+([а-яa-z]+)", t); target=m.group(1) if m else "русский"
            mapping={"english":"английский","russian":"русский","german":"немецкий","spanish":"испанский","french":"французский"}
            target=mapping.get(target,target); return True, target
        return False, ""

    def _build_msgs(self, is_tr: bool, target: str):
        msgs=self.messages[:]
        if is_tr:
            ocr_text=self.last_screen_ocr or ""
            if not ocr_text:
                try: _, ocr_text, _ = redvision.quick_screen_context_ultra_brief()
                except Exception: pass
            if not ocr_text:
                msgs.append({"role":"system","content":"На экране текста не найдено. Кратко скажи об этом."})
                msgs.append({"role":"user","content":"Переведи текст с экрана."})
            else:
                msgs.append({"role":"system","content":"Ты переводчик. Переводи максимально кратко и точно без вступлений."})
                msgs.append({"role":"user","content":f"Переведи на {target} этот текст с экрана:\n{ocr_text}"})
        else:
            if self.last_screen_desc: msgs.append({"role":"system","content": f"Контекст экрана: {self.last_screen_desc}"})
            if self.last_screen_title: msgs.append({"role":"system","content": f"Активное окно: {self.last_screen_title}"})
            if self.last_screen_ocr: msgs.append({"role":"system","content": f"OCR: {self.last_screen_ocr[:800]}"})
        return msgs

    def _on_llm_reply(self, content):
        self.messages.append({"role":"assistant","content": content}); self._append("assistant", content)
        self._speak(content)

    def _on_llm_err(self, err): self._append("assistant", f"LLM ошибка: {err}"); self.state_lbl.setText("State: Idle  |  PTT: Ctrl+3  |  Vision: Ctrl+4")

    def show_window(self): self.showNormal(); self.raise_(); self.activateWindow()
    def _append(self, role, text): self.chat_list.addItem(("Владыка:" if role=="user" else "Red:")+" "+text); self.chat_list.scrollToBottom()
    def closeEvent(self, e):
        try:
            for t in (self._vision, self._stt, self._llm):
                if t and t.isRunning(): t.wait(1000)
        finally: super().closeEvent(e)

# ---------- main ----------
def main():
    app = QApplication(sys.argv); app.setApplicationName(APP_TITLE)
    try:
        qss = (Path(__file__).parent / "ui" / "style.qss").read_text(encoding="utf-8"); app.setStyleSheet(qss)
    except Exception: pass

    # splash respect prefs
    prefs = user_prefs.load()
    if prefs.get("show_splash", True):
        assets_dir = (Path(__file__).parent.parent / "assets").resolve()
        splash_mp4 = assets_dir / "splash.mp4"
        try:
            if splash_mp4.exists():
                sw = SplashWindow(str(splash_mp4), duration_ms= int(1000*max(3,5)))
                sw.show_then(lambda: None)  # не блокируем по максимуму
        except Exception:
            pass

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
