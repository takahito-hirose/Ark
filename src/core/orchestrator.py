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
from typing import Final, Callable, Protocol
from src.tools.terminal import TerminalOracle

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.core.config import ConfigLoader
from src.core.factory import get_provider
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
    RunResult,
    ExecutionAttempt,
)
from src.core.runner import PythonRunner
from src.core.git_tools import GitTool
from src.core.agents import build_remediation_prompt, build_commit_msg_prompt

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
        self._on_status_change: StatusCallback | None = None

    def set_callback(self, callback: StatusCallback | None) -> None:
        self._on_status_change = callback

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
        if self._on_status_change:
            self._on_status_change(phase, status, self.retry_count, detail)

    def transition(self, phase: Phase) -> None:
        log.info("State transition: %s → %s", self.phase.value, phase.value)
        self.phase = phase
        self.save()
        if self._on_status_change:
            self._on_status_change(phase, "TRANSITION", self.retry_count, f"Moving to {phase.value}")


# ---------------------------------------------------------------------------
# (Mock SYLPH classes removed — replaced by src.agents layer)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Main autonomous loop controller.
    """

    def __init__(
        self, 
        config_path: Path | None = None, 
        workspace_path: str | Path | None = None, # 👈 引数を追加！
        on_status_change: StatusCallback | None = None
    ) -> None:
        # 1. コンフィグのロード
        self._cfg = ConfigLoader.load(config_path)
        
        # 2. ワークスペースの決定（引数優先 > 設定ファイル > カレントディレクトリ）
        ws_input = workspace_path or self._cfg.workspace_path or "."
        self._workspace = Path(ws_input).resolve()
        
        # 3. 状態管理の初期化（決定したワークスペースを使用）
        self._state = ARKState(self._workspace)
        if on_status_change:
            self._state.set_callback(on_status_change)

        # 4. 各エージェントの初期化（新しいワークスペースを共有！）
        self._architect = ArchitectAgent(
            get_provider("architect", self._cfg), 
            workspace_path=self._workspace
        )
        self._coder = CoderAgent(
            get_provider("coder", self._cfg), 
            workspace_path=self._workspace
        )
        self._reviewer = ReviewerAgent(
            get_provider("reviewer", self._cfg), 
            workspace_path=self._workspace
        )
        
        # 5. ツールの初期化
        self._runner = PythonRunner(timeout=30)
        self._terminal = TerminalOracle(workspace_path=self._workspace)
        self._git = GitTool(self._workspace)

        log.info(
            "Orchestrator initialized — workspace: %s, providers: architect=%r coder=%r reviewer=%r",
            self._workspace,
            self._cfg.architect_provider,
            self._cfg.coder_provider,
            self._cfg.reviewer_provider,
        )

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

        last_review: ReviewPayload | None = None
        execution_feedback: str = ""
        attempt_history: list[ExecutionAttempt] = []

        while self._state.retry_count < MAX_RETRIES:
            retry = self._state.retry_count

            # CODING（前回のレビューフィードバック または 実行エラーを Coder に渡す）
            self._state.transition(Phase.CODING)
            
            if execution_feedback:
                # 実行エラーに基づく修正依頼
                code_result = self._coder.remediate(
                    plan, 
                    retry,
                    failure_reason="Runtime Error",
                    stacktrace=execution_feedback,
                    current_source=code_result.files[0].content if code_result and code_result.files else "",
                    attempt_history=attempt_history
                )
            elif last_review:
                # レビューフィードバックに基づく修正依頼
                code_result = self._phase_code(plan, retry, reviewer_feedback=last_review.summary)
            else:
                # 初回または通常の継続
                code_result = self._phase_code(plan, retry)

            # -----------------------------------------------------------------
            # RUNNING (Self-Healing / Dynamic Verification)
            # -----------------------------------------------------------------
            run_result = self._phase_run(code_result)
            if not run_result.success:
                self._state.retry_count += 1
                
                # --- ここよ！このログが ARK の「根性」を可視化するわ！🚀✨ ---
                retry_msg = f"[🔄 SELF-HEALING] Attempt {self._state.retry_count}/{MAX_RETRIES}"
                print(f"\n{retry_msg}: Detecting issues and preparing fix...")
                
                self._state.push_event(
                    Phase.CODING, "FAIL",
                    f"{retry_msg} — Error: {run_result.stderr[:100]}"
                )
                self._state.save()
                
                # エラー内容を保存して次のループで修正させる
                if code_result and code_result.files:
                    attempt_history.append(ExecutionAttempt(
                        code=code_result.files[0].content,
                        error=run_result.stderr,
                        attempt_number=self._state.retry_count
                    ))
                
                execution_feedback = run_result.stderr
                log.warning(f"⚠️  {retry_msg}: Execution failed. Feeding back to Coder...")
                
                if self._state.retry_count >= MAX_RETRIES:
                    log.error(f"🚨 Max retries reached ({MAX_RETRIES}). ARK couldn't fix it this time...💔")
                    break
                continue
            
            # 成功した場合はフィードバックをクリア
            execution_feedback = ""

            # -----------------------------------------------------------------
            # REVIEWING
            # -----------------------------------------------------------------
            self._state.transition(Phase.REVIEWING)
            review = self._phase_review(code_result, retry)
            last_review = review

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
        committed = self._phase_commit(code_result, plan.goal)

        self._state.transition(Phase.DONE)
        log.info("🏛️  ARK loop complete — artefacts committed to: %s", self._workspace)
        return self._workspace

    # --------------------------------------------------------- phase methods

    def _phase_plan(self, goal: str) -> PlanPayload:
        Envelope.new(Phase.PLANNING, goal, model_name=self._cfg.model_name)
        log.info("[PLAN]  Architect generating PlanPayload …")
        plan = self._architect.plan(goal, task_id=self._state.task_id)
        self._state.push_event(Phase.PLANNING, "OK",
                               f"target_files={plan.target_files}")
        self._state.save()
        return plan

    def _phase_code(
        self,
        plan: PlanPayload,
        retry: int,
        reviewer_feedback: str = "",
    ) -> CodePayload:
        log.info("[CODE]  Coder synthesising code (retry=%d) …", retry)
        code = self._coder.code(plan, retry, reviewer_feedback=reviewer_feedback)
        self._state.push_event(Phase.CODING, "OK",
                               f"files={[f.path for f in code.files]}")
        self._state.save()
        return code

    def _phase_review(self, code: CodePayload, retry: int) -> ReviewPayload:
        log.info("[REVIEW] Reviewer auditing output …")
        review = self._reviewer.review(code, retry)
        return review

    def _phase_run(self, code: CodePayload) -> RunResult:
        log.info("[RUN]  Terminal Oracle executing code for verification …")
        
        # 👈 ステップ0: 実行前に「今生成されたばかりのコード」を一時的に保存するわよ！
        # これをやらないと、さっきみたいに「過去の亡霊」が動いちゃうの💋
        for fc in code.files:
            safe_path = self._workspace / Path(fc.path).name
            safe_path.write_text(fc.content, encoding="utf-8")
        
        # 👈 ステップ1: もし新しい requirements.txt があれば、実行前にインストール！
        # これで検証段階でも ModuleNotFoundError が出なくなるわ✨
        if any(f.path.endswith("requirements.txt") for f in code.files):
            log.info("[RUN] 新しい依存関係を検知！検証前にインストールしちゃうわよ💋")
            self._terminal.execute_command("pip install -r requirements.txt")

        # ステップ2: Pythonファイルを探して実行
        main_file = next((f.path for f in code.files if f.path.endswith(".py")), None)
        if not main_file:
            return RunResult(exit_code=-1, stdout="", stderr="No python file found", duration=0)
        
        script_name = Path(main_file).name
        result = self._terminal.execute_command(f"python {script_name}")
        
        if result.success:
            log.info("✅  Execution SUCCESS")
            print(f"\n--- 🚀 ARK EXECUTION OUTPUT ---\n{result.stdout}\n------------------------------\n")
        else:
            log.error("❌  Execution FAILED (exit=%d)", result.exit_code)
            
        return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)
    
    def _phase_commit(self, code: CodePayload, goal: str) -> list[Path]:
        """Write all generated files into workspace/ and perform Git operations."""
        # 1. Cleanup temporary verification files
        log.info("[COMMIT] Cleaning up temporary files...")
        for temp_file in self._workspace.glob("_verify_*.py"):
            try:
                temp_file.unlink()
                log.debug("Deleted temp file: %s", temp_file)
            except Exception as e:
                log.warning("Failed to delete temp file %s: %s", temp_file, e)

        # 2. Write files to workspace
        committed: list[Path] = []
        for fc in code.files:
            file_path = Path(fc.path)
            if file_path.parts[0] == self._workspace.name:
                safe_path = self._workspace.joinpath(*file_path.parts[1:])
            else:
                safe_path = self._workspace / file_path

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
        # ── 2.5 依存関係のセットアップ (New! 🚀) ──────────────────────
        # 書き出されたファイルの中に requirements.txt があるかチェック
        req_path = self._workspace / "requirements.txt"
        if req_path.exists():
            log.info("[SETUP] requirements.txt を発見！依存ライブラリをインストールするわ💋")
            # さっき作った Terminal Oracle に丸投げよ！
            install_res = self._terminal.execute_command("pip install -r requirements.txt")
            
            if install_res.success:
                log.info("✅ 依存ライブラリの準備完了！完璧よジェニー！")
            else:
                log.warning("⚠️ インストールで少し手こずったみたい。エラー：\n%s", install_res.stderr)
        # ────────────────────────────────────────────────────────────

        # 3. Git Operations
        try:
            # Topic Branch
            branch_name = self._git.create_topic_branch(self._state.task_id)
            
            # Generate Commit Message
            log.info("[COMMIT] Generating commit message via LLM...")
            prompt = build_commit_msg_prompt(goal, [f"{f.path}" for f in code.files])
            # Coder エージェント（または直接 Provider）を使ってメッセージ生成
            raw_msg = self._coder._call_llm(prompt)
            commit_message = raw_msg.strip().split("\n")[0] # 最初の1行のみ使用
            
            # Commit
            if self._git.commit(commit_message):
                # Push
                try:
                    self._git.push(branch_name)
                except Exception as e:
                    log.error("❌ Push failed (conflict?): %s", e)
                    log.warning("Skipping push but commit remains in local branch %s", branch_name)
            else:
                log.info("No changes to commit. Skiping Git flow.")

        except Exception as e:
            log.error("❌ Git failed: %s", e)
            log.warning("Proceeding without Git operations.")

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
