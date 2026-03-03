"""
ARK (Autonomous Resilient Kernel) — Provider Factory
=====================================================
エージェントロール（architect / coder / reviewer）に対応する
:class:`~src.core.providers.BaseProvider` インスタンスを生成するファクトリー。

設定値の優先順位は :class:`~src.core.config.ARKConfig` に従う:

1. 環境変数 ``ARK_ARCHITECT_PROVIDER`` 等
2. ``config.yaml``
3. デフォルト値 ``"ollama"``

Usage
-----
::

    from src.core.config import ConfigLoader
    from src.core.factory import get_provider

    cfg = ConfigLoader.load()

    architect_provider = get_provider("architect", cfg)
    coder_provider     = get_provider("coder",     cfg)
    reviewer_provider  = get_provider("reviewer",   cfg)

    response = architect_provider.generate("設計を考えよ")
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

def get_provider(role: str, cfg: "ARKConfig") -> BaseProvider:
    """エージェントロールに対応する :class:`BaseProvider` インスタンスを返す。

    Parameters
    ----------
    role:
        エージェントのロール名。
        ``"architect"`` / ``"coder"`` / ``"reviewer"`` のいずれか。
    cfg:
        :class:`~src.core.config.ARKConfig` のインスタンス。
        ``architect_provider``, ``coder_provider``, ``reviewer_provider``
        フィールドを参照してプロバイダー名を決定する。

    Returns
    -------
    BaseProvider
        指定されたロールに対応するプロバイダーインスタンス。

    Raises
    ------
    ValueError
        ``role`` が未知のロール名の場合、または
        設定に未登録のプロバイダー名が指定されている場合。

    Examples
    --------
    >>> from src.core.config import ConfigLoader
    >>> from src.core.factory import get_provider
    >>> cfg = ConfigLoader.load()
    >>> provider = get_provider("architect", cfg)
    >>> isinstance(provider, BaseProvider)
    True
    """
    # ---- ロールからプロバイダー名を解決 ------------------------------------
    role_lower = role.lower().strip()

    role_to_attr: dict[str, str] = {
        "architect": "architect_provider",
        "coder":     "coder_provider",
        "reviewer":  "reviewer_provider",
    }

    if role_lower not in role_to_attr:
        raise ValueError(
            f"未知のロール名: {role!r}。"
            f" 有効なロール: {list(role_to_attr.keys())}"
        )

    provider_name: str = getattr(cfg, role_to_attr[role_lower], "ollama").lower().strip()

    # ---- ロールからモデル名を解決 ------------------------------------------
    role_to_model: dict[str, str] = {
        "architect": "architect_model",
        "coder":     "coder_model",
        "reviewer":  "reviewer_model",
    }
    model_name: str = getattr(cfg, role_to_model[role_lower], cfg.model_name)

    log.info("Role %r → provider %r (model=%s)", role, provider_name, model_name)

    # ---- プロバイダー名からインスタンスを生成 --------------------------------
    return _build_provider(provider_name, model_name, cfg)


def _build_provider(provider_name: str, model_name: str, cfg: "ARKConfig") -> BaseProvider:
    """プロバイダー名と設定からインスタンスを生成する内部ヘルパー。

    Parameters
    ----------
    provider_name:
        ``"ollama"`` / ``"mock"`` / ``"gemini"`` のいずれか。
    model_name:
        使用するモデル名。
    cfg:
        ARK設定オブジェクト。

    Returns
    -------
    BaseProvider
        生成されたプロバイダーインスタンス。

    Raises
    ------
    ValueError
        `provider_name` が未登録の場合。
    """
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
        # _PROVIDER_REGISTRY のチェックで到達しないが型安全のために残す
        raise ValueError(f"未登録のプロバイダー名: {provider_name!r}")  # pragma: no cover

    log.debug("Built provider: %r", provider)
    return provider


# ---------------------------------------------------------------------------
# Utility: list available providers
# ---------------------------------------------------------------------------

def list_providers() -> list[str]:
    """登録済みプロバイダー名の一覧を返す。

    Returns
    -------
    list[str]
        例: ``["ollama", "mock", "gemini"]``
    """
    return sorted(_PROVIDER_REGISTRY.keys())
