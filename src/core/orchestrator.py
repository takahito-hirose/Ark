"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator
=======================================================================
「すべてを浄化し、完璧に同期する」
グランドフィナーレ・エンジン（Grand Finale Engine）搭載。
GitToolのバグを回避し、GitHubへのPR作成まで完走させるわ！
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
import re
import shutil
import shlex
from pathlib import Path
from typing import Final, Callable, Protocol, Optional
from dotenv import load_dotenv

# 記憶システムとツールのインポート
from src.memory import MemoryManager
from src.tools import memory_tools
from src.core.dock import Dock
from src.core.state import ARKState
from src.core.models import Phase, PlanPayload, CodePayload, ReviewPayload, ReviewStatus, RunResult, ExecutionAttempt
from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.agents.reflector import ReflectorAgent
from src.core.config import ConfigLoader
from src.core.factory import get_provider
from src.core.agents import build_commit_msg_prompt

# 分割したモジュールをインポート
from src.core.dock_manager import setup_dock
from src.core.github_publisher import publish_to_github

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
# Constants & Protocols
# ---------------------------------------------------------------------------

MAX_RETRIES: Final[int] = 3

class CircuitBreakerTripped(RuntimeError): pass
class OrchestratorBlocked(RuntimeError): pass

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

# ---------------------------------------------------------------------------
# Orchestrator (Grand Finale Engine)
# ---------------------------------------------------------------------------

