@echo off
setlocal

REM Windows-only one-click launcher for BB01 Arduino test UI.
REM If needed, choose COM port inside the UI after launch.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
  call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

python -m pip show pyserial >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing pyserial...
  python -m pip install pyserial
  if errorlevel 1 (
    echo [ERROR] Could not install pyserial.
    pause
    exit /b 1
  )
)

python "%SCRIPT_DIR%bb01_arduino_test_ui.py"
if errorlevel 1 (
  echo [ERROR] UI exited with error.
  pause
  exit /b 1
)

endlocal
@echo off
setlocal

REM Windows-only launcher for BB01 Arduino test UI.
REM This script is intended for Windows environments.
REM If you need a different default COM port, select it from the UI after launch.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Optional venv activation if present.
if exist "%SCRIPT_DIR%.venv\Scripts\activate.bat" (
  call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
)

REM Ensure pyserial is available. If install fails, user can run:
REM   pip install pyserial
python -m pip show pyserial >nul 2>&1
if errorlevel 1 (
  echo [INFO] pyserial not found. Installing...
  python -m pip install pyserial
  if errorlevel 1 (
    echo [ERROR] Failed to install pyserial.
    echo Run manually: python -m pip install pyserial
    pause
    exit /b 1
  )
)

python "%SCRIPT_DIR%bb01_arduino_test_ui.py"
if errorlevel 1 (
  echo [ERROR] UI exited with an error.
  pause
  exit /b 1
)

endlocal
