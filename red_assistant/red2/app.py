# -*- coding: utf-8 -*-
import sys, json, threading
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu
)

from .ui.left_eq import LeftEqBar
from .core import config
from .core import llm, stt, audio, tts

APP_TITLE = "Red Assistant — Voice MVP"

# --- Workers ---
class STTWorker(QThread):
    finished = Signal(str)  # text
    failed = Signal(str)

    def __init__(self, wav_path: str):
        super().__init__()
        self.wav_path = wav_path

    def run(self):
        try:
            # Try offline Vosk first (if configured), fall back to OpenAI
            text = stt.stt_vosk_wav(self.wav_path)
            if not text:
                text = stt.stt_openai_wav(self.wav_path)
            self.finished.emit(text.strip())
        except Exception as e:
            self.failed.emit(str(e))

class LLMWorker(QThread):
    finished = Signal(str)  # assistant content
    failed = Signal(str)

    def __init__(self, messages):
        super().__init__()
        self.messages = messages

    def run(self):
        try:
            out = llm.chat(self.messages, model=config.chat_model())
            self.finished.emit(out)
        except Exception as e:
            self.failed.emit(str(e))

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        self.eq = LeftEqBar()
        self.tts = tts.TTS(rate=175, volume=0.9)

        right = QWidget()
        v = QVBoxLayout(right)
        v.setContentsMargins(12, 24, 24, 24)
        v.setSpacing(16)

        # Top bar
        top = QFrame(objectName="Panel")
        top.setFixedHeight(72)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(16, 12, 16, 12)
        self.state_lbl = QLabel("State: Idle")
        top_l.addWidget(self.state_lbl)
        top_l.addStretch(1)
        self.btn_talk = QPushButton("🎤 Hold to Talk")
        self.btn_talk.setCheckable(True)
        top_l.addWidget(self.btn_talk)
        v.addWidget(top)

        # Chat panel
        chat_panel = QFrame(objectName="Panel")
        chat_l = QVBoxLayout(chat_panel)
        chat_l.setContentsMargins(16, 16, 16, 16)

        self.chat_list = QListWidget()
        chat_l.addWidget(self.chat_list, 1)

        in_l = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Владыка, введите запрос...")
        self.send_btn = QPushButton("Send")
        in_l.addWidget(self.inp, 1)
        in_l.addWidget(self.send_btn)
        chat_l.addLayout(in_l)
        v.addWidget(chat_panel, 1)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0,0,0,0)
        h.setSpacing(0)
        h.addWidget(self.eq, 0)
        h.addWidget(right, 1)
        self.setCentralWidget(central)

        # Tray
        self.tray = QSystemTrayIcon(QIcon(), self)
        self.tray.setToolTip("Red Assistant — running")
        menu = QMenu()
        act_open = menu.addAction("Open")
        act_quit = menu.addAction("Quit")
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()
        act_open.triggered.connect(self.show_window)
        act_quit.triggered.connect(QApplication.instance().quit)
        self.hide()  # start to tray

        # State
        self.messages = [
            {"role":"system","content": config.load_system_prompt()}
        ]
        self.rec = audio.Recorder()

        # Wire
        self.btn_talk.pressed.connect(self._start_rec)
        self.btn_talk.released.connect(self._stop_rec_and_transcribe)
        self.inp.returnPressed.connect(self._send_text)
        self.send_btn.clicked.connect(self._send_text)

        # LLM init check
        if llm.init_error():
            self._append("assistant", f"⚠ OpenAI init error: {llm.init_error()}")

    # UI helpers
    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _append(self, role, text):
        prefix = "Владыка:" if role == "user" else "Red:"
        self.chat_list.addItem(f"{prefix} {text}")
        self.chat_list.scrollToBottom()

    # Recording flow
    def _start_rec(self):
        self.eq.set_state("listening")
        self.state_lbl.setText("State: Listening")
        try:
            self.rec.start()
        except Exception as e:
            self._append("assistant", f"Микрофон ошибка: {e}")
            self.eq.set_state("idle")
            self.state_lbl.setText("State: Idle")

    def _stop_rec_and_transcribe(self):
        wav = ""
        try:
            wav = self.rec.stop()
        except Exception as e:
            self._append("assistant", f"Запись ошибка: {e}")
        if not wav:
            self.eq.set_state("idle")
            self.state_lbl.setText("State: Idle")
            return
        self.eq.set_state("idle")
        self.state_lbl.setText("State: Transcribing…")
        self._stt = STTWorker(wav)
        self._stt.finished.connect(self._on_stt_text)
        self._stt.failed.connect(self._on_stt_err)
        self._stt.start()

    def _on_stt_text(self, text):
        if not text:
            self.state_lbl.setText("State: Idle")
            return
        self._append("user", text)
        self.state_lbl.setText("State: Thinking…")
        msgs = self.messages + [{"role":"user","content": text}]
        self._llm = LLMWorker(msgs)
        self._llm.finished.connect(self._on_llm_reply)
        self._llm.failed.connect(self._on_llm_err)
        self._llm.start()

    def _on_stt_err(self, err):
        self._append("assistant", f"STT ошибка: {err}")
        self.state_lbl.setText("State: Idle")

    # Text flow
    def _send_text(self):
        txt = self.inp.text().strip()
        if not txt:
            return
        self.inp.clear()
        self._append("user", txt)
        msgs = self.messages + [{"role":"user","content": txt}]
        self._llm = LLMWorker(msgs)
        self._llm.finished.connect(self._on_llm_reply)
        self._llm.failed.connect(self._on_llm_err)
        self._llm.start()
        self.state_lbl.setText("State: Thinking…")

    # LLM results
    def _on_llm_reply(self, content):
        self.messages.append({"role":"user","content": self.chat_list.item(self.chat_list.count()-2).text().replace('Владыка: ','',1)})
        self.messages.append({"role":"assistant","content": content})
        self._append("assistant", content)
        # Speak
        self.eq.set_state("speaking")
        self.state_lbl.setText("State: Speaking")
        self.tts.speak(content, on_done=lambda: (self.eq.set_state("idle"), self.state_lbl.setText("State: Idle")))

    def _on_llm_err(self, err):
        self._append("assistant", f"LLM ошибка: {err}")
        self.state_lbl.setText("State: Idle")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    # Load style
    try:
        qss = (Path(__file__).parent / "ui" / "style.qss").read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except Exception:
        pass
    win = MainWindow()
    sys.exit(app.exec())
