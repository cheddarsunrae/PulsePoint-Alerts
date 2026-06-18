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


def active_section_text(text: str) -> str | None:
    """Return only the PulsePoint Active section, excluding Recent/closed incidents."""
    match = re.search(
        r"(?ims)(?:^|\n)\s*ACTIVE\s*(?:\n|$)(.*?)(?:\n\s*RECENT\b.*(?:\n|$)|\Z)",
        text,
    )
    if not match:
        return None
    return match.group(1)


def normalize_incident_text(text: str) -> str:
    cleaned = text.upper()
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b", "", cleaned)
    cleaned = re.sub(r"\b\d+\s*(MIN|MINS|MINUTE|MINUTES)\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def summarize_incident_block(block: str, max_chars: int = 700) -> str:
    """Create a compact call-detail summary suitable for phone push messages."""
    lines: list[str] = []
    seen: set[str] = set()

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = re.sub(r"\s+", " ", line)
        key = normalized.upper()
        if key in seen:
            continue
        seen.add(key)
        lines.append(normalized)

    summary = "\n".join(lines[:14]).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3].rstrip() + "..."
    return summary


def active_unit_incident_signatures(
    active_text: str,
    unit_re: re.Pattern[str] | None,
) -> tuple[dict[str, str], set[str]]:
    """Return signature->incident text and units found in the Active section."""
    if unit_re is None:
        return {}, set()

    lines = [line.strip() for line in active_text.splitlines() if line.strip()]
    signatures: dict[str, str] = {}
    units_found: set[str] = set()

    for index, line in enumerate(lines):
        matches = list(unit_re.finditer(line.upper()))
        if not matches:
            continue

        for match in matches:
            units_found.add(match.group(1).upper())

        start = max(0, index - 8)
        end = min(len(lines), index + 9)
        block = "\n".join(lines[start:end])
        normalized = normalize_incident_text(block)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        signatures[digest] = block

    return signatures, units_found


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
    previously_present_signatures: set[str] = set()
    baseline_hash: str | None = None
    unit_mode_baseline_captured = False
    last_refresh = 0.0

    try:
        with sync_playwright() as p:
            cfg = load_config()
            browser = p.chromium.launch(headless=bool(cfg.get("headless", True)))
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

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

                    if state.consume_manual_refresh():
                        state.log("Manual PulsePoint refresh requested.")
                        page.reload(wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(5000)
                        state.mark_refresh()
                        last_refresh = time.time()

                    text = page.locator("body").inner_text(timeout=10000)
                    state.mark_check()
                    upper_text = text.upper()
                    now = time.time()

                    if test_mode:
                        state.mark_success(None)
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
                        active_signatures: dict[str, str] = {}
                        active_text = active_section_text(text)
                        active_section_found = active_text is not None
                        state.mark_success(active_section_found)

                        if active_text is None:
                            state.log(
                                "Active section not found; skipping unit scan this cycle "
                                "to avoid matching Recent/closed incidents."
                            )
                        else:
                            active_signatures, found_units = active_unit_incident_signatures(active_text, unit_re)

                        current_signatures = set(active_signatures)

                        if not unit_mode_baseline_captured:
                            previously_present_units = found_units
                            previously_present_signatures = current_signatures
                            unit_mode_baseline_captured = True
                            if found_units:
                                state.log(
                                    "Unit mode baseline captured. Existing active incident signatures "
                                    f"will not alert until a new signature appears. Units: {', '.join(sorted(found_units))}"
                                )
                            else:
                                state.log("Unit mode baseline captured. No monitored units currently visible.")
                        else:
                            new_signatures = current_signatures - previously_present_signatures

                            if new_signatures and now - last_alert_time >= cooldown_seconds:
                                new_units: set[str] = set()
                                if unit_re:
                                    for signature in new_signatures:
                                        for match in unit_re.finditer(active_signatures.get(signature, "").upper()):
                                            new_units.add(match.group(1).upper())

                                alert_units = new_units or found_units
                                detail_blocks = [
                                    summarize_incident_block(active_signatures.get(signature, ""))
                                    for signature in sorted(new_signatures)
                                ]
                                details = "\n\n".join(block for block in detail_blocks if block)

                                reason = f"New active incident for unit(s): {', '.join(sorted(alert_units))}"
                                if details:
                                    reason = f"{reason}\n\nCall details:\n{details}"

                                trigger_alert(reason, state)
                                last_alert_time = now

                            previously_present_units = found_units
                            previously_present_signatures = current_signatures

                    state.log(
                        f"Checked. Mode={'TEST' if test_mode else 'UNIT'}; "
                        f"Units present={', '.join(sorted(previously_present_units)) if previously_present_units else 'none'}"
                    )

                    if now - last_refresh >= refresh_seconds:
                        page.reload(wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(5000)
                        state.mark_refresh()
                        last_refresh = now
                        state.log("PulsePoint page refreshed.")

                    time.sleep(poll_seconds)

                except Exception as exc:
                    state.log(f"Monitor error: {exc}. Reloading page.")
                    state.mark_error(str(exc))
                    try:
                        page.reload(wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(5000)
                    except Exception as reload_error:
                        state.log(f"Reload failed: {reload_error}")
                        state.mark_error(f"Reload failed: {reload_error}")
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


