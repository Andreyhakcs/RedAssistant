# -*- coding: utf-8 -*-
"""
Fullscreen splash with configurable duration and scaling.
- Put your video in assets/splash.mp4
- By default: FULLSCREEN = True, DURATION_MS = 8000 (8s), ASPECT_COVER = False (show whole video)
You can change the variables below without touching the rest of the code.
"""
from pathlib import Path
from typing import Optional, Callable
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QMainWindow, QApplication, QHBoxLayout,
    QSizePolicy
)

# --- Settings you can tweak ---
FULLSCREEN = True        # True = во весь экран; False = окно
DURATION_MS = 8000       # длительность заставки (мс)
ASPECT_COVER = False     # False = показать видео целиком (с полями), True = заполнить экран (вырезая края)
WINDOW_SIZE = (1280, 720)  # размер окна, если FULLSCREEN = False

# Optional multimedia (for mp4)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    _HAS_QTMULTIMEDIA = True
except Exception:
    _HAS_QTMULTIMEDIA = False

class _NeonPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(720, 420)
        self.setStyleSheet("background: transparent;")
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(10,10,-10,-10)
        p.setBrush(QColor(12,12,14)); p.setPen(Qt.NoPen); p.drawRoundedRect(r, 24, 24)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, QColor("#FF0033")); grad.setColorAt(1.0, QColor("#FF1A8A"))
        p.setBrush(Qt.NoBrush); p.setPen(QColor(255,0,51,200)); p.drawRoundedRect(r, 24, 24)

class SplashWindow(QMainWindow):
    """
    Заставка с видео. На Windows окно с видео — НЕ прозрачное, иначе QVideoWidget даёт чёрный экран.
    Параметр min_ms из app.py игнорируется — используется DURATION_MS (чтобы не менять app.py).
    """
    def __init__(self, video_path: Optional[Path], min_ms: int = 5000,
                 on_done: Optional[Callable[[], None]] = None):
        super().__init__()
        self._min_ms = max(1000, int(DURATION_MS))  # всегда берём из настроек выше
        self._on_done = on_done
        self._ready = False

        used_video = False
        video_path = Path(video_path) if video_path else None

        # Корневой контейнер
        root = QWidget(self)
        lay = QVBoxLayout(root); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        self.setCentralWidget(root)

        # Попытка видео
        if video_path and video_path.exists() and _HAS_QTMULTIMEDIA:
            try:
                # для видео — непрозрачный фон
                flags = Qt.FramelessWindowHint | Qt.Tool | Qt.SplashScreen
                self.setWindowFlags(flags)
                self.setStyleSheet("background: black;")
                self._video = QVideoWidget(self)
                self._video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

                try:
                    mode = (Qt.AspectRatioMode.KeepAspectRatioByExpanding
                            if ASPECT_COVER else Qt.AspectRatioMode.KeepAspectRatio)
                    self._video.setAspectRatioMode(mode)
                except Exception:
                    pass

                lay.addWidget(self._video, 1)
                self._audio = QAudioOutput(self); self._audio.setVolume(0.0)  # mute
                self._player = QMediaPlayer(self)
                self._player.setAudioOutput(self._audio)
                self._player.setVideoOutput(self._video)
                self._player.setSource(QUrl.fromLocalFile(str(video_path)))
                QTimer.singleShot(0, self._player.play)
                used_video = True
            except Exception:
                used_video = False

        if not used_video:
            # Фоллбэк: неоновая панель
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.SplashScreen)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            panel = _NeonPanel(self)
            lay.addWidget(panel, 1)

        # Нижняя строка статуса + совет
        bar = QWidget(self); bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(18, 10, 18, 12)
        bar.setStyleSheet("background: rgba(0,0,0,110);")
        self.status = QLabel("Запуск…", bar); self.status.setStyleSheet("color:#eee; font-size:14px;")
        self.tip = QLabel("Совет: Ctrl+3 — описание экрана + PTT.", bar); self.tip.setStyleSheet("color:#f06; font-size:12px;")
        bar_l.addWidget(self.status); bar_l.addStretch(1); bar_l.addWidget(self.tip)
        lay.addWidget(bar, 0)

        # Размер/режим
        if FULLSCREEN:
            self.showFullScreen()
        else:
            w, h = WINDOW_SIZE
            self.resize(max(640,w), max(360,h))
            self._center()

        # Таймеры
        self._min_timer = QTimer(self); self._min_timer.setSingleShot(True)
        self._min_timer.timeout.connect(self._try_finish)
        self._min_timer.start(self._min_ms)

        # Ротация советов
        self._tips = [
            "Совет: Ctrl+3 — описание экрана + PTT.",
            "Совет: «переведи текст» — переведу OCR с экрана.",
            "Совет: если хоткей не ловится — запусти от администратора.",
        ]
        self._tip_i = 0
        self._tip_timer = QTimer(self); self._tip_timer.timeout.connect(self._next_tip); self._tip_timer.start(1800)

    def keyPressEvent(self, e: QKeyEvent):
        # ESC — пропустить заставку
        if e.key() == Qt.Key_Escape:
            self._finish()
        else:
            super().keyPressEvent(e)

    def _next_tip(self):
        self._tip_i = (self._tip_i + 1) % len(self._tips)
        self.tip.setText(self._tips[self._tip_i])

    def _center(self):
        g = QApplication.primaryScreen().availableGeometry()
        self.move(g.center().x()-self.width()//2, g.center().y()-self.height()//2)

    def set_status(self, text: str):
        self.status.setText(text)

    def ready(self):
        self._ready = True; self._try_finish()

    def _try_finish(self):
        if self._ready and self._min_timer.isActive():
            return  # ждём DURATION_MS
        if self._ready or not self._min_timer.isActive():
            self._finish()

    def _finish(self):
        try:
            if hasattr(self, "_player"): self._player.stop()
        except Exception: pass
        self.close()
        if self._on_done: self._on_done()
