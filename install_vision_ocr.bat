@echo off
py -m pip install --upgrade pip
py -m pip install pytesseract pillow
py -m pip install QHotkey keyboard pynput
echo.
echo Если Tesseract не установлен, скачай и установи Windows Tesseract OCR.
echo По умолчанию ищется: "C:\Program Files\Tesseract-OCR\tesseract.exe".
echo Если другой путь, создай переменную окружения TESSERACT_PATH.
pause
