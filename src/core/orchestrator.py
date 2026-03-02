"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator
======================================================
Implements the autonomous PLAN → CODE → REVIEW → COMMIT loop.

Conforms to: specs/core_logic.md
State is persisted to workspace/.ark_state.json for crash resilience.

Usage
-----
::

    python -m src.core.orchestrator "Create a hello-world Flask app"

    # or from Python
    from src.core.orchestrator import Orchestrator
    orc = Orchestrator()
    orc.run("Create a hello-world Flask app")
"""

from __future__ import annotations

import json
import logging
import sys
import textwrap
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from src.core.config import ConfigLoader
from src.core.models import (
    CodePayload,
    Envelope,
    FileAction,
    FileChange,
    Phase,
    PlanPayload,
    ReviewIssue,
    ReviewPayload,
    ReviewStatus,
    IssueSeverity,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ARK.Orchestrator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES: Final[int] = 3
STATE_FILENAME: Final[str] = ".ark_state.json"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class CircuitBreakerTripped(RuntimeError):
    """Raised when MAX_RETRIES consecutive failures occur."""


class OrchestratorBlocked(RuntimeError):
    """Raised when the orchestrator enters BLOCKED state."""


# ---------------------------------------------------------------------------
# Persistent State
# ---------------------------------------------------------------------------

class ARKState:
    """Serialisable orchestrator state backed by workspace/.ark_state.json."""

    def __init__(self, workspace: Path) -> None:
        self._path: Path = workspace / STATE_FILENAME
        self.task_id:    str   = str(uuid.uuid4())
        self.phase:      Phase = Phase.IDLE
        self.goal:       str   = ""
        self.retry_count: int  = 0
        self.history:    list[dict] = []

    # ---- persistence -------------------------------------------------------

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
        if not self._path.exists():
            return
        data: dict = json.loads(self._path.read_text(encoding="utf-8"))
        self.task_id     = data.get("task_id", self.task_id)
        self.phase       = Phase(data.get("phase", Phase.IDLE.value))
        self.goal        = data.get("goal", "")
        self.retry_count = data.get("retry_count", 0)
        self.history     = data.get("history", [])

    # ---- helpers ------------------------------------------------------------

    def push_event(self, phase: Phase, status: str, detail: str = "") -> None:
        self.history.append({
            "phase":     phase.value,
            "status":    status,
            "detail":    detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def transition(self, phase: Phase) -> None:
        log.info("State transition: %s → %s", self.phase.value, phase.value)
        self.phase = phase
        self.save()


# ---------------------------------------------------------------------------
# Mock SYLPH Agents
# ---------------------------------------------------------------------------

class MockArchitect:
    """Simulates the Architect SYLPH (LLM call replaced by mock)."""

    def plan(self, goal: str, state: ARKState) -> PlanPayload:
        log.info("[Architect] Analysing goal: %r", goal[:60])
        # In production → call Ollama with architect prompt
        time.sleep(0.1)  # simulate LLM latency
        target = f"workspace/output_{state.task_id[:8]}.py"
        return PlanPayload(
            goal=goal,
            spec_path="specs/core_logic.md",
            target_files=[target],
            constraints=["Python 3.11+", "型ヒント必須"],
            acceptance_criteria=["no syntax errors", "file exists"],
        )


class MockCoder:
    """Simulates the Coder SYLPH (LLM call replaced by mock)."""

    def code(self, plan: PlanPayload, retry: int) -> CodePayload:
        log.info("[Coder] Generating code (attempt %d) for: %s", retry + 1, plan.target_files)
        time.sleep(0.1)
        path = plan.target_files[0]
        content = textwrap.dedent(f"""\
            # ARK — Auto-generated by Coder SYLPH
            # Goal: {plan.goal}
            # Attempt: {retry + 1}

            def main() -> None:
                print("Hello from ARK workspace!")

            if __name__ == "__main__":
                main()
        """)
        return CodePayload(
            plan_ref=plan.goal[:40],
            files=[FileChange(path=path, action=FileAction.CREATE, content=content)],
            test_command="python " + path,
            notes=f"Mock generation, attempt {retry + 1}",
        )


class MockReviewer:
    """Simulates the Reviewer SYLPH — always PASSes on attempt ≥ 2."""

    def review(self, code: CodePayload, retry: int) -> ReviewPayload:
        log.info("[Reviewer] Auditing %d file(s) (attempt %d) …", len(code.files), retry + 1)
        time.sleep(0.1)

        # First attempt always fails so we can demonstrate the retry loop
        if retry == 0:
            return ReviewPayload(
                status=ReviewStatus.FAIL,
                score=0.45,
                summary="型ヒントが不足しています。修正してください。",
                issues=[
                    ReviewIssue(
                        severity=IssueSeverity.WARNING,
                        file=code.files[0].path,
                        line=5,
                        message="Return type annotation missing on `main`",
                    )
                ],
                suggested_fix="def main() -> None:",
            )

        return ReviewPayload(
            status=ReviewStatus.PASS,
            score=0.97,
            summary="All acceptance criteria satisfied. ✅",
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Main autonomous loop controller.

    Phases
    ------
    IDLE → PLANNING → CODING → REVIEWING → COMMITTING → DONE
                        ↑______________|
                        (FAIL: retry, max=3)
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._cfg        = ConfigLoader.load(config_path)
        self._workspace  = Path(self._cfg.workspace_path)
        self._state      = ARKState(self._workspace)
        self._architect  = MockArchitect()
        self._coder      = MockCoder()
        self._reviewer   = MockReviewer()

    # ------------------------------------------------------------------ run

    def run(self, goal: str, *, resume: bool = False) -> Path:
        """
        Execute one full autonomous loop for *goal*.

        Parameters
        ----------
        goal:
            Natural-language description of what to build.
        resume:
            If True, attempt to resume from persisted state.

        Returns
        -------
        Path
            Workspace directory containing committed artefacts.

        Raises
        ------
        CircuitBreakerTripped
            When MAX_RETRIES consecutive failures occur.
        """
        self._workspace.mkdir(parents=True, exist_ok=True)

        if resume:
            self._state.load()
            log.info("Resuming from phase: %s (retry=%d)",
                     self._state.phase.value, self._state.retry_count)
        else:
            self._state = ARKState(self._workspace)
            self._state.goal = goal

        log.info("=" * 60)
        log.info("🚀  ARK Autonomous Loop — task %s", self._state.task_id)
        log.info("    GOAL: %s", goal)
        log.info("=" * 60)

        # ── PHASE 1: PLANNING ─────────────────────────────────────────────
        self._state.transition(Phase.PLANNING)
        plan = self._phase_plan(goal)

        # ── PHASE 2+3: CODE / REVIEW loop ─────────────────────────────────
        code_result: CodePayload | None = None

        while self._state.retry_count < MAX_RETRIES:
            retry = self._state.retry_count

            # CODING
            self._state.transition(Phase.CODING)
            code_result = self._phase_code(plan, retry)

            # REVIEWING
            self._state.transition(Phase.REVIEWING)
            review = self._phase_review(code_result, retry)

            if review.status == ReviewStatus.PASS:
                log.info("✅  Review PASSED  (score=%.2f)", review.score)
                self._state.push_event(Phase.REVIEWING, "PASS", review.summary)
                self._state.save()
                break

            # FAIL path
            self._state.retry_count += 1
            self._state.push_event(
                Phase.REVIEWING, "FAIL",
                f"retry={self._state.retry_count} — {review.summary}",
            )
            self._state.save()

            if self._state.retry_count >= MAX_RETRIES:
                self._state.transition(Phase.BLOCKED)
                msg = (
                    f"Circuit Breaker tripped after {MAX_RETRIES} consecutive failures.\n"
                    f"Last review summary: {review.summary}\n"
                    "Human intervention required."
                )
                log.error("🛑  %s", msg)
                raise CircuitBreakerTripped(msg)

            log.warning(
                "⚠️   Review FAILED (score=%.2f) — retrying (%d/%d) …",
                review.score, self._state.retry_count, MAX_RETRIES,
            )

        # ── PHASE 4: COMMIT ────────────────────────────────────────────────
        self._state.transition(Phase.COMMITTING)
        assert code_result is not None
        committed = self._phase_commit(code_result)

        self._state.transition(Phase.DONE)
        log.info("🏛️  ARK loop complete — artefacts committed to: %s", self._workspace)
        return self._workspace

    # --------------------------------------------------------- phase methods

    def _phase_plan(self, goal: str) -> PlanPayload:
        env = Envelope.new(Phase.PLANNING, goal, model_name=self._cfg.model_name)
        log.info("[PLAN]  Architect generating PlanPayload …")
        plan = self._architect.plan(goal, self._state)
        self._state.push_event(Phase.PLANNING, "OK",
                               f"target_files={plan.target_files}")
        self._state.save()
        return plan

    def _phase_code(self, plan: PlanPayload, retry: int) -> CodePayload:
        log.info("[CODE]  Coder synthesising code (retry=%d) …", retry)
        code = self._coder.code(plan, retry)
        self._state.push_event(Phase.CODING, "OK",
                               f"files={[f.path for f in code.files]}")
        self._state.save()
        return code

    def _phase_review(self, code: CodePayload, retry: int) -> ReviewPayload:
        log.info("[REVIEW] Reviewer auditing output …")
        review = self._reviewer.review(code, retry)
        return review

    def _phase_commit(self, code: CodePayload) -> list[Path]:
        """Write all generated files into workspace/."""
        committed: list[Path] = []
        for fc in code.files:
            # 💡 修正ポイント：
            # エージェントが返すパスが相対（output.py）でも
            # 確実にワークスペース内に収めるように結合する
            file_path = Path(fc.path)
            
            # もしエージェントが 'workspace/file.py' と返してきても、
            # ファイル名だけを取り出すか、安全に結合する
            if file_path.parts[0] == self._workspace.name:
                # 最初の階層が 'workspace' なら、それ以降を使う
                safe_path = self._workspace.joinpath(*file_path.parts[1:])
            else:
                safe_path = self._workspace / file_path

            # サンドボックス・チェック（絶対パスで厳密に）
            try:
                safe_path.resolve().relative_to(self._workspace.resolve())
            except ValueError:
                log.error("🚫  Sandbox violation blocked: %s", fc.path)
                continue

            if fc.action == FileAction.DELETE:
                if safe_path.exists():
                    safe_path.unlink()
                    log.info("[COMMIT] Deleted %s", safe_path)
            else:
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                safe_path.write_text(fc.content, encoding="utf-8")
                committed.append(safe_path)
                log.info("[COMMIT] Written %s (%d bytes)", safe_path, len(fc.content))

        self._state.push_event(
            Phase.COMMITTING, "OK",
            f"committed={[str(p) for p in committed]}",
        )
        self._state.save()
        return committed


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    goal = " ".join(argv) if argv else "Hello World Pythonスクリプトを生成せよ"

    orc = Orchestrator()
    try:
        orc.run(goal)
    except CircuitBreakerTripped as exc:
        log.critical("Loop halted: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
