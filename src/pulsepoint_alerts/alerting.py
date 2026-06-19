# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from .config import load_config, normalize_alert_profile
from .runtime import RuntimeState


def _play_sound_once(sound_file: str, state: RuntimeState) -> None:
    if os.name == "nt":
        import winsound
        try:
            winsound.PlaySound(sound_file, winsound.SND_FILENAME)
        except Exception as exc:
            state.log(f"Sound error: {exc}")
            try:
                winsound.Beep(1000, 1000)
            except Exception:
                pass
        return

    # macOS and Linux fallbacks. Best effort.
    candidates = []
    if os.uname().sysname == "Darwin":
        candidates = [["afplay", sound_file]]
    else:
        candidates = [["paplay", sound_file], ["pw-play", sound_file], ["aplay", sound_file]]
    for cmd in candidates:
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    state.log("No supported audio player found for this platform.")


def send_pushover(
    title: str,
    message: str,
    state: RuntimeState,
    emergency: bool = True,
    priority_override: int | None = None,
) -> bool:
    cfg = load_config()
    token = cfg.get("pushover_app_token", "").strip()
    user = cfg.get("pushover_user_key", "").strip()
    if not token or not user:
        state.log("Pushover skipped: missing app token or user key.")
        return False

    priority = (
        int(priority_override)
        if priority_override is not None
        else int(cfg.get("pushover_priority", 2 if emergency else 1))
    )
    retry = max(30, int(cfg.get("pushover_retry_seconds", 30)))
    expire = min(10800, max(60, int(cfg.get("pushover_expire_seconds", 1800))))

    payload: dict[str, Any] = {
        "token": token,
        "user": user,
        "title": title,
        "message": message,
        "priority": str(priority),
        "sound": cfg.get("pushover_sound", "persistent") or "persistent",
    }
    if cfg.get("pushover_device", "").strip():
        payload["device"] = cfg["pushover_device"].strip()
    if priority == 2:
        payload["retry"] = str(retry)
        payload["expire"] = str(expire)

    try:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status == 200:
                state.log("Phone push sent via Pushover.")
                return True
            state.log(f"Pushover returned HTTP {resp.status}: {body}")
            return False
    except Exception as exc:
        state.log(f"Pushover send error: {exc}")
        return False


def send_ntfy(
    title: str,
    message: str,
    state: RuntimeState,
    priority_override: int | None = None,
    allow_call: bool = True,
) -> bool:
    cfg = load_config()
    topic = cfg.get("ntfy_topic", "").strip()
    server = cfg.get("ntfy_server", "https://ntfy.sh").strip().rstrip("/")
    if not topic:
        state.log("ntfy skipped: missing topic.")
        return False
    url = f"{server}/{urllib.parse.quote(topic)}"
    headers = {
        "Title": title,
        "Priority": str(int(priority_override if priority_override is not None else cfg.get("ntfy_priority", 5))),
        "Tags": cfg.get("ntfy_tags", "rotating_light,ambulance"),
    }
    if cfg.get("ntfy_token", "").strip():
        headers["Authorization"] = f"Bearer {cfg['ntfy_token'].strip()}"
    if allow_call and cfg.get("ntfy_call", "").strip():
        headers["Call"] = cfg["ntfy_call"].strip()
    try:
        req = urllib.request.Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if 200 <= resp.status < 300:
                state.log("Phone push sent via ntfy.")
                return True
            state.log(f"ntfy returned HTTP {resp.status}: {body}")
            return False
    except Exception as exc:
        state.log(f"ntfy send error: {exc}")
        return False


def phone_push_reason(reason: str, cfg: dict[str, Any]) -> str:
    """Return the phone-safe alert reason based on privacy settings."""
    if bool(cfg.get("include_call_details_in_phone_push", True)):
        return reason

    marker = "\n\nCall details:"
    if marker in reason:
        return reason.split(marker, 1)[0].strip() + "\n\nCall details hidden by privacy setting."

    return reason


def send_phone_push_for_alert(reason: str, state: RuntimeState, profile: str = "alert_me") -> None:
    cfg = load_config()
    profile = normalize_alert_profile(profile)
    provider = cfg.get("push_provider", "pushover")
    if provider == "none":
        state.log("Phone push skipped: provider set to none.")
        return
    tracking = profile == "track_units"
    title = "PulsePoint Unit Tracking Update" if tracking else "PulsePoint Unit Alert"
    phone_reason = phone_push_reason(reason, cfg)
    message = f"{phone_reason}\n\nPulsePoint Alert Monitor triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
    if provider in ("pushover", "both"):
        send_pushover(
            title,
            message,
            state,
            emergency=not tracking,
            priority_override=-1 if tracking else None,
        )
    if provider in ("ntfy", "both"):
        send_ntfy(
            title,
            message,
            state,
            priority_override=2 if tracking else None,
            allow_call=not tracking,
        )


