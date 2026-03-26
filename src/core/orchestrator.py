"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator
=======================================================================
Phase 11.1: Refactoring & The Treasury Delegation Update
予算管理機構を `src.core.treasury` に委譲し、指揮系統をスリム化。
UI連携のためのリアルタイムコストブロードキャスト機能を追加。
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
import re
import shlex
from pathlib import Path
from typing import Final, Callable, Protocol, Any
from dotenv import load_dotenv

# 記憶システムとツールのインポート
from src.memory import MemoryManager
from src.tools import memory_tools
from src.core.dock import Dock
from src.core.state import ARKState
from src.core.models import (
    Phase, PlanPayload, CodePayload, ReviewPayload, 
    ReviewStatus, RunResult, ExecutionAttempt
)
from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.agents.reflector import ReflectorAgent
from src.core.config import ConfigLoader
from src.core.factory import get_provider
from src.core.agents import build_commit_msg_prompt

# 外部委譲されたマネージャー群
from src.core.dock_manager import setup_dock
from src.core.github_publisher import publish_to_github
from src.core.command_interceptor import handle_special_commands
from src.core.treasury import Treasury  # 会計モジュール

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ARK.Orchestrator")

MAX_RETRIES: Final[int] = 3

class CircuitBreakerTripped(RuntimeError): pass

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

