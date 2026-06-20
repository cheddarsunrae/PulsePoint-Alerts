# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import platform
import sys
import zipfile
import csv
import io
import threading

from flask import Flask, Response, redirect, request, send_from_directory

from . import __version__
from .alerting import send_ntfy, send_pushover, silence_alert, trigger_alert, trigger_desktop_alert
from .autostart import disable_start_at_login, enable_start_at_login, get_start_at_login_status
from .config import (
    DEFAULT_CONFIG,
    alert_profile_label,
    asset_default_sound,
    config_path,
    load_config,
    normalize_alert_profile,
    normalize_units,
    save_config,
)
from .keepawake import set_keep_awake
from .monitor import active_section_text, active_unit_incident_signatures, build_unit_regex, monitor_loop
from .runtime import RuntimeState

state = RuntimeState()
state.load_alert_history()
state.load_alert_evidence()
STATIC_DIR = Path(__file__).resolve().parent / "static"


def html_escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def checked(value: object) -> str:
    return "checked" if value else ""


def selected(actual: object, expected: object) -> str:
    return "selected" if str(actual) == str(expected) else ""


def help_tip(message: str) -> str:
    return f'<span class="help-tip" tabindex="0">?<span class="help-text">{html_escape(message)}</span></span>'


def units_display(units: list[str] | None) -> str:
    return ", ".join(units or [])





def agency_display(cfg: dict) -> str:
    agency_ids = str(cfg.get("agency_ids", "") or "").strip()
    if not agency_ids:
        return "(none)"

    for preset in cfg.get("agency_presets", []):
        preset_ids = str(preset.get("agency_ids", "") or "").strip()
        preset_name = str(preset.get("name", "") or "").strip()
        if preset_ids == agency_ids and preset_name:
            return f"{agency_ids} ({preset_name})"

    return agency_ids




def unit_set_display(cfg: dict) -> str:
    units = cfg.get("units", [])
    if isinstance(units, str):
        units = normalize_units(units)

    unit_text = units_display(units)
    if not unit_text:
        return "(none)"

    unit_key = ",".join(units)

    for preset in cfg.get("unit_presets", []):
        preset_units = preset.get("units", [])
        if isinstance(preset_units, str):
            preset_units = normalize_units(preset_units)

        preset_key = ",".join(preset_units)
        preset_name = str(preset.get("name", "") or "").strip()

        if preset_key == unit_key and preset_name:
            return f"{unit_text} ({preset_name})"

    return unit_text


def datetime_filename() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def now_local_iso() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")




def timestamp_age_seconds(timestamp: str) -> int | None:
    if not timestamp or timestamp == "never":
        return None

    try:
        from datetime import datetime
        parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        age = int((datetime.now() - parsed).total_seconds())
        return max(0, age)
    except Exception:
        return None


def age_display(timestamp: str) -> str:
    age = timestamp_age_seconds(timestamp)
    if age is None:
        return "never"

    if age < 60:
        return f"{age} sec ago"

    minutes = age // 60
    if minutes < 60:
        return f"{minutes} min ago"

    hours = minutes // 60
    minutes = minutes % 60
    if hours < 24:
        if minutes:
            return f"{hours} hr {minutes} min ago"
        return f"{hours} hr ago"

    days = hours // 24
    hours = hours % 24
    if hours:
        return f"{days} day {hours} hr ago"
    return f"{days} day ago"


def monitor_health_label(
    monitor_running: bool,
    last_success_time: str,
    consecutive_errors: int,
    poll_seconds: int,
) -> tuple[str, str]:
    if not monitor_running:
        return "STOPPED", "status-stopped"

    if consecutive_errors >= 3:
        return "ERROR", "status-alert-active"

    if consecutive_errors > 0:
        return "DEGRADED", "status-warn"

    age = timestamp_age_seconds(last_success_time)
    if age is None:
        return "WAITING", "status-warn"

    stale_after = max((poll_seconds * 2) + 10, 30)
    if age > stale_after:
        return "STALE", "status-alert-active"

    return "HEALTHY", "status-running"


def nav() -> str:
    return """
<nav>
<a href="/">Dashboard</a>
<a href="/first-run">Setup Wizard</a>
<a href="/agencies">Agencies</a>
<a href="/units">Apparatus / Units</a>
<a href="/setup">Monitor Setup</a>
<a href="/alerts">Alerts</a>
<a href="/history">History</a>
<a href="/debug/active">Active Debug</a>
<a href="/config">Config</a>
<a href="/logs">Logs</a>
<a href="/troubleshooting">Troubleshooting</a>
</nav>
"""


def layout(title: str, content: str) -> Response:
    cfg = load_config()
    icon_path = STATIC_DIR / "app.ico"
    icon_version = icon_path.stat().st_mtime_ns if icon_path.exists() else 0
    with state.lock:
        running_text = "RUNNING" if state.monitor_running else "STOPPED"
        active_text = "ACTIVE" if state.alert_active else "INACTIVE"
        reason = state.alert_reason
        last_check_time = state.last_check_time or "never"
        last_success_time = state.last_success_time or "never"
        last_refresh_time = state.last_refresh_time or "never"
        last_error = state.last_error
        consecutive_errors = state.consecutive_errors
        active_section_status = "found" if state.active_section_found else "not found"
    active_agency = html_escape(agency_display(cfg))
    active_units = html_escape(unit_set_display(cfg))
    profile = alert_profile_label(cfg.get("alert_profile"))
    mode = "TEST" if cfg.get("test_mode") else "UNIT"
    status_class = "danger" if state.alert_active else "good"
    monitor_class = "status-running" if state.monitor_running else "status-stopped"
    health_label, health_class = monitor_health_label(state.monitor_running, last_success_time, consecutive_errors, int(cfg.get("poll_seconds", 5)))
    last_check_age = age_display(last_check_time)
    last_success_age = age_display(last_success_time)
    last_refresh_age = age_display(last_refresh_time)
    alert_class = "status-alert-active" if state.alert_active else "status-alert-inactive"
    refresh_tag = '<meta http-equiv="refresh" content="10">' if title == "Dashboard" else ""
    alert_controls = ""
    if state.alert_active:
        alert_controls = f"""
<div class="danger" style="margin: 12px 20px;">
<strong>ALERT ACTIVE:</strong> {html_escape(reason)}
<form method="post" action="/ack" style="display:inline; margin-left: 12px;">
<button type="submit" class="btn-ack btn-ack-active" title="Acknowledge and silence active alert">ACK / Silence Alert</button>
</form>
</div>
"""
    return Response(f"""<!doctype html>
<html><head><title>{html_escape(title)} - PulsePoint Alert Monitor</title>{refresh_tag}
<link rel="icon" href="/static/app.ico?v={icon_version}" sizes="any">
<link rel="shortcut icon" href="/favicon.ico?v={icon_version}">
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; color: #222; }}
header {{ background: #222; color: white; padding: 18px 28px; }} header h1 {{ margin: 0; font-size: 24px; display: flex; align-items: center; gap: 12px; }} .brand-icon {{ width: 36px; height: 36px; object-fit: contain; border-radius: 8px; }}
nav {{ background: #333; padding: 0 20px; }} nav a {{ color: white; display: inline-block; padding: 12px 14px; text-decoration: none; }} nav a:hover {{ background: #555; }}
main {{ max-width: 1100px; margin: 25px auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 1px 6px #ccc; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 14px 0; background: #fff; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
label {{ font-weight: bold; display: block; margin-top: 14px; }}
input[type=text], input[type=password], input[type=number], select {{ width: 100%; padding: 9px; font-size: 16px; box-sizing: border-box; }}
button {{ padding: 10px 16px; font-size: 15px; margin: 6px 6px 6px 0; cursor: pointer; border-radius: 6px; border: 1px solid #999; }}
button:disabled {{ background: #c9c9c9 !important; color: #666 !important; border-color: #aaa !important; cursor: not-allowed; opacity: 0.75; }}
.btn-start {{ background: #28a745; color: white; border-color: #1e7e34; font-weight: bold; }}
.btn-start:hover {{ background: #218838; }}
.btn-stop {{ background: #dc3545; color: white; border-color: #bd2130; font-weight: bold; }}
.btn-stop:hover {{ background: #c82333; }}
@keyframes ackFlash {{
  0%, 100% {{ background: #b00020; color: white; box-shadow: 0 0 0 rgba(176,0,32,0.0); }}
  50% {{ background: #ff1f3d; color: white; box-shadow: 0 0 14px rgba(176,0,32,0.75); }}
}}
.btn-ack {{ background: #b00020; color: white; border-color: #7a0016; font-weight: bold; }}
.btn-ack:hover {{ background: #8b0018; }}
.btn-ack-active {{ animation: ackFlash 1s infinite; }}
.btn-ack-disabled {{ background: #c9c9c9 !important; color: #666 !important; border-color: #aaa !important; box-shadow: none !important; animation: none !important; }}
.btn-test {{ background: #ffc107; color: #222; border-color: #d39e00; font-weight: bold; }}
.btn-test:hover {{ background: #e0a800; }}
.btn-phone {{ background: #007bff; color: white; border-color: #0062cc; font-weight: bold; }}
.btn-phone:hover {{ background: #0069d9; }}
.good {{ background: #ddffdd; border: 1px solid #008000; padding: 10px; border-radius: 6px; }} .danger {{ background: #ffd6d6; border: 1px solid #b00020; padding: 10px; border-radius: 6px; font-weight: bold; }}
.warn {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 6px; }}
pre {{ background: #111; color: #0f0; padding: 15px; height: 400px; overflow-y: scroll; white-space: pre-wrap; }}
code {{ background: #eee; padding: 2px 4px; }} small {{ color: #555; }} table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }} th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }}
.statusbar {{ background: #eee; padding: 10px 20px; font-size: 14px; }}
.status-pill {{ display: inline-block; padding: 3px 8px; border-radius: 999px; font-weight: bold; }}
.status-toggle {{ border-radius: 999px; padding: 3px 8px; margin: 0; font-size: 14px; line-height: 1.2; cursor: pointer; vertical-align: baseline; }}
.status-toggle:hover {{ filter: brightness(0.95); }}
.status-running {{ background: #d4edda; color: #155724; border: 1px solid #28a745; }}
.status-stopped {{ background: #f8d7da; color: #721c24; border: 1px solid #dc3545; }}
.status-warn {{ background: #fff3cd; color: #856404; border: 1px solid #ffc107; }}
.status-alert-active {{ background: #f8d7da; color: #721c24; border: 1px solid #dc3545; }}
.status-alert-inactive {{ background: #d4edda; color: #155724; border: 1px solid #28a745; }}
.help-tip {{ position: relative; display: inline-block; margin-left: 6px; background: #444; color: #fff; border-radius: 50%; width: 18px; height: 18px; line-height: 18px; text-align: center; font-size: 12px; cursor: help; }}
.help-tip .help-text {{ visibility: hidden; opacity: 0; transition: opacity 0.15s ease-in-out; width: 280px; background: #222; color: #fff; text-align: left; border-radius: 6px; padding: 10px; position: absolute; z-index: 9999; top: 24px; left: -10px; box-shadow: 0 2px 8px #777; font-weight: normal; line-height: 1.35; }}
.help-tip:hover .help-text, .help-tip:focus .help-text {{ visibility: visible; opacity: 1; }}
</style></head>
<body><header><h1><img src="/static/app-icon.png" alt="PulsePoint Alert Monitor icon" class="brand-icon"> PulsePoint Alert Monitor <span style="font-size:14px;font-weight:normal;">v{__version__}</span></h1></header>{nav()}
<div class="statusbar"><strong>Monitor:</strong> <form method="post" action="/toggle-monitor" style="display:inline"><button type="submit" class="status-pill status-toggle {monitor_class}" title="Click to start/stop monitor">{running_text}</button></form> | <strong>Profile:</strong> {html_escape(profile)} | <strong>Mode:</strong> {mode} | <strong>Alert:</strong> <span class="status-pill {alert_class}">{active_text}</span> {html_escape(reason)} | <strong>Agency IDs:</strong> {active_agency} | <strong>Units:</strong> {active_units} | <strong>Health:</strong> <span class="status-pill {health_class}">{health_label}</span></div>
{alert_controls}<main>{content}</main></body></html>""", mimetype="text/html")