class Orchestrator:
    def __init__(
        self,
        config_path: Path | None = None,
        workspace_path: str | Path | None = None,
        on_status_change: StatusCallback | None = None,
        on_token_usage: Callable[[int], None] | None = None,
        mode: str = "ECO"
    ) -> None:
        self._cfg = ConfigLoader.load(config_path)
        self.mode = mode.upper()
        self.target_input = str(workspace_path) if workspace_path else ""
        self.is_url = self.target_input.startswith(("http://", "https://", "git@"))

        if self.is_url:
            self._base_workspace = Path(self._cfg.workspace_path).resolve()
        else:
            target_path = Path(workspace_path).resolve() if workspace_path else None
            self._base_workspace = target_path or Path(self._cfg.workspace_path).resolve()
        
        self.on_status_change = on_status_change
        self.on_token_usage = on_token_usage
        self._state = ARKState(self._base_workspace)
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)

        self._memory = MemoryManager(base_dir=self._base_workspace / ".ark_memory")
        memory_tools.inject_memory_manager(self._memory)

        self._architect = ArchitectAgent(get_provider("architect", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._coder = CoderAgent(get_provider("coder", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reviewer = ReviewerAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reflector = ReflectorAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, tools=[], on_token_usage=self.on_token_usage)
        
        self.dock: Dock | None = None 

    def run(self, goal: str, *, resume: bool = False) -> Path:
        self._base_workspace.mkdir(parents=True, exist_ok=True)
        if resume:
            self._state.load()
        else:
            self._state = ARKState(self._base_workspace)
            self._state.goal = goal
            
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)
        
        core_rules = self._memory.load_core_rules_prompt()
        if core_rules and "現在、特定のプロジェクト・コアルールは" not in core_rules:
            goal = f"{goal}\n\n{core_rules}"

        log.info("=" * 60)
        log.info("🚀  ARK Autonomous Loop (Grand Finale)")
        log.info(f"    GOAL: {goal}")
        log.info("=" * 60)

        try:
            # ── PHASE 1: PLANNING ─────────────────────────────────────────────
            self._update_phase(Phase.PLANNING, "START", "Drafting mission blueprint...")
            plan = self._phase_plan(goal)

            # ターゲット固定（迷路混入対策）
            goal_files = re.findall(r'(\w+\.py)', goal)
            if goal_files:
                plan.target_files = goal_files

            # [Hard Reset] ドックのクリーンアップ
            dock_id = self._state.task_id[:8]
            target_dock_path = self._base_workspace / "docks" / f"cloned-{dock_id}"
            if target_dock_path.exists():
                log.info("🧹 [Cleansing] Resetting dock path: %s", target_dock_path)
                shutil.rmtree(target_dock_path)

            self.dock = setup_dock(
                target_input=self.target_input,
                base_workspace=self._base_workspace,
                task_id=self._state.task_id,
                plan_project_name=getattr(plan, 'project_name', None)
            )

            # ── PHASE 2+3: CODE / REVIEW loop ─────────────────────────────────
            code_result: CodePayload | None = None
            last_review: ReviewPayload | None = None
            execution_feedback: str = ""
            reviewer_feedback: str = ""
            attempt_history: list[ExecutionAttempt] = []

            while self._state.retry_count < MAX_RETRIES:
                retry = self._state.retry_count
                self._update_phase(Phase.CODING, "START", f"Surgical Implementation (Attempt {retry+1})")
                
                current_source = ""
                if plan.target_files and self.dock:
                    target_file = self.dock.path / plan.target_files[0]
                    if target_file.exists():
                        current_source = target_file.read_text(encoding="utf-8")

                prompt_aug = f"\n\n### Current SOURCE of {plan.target_files[0]}:\n```python\n{current_source}\n```" if current_source else ""
                
                if execution_feedback:
                    code_result = self._coder.remediate(plan, retry, failure_reason="Execution Error", stacktrace=execution_feedback, current_source=current_source, attempt_history=attempt_history)
                else:
                    code_result = self._coder.code(plan, retry, reviewer_feedback=reviewer_feedback + prompt_aug)

                # 🚀 RUNNING
                self._state.push_event(Phase.CODING, "RUNNING", "Validating artifacts...")
                self._state.save()
                
                run_result = self._phase_run(code_result)
                if not run_result.success:
                    self._state.retry_count += 1
                    err_msg = run_result.stderr if run_result.stderr else run_result.stdout
                    self._state.push_event(Phase.CODING, "FAIL", f"Fail: {err_msg[:80]}...")
                    self._state.save()
                    
                    if code_result and code_result.files:
                        attempt_history.append(ExecutionAttempt(code=code_result.files[0].content, error=err_msg, attempt_number=self._state.retry_count))
                    execution_feedback = err_msg
                    continue
                
                execution_feedback = ""

                # 🔍 REVIEWING
                self._update_phase(Phase.REVIEWING, "START", "Auditing results...")
                review = self._phase_review(code_result, retry, plan)
                last_review = review

                if review.status == ReviewStatus.PASS:
                    self._state.push_event(Phase.REVIEWING, "PASS", "Perfect!")
                    self._state.save()
                    break

                reviewer_feedback = review.summary
                self._state.retry_count += 1
                self._state.save()

            if self._state.retry_count >= MAX_RETRIES and (not last_review or last_review.status != ReviewStatus.PASS):
                self._state.transition(Phase.BLOCKED)
                self._state.save()
                raise CircuitBreakerTripped(f"Surgery could not be stabilized. ")

            # ── PHASE 4: COMMITTING ───────────────────────────────────────────
            self._update_phase(Phase.COMMITTING, "START", "Finalizing sync...")
            assert code_result is not None
            self._phase_commit(code_result, plan.goal)

            is_new_project = not self.is_url and not (self.dock.path.exists() and (self.dock.path / ".git").exists())
            pr_url = publish_to_github(self.dock, self._state.task_id, plan.goal, is_new_project, self.is_url)
            
            if pr_url:
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", f"Create PR 👉 {pr_url}")
                self._state.save()

            # ── PHASE 5: REFLECT ──────────────────────────────────────────────
            self._state.push_event(Phase.COMMITTING, "REFLECT", "Knowledge archiving...")
            self._state.save()
            self._reflector.reflect(plan, code_result)

            self._update_phase(Phase.DONE, "FINISH", "Mission successful. Probe ship docked. ⚓️💋")
            return self.dock.path if self.dock else Path(".")

        except Exception as e:
            log.error(traceback.format_exc())
            self._state.transition(Phase.DONE)
            self._state.save()
            raise e

    # --------------------------------------------------------- Helpers

    def _update_phase(self, phase: Phase, status: str, detail: str):
        self._state.transition(phase)
        self._state.push_event(phase, status, detail)
        self._state.save()

    def _phase_plan(self, goal: str) -> PlanPayload:
        plan = self._architect.plan(goal, task_id=self._state.task_id)
        self._state.push_event(Phase.PLANNING, "OK", f"Target: {plan.target_files}")
        return plan

    def _phase_run(self, code: CodePayload) -> RunResult:
        if not self.dock: return RunResult(exit_code=-1, stdout="", stderr="No Dock", duration=0)
        try:
            self.dock.write_artifacts(code.files)
        except Exception as e:
            return RunResult(exit_code=1, stdout="", stderr=f"Dock write error: {e}", duration=0)

        main_file = next((f.path for f in code.files if f.path.endswith(".py") and not f.path.startswith("test_")), None)
        if not main_file: return RunResult(exit_code=0, stdout="Validated", stderr="", duration=0)
        
        file_name = Path(main_file).name
        
        python_cmd = ".venv/bin/python" if os.name != "nt" else ".venv\\Scripts\\python.exe"
        log.info(f"🧪 [Run] Executing via venv: {python_cmd} {file_name}")
        result = self.dock.terminal.execute_command(f"{python_cmd} {file_name}")
        
        return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)
    
    def _phase_review(self, code: CodePayload, retry: int, plan: PlanPayload) -> ReviewPayload:
        return self._reviewer.review(code, retry, plan=plan)

    def _phase_commit(self, code: CodePayload, goal: str) -> list[Path]:
        if not self.dock: return []
        try:
            prompt = build_commit_msg_prompt(goal, [f.path for f in code.files])
            raw_msg = self._coder._call_llm(prompt).strip()
            # 💋 [Fix] マークダウンのバッククォートを徹底的に掃除
            msg = raw_msg.replace("```plaintext", "").replace("```", "").strip().split("\n")[0]
            log.info("📝 [Commit] Recording surgery results: %s", msg)
            
            self.dock.terminal.execute_command("git add .")
            self.dock.terminal.execute_command(f"git commit -m {shlex.quote(msg)}")
            return [self.dock.path / Path(f.path).name for f in code.files]
        except Exception as e:
            log.warning("Commit failed: %s", e)
            return []

if __name__ == "__main__":
    load_dotenv()
    Orchestrator().run(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello World")