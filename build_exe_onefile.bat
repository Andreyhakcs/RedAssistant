@echo off
py -m pip install --upgrade pip
py -m pip install pyinstaller
py -m pip install QHotkey keyboard
py -m PyInstaller ^
  --name RedAssistant ^
  --onefile ^
  --windowed ^
  --paths . ^
  --collect-all PySide6 ^
  --collect-data sounddevice --collect-data soundfile ^
  --add-data "prompts\system_prompt.txt;prompts" ^
  --add-data "red2\ui\style.qss;red2\ui" ^
  --icon "assets\red.ico" ^
  --hidden-import qhotkey --hidden-import keyboard ^
  run.py
echo.
echo Build finished. Run dist\RedAssistant.exe
pause
