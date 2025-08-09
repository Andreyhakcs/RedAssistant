@echo off
py -m pip install --upgrade pip
py -m pip install pyinstaller
py -m pip install pillow pytesseract QHotkey keyboard pynput
py -m PyInstaller ^
  --name RedAssistant ^
  --onedir ^
  --windowed ^
  --paths . ^
  --collect-all PySide6 ^
  --hidden-import PIL ^
  --hidden-import pytesseract ^
  --add-data "prompts\system_prompt.txt;prompts" ^
  --add-data "red2\ui\style.qss;red2\ui" ^
  run.py
echo.
echo Build finished. Run dist\RedAssistant\RedAssistant.exe
pause
