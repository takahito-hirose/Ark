"""
ARK Core — Data Models (Payloads & Envelope)
=============================================
All inter-SYLPH communication is typed via these dataclasses.
Conforms to: specs/core_logic.md §2
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

ARK_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Phase(str, Enum):
    IDLE       = "IDLE"
    PLANNING   = "PLANNING"
    CODING     = "CODING"
    REVIEWING  = "REVIEWING"
    COMMITTING = "COMMITTING"
    BLOCKED    = "BLOCKED"
    DONE       = "DONE"


@dataclass
class RunResult:
    """Result of a code execution attempt."""
    exit_code: int
    stdout:    str
    stderr:    str
    duration:  float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class ReviewStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class FileAction(str, Enum):
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"


class IssueSeverity(str, Enum):
    ERROR   = "ERROR"
    WARNING = "WARNING"
    INFO    = "INFO"


# ---------------------------------------------------------------------------
# Payload models
# ---------------------------------------------------------------------------

@dataclass
class PlanPayload:
    """Architect → Coder: what to build."""
    goal:                 str
    spec_path:            str
    target_files:         list[str]
    constraints:          list[str]
    acceptance_criteria:  list[str]


@dataclass
class FileChange:
    """A single file operation inside a CodePayload."""
    path:    str
    action:  FileAction
    content: str


@dataclass
class CodePayload:
    """Coder → Reviewer: what was built."""
    plan_ref:     str           # task_id of originating task
    files:        list[FileChange]
    test_command: str
    notes:        str = ""


@dataclass
class ReviewIssue:
    severity: IssueSeverity
    file:     str
    line:     int
    message:  str


@dataclass
class ReviewPayload:
    """Reviewer → Orchestrator: quality verdict."""
    status:        ReviewStatus
    score:         float
    summary:       str
    issues:        list[ReviewIssue] = field(default_factory=list)
    suggested_fix: str = ""


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------

@dataclass
class Envelope:
    """Universal message wrapper for all SYLPH communication."""
    task_id:     str
    phase:       Phase
    payload:     Any
    model_name:  str  = "mock"
    retry_count: int  = 0
    ark_version: str  = ARK_VERSION
    timestamp:   str  = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @staticmethod
    def new(phase: Phase, payload: Any, **kwargs: Any) -> "Envelope":
        return Envelope(
            task_id=str(uuid.uuid4()),
            phase=phase,
            payload=payload,
            **kwargs,
        )
