# -*- coding: utf-8 -*-
import math, random
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PySide6.QtWidgets import QWidget

TOKENS = {
    "bg2": "#101114",
    "red": "#FF0033",
    "redHot": "#FF1A8A",
    "redDeep": "#A2001F",
}

class LeftEqBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(88)
        self.state = "idle"     # idle | listening | speaking
        self.muted = False
        self._t = 0
        self._timer = QTimer(self)
        self._timer.setInterval(50)  # ~20 FPS
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_state(self, state: str):
        self.state = state
        self.update()

    def set_muted(self, m: bool):
        self.muted = m
        self.update()

    def _tick(self):
        self._t = (self._t + 1) % 10_000
        self.update()

    def paintEvent(self, event):
        W = self.width()
        H = self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        p.fillRect(0, 0, W, H, QColor(TOKENS["bg2"]))

        bars = 32
        for i in range(bars):
            y0 = int(i*(H/bars))
            y1 = int((i+1)*(H/bars) - 3)

            if self.muted or self.state == "idle":
                base = 0.12
            elif self.state == "listening":
                base = 0.35
            else:  # speaking
                base = 0.65

            phase = (self._t/12.0) + i*0.55
            amp = base + 0.15*math.sin(phase) + 0.08*math.sin(phase*1.7) + (0 if self.muted else 0.05*random.random())
            amp = max(0.05, min(amp, 1.0))

            w = int(W * (0.18 + amp*0.70))
            grad = QLinearGradient(0, y0, w, y0)
            grad.setColorAt(0.0, QColor(TOKENS["red"]))
            grad.setColorAt(1.0, QColor(TOKENS["redHot"]))
            p.fillRect(0, y0, w, max(1, y1-y0), QBrush(grad))
            p.fillRect(0, y0+2, max(0, w-4), max(1, y1-y0-4), QColor(TOKENS["redDeep"]))

        seam_w = 6
        for x in range(seam_w):
            p.fillRect(W + x - seam_w, 0, 1, H, QColor(TOKENS["red"]))

        p.end()
