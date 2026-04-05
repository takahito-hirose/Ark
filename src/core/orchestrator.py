"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator
=======================================================================
Phase 13: Dynamic Worker Spawning (スリム化版)
Orchestratorは全体の進行管理のみを行い、重い並行処理ロジックは
ParallelTaskExecutor に移譲しています。
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
import re
import shlex
import asyncio
import threading
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
    ReviewStatus, RunResult, ExecutionAttempt,
    SubTask, TaskStatus
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
from src.core.treasury import Treasury

# 🌟 NEW: 外出ししたExecutorをインポート
from src.core.executor import ParallelTaskExecutor, CircuitBreakerTripped

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ARK.Orchestrator")

MAX_RETRIES: Final[int] = 3

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: pass

class Orchestrator:
    """方舟の全行程を統制する、絶対的な指揮官。"""

    def __init__(
        self,
        config_path: Path | None = None,
        workspace_path: str | Path | None = None,
        on_status_change: StatusCallback | None = None,
        on_token_usage: Callable[[int], None] | None = None,
        on_cost_update: Callable[[dict], None] | None = None,
        on_proposal: Callable[[dict], None] | None = None,
        on_plan_ready: Callable[[dict], bool] | None = None,
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

        self._treasury = Treasury(memory_dir=self._memory_dir, config=self._cfg)

        self.on_status_change = on_status_change
        self.on_token_usage = on_token_usage
        self.on_cost_update = on_cost_update
        self.on_proposal = on_proposal
        self.on_plan_ready = on_plan_ready
        
        self._state = ARKState(self._base_workspace)
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)
            
        # 🌟 並行処理時の状態更新保護用ロック
        self._state_lock = threading.Lock()

        os.environ["ARK_MOCK_MODE"] = "0"
        self.auto_approve_search = auto_approve_search
        log.info(f"⚙️ System Initialized / Auto Approve Search: {'ON' if self.auto_approve_search else 'OFF'}")

        self._architect = ArchitectAgent(get_provider("architect", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._coder = CoderAgent(get_provider("coder", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reviewer = ReviewerAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reflector = ReflectorAgent(get_provider("reflector", self._cfg), workspace_path=self._base_workspace, tools=[memory_tools.save_core_rule, memory_tools.archive_experience], on_token_usage=self.on_token_usage)
        
        self._agents = [self._architect, self._coder, self._reviewer, self._reflector]
        self._agent_names = ["Architect", "Coder", "Reviewer", "Reflector"]
        self.dock: Dock | None = None 

    def _broadcast_cost(self) -> None:
        if self.on_cost_update:
            with self._state_lock:
                payload = self._treasury.get_realtime_usage_payload(self._agents, self._agent_names)
            if self.on_cost_update:
                self.on_cost_update(payload)

    def _update_phase(self, phase: Phase, status: str, detail: str):
        with self._state_lock:
            self._state.transition(phase)
            self._state.push_event(phase, status, detail)
            self._state.save()

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
        
        self._update_phase(Phase.PLANNING, "RAG", "大図書館から過去の航海記録を検索中")
        core_rules = self._memory.load_core_rules_prompt()
        past_memories = self._memory.recall_memory(goal, n_results=3)
        context_injection = ""
        if core_rules and "現在、特定のプロジェクト・コアルールは" not in core_rules: 
            context_injection += f"{core_rules}\n"
        if past_memories and "見つかりませんでした" not in past_memories: 
            context_injection += f"{past_memories}\n"
        if context_injection:
            goal = f"{goal}\n\n{context_injection}"
            log.info("📚 [RAG] 過去の掟と知見をミッションプランに注入しました")

        self._treasury.check_soft_cap(self._agents, Phase.PLANNING, self._update_phase)
        self._broadcast_cost()

        log.info("=" * 60)
        log.info("  ARK Autonomous Loop (Grand Finale)")
        log.info(f"    GOAL: {goal}")
        log.info("=" * 60)

        try:
            while True:
                self._update_phase(Phase.PLANNING, "START", "Drafting mission blueprint")
                plan = self._phase_plan(goal)
                self._broadcast_cost()

                goal_files = re.findall(r'(\w+\.py)', goal)
                if goal_files: 
                    plan.target_files = goal_files

                if not getattr(plan, 'tasks', None):
                    fallback_task = SubTask(id="task-0", title="Single Pass Mode", description=plan.goal)
                    plan.tasks = [fallback_task]

                if self.on_plan_ready:
                    self._update_phase(Phase.PLANNING, "WAITING", "提督の設計・テストコード承認を待機中")
                    
                    plan_dict = {
                        "goal": plan.goal,
                        "target_files": plan.target_files,
                        "tasks": [{"id": t.id, "title": t.title, "description": t.description, "dependencies": getattr(t, 'dependencies', [])} for t in plan.tasks],
                        "test_code": getattr(plan, 'test_code', '# Test code not generated.')
                    }

                    is_approved = self.on_plan_ready(plan_dict)

                    if not is_approved:
                        log.warning("🚫 [Orchestrator] 提督によって設計が却下されました。再検討を実施します。")
                        self._update_phase(Phase.PLANNING, "REJECTED", "却下されました。プランを再考中")
                        goal += "\n[System Directive]: 前回の設計図とテストコードは提督によって却下されました。アプローチを見直し、改善したプランを再生成してください。"
                        continue
                    
                    self._update_phase(Phase.PLANNING, "APPROVED", "設計承認！大艦隊、作業開始！")
                
                break

            self.dock = setup_dock(self.target_input, self._base_workspace, self._state.task_id, getattr(plan, 'project_name', None))
            if self.dock:
                for agent in self._agents: 
                    agent._workspace_path = self.dock.path

            all_modified_files = set()
            attempt_history: list[ExecutionAttempt] = []
            task_artifacts: dict[str, list[str]] = {}
            original_goal = plan.goal

            # 🌟 並行実行エンジンの始動 (Executorへ委譲)
            log.info("🚀 [Orchestrator] Dynamic Worker Spawning (大艦隊の並列召喚) を開始します")
            
            executor = ParallelTaskExecutor(
                coder=self._coder,
                reviewer=self._reviewer,
                reflector=self._reflector,
                dock=self.dock,
                state=self._state,
                state_lock=self._state_lock,
                treasury=self._treasury,
                agents=self._agents,
                agent_names=self._agent_names,
                update_phase_cb=self._update_phase,
                broadcast_cost_cb=self._broadcast_cost,
                phase_run_cb=self._phase_run,
                phase_review_cb=self._phase_review
            )

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # イベントループがすでに回っている環境（FastAPI等）への安全策
                exc_info = []
                def run_loop_in_thread():
                    try:
                        asyncio.run(executor.execute_all(plan, task_artifacts, all_modified_files, attempt_history))
                    except Exception as e:
                        exc_info.append(e)

                t = threading.Thread(target=run_loop_in_thread)
                t.start()
                t.join()
                
                if exc_info:
                    raise exc_info[0]
            else:
                asyncio.run(executor.execute_all(plan, task_artifacts, all_modified_files, attempt_history))

            plan.goal = original_goal

            self._update_phase(Phase.COMMITTING, "START", "Finalizing sync for all tasks")
            
            modified_files_list = list(all_modified_files)
            if modified_files_list:
                self._phase_commit(modified_files_list, plan.goal)

            is_new_project = not self.is_url and not (self.dock.path.exists() and (self.dock.path / ".git").exists())
            pr_url = publish_to_github(self.dock, self._state.task_id, plan.goal, is_new_project, self.is_url)
            if pr_url:
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", f"Create PR 👉 {pr_url}")
                self._state.save()

            try:
                if hasattr(Phase, "PROPOSING"):
                    self._update_phase(Phase.PROPOSING, "START", "Architect is planning the next course")
                
                completed_tasks_summary = "\n".join([f"- [{t.id}] {t.title}: {t.description}" for t in plan.tasks])
                
                next_course = self._architect.propose_next_course(original_goal, completed_tasks_summary)
                next_course["workspace_path"] = str(self.dock.path) if self.dock else str(self._base_workspace)
                
                log.info(f"🧭 [Orchestrator] Next Course Proposal Ready!")
                log.info(f"  🎯 Next Goal: {next_course.get('next_goal')}")
                log.info(f"  📦 Artifacts: {next_course.get('expected_artifacts')}")
                log.info(f"  ⚠️ Risks: {next_course.get('risks')}")
                log.info(f"  📁 Workspace: {next_course.get('workspace_path')}")
                
                if hasattr(Phase, "PROPOSING"):
                    self._state.push_event(Phase.PROPOSING, "PROPOSED", f"Next Goal: {next_course.get('next_goal')}")
                    self._state.save()
                
                if self.on_proposal:
                    self.on_proposal(next_course)
                
                if self.auto_approve_search and next_course.get('next_goal'):
                    log.info("🚀 [Auto-Approve] 自律モード有効！承認をスキップして次のミッションへ突入します！")
                    self._treasury.report_and_enforce_hard_cap(self._agents, self._agent_names)
                    self._broadcast_cost()
                    return self.run(next_course.get('next_goal'), resume=True)
                else:
                    log.info("⏸️ [Manual Mode] ユーザーの承認（Approve）を待機します。")
                
            except Exception as e:
                log.warning(f"⚠️ [Orchestrator] Failed to propose next course: {e}")

            self._treasury.report_and_enforce_hard_cap(self._agents, self._agent_names)
            self._broadcast_cost()

            self._update_phase(Phase.DONE, "FINISH", "Mission successful. Waiting for next command. ⚓️")
            return self.dock.path if self.dock else Path(".")

        except Exception as e:
            log.error(traceback.format_exc())
            self._state.transition(Phase.DONE)
            self._state.save()
            self._broadcast_cost()
            raise e

    # =======================================================================
    # Sub-Phases
    # =======================================================================
    def _phase_plan(self, goal: str) -> PlanPayload:
        plan = self._architect.plan(goal, task_id=self._state.task_id)
        with self._state_lock:
            self._state.push_event(Phase.PLANNING, "OK", f"Target: {plan.target_files}")
        return plan

    def _phase_run(self, code: CodePayload) -> RunResult:
        if not self.dock: return RunResult(exit_code=-1, stdout="", stderr="No Dock", duration=0)
        try:
            # TODO: Step 4 に向けて、ここでの書き込みの競合解決（The Merge Protocol）が必要になります
            self.dock.write_artifacts(code.files)
        except Exception as e:
            return RunResult(exit_code=1, stdout="", stderr=f"Dock write error: {e}", duration=0)

        req_file = next((f for f in code.files if f.path == "requirements.txt"), None)
        python_cmd = ".venv/bin/python" if os.name != "nt" else ".venv\\Scripts\\python.exe"
        pip_cmd = ".venv/bin/pip" if os.name != "nt" else ".venv\\Scripts\\pip.exe"

        if req_file or (self.dock.path / "requirements.txt").exists():
            self.dock.terminal.execute_command(f"{pip_cmd} install -r requirements.txt")

        test_files = [f.path for f in code.files if f.path.startswith("test_") or f.path.endswith("_test.py")]
        has_existing_tests = len(list(self.dock.path.glob("test_*.py"))) > 0
        
        if test_files or has_existing_tests:
            self.dock.terminal.execute_command(f"{pip_cmd} install pytest")
            result = self.dock.terminal.execute_command(f"{python_cmd} -m pytest -v")
            return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)

        main_files = [f.path for f in code.files if f.path.endswith(".py") and not f.path.startswith("test_")]
        if not main_files: 
            return RunResult(exit_code=0, stdout="Validated", stderr="", duration=0)
        
        for main_file in main_files:
            result = self.dock.terminal.execute_command(f"{python_cmd} -m py_compile {main_file}")
            if result.exit_code != 0:
                return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)
                
        return RunResult(exit_code=0, stdout="Syntax check passed. (Waiting for unit tests for full validation)", stderr="", duration=0)
    
    def _phase_review(self, code: CodePayload, retry: int, plan: PlanPayload, run_result: RunResult | None = None) -> ReviewPayload:
        return self._reviewer.review(code, retry, plan=plan, run_result=run_result)

    def _phase_commit(self, modified_files: list[str], goal: str) -> list[Path]:
        if not self.dock: return []
        try:
            prompt = build_commit_msg_prompt(goal, modified_files)
            raw_msg = self._coder._call_llm(prompt).strip()
            msg = raw_msg.replace("```plaintext", "").replace("```", "").strip().split("\n")[0]
            self.dock.terminal.execute_command("git add .")
            self.dock.terminal.execute_command(f"git commit -m {shlex.quote(msg)}")
            return [self.dock.path / Path(f).name for f in modified_files]
        except Exception as e:
            log.warning("Commit failed: %s", e)
            return []