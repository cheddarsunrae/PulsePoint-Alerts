# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import app_dir


HISTORY_LIMIT = 500
EVIDENCE_LIMIT = 100


@dataclass
class RuntimeState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    monitor_stop: threading.Event = field(default_factory=threading.Event)
    alert_stop: threading.Event = field(default_factory=threading.Event)
    monitor_running: bool = False
    alert_active: bool = False
    alert_reason: str = ""
    log_lines: list[str] = field(default_factory=list)
    alert_events: list[dict[str, str]] = field(default_factory=list)
    alert_evidence: list[dict[str, Any]] = field(default_factory=list)
    last_check_time: str = ""
    last_success_time: str = ""
    last_refresh_time: str = ""
    last_error: str = ""
    consecutive_errors: int = 0
    active_section_found: bool = False
    manual_refresh_requested: bool = False

    def alert_history_path(self) -> Path:
        return app_dir() / "alert_history.json"

    def _write_alert_history(self, events: list[dict[str, str]]) -> None:
        try:
            path = self.alert_history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".json.tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(events[-HISTORY_LIMIT:], f, indent=2)
            tmp_path.replace(path)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Alert history save error: {exc}", flush=True)


    def alert_evidence_path(self) -> Path:
        return app_dir() / "alert_evidence.json"


    def _write_alert_evidence(self, evidence_items: list[dict[str, Any]]) -> None:
        try:
            path = self.alert_evidence_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(".json.tmp")
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(evidence_items[-EVIDENCE_LIMIT:], f, indent=2)
            tmp_path.replace(path)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Alert evidence save error: {exc}", flush=True)


    def load_alert_evidence(self) -> None:
        try:
            path = self.alert_evidence_path()
            if not path.exists():
                return
            with path.open("r", encoding="utf-8") as f:
                data: Any = json.load(f)
            if not isinstance(data, list):
                return

            evidence_items: list[dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    evidence_items.append(item)

            with self.lock:
                self.alert_evidence = evidence_items[-EVIDENCE_LIMIT:]

            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loaded {len(evidence_items[-EVIDENCE_LIMIT:])} alert evidence snapshots.", flush=True)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Alert evidence load error: {exc}", flush=True)


    def record_alert_evidence(self, evidence: dict[str, Any]) -> str:
        evidence_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        item = {
            "id": evidence_id,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **evidence,
        }

        with self.lock:
            self.alert_evidence.append(item)
            del self.alert_evidence[:-EVIDENCE_LIMIT]
            snapshot = list(self.alert_evidence)

        self._write_alert_evidence(snapshot)
        return evidence_id


    def find_alert_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self.lock:
            for item in reversed(self.alert_evidence):
                if str(item.get("id", "")) == str(evidence_id):
                    return dict(item)
        return None


    def alert_evidence_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.alert_evidence[-limit:])


    def clear_alert_evidence(self) -> None:
        with self.lock:
            self.alert_evidence.clear()

        self._write_alert_evidence([])


    def debug_snapshots_dir(self) -> Path:
        return app_dir() / "debug_snapshots"


    def record_debug_snapshot(self, reason: str, text: str) -> Path | None:
        """Write a local diagnostic text snapshot and return its path.

        Snapshots may contain full PulsePoint page text, including incident details.
        They are intentionally local-only troubleshooting artifacts.
        """
        try:
            safe_reason = "".join(
                char.lower() if char.isalnum() else "-"
                for char in str(reason).strip()
            ).strip("-") or "snapshot"
            while "--" in safe_reason:
                safe_reason = safe_reason.replace("--", "-")

            snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = self.debug_snapshots_dir() / f"{snapshot_id}_{safe_reason}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)

            header = (
                "PulsePointer Alerter debug snapshot\n"
                f"Reason: {reason}\n"
                f"Captured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "Warning: this file may contain PulsePoint call details, addresses, and units.\n"
                "\n--- PAGE TEXT ---\n"
            )
            path.write_text(header + str(text), encoding="utf-8", errors="replace")
            return path
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Debug snapshot save error: {exc}", flush=True)
            return None


    def load_alert_history(self) -> None:
        try:
            path = self.alert_history_path()
            if not path.exists():
                return
            with path.open("r", encoding="utf-8") as f:
                data: Any = json.load(f)
            if not isinstance(data, list):
                return

            events: list[dict[str, str]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                clean = {str(k): str(v) for k, v in item.items()}
                events.append(clean)

            with self.lock:
                self.alert_events = events[-HISTORY_LIMIT:]

            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loaded {len(events[-HISTORY_LIMIT:])} alert history events.", flush=True)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Alert history load error: {exc}", flush=True)



    def request_manual_refresh(self) -> None:
        with self.lock:
            self.manual_refresh_requested = True


    def consume_manual_refresh(self) -> bool:
        with self.lock:
            requested = self.manual_refresh_requested
            self.manual_refresh_requested = False
            return requested


    def mark_check(self) -> None:
        with self.lock:
            self.last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    def mark_success(self, active_section_found: bool | None = None) -> None:
        with self.lock:
            self.last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.consecutive_errors = 0
            self.last_error = ""
            if active_section_found is not None:
                self.active_section_found = active_section_found


    def mark_refresh(self) -> None:
        with self.lock:
            self.last_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    def mark_error(self, message: str) -> None:
        with self.lock:
            self.last_error = str(message)
            self.consecutive_errors += 1


    def log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(line, flush=True)
        with self.lock:
            self.log_lines.append(line)
            del self.log_lines[:-300]

    def record_alert(
        self,
        reason: str,
        desktop_enabled: bool,
        phone_enabled: bool,
        source: str = "monitor",
        evidence_id: str = "",
        profile: str = "alert_me",
        ack_required: bool = True,
    ) -> None:
        event = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "desktop": "yes" if desktop_enabled else "no",
            "phone": "yes" if phone_enabled else "no",
            "source": source,
            "profile": profile,
            "ack_required": "yes" if ack_required else "no",
            "acknowledged": "no" if ack_required else "not_required",
            "ack_time": "",
            "evidence_id": evidence_id,
        }
        with self.lock:
            self.alert_events.append(event)
            del self.alert_events[:-HISTORY_LIMIT]
            snapshot = list(self.alert_events)

        self._write_alert_history(snapshot)

    def acknowledge_latest_alert(self) -> None:
        ack_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        changed = False

        with self.lock:
            for event in reversed(self.alert_events):
                if event.get("acknowledged") == "no":
                    event["acknowledged"] = "yes"
                    event["ack_time"] = ack_time
                    changed = True
                    break
            snapshot = list(self.alert_events)

        if changed:
            self._write_alert_history(snapshot)

    def alert_history(self, limit: int = 100) -> list[dict[str, str]]:
        with self.lock:
            return list(self.alert_events[-limit:])

    def clear_alert_history(self) -> None:
        with self.lock:
            self.alert_events.clear()

        self._write_alert_history([])

    def logs(self, limit: int = 250) -> list[str]:
        with self.lock:
            return list(self.log_lines[-limit:])
