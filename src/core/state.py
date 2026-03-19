"""
ARK State Management
====================
ARKの現在のフェーズや、これまでの履歴を管理・保存するステートマシン。
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol

from src.core.models import Phase

log = logging.getLogger("ARK.State")

STATE_FILENAME: Final[str] = ".ark_state.json"

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

class ARKState:
    def __init__(self, workspace: Path) -> None:
        self._path: Path = workspace / STATE_FILENAME
        self.task_id:    str   = str(uuid.uuid4())
        self.phase:      Phase = Phase.IDLE
        self.goal:       str   = ""
        self.retry_count: int  = 0
        self.history:    list[dict] = []
        self._on_status_change: StatusCallback | None = None

    def set_callback(self, callback: StatusCallback | None) -> None:
        self._on_status_change = callback

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "task_id":    self.task_id,
            "phase":      self.phase.value,
            "goal":       self.goal,
            "retry_count": self.retry_count,
            "history":    self.history,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self._path.exists(): return
        data: dict = json.loads(self._path.read_text(encoding="utf-8"))
        self.task_id     = data.get("task_id", self.task_id)
        self.phase       = Phase(data.get("phase", Phase.IDLE.value))
        self.goal        = data.get("goal", "")
        self.retry_count = data.get("retry_count", 0)
        self.history     = data.get("history", [])

    def push_event(self, phase: Phase, status: str, detail: str = "") -> None:
        self.history.append({
            "phase":     phase.value,
            "status":    status,
            "detail":    detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if self._on_status_change:
            self._on_status_change(phase, status, self.retry_count, detail)

    def transition(self, phase: Phase) -> None:
        log.info("State transition: %s → %s", self.phase.value, phase.value)
        self.phase = phase
        self.save()
        if self._on_status_change:
            self._on_status_change(phase, "TRANSITION", self.retry_count, f"Moving to {phase.value}")