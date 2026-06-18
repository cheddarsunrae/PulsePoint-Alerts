#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium

mkdir -p "$HOME/.pulsepoint-alerts"
cp -f assets/alert.wav "$HOME/.pulsepoint-alerts/alert.wav"

echo "Install complete."
echo "Runtime config folder: $HOME/.pulsepoint-alerts"
echo "Run installers/linux/start.sh"
