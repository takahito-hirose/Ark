"""
ARK (Autonomous Resilient Kernel) — Core Orchestrator (The Dock Edition)
=======================================================================
新たなプロジェクト（探査船）を動的に生成し、GitHub リポジトリを自動造船する
『The Dock』機能を搭載したオーケストレーター。

Conforms to: specs/phase5_roadmap.md
"""

from __future__ import annotations

import json
import logging
import os
import sys
import textwrap
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Callable, Protocol
from dotenv import load_dotenv

# 記憶システムとツールのインポート
from src.memory import MemoryManager
from src.tools import memory_tools
from src.tools.terminal import TerminalOracle
from src.core.patch_engine import PatchEngine

class StatusCallback(Protocol):
    def __call__(self, phase: Phase, status: str, retry_count: int, detail: str = "") -> None: ...

from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.agents.reflector import ReflectorAgent

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

class CircuitBreakerTripped(RuntimeError): pass
class OrchestratorBlocked(RuntimeError): pass

# ---------------------------------------------------------------------------
# Persistent State
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Orchestrator (The Dock Edition)
# ---------------------------------------------------------------------------

class Orchestrator:
    def __init__(
        self,
        config_path: Path | None = None,
        workspace_path: str | Path | None = None,
        on_status_change: StatusCallback | None = None,
        on_token_usage: Callable[[int], None] | None = None,
        mode: str = "ECO"  # 🌟 NEW: mode引数を追加！
    ) -> None:
        self._cfg = ConfigLoader.load(config_path)
        
        # 🌟 NEW: モードに応じて Config (使用モデル) を動的切り替え！💋
        self.mode = mode.upper()
        if self.mode == "RICH":
            log.info("💎 RICH MODE ACTIVATED: Unleashing the power of Cloud LLMs!")
            self._cfg.architect_provider = "gemini"
            self._cfg.coder_provider = "gemini"
            self._cfg.reviewer_provider = "gemini"
            self._cfg.reflector_provider = "gemini"
        else:
            log.info("🌱 ECO MODE ACTIVATED: Conserving treasury with Local LLMs.")

        # 💡 [The Dock] 母艦のベースワークスペースを決定
        ws_input = workspace_path or self._cfg.workspace_path or "."
        self._base_workspace = Path(ws_input).resolve()
        
        # 初期状態ではベースを操作対象とする
        self._workspace = self._base_workspace
        
        # 🌟 NEW: コールバックをクラス全体で覚えておく！
        self.on_status_change = on_status_change
        self.on_token_usage = on_token_usage
        
        # 状態管理（状態は母艦直下に置く）
        self._state = ARKState(self._base_workspace)
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)

        # 🧠 記憶システム（母艦 ARK の中枢図書館）
        self._memory = MemoryManager(base_dir=self._base_workspace / ".ark_memory")
        memory_tools.inject_memory_manager(self._memory)
        log.info("🧠 Memory System initialized at %s", self._base_workspace / ".ark_memory")

        ark_tools = [
            memory_tools.save_core_rule,
            memory_tools.archive_experience,
            memory_tools.recall_memory
        ]

        # エージェントの初期化
        # 🌟 修正: on_token_usage ではなく self.on_token_usage を渡す！
        self._architect = ArchitectAgent(get_provider("architect", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._coder = CoderAgent(get_provider("coder", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reviewer = ReviewerAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, on_token_usage=self.on_token_usage)
        self._reflector = ReflectorAgent(get_provider("reviewer", self._cfg), workspace_path=self._base_workspace, tools=ark_tools, on_token_usage=self.on_token_usage)
        
        # ツール類（run 時に再設定される）
        self._terminal = TerminalOracle(workspace_path=self._base_workspace)
        self._git: GitTool | None = None 

    def run(self, goal: str, *, resume: bool = False) -> Path:
        self._base_workspace.mkdir(parents=True, exist_ok=True)

        if resume:
            self._state.load()
        else:
            self._state = ARKState(self._base_workspace)
            self._state.goal = goal
            
        # 🌟 修正: hasattr を使わず、上で設定した self.on_status_change を直接チェック！
        if self.on_status_change:
            self._state.set_callback(self.on_status_change)
        
        # 🧠 記憶の引き出し（ルールの合体）
        core_rules = self._memory.load_core_rules_prompt()
        if core_rules and "現在、特定のプロジェクト・コアルールは" not in core_rules:
            goal = f"{goal}\n\n{core_rules}"
            log.info("🧠 コアルールをミッション（Goal）に注入しました！")

        log.info("=" * 60)
        log.info("🚀  ARK Autonomous Loop (The Dock Edition) — task %s", self._state.task_id)
        log.info("    MODE: %s", self.mode)
        log.info("    GOAL: %s", goal)
        log.info("=" * 60)

        # ── PHASE 1: PLANNING ─────────────────────────────────────────────
        self._state.transition(Phase.PLANNING)
        plan = self._phase_plan(goal)

        # 🏗️ [The Dock] プロジェクトディレクトリ（造船ドック）の動的生成
        # Architect が project_name を決めていない場合は、task_id から生成
        project_id = getattr(plan, 'project_name', f"ark-project-{self._state.task_id[:8]}")
        self._workspace = self._base_workspace / project_id
        self._workspace.mkdir(parents=True, exist_ok=True)
        
        log.info("🏗️  Welcome to The Dock: %s", self._workspace)
        
        # GitTool と TerminalOracle をこのプロジェクトドック専用に初期化
        self._git = GitTool(self._workspace)
        self._terminal = TerminalOracle(workspace_path=self._workspace)

        # ── PHASE 2+3: CODE / REVIEW loop ─────────────────────────────────
        code_result: CodePayload | None = None
        last_review: ReviewPayload | None = None
        execution_feedback: str = ""
        attempt_history: list[ExecutionAttempt] = []

        while self._state.retry_count < MAX_RETRIES:
            retry = self._state.retry_count
            self._state.transition(Phase.CODING)
            
            if execution_feedback:
                code_result = self._coder.remediate(plan, retry, failure_reason="Runtime Error", stacktrace=execution_feedback, current_source=code_result.files[0].content if code_result and code_result.files else "", attempt_history=attempt_history)
            elif last_review:
                code_result = self._phase_code(plan, retry, reviewer_feedback=last_review.summary)
            else:
                code_result = self._phase_code(plan, retry)

            # RUNNING (ドック内で実行)
            run_result = self._phase_run(code_result)
            if not run_result.success:
                self._state.retry_count += 1
                retry_msg = f"[🔄 SELF-HEALING] Attempt {self._state.retry_count}/{MAX_RETRIES}"
                self._state.push_event(Phase.CODING, "FAIL", f"{retry_msg} — Error: {run_result.stderr[:100]}")
                self._state.save()
                
                if code_result and code_result.files:
                    attempt_history.append(ExecutionAttempt(code=code_result.files[0].content, error=run_result.stderr, attempt_number=self._state.retry_count))
                
                execution_feedback = run_result.stderr
                if self._state.retry_count >= MAX_RETRIES: break
                continue
            
            execution_feedback = ""

            # REVIEWING
            self._state.transition(Phase.REVIEWING)
            review = self._phase_review(code_result, retry, plan)
            last_review = review

            if review.status == ReviewStatus.PASS:
                log.info("✅  Review PASSED  (score=%.2f)", review.score)
                self._state.push_event(Phase.REVIEWING, "PASS", review.summary)
                self._state.save()
                break

            self._state.retry_count += 1
            self._state.save()

            if self._state.retry_count >= MAX_RETRIES:
                self._state.transition(Phase.BLOCKED)
                raise CircuitBreakerTripped("Circuit Breaker tripped.")

        # ── PHASE 4: COMMIT & PUSH (造船完了と射出) ──────────────────────────
        self._state.transition(Phase.COMMITTING)
        assert code_result is not None
        
        # 🌟 NEW: 全ての難関（コーディング＆レビュー）を突破したこの瞬間に、初めてGitHubにリポジトリを作るわ！
        if not resume and self._git and os.getenv("GITHUB_TOKEN"):
            repo_url = self._git.create_remote_repo(
                name=project_id,
                description=f"ARK Generated Project: {plan.goal[:50]}..."
            )
            if repo_url:
                self._git.setup_dock(repo_url)

        # そしてローカルにファイルを書き込んでコミット！
        committed = self._phase_commit(code_result, plan.goal)

        # 🚀 GitHub へプッシュ！
        if self._git and os.getenv("GITHUB_TOKEN"):
            log.info("[THE DOCK] Launching probe ship to GitHub...")
            branch_name = self._git.create_topic_branch(self._state.task_id)
            self._git.push(branch_name)
            
            # 🌟 NEW: Push成功後に、UIへURL付きで完了通知をブロードキャストするわよ！
            if self._git.repo_url:
                # 認証用の oauth2:トークン@ が含まれている場合は消して綺麗なURLにする💋
                clean_url = self._git.repo_url.split("@")[-1] if "@" in self._git.repo_url else self._git.repo_url
                clean_url = "https://" + clean_url if not clean_url.startswith("http") else clean_url
                
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", f"Probe ship launched to: {clean_url}")
            else:
                self._state.push_event(Phase.COMMITTING, "DEPLOYED", "Probe ship launched to GitHub.")

        # ── PHASE 5: REFLECT ──────────────────────────────────────────────
        log.info("[REFLECT] 振り返りフェーズ開始...")
        self._reflector.reflect(plan, code_result)
        self._state.push_event(Phase.COMMITTING, "REFLECT", "Knowledge archived.")
        self._state.save()

        self._state.transition(Phase.DONE)
        log.info("🏛️  ARK loop complete — Probe ship launched from The Dock: %s", self._workspace)
        return self._workspace

    # --------------------------------------------------------- internal helpers

    def _write_artifacts(self, task_dir: Path, files: list[FileChange]):
        """
        生成されたコードをファイルに書き出すわ。
        Phase 9仕様: パッチ形式なら外科手術、そうでなければ全上書きよ！💋
        """
        for fc in files:
            # ファイル名はフラットにドック直下に展開
            file_path = task_dir / Path(fc.path).name
            content = fc.content

            if "<<<<<<< SEARCH" in content:
                # 🏥 外科手術（パッチ適用）
                success = PatchEngine.apply_patches(str(file_path), content)
                if success:
                    log.info("✅ Surgically modified: %s", fc.path)
                else:
                    # パッチ適用失敗なら、安全のためにフォールバック（またはエラーに）
                    log.warning("⚠️ Patch failed for %s. Overwriting instead.", fc.path)
                    file_path.write_text(content, encoding="utf-8")
            else:
                # 🆕 新規作成 or 全上書き
                file_path.write_text(content, encoding="utf-8")
                log.info("📝 File written: %s", fc.path)

    # --------------------------------------------------------- phase methods

    def _phase_plan(self, goal: str) -> PlanPayload:
        log.info("[PLAN]  Architect generating PlanPayload …")
        plan = self._architect.plan(goal, task_id=self._state.task_id)
        self._state.push_event(Phase.PLANNING, "OK", f"project={getattr(plan, 'project_name', 'default')}")
        self._state.save()
        return plan

    def _phase_code(self, plan: PlanPayload, retry: int, reviewer_feedback: str = "") -> CodePayload:
        log.info("[CODE]  Coder synthesising code …")
        code = self._coder.code(plan, retry, reviewer_feedback=reviewer_feedback)
        self._state.push_event(Phase.CODING, "OK", f"files={[f.path for f in code.files]}")
        self._state.save()
        return code

    def _phase_review(self, code: CodePayload, retry: int, plan: PlanPayload) -> ReviewPayload:
        log.info("[REVIEW] Reviewer auditing output …")
        review = self._reviewer.review(code, retry, plan=plan)
        return review

    def _phase_run(self, code: CodePayload) -> RunResult:
        log.info("[RUN]  Terminal Oracle executing code within The Dock …")
        
        # 🏥 外科手術エンジンを使用した書き出し
        self._write_artifacts(self._workspace, code.files)
        
        if any(f.path.endswith("requirements.txt") for f in code.files):
            self._terminal.execute_command("pip install -r requirements.txt")

        main_file = next((f.path for f in code.files if f.path.endswith(".py")), None)
        if not main_file:
            return RunResult(exit_code=-1, stdout="", stderr="No python file found", duration=0)
        
        script_name = Path(main_file).name
        result = self._terminal.execute_command(f"python {script_name}")
        
        if result.success:
            print(f"\n--- 🚀 ARK EXECUTION OUTPUT ---\n{result.stdout}\n------------------------------\n")
        return RunResult(exit_code=result.exit_code, stdout=result.stdout, stderr=result.stderr, duration=0)
    
    def _phase_commit(self, code: CodePayload, goal: str) -> list[Path]:
        log.info("[COMMIT] Writing final artifacts to The Dock...")
        
        # 🏥 外科手術エンジンを使用した最終書き出し
        self._write_artifacts(self._workspace, code.files)
        
        committed = [self._workspace / Path(fc.path).name for fc in code.files]
                
        try:
            prompt = build_commit_msg_prompt(goal, [f.path for f in code.files])
            commit_message = self._coder._call_llm(prompt).strip().split("\n")[0]
            if self._git:
                self._git.commit(commit_message)
        except Exception as e:
            log.error("Commit failed: %s", e)

        self._state.push_event(Phase.COMMITTING, "OK", f"committed={[str(p) for p in committed]}")
        self._state.save()
        return committed

def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    
    if argv is None:
        argv = sys.argv[1:]
    goal = " ".join(argv) if argv else "Hello World Pythonスクリプトを生成せよ"
    orc = Orchestrator()
    try:
        orc.run(goal)
    except Exception as e:
        log.critical("Orchestrator failed: %s", e)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())