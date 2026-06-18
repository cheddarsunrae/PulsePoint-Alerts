@echo off
cd /d %~dp0\..\..

echo Installing PulsePoint Alert Monitor...
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium

echo.
echo Preparing runtime folder...
if not exist C:\pulsepoint-alert mkdir C:\pulsepoint-alert

echo Copying default alert sound...
copy /Y assets\alert.wav C:\pulsepoint-alert\alert.wav >nul

echo.
echo Install complete.
echo Runtime config folder: C:\pulsepoint-alert
echo Start the app with installers\windows\start.bat
pause
