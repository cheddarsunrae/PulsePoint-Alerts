# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "agency_ids": "",
    "units": ["M231"],
    "poll_seconds": 5,
    "sound_file": "",
    "test_mode": False,
    "alert_profile": "alert_me",
    "alert_mode": "until_ack",
    "alert_duration_seconds": 30,
    "desktop_alert_enabled": True,
    "phone_alert_enabled": True,
    "include_call_details_in_phone_push": True,
    "cooldown_seconds": 60,
    "refresh_seconds": 300,
    "headless": True,
    "prevent_sleep": True,
    "keep_display_on": False,
    "agency_presets": [],
    "unit_presets": [],
    "push_provider": "pushover",
    "pushover_app_token": "",
    "pushover_user_key": "",
    "pushover_device": "",
    "pushover_priority": 2,
    "pushover_retry_seconds": 30,
    "pushover_expire_seconds": 1800,
    "pushover_sound": "persistent",
    "ntfy_server": "https://ntfy.sh",
    "ntfy_topic": "",
    "ntfy_token": "",
    "ntfy_priority": 5,
    "ntfy_tags": "rotating_light,ambulance",
    "ntfy_call": "",
}

ALERT_PROFILES = {"alert_me", "track_units"}


def normalize_alert_profile(value: object) -> str:
    profile = str(value or "").strip().lower()
    return profile if profile in ALERT_PROFILES else "alert_me"


def alert_profile_label(value: object) -> str:
    return "Track Unit(s)" if normalize_alert_profile(value) == "track_units" else "Alert Me"


def app_dir() -> Path:
    override = os.environ.get("PULSEPOINT_ALERT_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(r"C:\pulsepoint-alert")
    return Path.home() / ".pulsepoint-alerts"


def config_path() -> Path:
    return app_dir() / "config.json"


def asset_default_sound() -> str:
    configured = app_dir() / "alert.wav"
    return str(configured)


def normalize_units(units_text: str) -> list[str]:
    return sorted({u.strip().upper() for u in units_text.replace("\n", ",").split(",") if u.strip()})


def ensure_config() -> None:
    app_dir().mkdir(parents=True, exist_ok=True)
    if not config_path().exists():
        cfg = DEFAULT_CONFIG.copy()
        cfg["sound_file"] = asset_default_sound()
        save_config(cfg)


def load_config() -> dict[str, Any]:
    ensure_config()
    with config_path().open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    merged["sound_file"] = asset_default_sound()
    merged.update(cfg)
    if isinstance(merged.get("units"), str):
        merged["units"] = normalize_units(merged["units"])
    if not isinstance(merged.get("agency_presets"), list):
        merged["agency_presets"] = []
    if not isinstance(merged.get("unit_presets"), list):
        merged["unit_presets"] = []
    merged["alert_profile"] = normalize_alert_profile(merged.get("alert_profile"))
    return merged


def save_config(cfg: dict[str, Any]) -> None:
    app_dir().mkdir(parents=True, exist_ok=True)
    with config_path().open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
