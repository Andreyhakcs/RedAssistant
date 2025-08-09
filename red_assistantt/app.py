# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu
)

from red_assistant.ui.left_eq import LeftEqBar
from red_assistant.core.openai_client import chat as llm_chat, is_ready, init_error
from red_assistant.core.tts import TTS

APP_TITLE = "Red Assistant — Minimal v1"

class ChatWorker(QThread):
    finished = Signal(str, str)  # role, content
    failed = Signal(str)

    def __init__(self, model: str, messages):
        super().__init__()
        self.model = model
        self.messages = messages

    def run(self):
        try:
            out = llm_chat(self.model, self.messages)
            self.finished.emit("assistant", out)
        except Exception as e:
            self.failed.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        self.eq = LeftEqBar()
        self.tts = TTS(rate=175)
        self.speak_enabled = True

        right = QWidget()
        v = QVBoxLayout(right)
        v.setContentsMargins(12, 24, 24, 24)
        v.setSpacing(16)

        top = QFrame(objectName="Panel")
        top.setFixedHeight(72)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(16, 12, 16, 12)
        self.state_lbl = QLabel("State: Idle")
        self.state_lbl.setObjectName("State")
        top_l.addWidget(self.state_lbl)
        top_l.addStretch(1)
        self.btn_idle = QPushButton("Idle")
        self.btn_listen = QPushButton("Listening")
        self.btn_speak = QPushButton("Speaking")
        self.btn_mute = QPushButton("Mute")
        for b in (self.btn_idle, self.btn_listen, self.btn_speak, self.btn_mute):
            top_l.addWidget(b)
        v.addWidget(top)

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

        self.btn_idle.clicked.connect(lambda: self._set_state("idle"))
        self.btn_listen.clicked.connect(lambda: self._set_state("listening"))
        self.btn_speak.clicked.connect(lambda: self._set_state("speaking"))
        self.btn_mute.clicked.connect(self._toggle_mute)
        self.send_btn.clicked.connect(self.send_message)
        self.inp.returnPressed.connect(self.send_message)

        self.tray = QSystemTrayIcon(QIcon(), self)
        self.tray.setToolTip("Red Assistant — running")
        menu = QMenu()
        act_open = menu.addAction("Open")
        menu.addSeparator()
        act_idle = menu.addAction("Idle")
        act_listen = menu.addAction("Listening")
        act_speak = menu.addAction("Speaking")
        act_mute = menu.addAction("Mute / Unmute")
        menu.addSeparator()
        act_quit = menu.addAction("Quit")
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

        act_open.triggered.connect(self.show_window)
        act_idle.triggered.connect(lambda: self._set_state("idle"))
        act_listen.triggered.connect(lambda: self._set_state("listening"))
        act_speak.triggered.connect(lambda: self._set_state("speaking"))
        act_mute.triggered.connect(self._toggle_mute)
        act_quit.triggered.connect(QApplication.instance().quit)

        self.hide()

        self.messages = [
            {"role":"system", "content": self.cfg.get("system_prompt", "You are Red.")}
        ]

        if not is_ready():
            self._append("assistant", f"⚠ OpenAI client not initialized: {init_error()}")

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _append(self, role, text):
        prefix = "Владыка:" if role == "user" else "Red:"
        self.chat_list.addItem(f"{prefix} {text}")
        self.chat_list.scrollToBottom()

    def _set_state(self, s):
        self.eq.set_state(s)
        self.state_lbl.setText(f"State: {s.capitalize()}")

    def _toggle_mute(self):
        self.eq.set_muted(not self.eq.muted)
        self.state_lbl.setText(f"State: {'Muted' if self.eq.muted else self.eq.state.capitalize()}")

    def send_message(self):
        text = self.inp.text().strip()
        if not text:
            return
        self.inp.clear()
        self._append("user", text)

        messages = self.messages + [{"role":"user","content": text}]
        self.worker = ChatWorker(self.cfg.get("model","gpt-4o-mini"), messages)
        self.worker.finished.connect(self._on_reply)
        self.worker.failed.connect(self._on_error)
        self.worker.start()

    def _on_reply(self, role, content):
        # Append to conversation
        self.messages.append({"role":"user","content": self.chat_list.item(self.chat_list.count()-2).text().replace('Владыка: ','',1)})
        self.messages.append({"role":"assistant","content": content})
        self._append(role, content)
        if self.speak_enabled and not self.eq.muted:
            try:
                self.tts.say(content)
            except Exception:
                pass

    def _on_error(self, err):
        self._append("assistant", f"Ошибка: {err}")

def load_config():
    p = Path(__file__).parent / "config.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"model":"gpt-4o-mini","system_prompt":"You are Red."}

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    try:
        qss = (Path(__file__).parent / "ui" / "red_neon.qss").read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except Exception:
        pass

    cfg = load_config()
    win = MainWindow(cfg)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
