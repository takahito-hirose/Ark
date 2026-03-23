"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator
=======================================================================
「すべてを浄化し、完璧に同期する」
特殊コマンドの処理を CommandInterceptor に委譲し、
メインの自律造船ループ（Grand Finale Engine）の統制に特化した指揮官よ💋
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
from src.core.models import (
    Phase, PlanPayload, CodePayload, ReviewPayload, 
    ReviewStatus, RunResult, ExecutionAttempt
)
from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.agents.reflector import ReflectorAgent
from src.core.config import ConfigLoader
from src.core.factory import get_provider
from src.core.agents import build_commit_msg_prompt

# 外部委譲されたマネージャーとインターセプター
from src.core.dock_manager import setup_dock
from src.core.github_publisher import publish_to_github
from src.core.command_interceptor import handle_special_commands # 🌟 コマンド傍受器💋

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

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

# ---------------------------------------------------------------------------
# Orchestrator (Grand Finale Engine)
# ---------------------------------------------------------------------------

class Orchestrator:
    """方舟の全行程を統制する、絶対的な指揮官。"""

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

        # ワークスペースの解決
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

        # 記憶システムの初期化
        self._memory = MemoryManager(base_dir=self._base_workspace / ".ark_memory")
        memory_tools.inject_memory_manager(self._memory)

        # モードに応じたモック設定
        is_mock = "1" if self.mode == "ECO" else "0"
        os.environ["ARK_MOCK_MODE"] = is_mock
        log.info(f"⚙️ System Mode: {self.mode} / 🔭 Telescope Mock: {'ON' if is_mock == '1' else 'OFF'}")

        # エージェント（精霊）たちの召喚
        self._architect = ArchitectAgent(
            get_provider("architect", self._cfg, mode=self.mode), 
            workspace_path=self._base_workspace, 
            on_token_usage=self.on_token_usage,
            use_mock_telescope=(self.mode == "ECO")
        )
        self._coder = CoderAgent(
            get_provider("coder", self._cfg, mode=self.mode), 
            workspace_path=self._base_workspace, 
            on_token_usage=self.on_token_usage
        )
        self._reviewer = ReviewerAgent(
            get_provider("reviewer", self._cfg, mode=self.mode), 
            workspace_path=self._base_workspace, 
            on_token_usage=self.on_token_usage
        )
        self._reflector = ReflectorAgent(
            get_provider("reflector", self._cfg, mode=self.mode), 
            workspace_path=self._base_workspace, 
            tools=[memory_tools.save_core_rule, memory_tools.archive_experience], 
            on_token_usage=self.on_token_usage
        )
        
        self.dock: Dock | None = None 

    def run(self, goal: str, *, resume: bool = False) -> Path:
        """ミッションを開始し、自律ループを回すわ。"""
        self._base_workspace.mkdir(parents=True, exist_ok=True)
        
        if resume:
            self._state.load()
        else:
            self._state = ARKState(self._base_workspace)
            self._state.goal = goal
            
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)
            
        # =========================================================================
        # 🌟 特殊コマンドの傍受 (Command Interception)
        # =========================================================================
        if handle_special_commands(goal, self._memory, self._update_phase, reflector=self._reflector):
            return self._base_workspace
        # =========================================================================
        
        # =========================================================================
        # 🧠 [PHASE 10-3 STEP 3] 大図書館からのRAG自動注入 (Context Injection) 💋
        # =========================================================================
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
        # =========================================================================

        log.info("=" * 60)
        log.info("🚀  ARK Autonomous Loop (Grand Finale)")
        log.info(f"    GOAL: {goal}")
        log.info("=" * 60)

        try:
            # ── PHASE 1: PLANNING ─────────────────────────────────────────────
            self._update_phase(Phase.PLANNING, "START", "Drafting mission blueprint...")
            plan = self._phase_plan(goal)

            # ターゲットファイルの固定
            goal_files = re.findall(r'(\w+\.py)', goal)
            if goal_files:
                plan.target_files = goal_files

            # ドック（造船所）の準備
            self.dock = setup_dock(
                target_input=self.target_input,
                base_workspace=self._base_workspace,
                task_id=self._state.task_id,
                plan_project_name=getattr(plan, 'project_name', None)
            )

            # エージェントたちの作業ディレクトリをドックに同期
            if self.dock:
                for agent in [self._architect, self._coder, self._reviewer, self._reflector]:
                    agent._workspace_path = self.dock.path

            # ── PHASE 2+3: CODE / REVIEW loop ─────────────────────────────────
            code_result: CodePayload | None = None
            last_review: ReviewPayload | None = None
            execution_feedback: str = ""
            reviewer_feedback: str = ""
            attempt_history: list[ExecutionAttempt] = []

            while self._state.retry_count < MAX_RETRIES:
                retry = self._state.retry_count
                self._update_phase(Phase.CODING, "START", f"Surgical Implementation (Attempt {retry+1})")
                
                # コンテキストとして現在のソースを読み込む
                current_source = ""
                if plan.target_files and self.dock:
                    target_file = self.dock.path / plan.target_files[0]
                    if target_file.exists():
                        current_source = target_file.read_text(encoding="utf-8")

                prompt_aug = f"\n\n### Current SOURCE of {plan.target_files[0]}:\n```python\n{current_source}\n```" if current_source else ""
                
                # コーディング実行（エラーがあれば自己修正）
                if execution_feedback:
                    code_result = self._coder.remediate(
                        plan, retry, failure_reason="Execution Error", 
                        stacktrace=execution_feedback, current_source=current_source, 
                        attempt_history=attempt_history
                    )
                else:
                    code_result = self._coder.code(plan, retry, reviewer_feedback=reviewer_feedback + prompt_aug)

                # 🚀 実行検証 (RUNNING)
                self._state.push_event(Phase.CODING, "RUNNING", "Validating artifacts...")
                self._state.save()
                
                run_result = self._phase_run(code_result)
                if not run_result.success:
                    self._state.retry_count += 1
                    err_msg = run_result.stderr if run_result.stderr else run_result.stdout
                    self._state.push_event(Phase.CODING, "FAIL", f"Fail: {err_msg[:80]}...")
                    self._state.save()
                    
                    if code_result and code_result.files:
                        attempt_history.append(ExecutionAttempt(
                            code=code_result.files[0].content, 
                            error=err_msg, 
                            attempt_number=self._state.retry_count
                        ))
                    execution_feedback = err_msg
                    continue
                
                execution_feedback = ""

                # 🔍 審査 (REVIEWING)
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

            # =========================================================================
            # 🚨 [致命的な敗北の処理] 
            # Orchestratorは分析せず、ただ司書(Reflector)に履歴をぶん投げるだけ💋
            # =========================================================================
            if self._state.retry_count >= MAX_RETRIES and (not last_review or last_review.status != ReviewStatus.PASS):
                self._state.transition(Phase.BLOCKED)
                self._state.save()
                
                log.warning("⚠️ [Orchestrator] 致命的な敗北を確認。原因分析を司書に委譲します...")
                self._state.push_event(Phase.BLOCKED, "REFLECT", "Archiving fatal failure...")
                self._state.save()
                
                # 敗北時はコードが不完全かもしれないので安全対策
                failed_code = code_result if code_result else CodePayload(files=[])
                
                # 🌟 is_failure=True という「フラグ」だけを渡して丸投げ！
                self._reflector.reflect(plan, failed_code, attempt_history=attempt_history, is_failure=True)
                
                raise CircuitBreakerTripped("Surgery could not be stabilized. Circuit breaker tripped. 💋")
            # =========================================================================

            # ── PHASE 4: COMMITTING ───────────────────────────────────────────
            self._update_phase(Phase.COMMITTING, "START", "Finalizing sync...")
            assert code_result is not None
            self._phase_commit(code_result, plan.goal)

            # GitHub へのパブリッシュ
            is_new_project = not self.is_url and not (self.dock.path.exists() and (self.dock.path / ".git").exists())
            pr_url = publish_to_github(self.dock, self._state.task_id, plan.goal, is_new_project, self.is_url)
            
            if pr_url:
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", f"Create PR 👉 {pr_url}")
                self._state.save()

            # ── PHASE 5: REFLECT ──────────────────────────────────────────────
            self._state.push_event(Phase.COMMITTING, "REFLECT", "Knowledge archiving...")
            self._state.save()
            
            # 🌟 [PHASE 10-3 STEP 1] 成功時は通常通り司書を呼ぶ
            self._reflector.reflect(plan, code_result, attempt_history=attempt_history, is_failure=False)

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

        # 依存関係のチェック
        req_file = next((f for f in code.files if f.path == "requirements.txt"), None)
        python_cmd = ".venv/bin/python" if os.name != "nt" else ".venv\\Scripts\\python.exe"
        pip_cmd = ".venv/bin/pip" if os.name != "nt" else ".venv\\Scripts\\pip.exe"

        if req_file or (self.dock.path / "requirements.txt").exists():
            log.info("📦 [Dock] Installing dependencies from requirements.txt...")
            self.dock.terminal.execute_command(f"{pip_cmd} install -r requirements.txt")

        # 実行テスト（.py ファイルを探して実行）
        main_file = next((f.path for f in code.files if f.path.endswith(".py") and not f.path.startswith("test_")), None)
        if not main_file: return RunResult(exit_code=0, stdout="Validated", stderr="", duration=0)
        
        log.info(f"🧪 [Run] Executing via venv: {python_cmd} {main_file}")
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
            log.info("📝 [Commit] Recording surgery results: %s", msg)
            
            self.dock.terminal.execute_command("git add .")
            self.dock.terminal.execute_command(f"git commit -m {shlex.quote(msg)}")
            return [self.dock.path / Path(f.path).name for f in code.files]
        except Exception as e:
            log.warning("Commit failed: %s", e)
            return []

if __name__ == "__main__":
    load_dotenv()
    # ターミナルから直接呼び出された場合の簡易エントリーポイント
    Orchestrator().run(" ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello World")