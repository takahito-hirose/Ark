"""
ARK Treasury — 予算・コスト管理システム
=======================================================================
各エージェントのAPI利用コストを集計し、タスクごとの予算上限（Soft Cap / Hard Cap）
を管理する。隠しプロパティへのアクセスを強化し、確実なコスト抽出を実現します。
"""

import logging
from pathlib import Path
from typing import Final, Any
from src.core.models import Phase

log = logging.getLogger("ARK.Treasury")

class Treasury:
    TASK_BUDGET_LIMIT: Final[float] = 1.0  # 1タスクあたりの予算上限(USD)

    def __init__(self, memory_dir: Path, config: Any):
        self._memory_dir = memory_dir
        self._config = config
        self._emergency_flag_path = self._memory_dir / "emergency_mode.flag"
        self._soft_cap_warned = False

        self._check_and_apply_emergency_override()

    def _check_and_apply_emergency_override(self) -> None:
        """フラグが存在すれば、全モデルをローカル(Ollama)に強制ダウングレードする"""
        if self._emergency_flag_path.exists():
            log.warning("🚨 [Emergency Override] 前回予算超過！全モデルをローカル(Ollama)に強制ダウングレード！")
            for role_attr in ["architect_provider", "coder_provider", "reviewer_provider", "reflector_provider"]:
                setattr(self._config, role_attr, "ollama/qwen2.5-coder:7b")

    def check_soft_cap(self, agents: list[Any], current_phase: Phase, state_updater: callable) -> None:
        """実行中のリアルタイム予算チェック（80%超過で警告）"""
        if self._soft_cap_warned:
            return
            
        total_usd = self._calculate_total_cost(agents)
        
        if total_usd >= (self.TASK_BUDGET_LIMIT * 0.8):
            self._soft_cap_warned = True
            log.warning(f"⚠️ [Soft Cap] 予算の80% (${total_usd:.4f}) に到達しました！このタスクは完遂まで現在のモデルで続行します。")
            state_updater(current_phase, "WARNING", f"Budget Soft Cap Reached: ${total_usd:.4f}")

    def get_realtime_usage_payload(self, agents: list[Any]) -> dict:
        """
        🌟 新機能: フロントエンド同期用のペイロードを生成します。
        メインループ(ark.pyなど)から呼び出し、WebSocketで送信してください。
        """
        total_usd = 0.0
        total_tokens = 0
        for agent in agents:
            cost, tokens = self._extract_stats(agent)
            total_usd += cost
            total_tokens += tokens

        return {
            "type": "TREASURY_UPDATE",
            "cost": float(total_usd),
            "tokens": int(total_tokens)
        }

    def report_and_enforce_hard_cap(self, agents: list[Any], agent_names: list[str]) -> None:
        """ミッション終了時の会計報告とHard Cap（予算超過）判定"""
        log.info("=" * 60)
        log.info("💎 [The Treasury] Mission Cost Report 💎")
        
        total_usd = 0.0
        total_tokens = 0

        for name, agent in zip(agent_names, agents):
            cost, tokens = self._extract_stats(agent)
            if cost > 0 or tokens > 0:
                log.info(f"  - {name:10s}: ${cost:.5f} ({tokens} tokens)")
                total_usd += cost
                total_tokens += tokens
            else:
                log.info(f"  - {name:10s}: $0.00000 (Free or 0 tokens)")
                
        log.info("-" * 60)
        log.info(f"  💰 TOTAL COST:   ${total_usd:.5f} / Budget: ${self.TASK_BUDGET_LIMIT:.2f}")
        log.info(f"  📈 TOTAL TOKENS: {total_tokens}")
        log.info("=" * 60)

        # 🚨 [Hard Cap] 最終精算で予算オーバーしていたらフラグを立てる！
        if total_usd >= self.TASK_BUDGET_LIMIT:
            log.warning(f"🚨 [Hard Cap] タスク予算({self.TASK_BUDGET_LIMIT}ドル)を超過して完遂しました！次期ミッションからローカルに強制移行します。")
            self._emergency_flag_path.touch(exist_ok=True)
        else:
            if self._emergency_flag_path.exists():
                self._emergency_flag_path.unlink()
                log.info("💸 予算内に収まったため、非常用フラグを解除しました！")

    def _calculate_total_cost(self, agents: list[Any]) -> float:
        return sum(self._extract_stats(agent)[0] for agent in agents)
        
    def _extract_stats(self, agent: Any) -> tuple[float, int]:
        """
        隠蔽されたプロバイダー属性を確実に探し出し、コストとトークンを抽出します。
        """
        # プロバイダーのインスタンスを探す（アンダースコア付きの隠しプロパティ対策）
        provider = getattr(agent, "provider", None) or getattr(agent, "_provider", None) or getattr(agent, "llm", None)
        if not provider:
            return 0.0, 0
        
        # コストを探す
        cost = (getattr(provider, "session_cost", None) or 
                getattr(provider, "total_cost", None) or 
                getattr(provider, "cost", None) or 
                0.0)
        
        # トークンを探す
        tokens = (getattr(provider, "session_tokens", None) or 
                  getattr(provider, "total_tokens", None) or 
                  getattr(provider, "tokens", None) or 
                  getattr(provider, "usage_tokens", None) or 
                  0)
                  
        return float(cost), int(tokens)