
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QSlider, QCheckBox, QPushButton, QFormLayout, QDialogButtonBox
)
from . import user_prefs
from ..core import tts as core_tts

EDGE_VOICES = [
    ("ru-RU-SvetlanaNeural", "Светлана (ru-RU)"),
    ("ru-RU-DmitryNeural", "Дмитрий (ru-RU)"),
    ("en-US-AriaNeural", "Aria (en-US)"),
    ("en-US-JennyNeural", "Jenny (en-US)"),
    ("en-US-GuyNeural", "Guy (en-US)"),
    ("en-GB-LibbyNeural", "Libby (en-GB)"),
    ("en-GB-RyanNeural", "Ryan (en-GB)"),
    ("uk-UA-PolinaNeural", "Polina (uk-UA)"),
    ("uk-UA-OstapNeural",  "Ostap (uk-UA)"),
]

def _list_system_voices():
    voices = [("", "System default")]
    try:
        import pyttsx3
        eng = pyttsx3.init()
        for v in eng.getProperty("voices") or []:
            voices.append((getattr(v, "id", ""), getattr(v, "name", "Voice")))
    except Exception:
        pass
    # убрать дубли
    seen=set(); out=[]
    for vid, name in voices:
        k=vid or "_default"
        if k in seen: continue
        seen.add(k); out.append((vid,name))
    return out

class SettingsDialog(QDialog):
    changed = Signal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — Red Assistant")
        self.setModal(True); self.setMinimumWidth(560)
        self.prefs = user_prefs.load()

        v = QVBoxLayout(self); v.setContentsMargins(16,16,16,16); v.setSpacing(12)
        form = QFormLayout(); form.setLabelAlignment(Qt.AlignLeft); form.setFormAlignment(Qt.AlignTop)

        # Model
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["gpt-4o-mini","gpt-4o","gpt-4.1-mini","o4-mini"])
        self.cmb_model.setCurrentText(self.prefs.get("model","gpt-4o-mini"))

        # Base URL
        self.ed_base = QLineEdit(self.prefs.get("base_url","https://api.openai.com/v1"))

        # Engine
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["edge","system"])
        self.cmb_engine.setCurrentText(self.prefs.get("tts_engine","edge"))
        self.cmb_engine.currentTextChanged.connect(self._refresh_voices)

        # TTS sliders
        self.sld_rate = QSlider(Qt.Horizontal); self.sld_rate.setRange(120,220); self.sld_rate.setValue(int(self.prefs.get("tts_rate",175)))
        self.sld_vol  = QSlider(Qt.Horizontal); self.sld_vol.setRange(20,100); self.sld_vol.setValue(int(float(self.prefs.get("tts_volume",0.9))*100))

        # Voices
        self.cmb_voice = QComboBox()
        self._refresh_voices(self.cmb_engine.currentText())

        # OCR
        self.cmb_ocr = QComboBox(); self.cmb_ocr.addItems(["auto","eng","rus","ukr","deu","spa","fra"])
        self.cmb_ocr.setCurrentText(self.prefs.get("ocr_lang","auto"))

        # Splash
        self.chk_splash = QCheckBox("Show splash on start")
        self.chk_splash.setChecked(bool(self.prefs.get("show_splash", True)))

        # Hotkeys (read-only)
        self.lbl_ptt = QLabel(self.prefs.get("ptt_key","ctrl+3"))
        self.lbl_vis = QLabel(self.prefs.get("vision_key","ctrl+4"))

        form.addRow("LLM Model:", self.cmb_model)
        form.addRow("Base URL:", self.ed_base)
        form.addRow("TTS Engine:", self.cmb_engine)
        form.addRow("TTS Rate:", self.sld_rate)
        form.addRow("TTS Volume:", self.sld_vol)
        form.addRow("TTS Voice:", self.cmb_voice)
        form.addRow("OCR Language:", self.cmb_ocr)
        form.addRow("Splash:", self.chk_splash)
        form.addRow("PTT hotkey:", self.lbl_ptt)
        form.addRow("Vision hotkey:", self.lbl_vis)

        v.addLayout(form)

        # Test
        test_row = QHBoxLayout()
        self.btn_tts_test = QPushButton("Test TTS")
        self.btn_tts_test.clicked.connect(self._test_tts)
        test_row.addWidget(self.btn_tts_test); test_row.addStretch(1); v.addLayout(test_row)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        btns.accepted.connect(self._save); btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._reset)
        v.addWidget(btns)

    def _refresh_voices(self, engine: str):
        self.cmb_voice.clear()
        if engine == "edge":
            for vid, label in EDGE_VOICES:
                self.cmb_voice.addItem(label, userData=vid)
            cur = self.prefs.get("tts_voice","ru-RU-SvetlanaNeural")
            ids = [self.cmb_voice.itemData(i) for i in range(self.cmb_voice.count())]
            self.cmb_voice.setCurrentIndex(ids.index(cur) if cur in ids else 0)
        else:
            for vid, name in _list_system_voices():
                self.cmb_voice.addItem(name, userData=vid)
            cur = self.prefs.get("tts_voice","")
            ids = [self.cmb_voice.itemData(i) for i in range(self.cmb_voice.count())]
            self.cmb_voice.setCurrentIndex(ids.index(cur) if cur in ids else 0)

    def _current_voice_id(self) -> str:
        i = max(0, self.cmb_voice.currentIndex())
        return self.cmb_voice.itemData(i) or ""

    def _test_tts(self):
        t = core_tts.TTS(
            rate=int(self.sld_rate.value()),
            volume=max(0.2, min(1.0, self.sld_vol.value()/100.0)),
            voice=self._current_voice_id() or None
        )
        try:
            t.speak("Это тест выбранного голоса.", on_done=lambda: None)
        except Exception as e:
            print("TTS test error:", e)

    def _reset(self):
        self.cmb_model.setCurrentText("gpt-4o-mini")
        self.ed_base.setText("https://api.openai.com/v1")
        self.cmb_engine.setCurrentText("edge")
        self.sld_rate.setValue(175); self.sld_vol.setValue(90)
        self._refresh_voices("edge")
        self.cmb_ocr.setCurrentText("auto")
        self.chk_splash.setChecked(True)

    def _save(self):
        prefs = {
            "model": self.cmb_model.currentText().strip(),
            "base_url": self.ed_base.text().strip() or "https://api.openai.com/v1",
            "tts_engine": self.cmb_engine.currentText().strip(),
            "tts_rate": int(self.sld_rate.value()),
            "tts_volume": max(0.2, min(1.0, self.sld_vol.value()/100.0)),
            "tts_voice": self._current_voice_id(),
            "ocr_lang": self.cmb_ocr.currentText().strip(),
            "show_splash": bool(self.chk_splash.isChecked()),
            "ptt_key": self.prefs.get("ptt_key","ctrl+3"),
            "vision_key": self.prefs.get("vision_key","ctrl+4"),
        }
        user_prefs.save(prefs)
        self.changed.emit(prefs)
        self.accept()
