"""
ARK (Autonomous Resilient Kernel) — Provider Factory
=====================================================
エージェントロール（architect / coder / reviewer / reflector）に対応する
:class:`~src.core.providers.BaseProvider` インスタンスを生成するファクトリー。

設定値の優先順位は :class:`~src.core.config.ARKConfig` に従う:

1. 環境変数 ``ARK_ARCHITECT_PROVIDER`` 等
2. ``config.yaml``
3. デフォルト値 ``"ollama"``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.core.providers import BaseProvider, GeminiProvider, MockProvider, OllamaProvider

if TYPE_CHECKING:
    from src.core.config import ARKConfig

log = logging.getLogger("ARK.Factory")


# ---------------------------------------------------------------------------
# Provider name → class mapping
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "ollama": OllamaProvider,
    "mock":   MockProvider,
    "gemini": GeminiProvider,
}


# ---------------------------------------------------------------------------
# Public factory function
# ---------------------------------------------------------------------------

# 🌟 第3引数に `mode: str = "ECO"` を追加！
def get_provider(role: str, cfg: "ARKConfig", mode: str = "ECO") -> BaseProvider:
    """エージェントロールに対応する :class:`BaseProvider` インスタンスを返す。

    Parameters
    ----------
    role:
        エージェントのロール名。
        ``"architect"`` / ``"coder"`` / ``"reviewer"`` / ``"reflector"`` のいずれか。
    cfg:
        :class:`~src.core.config.ARKConfig` のインスタンス。
    mode:
        システムの動作モード (``"ECO"`` または ``"RICH"``)。
        RICHの場合は強制的にGeminiプロバイダーを使用する。

    Returns
    -------
    BaseProvider
        指定されたロールに対応するプロバイダーインスタンス。
    """
    role_lower = role.lower().strip()

    # ---- 1. ロールからプロバイダー属性名を解決 --------------------------------
    role_to_provider_attr: dict[str, str] = {
        "architect": "architect_provider",
        "coder":     "coder_provider",
        "reviewer":  "reviewer_provider",
        "reflector": "reflector_provider",
    }

    if role_lower not in role_to_provider_attr:
        raise ValueError(
            f"未知のロール名: {role!r}。"
            f" 有効なロール: {list(role_to_provider_attr.keys())}"
        )

    # config からプロバイダー名（ollama/gemini等）を取得
    provider_name: str = getattr(cfg, role_to_provider_attr[role_lower], "ollama").lower().strip()

    # 🌟🌟🌟 ここが肝！RICHモードなら問答無用でGeminiにオーバーライド！ 🌟🌟🌟
    if mode == "RICH":
        provider_name = "gemini"

    # ---- 2. プロバイダー種別に応じてモデル属性名を解決 --------------------------
    # Gemini の場合は _gemini サフィックスが付いたフィールド（例: coder_model_gemini）を優先するわ
    is_gemini = (provider_name == "gemini")
    suffix = "_gemini" if is_gemini else ""
    
    model_attr_name = f"{role_lower}_model{suffix}"
    
    # config からモデル名を取得。なければグローバルの cfg.model_name にフォールバック
    model_name: str = getattr(cfg, model_attr_name, cfg.model_name)

    # 🚨 セーフティネット: RICHモードでモデル名が未設定（ollamaのモデル名が入っちゃう場合）への対策
    if mode == "RICH" and ("gemma" in model_name or "qwen" in model_name or "llama" in model_name or "phi" in model_name):
        model_name = "gemini-2.5-flash"  # フォールバック用のGeminiモデル
        log.warning(f"⚠️ [RICH MODE] {role} のGeminiモデルが未指定のため、強制的に {model_name} に設定しました。")

    log.info("Role %r → provider %r (model=%s) [Mode=%s]", role, provider_name, model_name, mode)

    # ---- 3. プロバイダーのビルド --------------------------------------------
    return _build_provider(provider_name, model_name, cfg)


def _build_provider(provider_name: str, model_name: str, cfg: "ARKConfig") -> BaseProvider:
    """プロバイダー名と設定からインスタンスを生成する内部ヘルパー。"""
    if provider_name not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"未登録のプロバイダー名: {provider_name!r}。"
            f" 登録済み: {list(_PROVIDER_REGISTRY.keys())}"
        )

    if provider_name == "ollama":
        provider = OllamaProvider(
            api_endpoint=cfg.api_endpoint,
            model_name=model_name,
        )

    elif provider_name == "mock":
        provider = MockProvider()

    elif provider_name == "gemini":
        provider = GeminiProvider(
            api_key=cfg.gemini_api_key,
            model_name=model_name,
        )

    else:
        raise ValueError(f"未登録のプロバイダー名: {provider_name!r}")

    log.debug("Built provider: %r", provider)
    return provider


def list_providers() -> list[str]:
    """登録済みプロバイダー名の一覧を返す。"""
    return sorted(_PROVIDER_REGISTRY.keys())