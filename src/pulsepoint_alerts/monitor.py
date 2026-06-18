# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import re
import time

from playwright.sync_api import sync_playwright

from .alerting import trigger_alert
from .config import load_config
from .keepawake import set_keep_awake
from .runtime import RuntimeState


def build_unit_regex(units: list[str]) -> re.Pattern[str] | None:
    escaped = [re.escape(u.upper()) for u in units if u.strip()]
    if not escaped:
        return None
    pattern = rf"(?<![A-Z0-9])[\?\^]?\s*({'|'.join(escaped)})(?![A-Z0-9])"
    return re.compile(pattern, re.I)


def page_hash(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip().upper())
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b", "", cleaned)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def monitor_loop(state: RuntimeState) -> None:
    cfg = load_config()
    agency_ids = cfg["agency_ids"].strip()
    units = cfg["units"]

    if not agency_ids:
        state.log("No agency IDs configured. Monitor stopped.")
        with state.lock:
            state.monitor_running = False
        return

    if cfg.get("prevent_sleep", True):
        try:
            set_keep_awake(True, bool(cfg.get("keep_display_on", False)))
            state.log("Sleep prevention enabled while monitor is running.")
        except Exception as exc:
            state.log(f"Sleep prevention error: {exc}")

    url = f"https://web.pulsepoint.org/?agencies={agency_ids}"
    state.log("Starting monitor.")
    state.log(f"PulsePoint URL: {url}")
    state.log(f"Units: {', '.join(units) if units else '(none)'}")
    state.log(f"Push provider: {cfg.get('push_provider', 'pushover')}")

    last_alert_time = 0.0
    previously_present_units: set[str] = set()
    baseline_hash: str | None = None
    last_refresh = 0.0

    try:
        with sync_playwright() as p:
            cfg = load_config()
            browser = p.chromium.launch(headless=bool(cfg.get("headless", True)))
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)

            while not state.monitor_stop.is_set():
                try:
                    cfg = load_config()
                    if cfg.get("prevent_sleep", True):
                        try:
                            set_keep_awake(True, bool(cfg.get("keep_display_on", False)))
                        except Exception as exc:
                            state.log(f"Sleep prevention refresh error: {exc}")

                    units = cfg["units"]
                    poll_seconds = max(5, int(cfg["poll_seconds"]))
                    cooldown_seconds = int(cfg.get("cooldown_seconds", 60))
                    refresh_seconds = int(cfg.get("refresh_seconds", 300))
                    test_mode = bool(cfg.get("test_mode", False))
                    unit_re = build_unit_regex(units)

                    text = page.locator("body").inner_text(timeout=10000)
                    upper_text = text.upper()
                    now = time.time()

                    if test_mode:
                        current_hash = page_hash(upper_text)
                        if baseline_hash is None:
                            baseline_hash = current_hash
                            state.log("Test mode baseline captured. Next page activity/change will alert.")
                        elif current_hash != baseline_hash:
                            if now - last_alert_time >= cooldown_seconds:
                                trigger_alert("Test mode: new PulsePoint page activity/change detected", state)
                                last_alert_time = now
                            baseline_hash = current_hash
                    else:
                        found_units: set[str] = set()
                        if unit_re:
                            for match in unit_re.finditer(upper_text):
                                found_units.add(match.group(1).upper())

                        newly_found = found_units - previously_present_units
                        if newly_found and now - last_alert_time >= cooldown_seconds:
                            trigger_alert(f"Unit(s) found: {', '.join(sorted(newly_found))}", state)
                            last_alert_time = now

                        previously_present_units = found_units

                    state.log(
                        f"Checked. Mode={'TEST' if test_mode else 'UNIT'}; "
                        f"Units present={', '.join(sorted(previously_present_units)) if previously_present_units else 'none'}"
                    )

                    if now - last_refresh >= refresh_seconds:
                        page.reload(wait_until="networkidle", timeout=60000)
                        last_refresh = now
                        state.log("PulsePoint page refreshed.")

                    time.sleep(poll_seconds)

                except Exception as exc:
                    state.log(f"Monitor error: {exc}. Reloading page.")
                    try:
                        page.reload(wait_until="networkidle", timeout=60000)
                    except Exception as reload_error:
                        state.log(f"Reload failed: {reload_error}")
                    time.sleep(max(5, int(load_config().get("poll_seconds", 5))))

            browser.close()

    except Exception as exc:
        state.log(f"Fatal monitor error: {exc}")

    try:
        set_keep_awake(False)
    except Exception:
        pass
    with state.lock:
        state.monitor_running = False
    state.log("Monitor stopped.")
