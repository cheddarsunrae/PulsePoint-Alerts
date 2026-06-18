# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime


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
    ) -> None:
        event = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "desktop": "yes" if desktop_enabled else "no",
            "phone": "yes" if phone_enabled else "no",
            "source": source,
            "acknowledged": "no",
            "ack_time": "",
        }
        with self.lock:
            self.alert_events.append(event)
            del self.alert_events[:-500]

    def acknowledge_latest_alert(self) -> None:
        ack_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            for event in reversed(self.alert_events):
                if event.get("acknowledged") == "no":
                    event["acknowledged"] = "yes"
                    event["ack_time"] = ack_time
                    break

    def alert_history(self, limit: int = 100) -> list[dict[str, str]]:
        with self.lock:
            return list(self.alert_events[-limit:])

    def clear_alert_history(self) -> None:
        with self.lock:
            self.alert_events.clear()

    def logs(self, limit: int = 250) -> list[str]:
        with self.lock:
            return list(self.log_lines[-limit:])
