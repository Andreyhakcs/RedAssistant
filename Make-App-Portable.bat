@echo off
setlocal enabledelayedexpansion
title RedAssistant — one‑click build (portable folder)

REM Clean previous build to avoid stale errors
if exist build rd /s /q build
if exist dist rd /s /q dist

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  py -m pip install --upgrade pip wheel
  py -m pip install pyinstaller
  if errorlevel 1 (
    echo Failed to install PyInstaller. Press any key to exit.
    pause >nul
    exit /b 1
  )
)

echo.
echo Creating .env if missing...
if not exist ".env" (
  > ".env" echo OPENAI_API_KEY=
)

echo.
echo Building portable app folder...
py -m PyInstaller --noconfirm --clean RedAssistant.spec
if errorlevel 1 (
  echo.
  echo Build failed. Check messages above.
  echo Частая причина: в .spec ссылались на несуществующую папку 'config'. В этой версии это исправлено.
  pause
  exit /b 1
)

echo.
if not exist "dist\RedAssistant" (
  echo ERROR: dist\RedAssistant not found.
  pause
  exit /b 1
)

echo Copying .env into output...
copy /Y ".env" "dist\RedAssistant\.env" >nul

echo.
echo Launching app...
start "" "dist\RedAssistant\RedAssistant.exe"

echo Done. Output in dist\RedAssistant
pause
