# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading

from flask import Flask, Response, redirect, request

from .alerting import send_ntfy, send_pushover, silence_alert, trigger_alert
from .config import load_config, normalize_units, save_config
from .keepawake import set_keep_awake
from .monitor import monitor_loop
from .runtime import RuntimeState

state = RuntimeState()


def html_escape(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def checked(value: object) -> str:
    return "checked" if value else ""


def selected(actual: object, expected: object) -> str:
    return "selected" if str(actual) == str(expected) else ""


def units_display(units: list[str] | None) -> str:
    return ", ".join(units or [])


def nav() -> str:
    return """
<nav>
<a href="/">Dashboard</a>
<a href="/agencies">Agencies</a>
<a href="/units">Apparatus / Units</a>
<a href="/setup">Monitor Setup</a>
<a href="/alerts">Alerts</a>
<a href="/logs">Logs</a>
</nav>
"""


def layout(title: str, content: str) -> Response:
    cfg = load_config()
    with state.lock:
        running_text = "RUNNING" if state.monitor_running else "STOPPED"
        active_text = "ACTIVE" if state.alert_active else "INACTIVE"
        reason = state.alert_reason
    active_agency = html_escape(cfg.get("agency_ids", "") or "(none)")
    active_units = html_escape(units_display(cfg.get("units", [])) or "(none)")
    mode = "TEST" if cfg.get("test_mode") else "UNIT"
    status_class = "danger" if state.alert_active else "good"
    return Response(f"""<!doctype html>
<html><head><title>{html_escape(title)} - PulsePoint Alert Monitor</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; color: #222; }}
header {{ background: #222; color: white; padding: 18px 28px; }} header h1 {{ margin: 0; font-size: 24px; }}
nav {{ background: #333; padding: 0 20px; }} nav a {{ color: white; display: inline-block; padding: 12px 14px; text-decoration: none; }} nav a:hover {{ background: #555; }}
main {{ max-width: 1100px; margin: 25px auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 1px 6px #ccc; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 14px 0; background: #fff; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
label {{ font-weight: bold; display: block; margin-top: 14px; }}
input[type=text], input[type=password], input[type=number], select {{ width: 100%; padding: 9px; font-size: 16px; box-sizing: border-box; }}
button {{ padding: 10px 16px; font-size: 15px; margin: 6px 6px 6px 0; cursor: pointer; }}
.good {{ background: #ddffdd; border: 1px solid #008000; padding: 10px; border-radius: 6px; }} .danger {{ background: #ffd6d6; border: 1px solid #b00020; padding: 10px; border-radius: 6px; font-weight: bold; }}
.warn {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 6px; }}
pre {{ background: #111; color: #0f0; padding: 15px; height: 400px; overflow-y: scroll; white-space: pre-wrap; }}
code {{ background: #eee; padding: 2px 4px; }} small {{ color: #555; }} table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }} th, td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }}
.statusbar {{ background: #eee; padding: 10px 20px; font-size: 14px; }}
</style></head>
<body><header><h1>PulsePoint Alert Monitor</h1></header>{nav()}
<div class="statusbar"><strong>Monitor:</strong> {running_text} | <strong>Mode:</strong> {mode} | <strong>Alert:</strong> {active_text} {html_escape(reason)} | <strong>Agency IDs:</strong> {active_agency} | <strong>Units:</strong> {active_units}</div>
<main>{content}</main></body></html>""", mimetype="text/html")


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def dashboard() -> Response:
        cfg = load_config()
        logs = state.logs(60)
        content = f"""
<h2>Dashboard</h2><div class="warn">Backup alert only. Not affiliated with PulsePoint Foundation or any public safety agency. Not official dispatch. No warranty. Do not rely on this as your sole alerting method.</div>
<div class="grid"><div class="card"><h3>Active Monitor Setup</h3>
<p><strong>Agency IDs:</strong> <code>{html_escape(cfg.get('agency_ids') or '(none)')}</code></p>
<p><strong>Units:</strong> <code>{html_escape(units_display(cfg.get('units')) or '(none)')}</code></p>
<p><strong>Poll:</strong> {cfg.get('poll_seconds', 5)} seconds</p><p><strong>Mode:</strong> {'TEST' if cfg.get('test_mode') else 'UNIT'}</p>
<p><strong>Sleep prevention:</strong> {'ON' if cfg.get('prevent_sleep') else 'OFF'}</p></div>
<div class="card"><h3>Actions</h3><form method="post" action="/start" style="display:inline"><button type="submit">Start Monitor</button></form>
<form method="post" action="/stop" style="display:inline"><button type="submit">Stop Monitor</button></form>
<form method="post" action="/ack" style="display:inline"><button type="submit">ACK / Silence Alert</button></form>
<form method="post" action="/test-sound"><button type="submit">Test Laptop Alert</button></form>
<form method="post" action="/test-push"><button type="submit">Test Phone Push</button></form></div></div>
<div class="card"><h3>Recent Log</h3><pre>{html_escape(chr(10).join(logs))}</pre></div>"""
        return layout("Dashboard", content)

    @app.route("/agencies")
    def agencies_page() -> Response:
        cfg = load_config(); rows = ""
        for i, item in enumerate(cfg.get("agency_presets", [])):
            rows += f"<tr><td>{html_escape(item.get('name',''))}</td><td><code>{html_escape(item.get('agency_ids',''))}</code></td><td><form method='post' action='/use-agency/{i}' style='display:inline'><button>Use</button></form><form method='post' action='/delete-agency/{i}' style='display:inline'><button>Delete</button></form></td></tr>"
        if not rows: rows = '<tr><td colspan="3"><em>No agencies saved yet.</em></td></tr>'
        content = f"""<h2>Agencies</h2><p>Save each PulsePoint feed by a human name.</p><div class="card"><h3>Add / Save Agency</h3><form method="post" action="/agencies/add"><label>Agency name</label><input type="text" name="name" placeholder="Example: AMR San Diego"><label>PulsePoint agency ID(s)</label><input type="text" name="agency_ids" placeholder="Example: 37047 or 37047,12345"><small>Use the number after <code>?agencies=</code> in the PulsePoint Web URL.</small><br><button type="submit">Save Agency</button></form></div><div class="card"><h3>Saved Agencies</h3><table><tr><th>Name</th><th>Agency IDs</th><th>Actions</th></tr>{rows}</table></div>"""
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
        content = f"""<h2>Apparatus / Units</h2><div class="card"><h3>Add / Save Unit Set</h3><form method="post" action="/units/add"><label>Name</label><input type="text" name="name" placeholder="Example: M231 shift / Station 36"><label>Units</label><input type="text" name="units" placeholder="Example: M231, M36, E36"><small>Comma-separated.</small><br><button type="submit">Save Unit Set</button></form></div><div class="card"><h3>Saved Unit Sets</h3><table><tr><th>Name</th><th>Units</th><th>Actions</th></tr>{rows}</table></div>"""
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
        content = f"""<h2>Monitor Setup</h2><div class="card"><form method="post" action="/setup/save"><label>Choose saved agency</label><select name="agency_index">{agency_opts}</select><label>Or enter agency ID(s) manually</label><input type="text" name="agency_ids" value="{html_escape(cfg.get('agency_ids', ''))}"><label>Choose saved apparatus / unit set</label><select name="unit_index">{unit_opts}</select><label>Or enter units manually</label><input type="text" name="units" value="{html_escape(units_display(cfg.get('units', [])))}"><label>Poll interval, seconds</label><input type="number" name="poll_seconds" value="{cfg.get('poll_seconds', 5)}" min="5" max="60"><label>PulsePoint page refresh interval, seconds</label><input type="number" name="refresh_seconds" value="{cfg.get('refresh_seconds', 300)}" min="60" max="1800"><label><input type="checkbox" name="test_mode" {checked(cfg.get('test_mode', False))}> Test mode</label><label><input type="checkbox" name="headless" {checked(cfg.get('headless', True))}> Headless browser mode</label><label><input type="checkbox" name="prevent_sleep" {checked(cfg.get('prevent_sleep', True))}> Prevent sleep</label><label><input type="checkbox" name="keep_display_on" {checked(cfg.get('keep_display_on', False))}> Keep display on</label><br><button type="submit">Save Monitor Setup</button></form></div>"""
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
        content = f"""<h2>Alerts</h2><div class="card"><form method="post" action="/alerts/save"><h3>Laptop Alert</h3><label>Alert sound file</label><input type="text" name="sound_file" value="{html_escape(cfg.get('sound_file',''))}"><label>Alert mode</label><select name="alert_mode"><option value="until_ack" {selected(cfg.get('alert_mode'), 'until_ack')}>Keep alerting until acknowledged</option><option value="timed" {selected(cfg.get('alert_mode'), 'timed')}>Alert for fixed duration</option></select><label>Alert duration, seconds</label><input type="number" name="alert_duration_seconds" value="{cfg.get('alert_duration_seconds',30)}"><label>Cooldown, seconds</label><input type="number" name="cooldown_seconds" value="{cfg.get('cooldown_seconds',60)}"><h3>Phone Push</h3><label>Push provider</label><select name="push_provider"><option value="none" {selected(provider, 'none')}>None</option><option value="pushover" {selected(provider, 'pushover')}>Pushover</option><option value="ntfy" {selected(provider, 'ntfy')}>ntfy</option><option value="both" {selected(provider, 'both')}>Both</option></select><h4>Pushover</h4><label>App API Token</label><input type="password" name="pushover_app_token" value="{html_escape(cfg.get('pushover_app_token',''))}"><label>User Key</label><input type="password" name="pushover_user_key" value="{html_escape(cfg.get('pushover_user_key',''))}"><label>Device Name — optional</label><input type="text" name="pushover_device" value="{html_escape(cfg.get('pushover_device',''))}"><label>Priority</label><input type="number" name="pushover_priority" value="{cfg.get('pushover_priority',2)}"><label>Retry Seconds</label><input type="number" name="pushover_retry_seconds" value="{cfg.get('pushover_retry_seconds',30)}"><label>Expire Seconds</label><input type="number" name="pushover_expire_seconds" value="{cfg.get('pushover_expire_seconds',1800)}"><label>Sound</label><input type="text" name="pushover_sound" value="{html_escape(cfg.get('pushover_sound','persistent'))}"><h4>ntfy</h4><label>Server</label><input type="text" name="ntfy_server" value="{html_escape(cfg.get('ntfy_server','https://ntfy.sh'))}"><label>Topic</label><input type="text" name="ntfy_topic" value="{html_escape(cfg.get('ntfy_topic',''))}"><label>Bearer Token — optional</label><input type="password" name="ntfy_token" value="{html_escape(cfg.get('ntfy_token',''))}"><label>Priority</label><input type="number" name="ntfy_priority" value="{cfg.get('ntfy_priority',5)}"><label>Tags</label><input type="text" name="ntfy_tags" value="{html_escape(cfg.get('ntfy_tags','rotating_light,ambulance'))}"><label>Call — optional</label><input type="text" name="ntfy_call" value="{html_escape(cfg.get('ntfy_call',''))}"><br><button type="submit">Save Alert Settings</button></form><form method="post" action="/test-sound" style="display:inline"><button>Test Laptop Alert</button></form><form method="post" action="/test-push" style="display:inline"><button>Test Phone Push</button></form></div>"""
        return layout("Alerts", content)

    @app.route("/alerts/save", methods=["POST"])
    def save_alerts() -> Response:
        cfg = load_config(); fields = ["sound_file","alert_mode","push_provider","pushover_app_token","pushover_user_key","pushover_device","pushover_sound","ntfy_server","ntfy_topic","ntfy_token","ntfy_tags","ntfy_call"]
        for field in fields: cfg[field] = request.form.get(field, "").strip()
        for field in ["alert_duration_seconds","cooldown_seconds","pushover_priority","pushover_retry_seconds","pushover_expire_seconds","ntfy_priority"]: cfg[field] = int(request.form.get(field, cfg.get(field, 0)))
        cfg["pushover_retry_seconds"] = max(30, cfg["pushover_retry_seconds"]); cfg["pushover_expire_seconds"] = min(10800, cfg["pushover_expire_seconds"]); save_config(cfg); state.log("Alert settings saved."); return redirect("/alerts")

    @app.route("/logs")
    def logs_page() -> Response:
        return layout("Logs", f"<h2>Logs</h2><div class='card'><form method='get' action='/logs'><button>Refresh Logs</button></form><pre>{html_escape(chr(10).join(state.logs()))}</pre></div>")

    @app.route("/start", methods=["POST"])
    def start() -> Response:
        with state.lock:
            if state.monitor_running:
                state.log("Monitor already running."); return redirect("/")
            state.monitor_running = True
        state.monitor_stop.clear(); threading.Thread(target=monitor_loop, args=(state,), daemon=True).start(); state.log("Monitor start requested."); return redirect("/")

    @app.route("/stop", methods=["POST"])
    def stop() -> Response:
        state.monitor_stop.set(); silence_alert(state)
        try: set_keep_awake(False)
        except Exception: pass
        state.log("Monitor stop requested."); return redirect("/")

    @app.route("/ack", methods=["POST"])
    def ack() -> Response:
        silence_alert(state); state.log("Laptop alert acknowledged/silenced."); return redirect("/")

    @app.route("/test-sound", methods=["POST"])
    def test_sound() -> Response:
        trigger_alert("Manual laptop test alert", state); return redirect("/alerts")

    @app.route("/test-push", methods=["POST"])
    def test_push() -> Response:
        cfg = load_config(); provider = cfg.get("push_provider", "pushover"); title = "PulsePoint Alert Monitor Test"; message = "Test phone push sent."
        if provider in ("pushover", "both"): send_pushover(title, message, state, emergency=True)
        if provider in ("ntfy", "both"): send_ntfy(title, message, state)
        if provider == "none": state.log("Test phone push skipped: provider set to none.")
        return redirect("/alerts")

    return app


def main() -> None:
    state.log("PulsePoint Alert App started.")
    state.log("Open http://127.0.0.1:8765")
    create_app().run(host="127.0.0.1", port=8765, debug=False)

