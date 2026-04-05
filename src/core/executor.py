"""
ARK — Parallel Task Executor
=======================================================================
Phase 13: Dynamic Worker Spawning
Orchestratorから独立した、DAGベースのタスク並行実行エンジン。
各SubTaskの依存関係を解決しながら、スレッドプール上で安全にエージェントを稼働させます。
"""

import asyncio
import copy
import logging
import threading
from pathlib import Path
from typing import Callable

from src.core.models import (
    Phase, PlanPayload, CodePayload, ReviewPayload,
    ReviewStatus, RunResult, ExecutionAttempt,
    SubTask, TaskStatus
)
from src.core.state import ARKState
from src.core.dock import Dock
from src.core.treasury import Treasury

log = logging.getLogger("ARK.Executor")

MAX_RETRIES = 3

class CircuitBreakerTripped(RuntimeError): pass

class ParallelTaskExecutor:
    """大艦隊（Coderスレッド群）の並列召喚と進行管理を司る実行部隊"""

    def __init__(
        self,
        coder,
        reviewer,
        reflector,
        dock: Dock,
        state: ARKState,
        state_lock: threading.Lock,
        treasury: Treasury,
        agents: list,
        agent_names: list,
        update_phase_cb: Callable,
        broadcast_cost_cb: Callable,
        phase_run_cb: Callable,
        phase_review_cb: Callable,
    ):
        self.coder = coder
        self.reviewer = reviewer
        self.reflector = reflector
        self.dock = dock
        self.state = state
        self.state_lock = state_lock
        self.treasury = treasury
        self.agents = agents
        self.agent_names = agent_names
        
        # Orchestratorから引き継いだコールバック群
        self._update_phase = update_phase_cb
        self._broadcast_cost = broadcast_cost_cb
        self._phase_run = phase_run_cb
        self._phase_review = phase_review_cb

    async def execute_all(
        self, 
        plan: PlanPayload, 
        task_artifacts: dict[str, list[str]], 
        all_modified_files: set, 
        attempt_history: list[ExecutionAttempt]
    ):
        """DAG（有向非巡回グラフ）に基づき、依存関係が解決したタスクから並行実行する"""
        task_events = {t.id: asyncio.Event() for t in plan.tasks}
        tasks_coros = []

        async def worker(task: SubTask):
            # 依存タスク（Prerequisites）の完了を待機
            if hasattr(task, 'dependencies') and task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id in task_events:
                        await task_events[dep_id].wait()

            success = await asyncio.to_thread(
                self._process_single_task_sync,
                task, plan, task_artifacts, all_modified_files, attempt_history
            )

            if success:
                task_events[task.id].set() # 次のタスクへの青信号を点灯
            else:
                raise CircuitBreakerTripped(f"Surgery could not be stabilized in {task.id}. Circuit breaker tripped.")

        for t in plan.tasks:
            tasks_coros.append(asyncio.create_task(worker(t)))

        if not tasks_coros:
            return

        # いずれかのタスクが致命的エラーでコケた場合、全体をキャンセルして停止する
        done, pending = await asyncio.wait(tasks_coros, return_when=asyncio.FIRST_EXCEPTION)
        
        for t in done:
            if t.exception():
                for p in pending:
                    p.cancel()
                raise t.exception()

    def _process_single_task_sync(
        self, 
        current_task: SubTask, 
        plan: PlanPayload, 
        task_artifacts: dict[str, list[str]], 
        all_modified_files: set, 
        attempt_history: list[ExecutionAttempt]
    ) -> bool:
        """単一タスクを実行するワーカープロセス（スレッドプール内で安全に実行される）"""
        with self.state_lock:
            current_task.status = TaskStatus.IN_PROGRESS
        
        task_log_prefix = f"[{current_task.id}] {current_task.title}"
        log.info(f"⚓️ [Executor] Worker Spawning: {task_log_prefix}")

        # スレッド間での目標やプロンプトの競合を防ぐため、プランの複製（DeepCopy）を作成
        task_plan = copy.deepcopy(plan)
        task_plan.goal = f"【Overall Goal】\n{plan.goal}\n\n【Current Task: {current_task.title}】\n{current_task.description}"

        retry_count = 0
        code_result: CodePayload | None = None
        execution_feedback: str = ""
        reviewer_feedback: str = ""
        task_success = False

        while retry_count < MAX_RETRIES:
            self._update_phase(Phase.CODING, "START", f"{task_log_prefix} (Attempt {retry_count+1})")
            
            accumulated_context = ""
            if self.dock and current_task.dependencies:
                files_to_inject = set()
                with self.state_lock:
                    for dep_id in current_task.dependencies:
                        if dep_id in task_artifacts:
                            files_to_inject.update(task_artifacts[dep_id])
                
                if files_to_inject:
                    accumulated_context += "\n\n【📝 Context from Required Prerequisite Tasks】\n"
                    for dep_file in files_to_inject:
                        target_path = self.dock.path / Path(dep_file).name
                        if target_path.exists():
                            content = target_path.read_text(encoding="utf-8")
                            accumulated_context += f"### Prerequisite File: {Path(dep_file).name}\n```python\n{content}\n```\n"

            current_source = ""
            if task_plan.target_files and self.dock:
                unique_targets = list(dict.fromkeys(task_plan.target_files))
                for target in unique_targets:
                    target_file = self.dock.path / target
                    if target_file.exists():
                        content = target_file.read_text(encoding="utf-8")
                        current_source += f"### File: {target}\n```python\n{content}\n```\n\n"

            prompt_aug = accumulated_context
            
            # Coderへ指示（エラー修正モード or 新規実装モード）
            if execution_feedback:
                code_result = self.coder.remediate(task_plan, retry_count, failure_reason="Execution Error", stacktrace=execution_feedback, current_source=current_source, attempt_history=attempt_history)
            else:
                code_result = self.coder.code(task_plan, retry_count, reviewer_feedback=reviewer_feedback + prompt_aug)

            self.treasury.check_soft_cap(self.agents, Phase.CODING, self._update_phase)
            self._broadcast_cost()

            with self.state_lock:
                self.state.push_event(Phase.CODING, "RUNNING", f"Validating artifacts for {current_task.id}")
                self.state.save()
            
            # テスト実行（Dockへの書き込み）
            run_result = self._phase_run(code_result)
            if not run_result.success:
                retry_count += 1
                err_msg = run_result.stderr if run_result.stderr else run_result.stdout
                with self.state_lock:
                    self.state.push_event(Phase.CODING, "FAIL", f"Fail: {err_msg[:80]}")
                    self.state.save()
                    if code_result and code_result.files:
                        attempt_history.append(ExecutionAttempt(code=code_result.files[0].content, error=err_msg, attempt_number=retry_count))
                execution_feedback = err_msg
                continue
            
            execution_feedback = ""

            self._update_phase(Phase.REVIEWING, "START", f"Auditing {current_task.id}")
            # レビュー実行（ハイブリッド審査対応）
            review = self._phase_review(code_result, retry_count, task_plan, run_result=run_result)
            
            self.treasury.check_soft_cap(self.agents, Phase.REVIEWING, self._update_phase)
            self._broadcast_cost()

            if review.status == ReviewStatus.PASS:
                with self.state_lock:
                    self.state.push_event(Phase.REVIEWING, "PASS", f"Task {current_task.id} Perfect!")
                    self.state.save()
                    task_success = True
                    if code_result and code_result.files:
                        task_modified = [f.path for f in code_result.files]
                        task_artifacts[current_task.id] = task_modified
                        all_modified_files.update(task_modified)
                break

            reviewer_feedback = review.summary
            retry_count += 1

        if not task_success:
            with self.state_lock:
                current_task.status = TaskStatus.FAILED
                self.state.transition(Phase.BLOCKED)
                self.state.push_event(Phase.BLOCKED, "REFLECT", f"Archiving fatal failure in {current_task.id}")
                self.state.save()
            
            log.warning(f"⚠️ [Executor] 致命的な敗北を確認 ({current_task.id})。原因分析を司書に委譲します")
            failed_code = code_result if code_result else CodePayload(files=[])
            self.reflector.reflect(task_plan, failed_code, attempt_history=attempt_history, is_failure=True)
            self.treasury.report_and_enforce_hard_cap(self.agents, self.agent_names)
            self._broadcast_cost()
            return False

        with self.state_lock:
            current_task.status = TaskStatus.COMPLETED
        log.info(f"✅ [Executor] Worker for [{current_task.id}] Completed successfully!")
        
        if code_result:
            self.reflector.reflect(task_plan, code_result, attempt_history=attempt_history, is_failure=False)

        return True