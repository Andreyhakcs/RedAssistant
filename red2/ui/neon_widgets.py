
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QBrush
from PySide6.QtWidgets import QWidget

class NeonSideBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._state = "idle"  # idle|listening|speaking
        self._t = 0
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.setFixedWidth(14)

    def set_level(self, v: float):
        self._level = max(0.0, min(1.0, float(v)))
        self.update()

    def set_state(self, s: str):
        self._state = s
        self.update()

    def _tick(self):
        self._t = (self._t + 1) % 10000
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = self.width(); h = self.height()
        p.fillRect(self.rect(), QColor(10,12,18))
        bars = 10; gap = 3; bw = w - 6
        for i in range(bars):
            y = h - 6 - i * (gap + 10)
            bar_h = 8
            if self._state == "idle":
                amp = 0.12
            elif self._state == "listening":
                amp = 0.25 + 0.6*self._level
            else:
                amp = 0.45
            amp += 0.1*((self._t/7 + i*0.9) % 2 > 1) * (1 if self._state!="idle" else 0)
            amp = max(0.08, min(1.0, amp))
            bh = int(bar_h * (0.5 + 0.5*amp))
            rect = QRectF(3, y, bw, bh)
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QColor("#ff0033"))
            grad.setColorAt(1.0, QColor("#ff1a8a"))
            p.fillRect(rect, QBrush(grad))
        p.setPen(QColor(255,0,51,120))
        p.drawRect(self.rect().adjusted(0,0,-1,-1))
        p.end()