def play_alert_loop(reason: str, state: RuntimeState) -> None:
    cfg = load_config()
    sound_file = cfg["sound_file"]
    alert_mode = cfg.get("alert_mode", "until_ack")
    duration = int(cfg.get("alert_duration_seconds", 30))
    with state.lock:
        state.alert_active = True
        state.alert_reason = reason
    state.log(f"ALERT ACTIVE: {reason}")
    started = time.time()

    if os.name == "nt":
        import winsound
        try:
            winsound.PlaySound(
                sound_file,
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
            )
            while not state.alert_stop.is_set():
                if alert_mode != "until_ack" and time.time() - started >= duration:
                    break
                time.sleep(0.25)
        except Exception as exc:
            state.log(f"Sound error: {exc}")
            try:
                winsound.Beep(1000, 1000)
            except Exception:
                pass
        finally:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
    else:
        while not state.alert_stop.is_set():
            if alert_mode != "until_ack" and time.time() - started >= duration:
                break
            _play_sound_once(sound_file, state)
            time.sleep(0.25)

    with state.lock:
        state.alert_active = False
        state.alert_reason = ""
    state.log("Alert silenced.")


def trigger_desktop_alert(reason: str, state: RuntimeState) -> None:
    """Trigger only the local desktop/laptop audible alert."""
    with state.lock:
        already_active = state.alert_active
        if not already_active:
            state.alert_active = True
            state.alert_reason = reason

    if already_active:
        state.log(f"Alert already active. Additional desktop test ignored: {reason}")
        return
    cfg = load_config()
    profile = normalize_alert_profile(cfg.get("alert_profile"))
    state.record_alert(
        reason,
        desktop_enabled=True,
        phone_enabled=False,
        source="manual_desktop",
        profile=profile,
        ack_required=True,
    )
    state.alert_stop.clear()
    thread = threading.Thread(target=play_alert_loop, args=(reason, state), daemon=True)
    thread.start()


def trigger_alert(reason: str, state: RuntimeState, evidence: dict[str, Any] | None = None) -> None:
    cfg = load_config()
    profile = normalize_alert_profile(cfg.get("alert_profile"))
    tracking = profile == "track_units"
    desktop_enabled = bool(cfg.get("desktop_alert_enabled", True)) and not tracking
    phone_enabled = bool(cfg.get("phone_alert_enabled", True))

    if desktop_enabled:
        with state.lock:
            already_active = state.alert_active
            if not already_active:
                state.alert_active = True
                state.alert_reason = reason

        if already_active:
            state.log(f"Alert already active. Additional trigger ignored: {reason}")
            return

    evidence_payload = None
    if evidence is not None:
        evidence_payload = dict(evidence)
        evidence_payload["alert_profile"] = profile
    evidence_id = state.record_alert_evidence(evidence_payload) if evidence_payload is not None else ""
    state.record_alert(
        reason,
        desktop_enabled=desktop_enabled,
        phone_enabled=phone_enabled,
        source="monitor",
        evidence_id=evidence_id,
        profile=profile,
        ack_required=not tracking,
    )

    if phone_enabled:
        send_phone_push_for_alert(reason, state, profile=profile)
    else:
        state.log("Phone push skipped: phone alert channel disabled.")

    if desktop_enabled:
        state.alert_stop.clear()
        thread = threading.Thread(target=play_alert_loop, args=(reason, state), daemon=True)
        thread.start()
    else:
        if tracking:
            state.log("Desktop/laptop alert skipped: Track Unit(s) profile does not use looping desktop alerts.")
        else:
            state.log("Desktop/laptop alert skipped: desktop alert channel disabled.")

    if not desktop_enabled and not phone_enabled:
        state.log(f"Alert recorded but all alert channels are disabled: {reason}")


def silence_alert(state: RuntimeState) -> None:
    state.alert_stop.set()
    state.acknowledge_latest_alert()
    with state.lock:
        state.alert_active = False
        state.alert_reason = ""
    if os.name == "nt":
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
