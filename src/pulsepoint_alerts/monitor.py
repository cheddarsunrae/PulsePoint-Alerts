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


INCIDENT_TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?$", re.I)
ACTIVE_COUNT_RE = re.compile(r"^\(\d+\)$")
UNIT_ONLY_RE = re.compile(r"^[\?\^]?\s*[A-Z]{1,6}\d{1,5}$", re.I)


def build_unit_regex(units: list[str]) -> re.Pattern[str] | None:
    escaped = [re.escape(u.upper()) for u in units if u.strip()]
    if not escaped:
        return None
    pattern = rf"(?<![A-Z0-9])[\?\^]?\s*({'|'.join(escaped)})(?![A-Z0-9])"
    return re.compile(pattern, re.I)


def unit_baseline_key(units: list[str]) -> tuple[str, ...]:
    """Return a stable key for the monitored unit set.

    The key ignores order, whitespace, and case so simple CSV reordering does
    not force an unnecessary baseline reset.
    """
    return tuple(sorted({unit.strip().upper() for unit in units if unit.strip()}))


def reset_unit_baseline_if_units_changed(
    current_units: list[str],
    last_units_key: tuple[str, ...],
    baseline_captured: bool,
    previous_units: set[str],
    previous_signatures: set[str],
) -> tuple[tuple[str, ...], bool, set[str], set[str], bool]:
    """Reset unit-mode baseline state when the configured monitored units change."""
    current_key = unit_baseline_key(current_units)
    if current_key == last_units_key:
        return last_units_key, baseline_captured, previous_units, previous_signatures, False

    return current_key, False, set(), set(), True


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
    cleaned = re.sub(r"\(\d+\)", "", cleaned)
    cleaned = re.sub(r"(?<![A-Z0-9])[\?\^]\s*(?=[A-Z]{1,6}\d{1,5}\b)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def incident_signature_text(block: str) -> str:
    """Return stable text used for incident identity.

    Unit-only lines are intentionally ignored so responder-list changes,
    unit-status marker changes, or unit ordering changes do not create
    false new incident signatures.
    """
    signature_lines: list[str] = []

    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ACTIVE_COUNT_RE.match(line):
            continue
        if UNIT_ONLY_RE.match(line):
            continue
        signature_lines.append(line)

    return normalize_incident_text("\n".join(signature_lines))


def split_active_incident_blocks(active_text: str) -> list[str]:
    """Split the PulsePoint Active section into incident-sized blocks.

    PulsePoint Web text generally presents an incident as:
    call type
    time
    address/location
    units...

    If incident boundaries cannot be identified, return no blocks rather than
    bundling unrelated incidents together.
    """
    lines = [
        line.strip()
        for line in active_text.splitlines()
        if line.strip() and not ACTIVE_COUNT_RE.match(line.strip())
    ]

    if not lines:
        return []

    starts: list[int] = []
    for index in range(len(lines) - 1):
        current = lines[index]
        next_line = lines[index + 1]
        if INCIDENT_TIME_RE.match(next_line) and not INCIDENT_TIME_RE.match(current):
            starts.append(index)

    if not starts:
        return []

    blocks: list[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block_lines = lines[start:end]
        if block_lines:
            blocks.append("\n".join(block_lines))

    return blocks

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
    """Return signature->incident text and units found in monitored Active incidents."""
    if unit_re is None:
        return {}, set()

    signatures: dict[str, str] = {}
    units_found: set[str] = set()

    for block in split_active_incident_blocks(active_text):
        matches = list(unit_re.finditer(block.upper()))
        if not matches:
            continue

        for match in matches:
            units_found.add(match.group(1).upper())

        stable_text = incident_signature_text(block)
        if not stable_text:
            continue

        digest = hashlib.sha256(stable_text.encode("utf-8")).hexdigest()
        signatures[digest] = block

    return signatures, units_found


def maybe_record_active_missing_snapshot(
    state: RuntimeState,
    page_text: str,
    snapshot_already_saved: bool,
) -> bool:
    """Record one full-page diagnostic snapshot per missing-Active streak."""
    if snapshot_already_saved:
        return True

    snapshot_path = state.record_debug_snapshot("active-section-missing", page_text)
    if snapshot_path is not None:
        state.log(f"Debug snapshot saved for missing Active section: {snapshot_path}")
    else:
        state.log("Debug snapshot could not be saved for missing Active section.")

    return True

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
    active_missing_snapshot_saved = False
    last_unit_baseline_key = unit_baseline_key(units)

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
                    (
                        last_unit_baseline_key,
                        unit_mode_baseline_captured,
                        previously_present_units,
                        previously_present_signatures,
                        unit_list_changed,
                    ) = reset_unit_baseline_if_units_changed(
                        units,
                        last_unit_baseline_key,
                        unit_mode_baseline_captured,
                        previously_present_units,
                        previously_present_signatures,
                    )
                    if unit_list_changed:
                        state.log(
                            "Monitored unit list changed while monitor is running; "
                            "recapturing unit baseline before alerting."
                        )

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
                            active_missing_snapshot_saved = maybe_record_active_missing_snapshot(
                                state,
                                text,
                                active_missing_snapshot_saved,
                            )
                        else:
                            active_missing_snapshot_saved = False
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

                                evidence = {
                                    "source": "monitor",
                                    "agency_ids": agency_ids,
                                    "configured_units": list(units),
                                    "matched_units": sorted(alert_units),
                                    "new_signatures": sorted(new_signatures),
                                    "new_incident_blocks": {
                                        signature: active_signatures.get(signature, "")
                                        for signature in sorted(new_signatures)
                                    },
                                    "current_signatures": sorted(current_signatures),
                                    "previously_present_signatures": sorted(previously_present_signatures),
                                    "active_section_found": active_section_found,
                                    "active_section_text": active_text or "",
                                    "signature_method": "incident-block-stable-text-with-unit-only-lines-ignored",
                                }

                                trigger_alert(reason, state, evidence=evidence)
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