class Orchestrator:
    """方舟の全行程を統制する、絶対的な指揮官。"""

    def __init__(
        self,
        config_path: Path | None = None,
        workspace_path: str | Path | None = None,
        on_status_change: StatusCallback | None = None,
        on_token_usage: Callable[[int], None] | None = None,
        on_cost_update: Callable[[dict], None] | None = None,  # 🌟 NEW: UI同期用コールバック
        auto_approve_search: bool = False,
        config_overrides: dict[str, str] | None = None
    ) -> None:
        self._cfg = ConfigLoader.load(config_path)
        
        if config_overrides:
            for key, val in config_overrides.items():
                setattr(self._cfg, key, val)

        self.target_input = str(workspace_path) if workspace_path else ""
        self.is_url = self.target_input.startswith(("http://", "https://", "git@"))

        target_path = Path(workspace_path).resolve() if workspace_path else None
        self._base_workspace = Path(self._cfg.workspace_path).resolve() if self.is_url else (target_path or Path(self._cfg.workspace_path).resolve())

        self._memory_dir = self._base_workspace / ".ark_memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory = MemoryManager(base_dir=self._memory_dir)
        memory_tools.inject_memory_manager(self._memory)

        # 会計システム（Treasury）の初期化
        self._treasury = Treasury(memory_dir=self._memory_dir, config=self._cfg)

        self.on_status_change = on_status_change
        self.on_token_usage = on_token_usage
        self.on_cost_update = on_cost_update  # 🌟 NEW: コールバックを保持
        
        self._state = ARKState(self._base_workspace)
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)

        os.environ["ARK_MOCK_MODE"] = "0"
        self.auto_approve_search = auto_approve_search
        log.info(f"⚙️ System Initialized / Auto Approve Search: {'ON' if self.auto_approve_search else 'OFF'}")

        # 各エージェントの初期化
        self._architect = ArchitectAgent(get_provider("architect", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._coder = CoderAgent(get_provider("coder", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reviewer = ReviewerAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reflector = ReflectorAgent(get_provider("reflector", self._cfg), workspace_path=self._base_workspace, tools=[memory_tools.save_core_rule, memory_tools.archive_experience], on_token_usage=self.on_token_usage)
        
        self._agents = [self._architect, self._coder, self._reviewer, self._reflector]
        self._agent_names = ["Architect", "Coder", "Reviewer", "Reflector"]
        self.dock: Dock | None = None 

    def _broadcast_cost(self) -> None:
        """🌟 NEW: 現在の累積コストを上位レイヤー（UI）へ送信する"""
        if self.on_cost_update:
            # 💡 修正箇所: agent_names を追加してリッチなペイロードを要求する
            payload = self._treasury.get_realtime_usage_payload(self._agents, self._agent_names)
            self.on_cost_update(payload)

    def run(self, goal: str, *, resume: bool = False) -> Path:
        self._base_workspace.mkdir(parents=True, exist_ok=True)
        
        if resume:
            self._state.load()
        else:
            self._state = ARKState(self._base_workspace)
            self._state.goal = goal
            
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)
            
        if handle_special_commands(goal, self._memory, self._update_phase, reflector=self._reflector):
            return self._base_workspace
        
        # RAGコンテキスト注入
        self._update_phase(Phase.PLANNING, "RAG", "大図書館から過去の航海記録を検索中...")
        core_rules = self._memory.load_core_rules_prompt()
        past_memories = self._memory.recall_memory(goal, n_results=3)
        context_injection = ""
        if core_rules and "現在、特定のプロジェクト・コアルールは" not in core_rules: 
            context_injection += f"{core_rules}\n"
        if past_memories and "見つかりませんでした" not in past_memories: 
            context_injection += f"{past_memories}\n"
        if context_injection:
            goal = f"{goal}\n\n{context_injection}"
            log.info("📚 [RAG] 過去の掟と知見をミッションプランに注入しました！")

        # 実行前のSoft Cap（予算警告）チェック
        self._treasury.check_soft_cap(self._agents, Phase.PLANNING, self._update_phase)
        self._broadcast_cost()  # 🌟 コスト送信

        log.info("=" * 60)
        log.info("  ARK Autonomous Loop (Grand Finale)")
        log.info(f"    GOAL: {goal}")
        log.info("=" * 60)

        try:
            # 1. Planning Phase
            self._update_phase(Phase.PLANNING, "START", "Drafting mission blueprint...")
            plan = self._phase_plan(goal)
            self._broadcast_cost()  # 🌟 Planning後のコスト送信

            goal_files = re.findall(r'(\w+\.py)', goal)
            if goal_files: 
                plan.target_files = goal_files

            self.dock = setup_dock(self.target_input, self._base_workspace, self._state.task_id, getattr(plan, 'project_name', None))
            if self.dock:
                for agent in self._agents: 
                    agent._workspace_path = self.dock.path

            code_result: CodePayload | None = None
            last_review: ReviewPayload | None = None
            execution_feedback: str = ""
            reviewer_feedback: str = ""
            attempt_history: list[ExecutionAttempt] = []

            # 2. Iterative Coding & Review Phase
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

                # コーディング後の予算チェックとコスト送信
                self._treasury.check_soft_cap(self._agents, Phase.CODING, self._update_phase)
                self._broadcast_cost()  # 🌟 Coding後のコスト送信

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

                self._update_phase(Phase.REVIEWING, "START", "Auditing results...")
                review = self._phase_review(code_result, retry, plan)
                last_review = review
                
                # レビュー後の予算チェックとコスト送信
                self._treasury.check_soft_cap(self._agents, Phase.REVIEWING, self._update_phase)
                self._broadcast_cost()  # 🌟 Review後のコスト送信

                if review.status == ReviewStatus.PASS:
                    self._state.push_event(Phase.REVIEWING, "PASS", "Perfect!")
                    self._state.save()
                    break

                reviewer_feedback = review.summary
                self._state.retry_count += 1
                self._state.save()

            # 3. Circuit Breaker (Failed after MAX_RETRIES)
            if self._state.retry_count >= MAX_RETRIES and (not last_review or last_review.status != ReviewStatus.PASS):
                self._state.transition(Phase.BLOCKED)
                self._state.save()
                log.warning("⚠️ [Orchestrator] 致命的な敗北を確認。原因分析を司書に委譲します...")
                self._state.push_event(Phase.BLOCKED, "REFLECT", "Archiving fatal failure...")
                self._state.save()
                
                failed_code = code_result if code_result else CodePayload(files=[])
                self._reflector.reflect(plan, failed_code, attempt_history=attempt_history, is_failure=True)
                
                # 失敗時も会計報告とコスト送信を実施
                self._treasury.report_and_enforce_hard_cap(self._agents, self._agent_names)
                self._broadcast_cost()  # 🌟 エラー終了時のコスト送信
                raise CircuitBreakerTripped("Surgery could not be stabilized. Circuit breaker tripped.")

            # 4. Committing Phase
            self._update_phase(Phase.COMMITTING, "START", "Finalizing sync...")
            assert code_result is not None
            self._phase_commit(code_result, plan.goal)

            is_new_project = not self.is_url and not (self.dock.path.exists() and (self.dock.path / ".git").exists())
            pr_url = publish_to_github(self.dock, self._state.task_id, plan.goal, is_new_project, self.is_url)
            if pr_url:
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", f"Create PR 👉 {pr_url}")
                self._state.save()

            self._state.push_event(Phase.COMMITTING, "REFLECT", "Knowledge archiving...")
            self._state.save()
            self._reflector.reflect(plan, code_result, attempt_history=attempt_history, is_failure=False)

            # ミッション完了時の最終会計報告とコスト送信
            self._treasury.report_and_enforce_hard_cap(self._agents, self._agent_names)
            self._broadcast_cost()  # 🌟 ミッション完了時のコスト送信

            self._update_phase(Phase.DONE, "FINISH", "Mission successful. Probe ship docked. ⚓️")
            return self.dock.path if self.dock else Path(".")

        except Exception as e:
            log.error(traceback.format_exc())
            self._state.transition(Phase.DONE)
            self._state.save()
            self._broadcast_cost()  # 🌟 例外発生時も念のためコストを送信
            raise e

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

        req_file = next((f for f in code.files if f.path == "requirements.txt"), None)
        python_cmd = ".venv/bin/python" if os.name != "nt" else ".venv\\Scripts\\python.exe"
        pip_cmd = ".venv/bin/pip" if os.name != "nt" else ".venv\\Scripts\\pip.exe"

        if req_file or (self.dock.path / "requirements.txt").exists():
            self.dock.terminal.execute_command(f"{pip_cmd} install -r requirements.txt")

        main_file = next((f.path for f in code.files if f.path.endswith(".py") and not f.path.startswith("test_")), None)
        if not main_file: return RunResult(exit_code=0, stdout="Validated", stderr="", duration=0)
        
        result = self.dock.terminal.execute_command(f"{python_cmd} {main_file}")
        return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)
    
    def _phase_review(self, code: CodePayload, retry: int, plan: PlanPayload) -> ReviewPayload:
        return self._reviewer.review(code, retry, plan=plan)

    def _phase_commit(self, code: CodePayload, goal: str) -> list[Path]:
        if not self.dock: return []
        try:
            prompt = build_commit_msg_prompt(goal, [f.path for f in code.files])
            raw_msg = self._coder._call_llm(prompt).strip()
            msg = raw_msg.replace("```plaintext", "").replace("```", "").strip().split("\n")[0]
            self.dock.terminal.execute_command("git add .")
            self.dock.terminal.execute_command(f"git commit -m {shlex.quote(msg)}")
            return [self.dock.path / Path(f.path).name for f in code.files]
        except Exception as e:
            log.warning("Commit failed: %s", e)
            return []