def start_monitor_if_needed(log_message: str = "Monitor start requested.") -> bool:
    """Start the monitor thread if it is not already running."""
    with state.lock:
        if state.monitor_running:
            should_start = False
        else:
            state.monitor_running = True
            should_start = True

    if not should_start:
        state.log("Monitor start ignored: monitor is already running.")
        return False

    state.monitor_stop.clear()
    threading.Thread(target=monitor_loop, args=(state,), daemon=True).start()
    state.log(log_message)
    return True


def stop_monitor(log_message: str = "Monitor stop requested.") -> None:
    """Request a monitor stop and perform the standard stop cleanup."""
    state.monitor_stop.set()
    silence_alert(state)
    try:
        set_keep_awake(False)
    except Exception:
        pass
    state.log(log_message)


def recent_debug_snapshots(limit: int = 20) -> list[dict[str, str]]:
    """Return recent local debug snapshot metadata for display."""
    snapshot_dir = state.debug_snapshots_dir()
    if not snapshot_dir.exists():
        return []

    items: list[dict[str, str]] = []
    for path in sorted(snapshot_dir.glob("*.txt"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "size": f"{stat.st_size:,} bytes",
                }
            )
        except OSError:
            continue
    return items


def safe_debug_snapshot_path(filename: str) -> Path | None:
    """Resolve a snapshot filename safely under the debug snapshot directory."""
    base = state.debug_snapshots_dir().resolve()
    candidate = (base / filename).resolve()

    if candidate == base or base not in candidate.parents:
        return None
    if candidate.suffix.lower() != ".txt":
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate



