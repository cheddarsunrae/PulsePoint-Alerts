@echo off
cd /d %~dp0\..\..
echo Installing PulsePoint Alert Monitor...
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium
echo.
echo Install complete.
echo Run installers\windows\start.bat next.
pause
