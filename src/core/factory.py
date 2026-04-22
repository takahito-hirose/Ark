"""
ARK (Autonomous Resilient Kernel) — Team Factory & Model Router
================================================================
Phase 15: The Fleet Awakening (Step 2: Ark Model Router)
ただプロバイダーを返すだけの関数から、自律的にモデルを切り替え、
エージェントを動的に生成する「ファクトリー（工場）」へ進化させたよ💋
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

from src.core.providers import BaseProvider, UniversalProvider, MockProvider

if TYPE_CHECKING:
    from src.core.config import ARKConfig
    from src.agents.base_agent import BaseAgent

log = logging.getLogger("ARK.Factory")

class ArkModelRouter:
    """
    モデル選択とルーティングを司る頭脳。
    「完全自動航行（Overdrive）」に向けて、予算やタスク難易度に応じた
    自律的なダウングレード/アップグレード機能の土台になるよ！
    """
    def __init__(self, cfg: "ARKConfig"):
        self.cfg = cfg

    def resolve_provider(self, role: str, force_local: bool = False) -> BaseProvider:
        """ロールに最適なプロバイダー（LiteLLMラッパー）を返すわ💋"""
        role_lower = role.lower().strip()
        role_to_provider_attr = {
            "architect": "architect_provider",
            "coder":     "coder_provider",
            "reviewer":  "reviewer_provider",
            "reflector": "reflector_provider",
        }

        if role_lower not in role_to_provider_attr:
            raise ValueError(f"未知のロール名: {role!r}。")

        # 🌟 [OVERDRIVE READY] 予算超過や夜間自律航行時の強制ローカルモード！
        if force_local:
            # 強制的にローカルの軽量・高速モデルにフォールバック
            raw_val = "ollama/qwen2.5-coder:7b" if role_lower == "coder" else "ollama/gemma4:e4b"
            log.warning(f"⚠️ [Router] {role_lower} は強制ローカルモード({raw_val})で起動します！")
        else:
            raw_val = getattr(self.cfg, role_to_provider_attr[role_lower], "ollama").lower().strip()

        provider_name, model_name = self._parse_model_string(raw_val, role_lower)
        log.info("🧭 [Router] Role %r → provider %r (model=%s)", role, provider_name, model_name)

        return self._build_provider(provider_name, model_name)

    def _parse_model_string(self, raw_val: str, role_lower: str) -> tuple[str, str]:
        """Slackなどの動的入力を解析するノア特製パーサーよ💋"""
        provider_name = ""
        model_name = ""

        if raw_val.startswith("ollama|"):
            provider_name = "ollama"
            model_name = raw_val.split("|", 1)[1]
        elif raw_val.startswith("ollama/"):
            provider_name = "ollama"
            model_name = raw_val.replace("ollama/", "", 1)
        elif "gemini" in raw_val:
            provider_name = "gemini"
            model_name = raw_val if raw_val.startswith("gemini/") else f"gemini/{raw_val}"
        elif "claude" in raw_val:
            provider_name = "anthropic"
            model_name = raw_val
        elif "deepseek" in raw_val:
            provider_name = "deepseek"
            model_name = raw_val
        elif "gpt" in raw_val or raw_val == "openai":
            provider_name = "openai"
            if raw_val == "openai":
                model_name = getattr(self.cfg, f"{role_lower}_model_openai", getattr(self.cfg, "model_name", "gpt-4o"))
            else:
                model_name = raw_val
        else:
            provider_name = raw_val
            suffix = f"_{provider_name}" if provider_name != "ollama" else ""
            model_attr_name = f"{role_lower}_model{suffix}"
            model_name = getattr(self.cfg, model_attr_name, getattr(self.cfg, "model_name", "qwen2.5-coder:7b"))

        return provider_name, model_name

    def _build_provider(self, provider_name: str, model_name: str) -> BaseProvider:
        """プロバイダー名と設定からLiteLLMインスタンスを生成するよ！"""
        if provider_name == "mock":
            return MockProvider()

        api_key = ""
        api_base = ""

        if provider_name == "ollama":
            api_base = getattr(self.cfg, "api_endpoint", "http://localhost:11434")
        elif provider_name == "gemini":
            api_key = getattr(self.cfg, "gemini_api_key", "")
        elif provider_name in ["claude", "anthropic"]:
            api_key = getattr(self.cfg, "anthropic_api_key", "")
        elif provider_name == "deepseek":
            api_key = getattr(self.cfg, "deepseek_api_key", "")
        elif provider_name == "openai":
            api_key = getattr(self.cfg, "openai_api_key", "")

        return UniversalProvider(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base
        )


class ArkTeamFactory:
    """
    ルーターを使ってエージェントたちを爆誕させる工場（ファクトリー）よ💋
    将来的には「バックオフィスチーム」や「リサーチチーム」の編成もここでやるわ！
    """
    def __init__(self, router: ArkModelRouter):
        self.router = router

    def spawn_agent(self, role_class: Type['BaseAgent'], role_name: str, force_local: bool = False, **kwargs) -> 'BaseAgent':
        """1人のエージェントを適切なモデル（武器）を持たせて召喚する！"""
        provider = self.router.resolve_provider(role_name, force_local=force_local)
        return role_class(provider=provider, **kwargs)


# =========================================================================
# Legacy Wrapper (後方互換性)
# =========================================================================
def get_provider(role: str, cfg: "ARKConfig", force_local: bool = False) -> BaseProvider:
    """
    旧仕様の Orchestrator を壊さないためのラッパー関数。
    いずれ Orchestrator 側も ArkTeamFactory を使って一括生成するように移行するよ！
    """
    router = ArkModelRouter(cfg)
    return router.resolve_provider(role, force_local=force_local)