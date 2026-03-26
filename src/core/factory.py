"""
ARK (Autonomous Resilient Kernel) — Provider Factory
=====================================================
Phase 11.2: LiteLLM Router Fix
Vertex AI への誤爆を防ぎ、Google AI Studio (Gemini API) を
優先的に使用するようにモデル名のパースを強化したよ！
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.providers import BaseProvider, UniversalProvider, MockProvider

if TYPE_CHECKING:
    from src.core.config import ARKConfig

log = logging.getLogger("ARK.Factory")

def get_provider(role: str, cfg: "ARKConfig") -> BaseProvider:
    """エージェントロールに対応するプロバイダーを生成するよ！"""
    role_lower = role.lower().strip()

    role_to_provider_attr: dict[str, str] = {
        "architect": "architect_provider",
        "coder":     "coder_provider",
        "reviewer":  "reviewer_provider",
        "reflector": "reflector_provider",
    }

    if role_lower not in role_to_provider_attr:
        raise ValueError(f"未知のロール名: {role!r}。")

    raw_val: str = getattr(cfg, role_to_provider_attr[role_lower], "ollama").lower().strip()

    provider_name = ""
    model_name = ""

    # 🌟 ノア特製・Vertex AI 誤爆防止パーサー
    if raw_val.startswith("ollama/"):
        provider_name = "ollama"
        model_name = raw_val.replace("ollama/", "", 1)
    elif "gemini" in raw_val:
        provider_name = "gemini"
        # LiteLLM で Vertex AI ではなく Google AI Studio を使うには
        # モデル名の先頭に "gemini/" をつけるのが確実なんだって！
        if not raw_val.startswith("gemini/"):
            model_name = f"gemini/{raw_val}"
        else:
            model_name = raw_val
    elif "claude" in raw_val:
        provider_name = "anthropic"
        model_name = raw_val
    elif "deepseek" in raw_val:
        provider_name = "deepseek"
        model_name = raw_val
    else:
        provider_name = raw_val
        suffix = f"_{provider_name}" if provider_name != "ollama" else ""
        model_attr_name = f"{role_lower}_model{suffix}"
        model_name = getattr(cfg, model_attr_name, getattr(cfg, "model_name", "qwen2.5-coder:7b"))

    log.info("Role %r → provider %r (model=%s)", role, provider_name, model_name)

    return _build_provider(provider_name, model_name, cfg)

def _build_provider(provider_name: str, model_name: str, cfg: "ARKConfig") -> BaseProvider:
    """プロバイダー名と設定からインスタンスを生成するよ！"""
    
    if provider_name == "mock":
        return MockProvider()

    api_key = ""
    api_base = ""

    if provider_name == "ollama":
        api_base = getattr(cfg, "api_endpoint", "http://localhost:11434")
    elif provider_name == "gemini":
        # ここで .env から読み込んだ GEMINI_API_KEY を確実に渡す！
        api_key = getattr(cfg, "gemini_api_key", "")
    elif provider_name in ["claude", "anthropic"]:
        api_key = getattr(cfg, "anthropic_api_key", "")
    elif provider_name == "deepseek":
        api_key = getattr(cfg, "deepseek_api_key", "")
    elif provider_name == "openai":
        api_key = getattr(cfg, "openai_api_key", "")

    return UniversalProvider(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base
    )