def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return send_from_directory(STATIC_DIR, "app.ico", mimetype="image/vnd.microsoft.icon")


    @app.route("/")
    def dashboard() -> Response:
        cfg = load_config()
        logs = state.logs(60)
        with state.lock:
            monitor_running = state.monitor_running
            last_check_time = state.last_check_time or "never"
            last_success_time = state.last_success_time or "never"
            last_refresh_time = state.last_refresh_time or "never"
            last_error = state.last_error
            consecutive_errors = state.consecutive_errors
            active_section_status = "found" if state.active_section_found else "not found"
        dashboard_health_label, dashboard_health_class = monitor_health_label(monitor_running, last_success_time, consecutive_errors, int(cfg.get("poll_seconds", 5)))
        last_check_age = age_display(last_check_time)
        last_success_age = age_display(last_success_time)
        last_refresh_age = age_display(last_refresh_time)
        start_disabled = "disabled" if monitor_running else ""
        stop_disabled = "" if monitor_running else "disabled"
        manual_refresh_disabled = "" if monitor_running else "disabled"
        alert_active_for_ack = state.alert_active
        ack_button_disabled = "" if alert_active_for_ack else "disabled"
        ack_button_class = "btn-ack btn-ack-active" if alert_active_for_ack else "btn-ack btn-ack-disabled"
        ack_button_label = "ACK / Silence Alert" if alert_active_for_ack else "No Active Alert"
        ack_button_title = "Acknowledge and silence active alert" if alert_active_for_ack else "No active alert to acknowledge"
        first_run_html = ""
        if not cfg.get("agency_ids") or not cfg.get("units"):
            first_run_html = """
<div class="danger">
<h3>Setup needed</h3>
<p>No agency or unit is fully configured yet. Start with the setup wizard.</p>
<form method="get" action="/first-run">
<button type="submit">Start Setup Wizard</button>
</form>
</div>
"""
        content = f"""
{first_run_html}<h2>Dashboard</h2><div class="good"><strong>Dashboard auto-refreshes every 10 seconds.</strong> Configuration pages do not auto-refresh so typed settings are not lost.</div><div class="warn">Backup alert only. Not affiliated with PulsePoint Foundation or any public safety agency. Not official dispatch. No warranty. Do not rely on this as your sole alerting method.</div>
<div class="grid"><div class="card"><h3>Active Monitor Setup</h3>
<p><strong>Agency:</strong> <code>{html_escape(agency_display(cfg))}</code></p>
<p><strong>Units:</strong> <code>{html_escape(unit_set_display(cfg))}</code></p>
<p><strong>Alert profile:</strong> {html_escape(alert_profile_label(cfg.get('alert_profile')))}</p>
<p><strong>Poll:</strong> {cfg.get('poll_seconds', 5)} seconds</p><p><strong>Mode:</strong> {'TEST' if cfg.get('test_mode') else 'UNIT'}</p>
<p><strong>Sleep prevention:</strong> {'ON' if cfg.get('prevent_sleep') else 'OFF'}</p></div>
<div class="card"><h3>Monitor Health</h3>
<table>
<tr><th>Item</th><th>Status</th></tr>
<tr><td>Overall health</td><td><span class="status-pill {dashboard_health_class}">{dashboard_health_label}</span></td></tr>
<tr><td>Last check</td><td>{html_escape(last_check_age)} <small>({html_escape(last_check_time)})</small></td></tr>
<tr><td>Last success</td><td>{html_escape(last_success_age)} <small>({html_escape(last_success_time)})</small></td></tr>
<tr><td>Last refresh</td><td>{html_escape(last_refresh_age)} <small>({html_escape(last_refresh_time)})</small></td></tr>
<tr><td>Active section</td><td>{active_section_status}</td></tr>
<tr><td>Consecutive errors</td><td>{consecutive_errors}</td></tr>
<tr><td>Last error</td><td>{html_escape(last_error or "(none)")}</td></tr>
</table>
</div>
<div class="card"><h3>Actions</h3><form method="post" action="/start" style="display:inline"><button type="submit" class="btn-start" {start_disabled}>Start Monitor</button></form>
<form method="post" action="/stop" style="display:inline"><button type="submit" class="btn-stop" {stop_disabled}>Stop Monitor</button></form>
<form method="post" action="/ack" style="display:inline"><button type="submit" class="{ack_button_class}" {ack_button_disabled} title="{ack_button_title}">{ack_button_label}</button></form>
<form method="post" action="/test-sound"><button type="submit" class="btn-test">Test Laptop Alert</button></form>
<form method="post" action="/test-push"><button type="submit" class="btn-phone">Test Phone Push</button></form><form method="post" action="/refresh-now" style="display:inline"><button type="submit" class="btn-phone" {manual_refresh_disabled}>Refresh PulsePoint Now</button></form></div></div>
<div class="card"><h3>Recent Log</h3><pre>{html_escape(chr(10).join(logs))}</pre></div>"""
        return layout("Dashboard", content)


    @app.route("/first-run")
    def first_run_page() -> Response:
        cfg = load_config()
        content = f"""
<h2>First-Run Setup Wizard</h2>
<div class="warn">
This wizard configures the minimum needed to start monitoring. You can fine-tune phone alerts later on the Alerts page.
</div>

<div class="card">
<form method="post" action="/first-run/save">
<h3>Step 1: Agency / PulsePoint Feed</h3>
<label>Agency preset name</label>
<input type="text" name="agency_name" value="Primary Agency" placeholder="Example: AMR San Diego">

<label>PulsePoint agency ID(s) {help_tip("The number after ?agencies= in the PulsePoint Web URL. Multiple agency IDs can be comma-separated.")}</label>
<input type="text" name="agency_ids" value="{html_escape(cfg.get('agency_ids', ''))}" placeholder="Example: 37047 or 37047,12345">
<small>Use the number after <code>?agencies=</code> in the PulsePoint Web URL.</small>

<h3>Step 2: Apparatus / Unit Set</h3>
<label>Unit set name</label>
<input type="text" name="unit_name" value="Primary Unit" placeholder="Example: M231 Shift">

<label>Units to monitor {help_tip("Unit or apparatus IDs to watch for in the Active section. Example: M231, M36, E36.")}</label>
<input type="text" name="units" value="{html_escape(units_display(cfg.get('units', [])))}" placeholder="Example: M231, M36, E36">
<small>Comma-separated. Example: <code>M231</code> or <code>M231, M232</code>.</small>

<h3>Step 3: Basic Monitor Settings</h3>
<label>Poll interval, seconds {help_tip("How often the app checks the PulsePoint page. Lower is faster but uses more browser/network activity. Minimum is 5 seconds.")}</label>
<input type="number" name="poll_seconds" value="{cfg.get('poll_seconds', 5)}" min="5" max="60">

<label><input type="checkbox" name="test_mode" checked> Start in test mode</label>
<small>Recommended for first setup. Test mode alerts on any new PulsePoint page activity/change.</small>

<label><input type="checkbox" name="prevent_sleep" checked> Prevent Windows sleep while monitor is running</label>

<div class="button-row">
<button type="submit">Save First-Run Setup</button>
</div>
</form>
</div>

<div class="card">
<h3>After saving</h3>
<ol>
<li>Go to <strong>Alerts</strong> and test laptop/phone alerts.</li>
<li>Leave test mode on until you confirm a real page activity trigger works.</li>
<li>Then turn test mode off and monitor your real unit list.</li>
</ol>
</div>
"""
        return layout("First-Run Setup", content)


    @app.route("/first-run/save", methods=["POST"])
    def save_first_run() -> Response:
        cfg = load_config()

        agency_name = request.form.get("agency_name", "Primary Agency").strip() or "Primary Agency"
        agency_ids = request.form.get("agency_ids", "").strip()
        unit_name = request.form.get("unit_name", "Primary Unit").strip() or "Primary Unit"
        units = normalize_units(request.form.get("units", ""))

        if not agency_ids:
            state.log("First-run setup not saved: agency ID(s) required.")
            return redirect("/first-run")

        if not units:
            state.log("First-run setup not saved: at least one unit is required.")
            return redirect("/first-run")

        cfg["agency_ids"] = agency_ids
        cfg["units"] = units
        cfg["poll_seconds"] = max(5, int(request.form.get("poll_seconds", 5)))
        cfg["test_mode"] = bool(request.form.get("test_mode"))
        cfg["prevent_sleep"] = bool(request.form.get("prevent_sleep"))

        agency_presets = cfg.get("agency_presets", [])
        agency_presets = [
            p for p in agency_presets
            if p.get("name") != agency_name and p.get("agency_ids") != agency_ids
        ]
        agency_presets.append({"name": agency_name, "agency_ids": agency_ids})
        cfg["agency_presets"] = agency_presets[-50:]

        unit_presets = cfg.get("unit_presets", [])
        unit_key = ",".join(units)
        unit_presets = [
            p for p in unit_presets
            if p.get("name") != unit_name and ",".join(p.get("units", [])) != unit_key
        ]
        unit_presets.append({"name": unit_name, "units": units})
        cfg["unit_presets"] = unit_presets[-50:]

        save_config(cfg)
        state.log("First-run setup saved.")
        return redirect("/alerts")



    @app.route("/agencies")
    def agencies_page() -> Response:
        cfg = load_config(); rows = ""
        for i, item in enumerate(cfg.get("agency_presets", [])):
            rows += f"<tr><td>{html_escape(item.get('name',''))}</td><td><code>{html_escape(item.get('agency_ids',''))}</code></td><td><form method='post' action='/use-agency/{i}' style='display:inline'><button>Use</button></form><form method='post' action='/delete-agency/{i}' style='display:inline'><button>Delete</button></form></td></tr>"
        if not rows: rows = '<tr><td colspan="3"><em>No agencies saved yet.</em></td></tr>'
        content = f"""<h2>Agencies</h2><p>Save each PulsePoint feed by a human name.</p><div class="card"><h3>Add / Save Agency</h3><form method="post" action="/agencies/add"><label>Agency name</label><input type="text" name="name" placeholder="Example: AMR San Diego"><label>PulsePoint agency ID(s) {help_tip("The number after ?agencies= in the PulsePoint Web URL. Multiple agency IDs can be comma-separated.")}</label><input type="text" name="agency_ids" placeholder="Example: 37047 or 37047,12345"><small>Use the number after <code>?agencies=</code> in the PulsePoint Web URL.</small><br><button type="submit">Save Agency</button></form></div><div class="card"><h3>Saved Agencies</h3><table><tr><th>Name</th><th>Agency IDs</th><th>Actions</th></tr>{rows}</table></div>"""
        return layout("Agencies", content)

    @app.route("/agencies/add", methods=["POST"])
    def add_agency() -> Response:
        cfg = load_config(); name = request.form.get("name", "").strip(); agency_ids = request.form.get("agency_ids", "").strip()
        if not name or not agency_ids:
            state.log("Agency not saved: name and agency IDs are required."); return redirect("/agencies")
        presets = [p for p in cfg.get("agency_presets", []) if p.get("name") != name and p.get("agency_ids") != agency_ids]
        presets.append({"name": name, "agency_ids": agency_ids}); cfg["agency_presets"] = presets[-50:]; save_config(cfg); state.log(f"Saved agency: {name}"); return redirect("/agencies")

    @app.route("/use-agency/<int:index>", methods=["POST"])
    def use_agency(index: int) -> Response:
        cfg = load_config(); presets = cfg.get("agency_presets", [])
        if 0 <= index < len(presets): cfg["agency_ids"] = presets[index].get("agency_ids", ""); save_config(cfg); state.log(f"Using agency: {presets[index].get('name')}")
        return redirect("/setup")

    @app.route("/delete-agency/<int:index>", methods=["POST"])
    def delete_agency(index: int) -> Response:
        cfg = load_config(); presets = cfg.get("agency_presets", [])
        if 0 <= index < len(presets): removed = presets.pop(index); cfg["agency_presets"] = presets; save_config(cfg); state.log(f"Deleted agency: {removed.get('name')}")
        return redirect("/agencies")

    @app.route("/units")
    def units_page() -> Response:
        cfg = load_config(); rows = ""
        for i, item in enumerate(cfg.get("unit_presets", [])):
            rows += f"<tr><td>{html_escape(item.get('name',''))}</td><td><code>{html_escape(units_display(item.get('units', [])))}</code></td><td><form method='post' action='/use-units/{i}' style='display:inline'><button>Use</button></form><form method='post' action='/delete-units/{i}' style='display:inline'><button>Delete</button></form></td></tr>"
        if not rows: rows = '<tr><td colspan="3"><em>No unit sets saved yet.</em></td></tr>'
        content = f"""<h2>Apparatus / Units</h2><div class="card"><h3>Add / Save Unit Set</h3><form method="post" action="/units/add"><label>Name</label><input type="text" name="name" placeholder="Example: M231 shift / Station 36"><label>Units {help_tip("Comma-separated apparatus/unit IDs. Example: M231, M36, E36.")}</label><input type="text" name="units" placeholder="Example: M231, M36, E36"><small>Comma-separated.</small><br><button type="submit">Save Unit Set</button></form></div><div class="card"><h3>Saved Unit Sets</h3><table><tr><th>Name</th><th>Units</th><th>Actions</th></tr>{rows}</table></div>"""
        return layout("Apparatus / Units", content)

    @app.route("/units/add", methods=["POST"])
    def add_units() -> Response:
        cfg = load_config(); name = request.form.get("name", "").strip(); units = normalize_units(request.form.get("units", ""))
        if not name or not units:
            state.log("Unit set not saved: name and at least one unit are required."); return redirect("/units")
        unit_key = ",".join(units); presets = [p for p in cfg.get("unit_presets", []) if p.get("name") != name and ",".join(p.get("units", [])) != unit_key]
        presets.append({"name": name, "units": units}); cfg["unit_presets"] = presets[-50:]; save_config(cfg); state.log(f"Saved unit set: {name}"); return redirect("/units")

    @app.route("/use-units/<int:index>", methods=["POST"])
    def use_units(index: int) -> Response:
        cfg = load_config(); presets = cfg.get("unit_presets", [])
        if 0 <= index < len(presets): cfg["units"] = presets[index].get("units", []); save_config(cfg); state.log(f"Using unit set: {presets[index].get('name')}")
        return redirect("/setup")

    @app.route("/delete-units/<int:index>", methods=["POST"])
    def delete_units(index: int) -> Response:
        cfg = load_config(); presets = cfg.get("unit_presets", [])
        if 0 <= index < len(presets): removed = presets.pop(index); cfg["unit_presets"] = presets; save_config(cfg); state.log(f"Deleted unit set: {removed.get('name')}")
        return redirect("/units")

    @app.route("/setup")
    def setup_page() -> Response:
        cfg = load_config(); agency_opts = '<option value="">Keep current / manual</option>'; unit_opts = '<option value="">Keep current / manual</option>'
        for i, item in enumerate(cfg.get("agency_presets", [])): agency_opts += f'<option value="{i}">{html_escape(item.get("name", ""))} — {html_escape(item.get("agency_ids", ""))}</option>'
        for i, item in enumerate(cfg.get("unit_presets", [])): unit_opts += f'<option value="{i}">{html_escape(item.get("name", ""))} — {html_escape(units_display(item.get("units", [])))}</option>'
        content = f"""<h2>Monitor Setup</h2><div class="card"><form method="post" action="/setup/save"><label>Choose saved agency</label><select name="agency_index">{agency_opts}</select><label>Or enter agency ID(s) manually {help_tip("The PulsePoint agency feed number. Example: 37047. Use comma-separated values for multiple feeds.")}</label><input type="text" name="agency_ids" value="{html_escape(cfg.get('agency_ids', ''))}"><label>Choose saved apparatus / unit set</label><select name="unit_index">{unit_opts}</select><label>Or enter units manually {help_tip("Comma-separated unit IDs. The monitor alerts when one appears in an Active incident.")}</label><input type="text" name="units" value="{html_escape(units_display(cfg.get('units', [])))}"><label>Poll interval, seconds {help_tip("How often the app checks the PulsePoint page. Lower is faster but uses more browser/network activity. Minimum is 5 seconds.")}</label><input type="number" name="poll_seconds" value="{cfg.get('poll_seconds', 5)}" min="5" max="60"><label>PulsePoint page refresh interval, seconds {help_tip("How often the browser reloads the PulsePoint page completely. This helps recover from stale page state.")}</label><input type="number" name="refresh_seconds" value="{cfg.get('refresh_seconds', 300)}" min="60" max="1800"><label><input type="checkbox" name="test_mode" {checked(cfg.get('test_mode', False))}> Test mode {help_tip("Setup/testing mode. Alerts on general PulsePoint page activity/change instead of only configured units. Turn this off for normal use.")}</label><label><input type="checkbox" name="headless" {checked(cfg.get('headless', True))}> Headless browser mode {help_tip("Runs the monitoring browser invisibly in the background. Turn off only for troubleshooting.")}</label><label><input type="checkbox" name="prevent_sleep" {checked(cfg.get('prevent_sleep', True))}> Prevent sleep {help_tip("Keeps Windows awake while the monitor is running so the laptop does not sleep through alerts.")}</label><label><input type="checkbox" name="keep_display_on" {checked(cfg.get('keep_display_on', False))}> Keep display on {help_tip("Also tries to keep the screen awake. Usually not necessary unless your system still sleeps or dims aggressively.")}</label><br><button type="submit">Save Monitor Setup</button></form></div>"""
        return layout("Monitor Setup", content)

    @app.route("/setup/save", methods=["POST"])
    def save_setup() -> Response:
        cfg = load_config(); agency_index = request.form.get("agency_index", ""); unit_index = request.form.get("unit_index", "")
        if agency_index != "":
            try: cfg["agency_ids"] = cfg.get("agency_presets", [])[int(agency_index)].get("agency_ids", "")
            except Exception: state.log("Invalid agency preset selection.")
        else: cfg["agency_ids"] = request.form.get("agency_ids", "").strip()
        if unit_index != "":
            try: cfg["units"] = cfg.get("unit_presets", [])[int(unit_index)].get("units", [])
            except Exception: state.log("Invalid unit preset selection.")
        else: cfg["units"] = normalize_units(request.form.get("units", ""))
        cfg["poll_seconds"] = max(5, int(request.form.get("poll_seconds", 5))); cfg["refresh_seconds"] = int(request.form.get("refresh_seconds", 300)); cfg["test_mode"] = bool(request.form.get("test_mode")); cfg["headless"] = bool(request.form.get("headless")); cfg["prevent_sleep"] = bool(request.form.get("prevent_sleep")); cfg["keep_display_on"] = bool(request.form.get("keep_display_on")); save_config(cfg); state.log("Monitor setup saved."); return redirect("/setup")

    @app.route("/alerts")
    def alerts_page() -> Response:
        cfg = load_config(); provider = cfg.get("push_provider", "pushover")
        content = f"""<h2>Alerts</h2><div class="card"><form method="post" action="/alerts/save"><h3>Alert Profile</h3>
<p><strong>Selected profile:</strong> {html_escape(alert_profile_label(cfg.get('alert_profile')))}</p>
<label>Profile {help_tip("Alert Me uses looping desktop alerts and emergency/repeating phone pushes that require acknowledgement. Track Unit(s) records activity and sends low-priority phone updates without a desktop loop or ACK requirement.")}</label>
<select name="alert_profile"><option value="alert_me" {selected(cfg.get('alert_profile'), 'alert_me')}>Alert Me</option><option value="track_units" {selected(cfg.get('alert_profile'), 'track_units')}>Track Unit(s)</option></select>
<div class="warn"><strong>Alert Me:</strong> full desktop alert, emergency/repeating phone push, and ACK workflow.<br><strong>Track Unit(s):</strong> no looping desktop alert, low-priority phone push, and no ACK requirement. Both profiles retain history and evidence.</div>
<h3>Alert Channels</h3>
<label><input type="checkbox" name="desktop_alert_enabled" {checked(cfg.get('desktop_alert_enabled', True))}> Laptop / desktop audible alert {help_tip("When enabled, the computer plays the local alert sound when a monitored unit is detected.")}</label>
<label><input type="checkbox" name="phone_alert_enabled" {checked(cfg.get('phone_alert_enabled', True))}> Phone push alert {help_tip("When enabled, the app sends a push notification through the configured phone provider.")}</label>
<label><input type="checkbox" name="include_call_details_in_phone_push" {checked(cfg.get('include_call_details_in_phone_push', True))}> Include call details in phone push {help_tip("When enabled, phone pushes can include incident details such as call type, address/context, and units. Turn off if you do not want details visible on your phone lock screen.")}</label>
<h3>Laptop Alert</h3><label>Alert sound file {help_tip("Path to the local WAV file used for the laptop alert. The installer copies a default alert.wav into the runtime folder.")}</label><input type="text" name="sound_file" value="{html_escape(cfg.get('sound_file',''))}"><label>Alert mode {help_tip("Until acknowledged keeps sounding until ACK/Silence is clicked. Timed mode stops after the configured duration.")}</label><select name="alert_mode"><option value="until_ack" {selected(cfg.get('alert_mode'), 'until_ack')}>Keep alerting until acknowledged</option><option value="timed" {selected(cfg.get('alert_mode'), 'timed')}>Alert for fixed duration</option></select><label>Alert duration, seconds {help_tip("Only used in timed mode. Until-acknowledged mode ignores this and continues until silenced.")}</label><input type="number" name="alert_duration_seconds" value="{cfg.get('alert_duration_seconds',30)}"><label>Cooldown, seconds {help_tip("Minimum time between alerts. Helps prevent repeated alerts from rapid page changes or repeated signatures.")}</label><input type="number" name="cooldown_seconds" value="{cfg.get('cooldown_seconds',60)}"><h3>Phone Push</h3><label>Push provider {help_tip("Choose which phone push service to use. Pushover is recommended for emergency-style repeated alerts.")}</label><select name="push_provider"><option value="none" {selected(provider, 'none')}>None</option><option value="pushover" {selected(provider, 'pushover')}>Pushover</option><option value="ntfy" {selected(provider, 'ntfy')}>ntfy</option><option value="both" {selected(provider, 'both')}>Both</option></select><h4>Pushover</h4><label>App API Token {help_tip("Pushover application/API token. This is different from your user key.")}</label><input type="password" name="pushover_app_token" value="{html_escape(cfg.get('pushover_app_token',''))}"><label>User Key {help_tip("Your Pushover recipient/user key. This identifies the phone/account receiving alerts.")}</label><input type="password" name="pushover_user_key" value="{html_escape(cfg.get('pushover_user_key',''))}"><label>Device Name — optional</label><input type="text" name="pushover_device" value="{html_escape(cfg.get('pushover_device',''))}"><label>Priority {help_tip("For Pushover, priority 2 is emergency priority and repeats until acknowledged in Pushover or until expiry.")}</label><input type="number" name="pushover_priority" value="{cfg.get('pushover_priority',2)}"><label>Retry Seconds {help_tip("For Pushover emergency priority, how often Pushover repeats the notification. Minimum is 30 seconds.")}</label><input type="number" name="pushover_retry_seconds" value="{cfg.get('pushover_retry_seconds',30)}"><label>Expire Seconds {help_tip("For Pushover emergency priority, how long Pushover keeps retrying before giving up. Maximum is 10800 seconds.")}</label><input type="number" name="pushover_expire_seconds" value="{cfg.get('pushover_expire_seconds',1800)}"><label>Sound</label><input type="text" name="pushover_sound" value="{html_escape(cfg.get('pushover_sound','persistent'))}"><h4>ntfy</h4><label>Server</label><input type="text" name="ntfy_server" value="{html_escape(cfg.get('ntfy_server','https://ntfy.sh'))}"><label>Topic</label><input type="text" name="ntfy_topic" value="{html_escape(cfg.get('ntfy_topic',''))}"><label>Bearer Token — optional</label><input type="password" name="ntfy_token" value="{html_escape(cfg.get('ntfy_token',''))}"><label>Priority {help_tip("For Pushover, priority 2 is emergency priority and repeats until acknowledged in Pushover or until expiry.")}</label><input type="number" name="ntfy_priority" value="{cfg.get('ntfy_priority',5)}"><label>Tags</label><input type="text" name="ntfy_tags" value="{html_escape(cfg.get('ntfy_tags','rotating_light,ambulance'))}"><label>Call — optional {help_tip("ntfy call option. On public ntfy.sh this may require a paid plan and a verified phone number.")}</label><input type="text" name="ntfy_call" value="{html_escape(cfg.get('ntfy_call',''))}"><br><button type="submit">Save Alert Settings</button></form><form method="post" action="/test-sound" style="display:inline"><button class="btn-test">Test Laptop Alert</button></form><form method="post" action="/test-push" style="display:inline"><button class="btn-phone">Test Phone Push</button></form><form method="post" action="/simulate-incident" style="display:inline"><button class="btn-test">Simulate Active Incident Alert</button></form></div>"""
        return layout("Alerts", content)

    @app.route("/alerts/save", methods=["POST"])
    def save_alerts() -> Response:
        cfg = load_config(); fields = ["sound_file","alert_mode","push_provider","pushover_app_token","pushover_user_key","pushover_device","pushover_sound","ntfy_server","ntfy_topic","ntfy_token","ntfy_tags","ntfy_call"]
        for field in fields: cfg[field] = request.form.get(field, "").strip()
        cfg["desktop_alert_enabled"] = bool(request.form.get("desktop_alert_enabled"))
        cfg["phone_alert_enabled"] = bool(request.form.get("phone_alert_enabled"))
        cfg["alert_profile"] = normalize_alert_profile(request.form.get("alert_profile"))
        cfg["include_call_details_in_phone_push"] = bool(request.form.get("include_call_details_in_phone_push"))
        for field in ["alert_duration_seconds","cooldown_seconds","pushover_priority","pushover_retry_seconds","pushover_expire_seconds","ntfy_priority"]: cfg[field] = int(request.form.get(field, cfg.get(field, 0)))
        cfg["pushover_retry_seconds"] = max(30, cfg["pushover_retry_seconds"]); cfg["pushover_expire_seconds"] = min(10800, cfg["pushover_expire_seconds"]); save_config(cfg); state.log("Alert settings saved."); return redirect("/alerts")


    @app.route("/history")
    def history_page() -> Response:
        events = list(reversed(state.alert_history(100)))
        rows = ""
        for event in events:
            ack = event.get("acknowledged", "no")
            ack_class = "good" if ack == "yes" else "warn"
            evidence_id = event.get("evidence_id", "")
            evidence_cell = (
                f"<a href='/history/evidence/{html_escape(evidence_id)}'>View</a>"
                if evidence_id else ""
            )
            rows += (
                "<tr>"
                f"<td>{html_escape(event.get('time', ''))}</td>"
                f"<td>{html_escape(event.get('source', ''))}</td>"
                f"<td>{html_escape(alert_profile_label(event.get('profile', 'alert_me')))}</td>"
                f"<td>{evidence_cell}</td>"
                f"<td>{html_escape(event.get('reason', ''))}</td>"
                f"<td>{html_escape(event.get('desktop', ''))}</td>"
                f"<td>{html_escape(event.get('phone', ''))}</td>"
                f"<td><span class='{ack_class}'>{html_escape(ack)}</span></td>"
                f"<td>{html_escape(event.get('ack_time', ''))}</td>"
                "</tr>"
            )

        if not rows:
            rows = '<tr><td colspan="9"><em>No alert history yet.</em></td></tr>'

        content = f"""
<h2>Alert History</h2>
<div class="card"><p><small>Alert history is saved locally in the app runtime folder and survives restarts.</small></p>
<form method="post" action="/history/clear" style="display:inline">
<button type="submit">Clear History</button>
</form>
<a href="/history/export.csv"><button type="button">Export CSV</button></a>
<table>
<tr>
<th>Time</th>
<th>Source</th>
<th>Profile</th>
<th>Evidence</th>
<th>Reason</th>
<th>Desktop</th>
<th>Phone</th>
<th>Acknowledged</th>
<th>ACK Time</th>
</tr>
{rows}
</table>
</div>
"""
        return layout("Alert History", content)




    @app.route("/history/evidence/<evidence_id>")
    def history_evidence_page(evidence_id: str) -> Response:
        evidence = state.find_alert_evidence(evidence_id)
        if evidence is None:
            content = f"""
<h2>Alert Evidence</h2>
<div class="danger">No alert evidence found for ID <code>{html_escape(evidence_id)}</code>.</div>
"""
            return layout("Alert Evidence", content)

        new_blocks = evidence.get("new_incident_blocks", {})
        block_rows = ""
        if isinstance(new_blocks, dict):
            for signature, block in new_blocks.items():
                block_rows += (
                    "<tr>"
                    f"<td><code>{html_escape(str(signature)[:16])}</code></td>"
                    f"<td><pre style='height:180px'>{html_escape(block)}</pre></td>"
                    "</tr>"
                )

        if not block_rows:
            block_rows = '<tr><td colspan="2"><em>No incident block evidence stored.</em></td></tr>'

        raw_json = json.dumps(evidence, indent=2, default=str)
        active_section = str(evidence.get("active_section_text", ""))

        content = f"""
<h2>Alert Evidence</h2>

<div class="warn">
<strong>Privacy:</strong> This page may contain call details and addresses captured from PulsePoint Active at the moment of alert.
</div>

<div class="card">
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Evidence ID</td><td><code>{html_escape(evidence.get("id", ""))}</code></td></tr>
<tr><td>Time</td><td>{html_escape(evidence.get("time", ""))}</td></tr>
<tr><td>Alert profile</td><td>{html_escape(alert_profile_label(evidence.get("alert_profile", "alert_me")))}</td></tr>
<tr><td>Agency IDs</td><td><code>{html_escape(evidence.get("agency_ids", ""))}</code></td></tr>
<tr><td>Configured units</td><td><code>{html_escape(", ".join(evidence.get("configured_units", [])) if isinstance(evidence.get("configured_units"), list) else evidence.get("configured_units", ""))}</code></td></tr>
<tr><td>Matched units</td><td><code>{html_escape(", ".join(evidence.get("matched_units", [])) if isinstance(evidence.get("matched_units"), list) else evidence.get("matched_units", ""))}</code></td></tr>
<tr><td>Signature method</td><td><code>{html_escape(evidence.get("signature_method", ""))}</code></td></tr>
</table>
</div>

<div class="card">
<h3>New Incident Blocks That Triggered</h3>
<table>
<tr><th>Signature</th><th>Incident Block</th></tr>
{block_rows}
</table>
</div>

<div class="card">
<h3>Raw Active Section at Alert Time</h3>
<pre>{html_escape(active_section[:20000])}</pre>
</div>

<div class="card">
<h3>Full Evidence JSON</h3>
<pre>{html_escape(raw_json[:30000])}</pre>
</div>
"""
        return layout("Alert Evidence", content)


    @app.route("/history/export.csv")
    def export_history_csv() -> Response:
        events = state.alert_history(500)
        output = io.StringIO()
        fieldnames = ["time", "source", "profile", "evidence_id", "reason", "desktop", "phone", "ack_required", "acknowledged", "ack_time"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for event in events:
            writer.writerow({field: event.get(field, "") for field in fieldnames})

        filename = f"pulsepoint_alert_history_{datetime_filename()}.csv"
        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        state.log("Alert history exported as CSV.")
        return response


    @app.route("/history/clear", methods=["POST"])
    def clear_history() -> Response:
        state.clear_alert_history()
        state.clear_alert_evidence()
        state.log("Alert history and evidence cleared.")
        return redirect("/history")



    @app.route("/debug/active")
    def active_debug_page() -> Response:
        cfg = load_config()
        agency_ids = (cfg.get("agency_ids") or "").strip()
        units = cfg.get("units", [])
        unit_re = build_unit_regex(units)
        url = f"https://web.pulsepoint.org/?agencies={agency_ids}" if agency_ids else ""

        if not agency_ids:
            content = """
<h2>Active Incident Debug</h2>
<div class="danger">No agency ID is configured.</div>
"""
            return layout("Active Incident Debug", content)

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = None
                try:
                    state.log("Active debug fetch requested.")
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)
                    page_text = page.locator("body").inner_text(timeout=10000)
                    state.log("Active debug fetch completed.")
                finally:
                    if browser is not None:
                        browser.close()

            active_text = active_section_text(page_text)

            if active_text is None:
                content = f"""
<h2>Active Incident Debug</h2>
<div class="danger">Active section was not found.</div>
<div class="card">
<p><strong>URL:</strong> <code>{html_escape(url)}</code></p>
<p><strong>Configured units:</strong> <code>{html_escape(units_display(units))}</code></p>
</div>
<div class="card">
<h3>First 4000 characters of page text</h3>
<pre>{html_escape(page_text[:4000])}</pre>
</div>
"""
                return layout("Active Incident Debug", content)

            signatures, units_found = active_unit_incident_signatures(active_text, unit_re)

            signature_rows = ""
            for signature, block in signatures.items():
                short_sig = signature[:16]
                signature_rows += (
                    "<tr>"
                    f"<td><code>{html_escape(short_sig)}</code></td>"
                    f"<td><pre style='height:140px'>{html_escape(block)}</pre></td>"
                    "</tr>"
                )

            if not signature_rows:
                signature_rows = '<tr><td colspan="2"><em>No monitored-unit incident signatures found in Active.</em></td></tr>'

            content = f"""
<h2>Active Incident Debug</h2>
<div class="card">
<form method="get" action="/debug/active">
<button type="submit">Refresh Active Debug</button>
</form>
<p><strong>URL:</strong> <code>{html_escape(url)}</code></p>
<p><strong>Configured units:</strong> <code>{html_escape(units_display(units))}</code></p>
<p><strong>Units detected in Active:</strong> <code>{html_escape(', '.join(sorted(units_found)) if units_found else '(none)')}</code></p>
<p><strong>Incident signatures:</strong> <code>{len(signatures)}</code></p>
</div>

<div class="card">
<h3>Detected Incident Signatures</h3>
<table>
<tr><th>Signature</th><th>Matched Active Incident Text</th></tr>
{signature_rows}
</table>
</div>

<div class="card">
<h3>Raw Active Section Preview</h3>
<pre>{html_escape(active_text[:8000])}</pre>
</div>
"""
            return layout("Active Incident Debug", content)

        except Exception as exc:
            content = f"""
<h2>Active Incident Debug</h2>
<div class="danger">Debug fetch failed: {html_escape(exc)}</div>
<div class="card">
<p><strong>URL:</strong> <code>{html_escape(url)}</code></p>
<p><strong>Configured units:</strong> <code>{html_escape(units_display(units))}</code></p>
</div>
"""
            return layout("Active Incident Debug", content)




    @app.route("/troubleshooting")
    def troubleshooting_page() -> Response:
        cfg = load_config()
        runtime_dir = Path(config_path()).parent
        start_at_login = get_start_at_login_status()
        snapshot_rows = ""
        for snapshot in recent_debug_snapshots():
            name = html_escape(snapshot["name"])
            snapshot_rows += (
                "<tr>"
                f"<td><code>{name}</code></td>"
                f"<td>{html_escape(snapshot['modified'])}</td>"
                f"<td>{html_escape(snapshot['size'])}</td>"
                f"<td><a href='/debug-snapshots/{name}'>View</a></td>"
                "</tr>"
            )
        if not snapshot_rows:
            snapshot_rows = '<tr><td colspan="4"><em>No debug snapshots saved yet.</em></td></tr>'

        try:
            import importlib.util
            playwright_status = "installed" if importlib.util.find_spec("playwright") else "not found"
        except Exception as exc:
            playwright_status = f"check failed: {exc}"

        desktop_shortcut = Path.home() / "Desktop" / "PulsePoint Alert Monitor.lnk"
        with state.lock:
            monitor_running = state.monitor_running
            alert_active = state.alert_active
            alert_reason = state.alert_reason
            last_check_time = state.last_check_time or "never"
            last_success_time = state.last_success_time or "never"
            last_refresh_time = state.last_refresh_time or "never"
            last_error = state.last_error or ""
            consecutive_errors = state.consecutive_errors
            active_section_found = state.active_section_found
            history_count = len(state.alert_events)
            evidence_count = len(getattr(state, "alert_evidence", []))

        health_label, health_class = monitor_health_label(
            monitor_running,
            last_success_time,
            consecutive_errors,
            int(cfg.get("poll_seconds", 5)),
        )

        content = f"""
<h2>Troubleshooting</h2>

<div class="warn">
This page is primarily read-only. The Start at Login controls change only the current user's login settings.
</div>

<div class="grid">
<div class="card">
<h3>App</h3>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Version</td><td><code>{html_escape(__version__)}</code></td></tr>
<tr><td>Python</td><td><code>{html_escape(sys.version.split()[0])}</code></td></tr>
<tr><td>Platform</td><td><code>{html_escape(platform.platform())}</code></td></tr>
<tr><td>Playwright package</td><td><code>{html_escape(playwright_status)}</code></td></tr>
</table>
</div>

<div class="card">
<h3>Paths</h3>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Config path</td><td><code>{html_escape(config_path())}</code></td></tr>
<tr><td>Runtime folder</td><td><code>{html_escape(runtime_dir)}</code></td></tr>
<tr><td>Desktop shortcut</td><td>{'FOUND' if desktop_shortcut.exists() else 'not found'}<br><small><code>{html_escape(desktop_shortcut)}</code></small></td></tr>
<tr><td>Start at login</td><td>{'ENABLED' if start_at_login.enabled else 'disabled'}<br><small><code>{html_escape(start_at_login.path or '(unsupported)')}</code></small></td></tr>
</table>
</div>
</div>

<div class="grid">
<div class="card">
<h3>Monitor Health</h3>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Monitor</td><td>{'RUNNING' if monitor_running else 'STOPPED'}</td></tr>
<tr><td>Health</td><td><span class="status-pill {health_class}">{health_label}</span></td></tr>
<tr><td>Alert</td><td>{'ACTIVE' if alert_active else 'INACTIVE'}</td></tr>
<tr><td>Alert reason</td><td>{html_escape(alert_reason or '(none)')}</td></tr>
<tr><td>Last check</td><td>{html_escape(age_display(last_check_time))} <small>({html_escape(last_check_time)})</small></td></tr>
<tr><td>Last success</td><td>{html_escape(age_display(last_success_time))} <small>({html_escape(last_success_time)})</small></td></tr>
<tr><td>Last refresh</td><td>{html_escape(age_display(last_refresh_time))} <small>({html_escape(last_refresh_time)})</small></td></tr>
<tr><td>Active section</td><td>{'found' if active_section_found else 'not found'}</td></tr>
<tr><td>Consecutive errors</td><td>{consecutive_errors}</td></tr>
<tr><td>Last error</td><td>{html_escape(last_error or '(none)')}</td></tr>
</table>
</div>

<div class="card">
<h3>Configured Monitoring</h3>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Agency</td><td><code>{html_escape(agency_display(cfg))}</code></td></tr>
<tr><td>Units</td><td><code>{html_escape(unit_set_display(cfg))}</code></td></tr>
<tr><td>Alert profile</td><td>{html_escape(alert_profile_label(cfg.get('alert_profile')))}</td></tr>
<tr><td>Test mode</td><td>{'ON' if cfg.get('test_mode') else 'OFF'}</td></tr>
<tr><td>Poll seconds</td><td>{html_escape(cfg.get('poll_seconds'))}</td></tr>
<tr><td>Refresh seconds</td><td>{html_escape(cfg.get('refresh_seconds'))}</td></tr>
<tr><td>Desktop alert</td><td>{'ON' if cfg.get('desktop_alert_enabled') else 'OFF'}</td></tr>
<tr><td>Phone alert</td><td>{'ON' if cfg.get('phone_alert_enabled') else 'OFF'}</td></tr>
<tr><td>Push provider</td><td><code>{html_escape(cfg.get('push_provider', ''))}</code></td></tr>
</table>
</div>
</div>

<div class="grid">
<div class="card">
<h3>Start at Login</h3>
<p><strong>Platform:</strong> {html_escape(start_at_login.platform_name)}</p>
<p><strong>Status:</strong> {'ENABLED' if start_at_login.enabled else 'disabled'}</p>
<p><small>{html_escape(start_at_login.detail)}</small></p>
<form method="post" action="/start-at-login/enable" style="display:inline">
<button type="submit" class="btn-start" {'disabled' if start_at_login.enabled or not start_at_login.supported else ''}>Enable Start at Login</button>
</form>
<form method="post" action="/start-at-login/disable" style="display:inline">
<button type="submit" class="btn-stop" {'disabled' if not start_at_login.enabled or not start_at_login.supported else ''}>Disable Start at Login</button>
</form>
</div>

<div class="card">
<h3>Debug Snapshots</h3>
<p><strong>Warning:</strong> debug snapshots may contain PulsePoint page text, call details, locations, and unit information. Do not post publicly unless reviewed/redacted.</p>
<table>
<tr><th>File</th><th>Modified</th><th>Size</th><th>Action</th></tr>
{snapshot_rows}
</table>
</div>

<div class="card">
<h3>Local Data</h3>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Alert history events</td><td>{history_count}</td></tr>
<tr><td>Alert evidence snapshots</td><td>{evidence_count}</td></tr>
</table>
</div>

<div class="card">
<h3>Exports</h3>
<p>Use these for troubleshooting after a false alert or missed alert.</p>
<a href="/diagnostics/export"><button type="button">Export Diagnostics ZIP</button></a>
<a href="/history/export.csv"><button type="button">Export Alert History CSV</button></a>
<a href="/config/export-redacted"><button type="button">Export Redacted Config JSON</button></a>
</div>
</div>
"""
        return layout("Troubleshooting", content)


    @app.route("/debug-snapshots/<path:filename>")
    def view_debug_snapshot(filename: str) -> Response:
        snapshot_path = safe_debug_snapshot_path(filename)
        if snapshot_path is None:
            return Response("Debug snapshot not found.", status=404, mimetype="text/plain")

        try:
            text = snapshot_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return Response(f"Could not read debug snapshot: {exc}", status=500, mimetype="text/plain")

        content = f"""
<h2>Debug Snapshot</h2>
<div class="warn">
<strong>Privacy warning:</strong> this local file may contain PulsePoint page text, call details, locations, and unit information. Do not post publicly unless reviewed/redacted.
</div>
<div class="card">
<p><strong>File:</strong> <code>{html_escape(snapshot_path.name)}</code></p>
<p><a href="/troubleshooting">Back to Troubleshooting</a></p>
<pre style="white-space:pre-wrap; background:#111; color:#eee; padding:12px; border-radius:8px; overflow:auto;">{html_escape(text)}</pre>
</div>
"""
        return layout("Debug Snapshot", content)


    @app.route("/start-at-login/enable", methods=["POST"])
    def enable_start_at_login_route() -> Response:
        try:
            status = enable_start_at_login()
            state.log(f"Start at login enabled for {status.platform_name}: {status.path}")
        except Exception as exc:
            state.log(f"Could not enable start at login: {exc}")
        return redirect("/troubleshooting")


    @app.route("/start-at-login/disable", methods=["POST"])
    def disable_start_at_login_route() -> Response:
        try:
            status = disable_start_at_login()
            state.log(f"Start at login disabled for {status.platform_name}.")
        except Exception as exc:
            state.log(f"Could not disable start at login: {exc}")
        return redirect("/troubleshooting")


    @app.route("/config")
    def config_page() -> Response:
        cfg = load_config()
        path = config_path()
        content = f"""
<h2>Config Backup / Import / Reset</h2>

<div class="warn">
<strong>Warning:</strong> Full config exports may include Pushover keys, ntfy tokens, agency IDs, unit IDs, and other sensitive settings. Store full backups securely.
</div>

<div class="card">
<h3>Config File</h3>
<p><strong>Path:</strong> <code>{html_escape(path)}</code></p>
</div>

<div class="card">
<h3>Export</h3>
<p>Use full export for personal backup/restore. Use redacted export for troubleshooting or sharing.</p>
<a href="/config/export"><button type="button">Export Full Config JSON</button></a>
<a href="/config/export-redacted"><button type="button">Export Redacted Config JSON</button></a>
<a href="/diagnostics/export"><button type="button">Export Diagnostics ZIP</button></a>
</div>

<div class="card">
<h3>Import</h3>
<form method="post" action="/config/import" enctype="multipart/form-data">
<label>Config JSON file</label>
<input type="file" name="config_file" accept=".json,application/json">
<br>
<button type="submit">Import Config</button>
</form>
</div>

<div class="card">
<h3>Reset</h3>
<p>This resets the app config to defaults. It does not delete alert history.</p>
<form method="post" action="/config/reset">
<button type="submit" class="btn-stop">Reset Config to Defaults</button>
</form>
</div>

<div class="card">
<h3>Current Non-Secret Summary</h3>
<table>
<tr><th>Setting</th><th>Value</th></tr>
<tr><td>Agency</td><td><code>{html_escape(agency_display(cfg))}</code></td></tr>
<tr><td>Units</td><td><code>{html_escape(unit_set_display(cfg))}</code></td></tr>
<tr><td>Alert profile</td><td>{html_escape(alert_profile_label(cfg.get('alert_profile')))}</td></tr>
<tr><td>Desktop alert</td><td>{'ON' if cfg.get('desktop_alert_enabled') else 'OFF'}</td></tr>
<tr><td>Phone alert</td><td>{'ON' if cfg.get('phone_alert_enabled') else 'OFF'}</td></tr>
<tr><td>Push provider</td><td><code>{html_escape(cfg.get("push_provider", ""))}</code></td></tr>
<tr><td>Include call details in phone push</td><td>{'ON' if cfg.get('include_call_details_in_phone_push') else 'OFF'}</td></tr>
<tr><td>Auto-start monitor</td><td>{'ON' if cfg.get('auto_start_monitor') else 'OFF'}</td></tr>
<tr><td>Prevent sleep</td><td>{'ON' if cfg.get('prevent_sleep') else 'OFF'}</td></tr>
</table>
</div>
"""
        return layout("Config", content)


    def redacted_config(cfg: dict) -> dict:
        redacted = dict(cfg)
        secret_fields = [
            "pushover_app_token",
            "pushover_user_key",
            "ntfy_token",
        ]
        for field in secret_fields:
            if redacted.get(field):
                redacted[field] = "REDACTED"
        return redacted



    @app.route("/diagnostics/export")
    def export_diagnostics() -> Response:
        cfg = load_config()
        redacted_cfg = redacted_config(cfg)
        start_at_login = get_start_at_login_status()

        with state.lock:
            state_snapshot = {
                "monitor_running": getattr(state, "monitor_running", None),
                "alert_active": getattr(state, "alert_active", None),
                "alert_reason": getattr(state, "alert_reason", None),
                "last_status": getattr(state, "last_status", None),
                "last_error": getattr(state, "last_error", None),
                "last_check_time": getattr(state, "last_check_time", None),
                "last_success_time": getattr(state, "last_success_time", None),
                "last_refresh_time": getattr(state, "last_refresh_time", None),
                "consecutive_errors": getattr(state, "consecutive_errors", None),
                "active_section_found": getattr(state, "active_section_found", None),
            }
            alert_history = list(getattr(state, "alert_events", []))[-200:]
            alert_evidence = list(getattr(state, "alert_evidence", []))[-100:]

        recent_logs = state.logs(200)

        diagnostics = {
            "generated_at": now_local_iso(),
            "app": {
                "name": "PulsePoint Alert Monitor",
                "runtime": "local",
            },
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
            },
            "paths": {
                "config_path": str(config_path()),
                "runtime_dir": str(Path(config_path()).parent),
            },
            "monitor": state_snapshot,
            "start_at_login": {
                "supported": start_at_login.supported,
                "enabled": start_at_login.enabled,
                "platform": start_at_login.platform_name,
                "path": str(start_at_login.path) if start_at_login.path else None,
                "detail": start_at_login.detail,
            },
            "settings_summary": {
                "agency_ids": redacted_cfg.get("agency_ids"),
                "units": redacted_cfg.get("units"),
                "alert_profile": redacted_cfg.get("alert_profile"),
                "test_mode": redacted_cfg.get("test_mode"),
                "poll_seconds": redacted_cfg.get("poll_seconds"),
                "desktop_alert_enabled": redacted_cfg.get("desktop_alert_enabled"),
                "phone_alert_enabled": redacted_cfg.get("phone_alert_enabled"),
                "push_provider": redacted_cfg.get("push_provider"),
                "include_call_details_in_phone_push": redacted_cfg.get("include_call_details_in_phone_push"),
                "prevent_sleep": redacted_cfg.get("prevent_sleep"),
                "auto_start_monitor": redacted_cfg.get("auto_start_monitor"),
            },
            "counts": {
                "recent_log_lines": len(recent_logs),
                "alert_history_events_included": len(alert_history),
                "alert_evidence_snapshots_included": len(alert_evidence),
            },
        }

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("diagnostics.json", json.dumps(diagnostics, indent=2))
            archive.writestr("redacted_config.json", json.dumps(redacted_cfg, indent=2))
            archive.writestr("recent_logs.txt", "\n".join(recent_logs))
            archive.writestr("alert_history_recent.json", json.dumps(alert_history, indent=2))
            archive.writestr("alert_evidence_recent.json", json.dumps(alert_evidence, indent=2))

        buffer.seek(0)

        response = Response(buffer.getvalue(), mimetype="application/zip")
        response.headers["Content-Disposition"] = f'attachment; filename="pulsepoint_diagnostics_{datetime_filename()}.zip"'
        state.log("Diagnostics ZIP exported.")
        return response


    @app.route("/config/export")
    def export_config() -> Response:
        cfg = load_config()
        body = json.dumps(cfg, indent=2)
        response = Response(body, mimetype="application/json")
        response.headers["Content-Disposition"] = f'attachment; filename="pulsepoint_config_full_{datetime_filename()}.json"'
        state.log("Full config exported.")
        return response


    @app.route("/config/export-redacted")
    def export_redacted_config() -> Response:
        cfg = redacted_config(load_config())
        body = json.dumps(cfg, indent=2)
        response = Response(body, mimetype="application/json")
        response.headers["Content-Disposition"] = f'attachment; filename="pulsepoint_config_redacted_{datetime_filename()}.json"'
        state.log("Redacted config exported.")
        return response


    @app.route("/config/import", methods=["POST"])
    def import_config() -> Response:
        uploaded = request.files.get("config_file")
        if uploaded is None or not uploaded.filename:
            state.log("Config import failed: no file selected.")
            return redirect("/config")

        try:
            data = json.load(uploaded.stream)
            if not isinstance(data, dict):
                raise ValueError("Config JSON root must be an object.")

            if isinstance(data.get("units"), str):
                data["units"] = normalize_units(data["units"])

            save_config(data)
            state.log(f"Config imported from {uploaded.filename}.")
        except Exception as exc:
            state.log(f"Config import failed: {exc}")

        return redirect("/config")


    @app.route("/config/reset", methods=["POST"])
    def reset_config() -> Response:
        cfg = DEFAULT_CONFIG.copy()
        cfg["sound_file"] = asset_default_sound()
        save_config(cfg)
        state.log("Config reset to defaults.")
        return redirect("/config")


    @app.route("/logs")
    def logs_page() -> Response:
        return layout("Logs", f"<h2>Logs</h2><div class='card'><form method='get' action='/logs'><button>Refresh Logs</button></form><pre>{html_escape(chr(10).join(state.logs()))}</pre></div>")

    @app.route("/start", methods=["POST"])
    def start() -> Response:
        start_monitor_if_needed()
        return redirect("/")

    @app.route("/stop", methods=["POST"])
    def stop() -> Response:
        stop_monitor()
        return redirect("/")



    @app.route("/toggle-monitor", methods=["POST"])
    def toggle_monitor() -> Response:
        with state.lock:
            running = state.monitor_running

        if running:
            stop_monitor("Monitor stop requested from top status bar.")
        else:
            start_monitor_if_needed("Monitor start requested from top status bar.")

        return redirect(request.referrer or "/")


    @app.route("/refresh-now", methods=["POST"])
    def refresh_now() -> Response:
        with state.lock:
            running = state.monitor_running

        if not running:
            state.log("Manual refresh ignored: monitor is not running.")
            return redirect("/")

        state.request_manual_refresh()
        state.log("Manual refresh queued.")
        return redirect("/")


    @app.route("/ack", methods=["POST"])
    def ack() -> Response:
        silence_alert(state); state.log("Laptop alert acknowledged/silenced."); return redirect("/")

    @app.route("/test-sound", methods=["POST"])
    def test_sound() -> Response:
        trigger_desktop_alert("Manual laptop test alert", state); return redirect("/alerts")


    @app.route("/simulate-incident", methods=["POST"])
    def simulate_incident() -> Response:
        cfg = load_config()
        units = cfg.get("units") or ["M231"]
        unit = units[0] if units else "M231"
        reason = (
            f"New active incident for unit(s): {unit}\n\n"
            "Call details:\n"
            "SIMULATED TEST INCIDENT\n"
            "Medical Aid / Unknown Problem\n"
            "123 Example St\n"
            f"{unit}\n"
            "Generated by PulsePoint Alert Monitor local test"
        )
        trigger_alert(reason, state)
        state.log("Simulated active incident alert requested.")
        return redirect("/alerts")


    @app.route("/test-push", methods=["POST"])
    def test_push() -> Response:
        cfg = load_config()
        profile = normalize_alert_profile(cfg.get("alert_profile"))
        tracking = profile == "track_units"
        provider = cfg.get("push_provider", "pushover")
        title = "PulsePoint Alert Monitor Test"
        message = "Manual phone push test sent."

        sent_any = False

        if provider in ("pushover", "both"):
            sent_any = send_pushover(
                title,
                message,
                state,
                emergency=not tracking,
                priority_override=-1 if tracking else None,
            ) or sent_any

        if provider in ("ntfy", "both"):
            sent_any = send_ntfy(
                title,
                message,
                state,
                priority_override=2 if tracking else None,
                allow_call=not tracking,
            ) or sent_any

        if provider == "none":
            state.log("Test phone push skipped: provider set to none.")

        reason = "Manual phone push test sent." if sent_any else "Manual phone push test attempted but no provider confirmed success."
        state.record_alert(
            reason,
            desktop_enabled=False,
            phone_enabled=sent_any,
            source="manual_phone",
            profile=profile,
            ack_required=False,
        )

        return redirect("/alerts")

    return app


def main() -> None:
    state.log("PulsePoint Alert App started.")
    state.log("Open http://127.0.0.1:8765")
    create_app().run(host="127.0.0.1", port=8765, debug=False)
