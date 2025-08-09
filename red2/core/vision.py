# -*- coding: utf-8 -*-
import base64, os, io, ctypes
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from . import llm

def _active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value.strip()
    except Exception:
        return ""

def grab_screen_png_bytes() -> bytes:
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("No screen found")
    pix = screen.grabWindow(0)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    ok = pix.save(buf, "PNG")
    buf.close()
    if not ok:
        raise RuntimeError("Failed to save pixmap to PNG")
    return bytes(ba)

def try_ocr_from_png(png_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        tcmd = os.getenv("TESSERACT_PATH", "")
        if tcmd:
            pytesseract.pytesseract.tesseract_cmd = tcmd
        img = Image.open(io.BytesIO(png_bytes))
        txt = pytesseract.image_to_string(img, lang=os.getenv("TESSERACT_LANG","eng+rus"))
        txt = (txt or "").strip()
        txt = " ".join(txt.split())
        return txt[:2000]
    except Exception:
        return ""

def describe_screen_via_llm_ultra_brief(png_bytes: bytes, ocr_text: str) -> str:
    try:
        img_b64 = base64.b64encode(png_bytes).decode("utf-8")
        title = _active_window_title()
        sys_prompt = (
            "Опиши экран КРАЙНЕ кратко, одним предложением до 10 слов. "
            "Сначала назови тип и/или приложение (браузер, игра, проводник, YouTube и т.п.), "
            "потом главное действие/состояние. Без вступлений, без лишних слов."
        )
        user_text = "Заголовок активного окна: " + (title or "(нет)") + "\n"
        if ocr_text:
            user_text += "OCR (обрезано): " + ocr_text[:400]
        parts = [
            {"role":"system","content": sys_prompt},
            {"role":"user","content":[
                {"type":"text","text": user_text},
                {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}}
            ]}
        ]
        out = llm.chat(parts)
        return (out or "").strip()
    except Exception as e:
        return f"Не смог получить описание экрана: {type(e).__name__}: {e}"

def quick_screen_context_ultra_brief() -> tuple[str, str, str]:
    png = grab_screen_png_bytes()
    ocr = try_ocr_from_png(png)
    desc = describe_screen_via_llm_ultra_brief(png, ocr)
    title = _active_window_title()
    return desc, (ocr or ""), (title or "")
