"""
ARK (Autonomous Resilient Kernel) - Configuration Loader
=========================================================
Loads and validates ARK runtime configuration from ``config.yaml``
(project root) with optional environment-variable overrides.

Priority (highest → lowest)
---------------------------
1. Environment variables prefixed with ``ARK_``
2. ``config.yaml`` in the project root
3. Hard-coded defaults defined in :class:`ARKConfig`

Usage
-----
::

    from src.core.config import ConfigLoader

    cfg = ConfigLoader.load()
    print(cfg.model_name)
    print(cfg.api_endpoint)
    print(cfg.workspace_path)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional dependency resolution
# ---------------------------------------------------------------------------
# pydantic-settings is preferred; fall back to a lightweight YAML-only loader
# so the project can bootstrap even before dependencies are installed.
try:
    from pydantic import field_validator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYDANTIC_SETTINGS_AVAILABLE = False

try:
    import yaml  # pyyaml

    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


# ---------------------------------------------------------------------------
# Project root helper
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Return the ARK project root (two levels above this file)."""
    return Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Default config file location
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH: Path = _project_root() / "config.yaml"


# ---------------------------------------------------------------------------
# Pydantic-settings backed implementation
# ---------------------------------------------------------------------------

if _PYDANTIC_SETTINGS_AVAILABLE:

    class ARKConfig(BaseSettings):
        """Validated ARK runtime configuration.

        Attributes
        ----------
        model_name:
            Name of the local LLM served by Ollama (or compatible runner).
        api_endpoint:
            Base URL of the local LLM API (e.g. ``http://localhost:11434``).
        workspace_path:
            Absolute path to the AI sandbox workspace directory.
        """

        model_config = SettingsConfigDict(
            env_prefix="ARK_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # --- LLM 基本設定 ---
        model_name: str = "deepseek-coder-v2"
        api_endpoint: str = "http://localhost:11434"
        workspace_path: Path = _project_root() / "workspace"

        # --- エージェントごとのプロバイダー設定 ---
        # 有効な値: "ollama" | "gemini" | "mock"
        # 環境変数: ARK_ARCHITECT_PROVIDER / ARK_CODER_PROVIDER / ARK_REVIEWER_PROVIDER
        architect_provider: str = "ollama"
        coder_provider: str = "ollama"
        reviewer_provider: str = "ollama"

        # --- Gemini 設定 ---
        # 環境変数: ARK_GEMINI_API_KEY / ARK_GEMINI_MODEL_NAME
        gemini_api_key: str = ""
        
        # ロールごとのモデル指定 (Geminiで主に使用)
        # 指定がない場合は gemini_model_name が使われる (factory.py 側の実装に依る)
        architect_model: str = "gemini-1.5-pro"
        coder_model: str = "gemini-1.5-flash"
        reviewer_model: str = "gemini-1.5-flash"

        # 互換性のためのデフォルトモデル名
        gemini_model_name: str = "gemini-1.5-flash"

        @field_validator("workspace_path", mode="before")
        @classmethod
        def _resolve_workspace(cls, v: Any) -> Path:
            return Path(v).resolve()

        @field_validator("api_endpoint", mode="before")
        @classmethod
        def _strip_trailing_slash(cls, v: Any) -> str:
            return str(v).rstrip("/")

    # -----------------------------------------------------------------------
    # ConfigLoader
    # -----------------------------------------------------------------------

    class ConfigLoader:
        """Factory that constructs a validated :class:`ARKConfig`.

        Examples
        --------
        >>> cfg = ConfigLoader.load()
        >>> cfg.model_name
        'deepseek-coder-v2'
        """

        @staticmethod
        def load(config_path: Path | None = None) -> ARKConfig:
            """Load and return an :class:`ARKConfig` instance.

            Parameters
            ----------
            config_path:
                Path to the YAML configuration file.  Defaults to
                ``<project_root>/config.yaml``.

            Returns
            -------
            ARKConfig
                A fully-validated configuration object.
            """
            path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            yaml_values: dict[str, Any] = {}

            if path.is_file():
                if not _YAML_AVAILABLE:
                    import warnings
                    warnings.warn(
                        "pyyaml is not installed; ignoring config.yaml.",
                        stacklevel=2,
                    )
                else:
                    with path.open("r", encoding="utf-8") as fh:
                        yaml_values = yaml.safe_load(fh) or {}

            return ARKConfig(**yaml_values)

        @staticmethod
        def display(cfg: ARKConfig) -> None:
            """Pretty-print configuration to stdout."""
            print("\n⚙️   ARK Configuration")
            print("  ─────────────────────────────────────")
            print(f"  model_name         : {cfg.model_name}")
            print(f"  api_endpoint       : {cfg.api_endpoint}")
            print(f"  workspace_path     : {cfg.workspace_path}")
            print(f"  architect_provider : {cfg.architect_provider}")
            print(f"  coder_provider     : {cfg.coder_provider}")
            print(f"  reviewer_provider  : {cfg.reviewer_provider}")
            print(f"  gemini_model_name  : {cfg.gemini_model_name}")
            print("  ─────────────────────────────────────\n")


# ---------------------------------------------------------------------------
# Lightweight fallback (no pydantic-settings)
# ---------------------------------------------------------------------------

else:  # pragma: no cover

    import dataclasses

    @dataclasses.dataclass
    class ARKConfig:  # type: ignore[no-redef]
        """Minimal ARK configuration (pydantic-settings not available)."""

        # --- LLM 基本設定 ---
        model_name: str = "deepseek-coder-v2"
        api_endpoint: str = "http://localhost:11434"
        workspace_path: Path = dataclasses.field(
            default_factory=lambda: _project_root() / "workspace"
        )

        # --- エージェントごとのプロバイダー設定 ---
        architect_provider: str = "ollama"
        coder_provider: str = "ollama"
        reviewer_provider: str = "ollama"

        # --- Gemini 設定 ---
        gemini_api_key: str = ""
        gemini_model_name: str = "gemini-1.5-flash"
        architect_model: str = "gemini-1.5-pro"
        coder_model: str = "gemini-1.5-flash"
        reviewer_model: str = "gemini-1.5-flash"

        def __post_init__(self) -> None:
            self.workspace_path = Path(self.workspace_path).resolve()
            self.api_endpoint = str(self.api_endpoint).rstrip("/")

    class ConfigLoader:  # type: ignore[no-redef]
        """Fallback ConfigLoader using only pyyaml + env-vars."""

        _ENV_PREFIX = "ARK_"
        _FIELD_MAP: dict[str, str] = {
            "model_name":         "ARK_MODEL_NAME",
            "api_endpoint":       "ARK_API_ENDPOINT",
            "workspace_path":     "ARK_WORKSPACE_PATH",
            "architect_provider": "ARK_ARCHITECT_PROVIDER",
            "coder_provider":     "ARK_CODER_PROVIDER",
            "reviewer_provider":  "ARK_REVIEWER_PROVIDER",
            "gemini_api_key":     "ARK_GEMINI_API_KEY",
            "gemini_model_name":  "ARK_GEMINI_MODEL_NAME",
            "architect_model":    "ARK_ARCHITECT_MODEL",
            "coder_model":        "ARK_CODER_MODEL",
            "reviewer_model":     "ARK_REVIEWER_MODEL",
        }

        @staticmethod
        def load(config_path: Path | None = None) -> ARKConfig:
            path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            values: dict[str, Any] = {}

            if path.is_file() and _YAML_AVAILABLE:
                with path.open("r", encoding="utf-8") as fh:
                    values = yaml.safe_load(fh) or {}

            # env-var overrides
            for field, env_key in ConfigLoader._FIELD_MAP.items():
                env_val = os.environ.get(env_key)
                if env_val is not None:
                    values[field] = env_val

            return ARKConfig(**values)

        @staticmethod
        def display(cfg: ARKConfig) -> None:
            print("\n⚙️   ARK Configuration")
            print("  ─────────────────────────────────────")
            print(f"  model_name         : {cfg.model_name}")
            print(f"  api_endpoint       : {cfg.api_endpoint}")
            print(f"  workspace_path     : {cfg.workspace_path}")
            print(f"  architect_provider : {cfg.architect_provider}")
            print(f"  coder_provider     : {cfg.coder_provider}")
            print(f"  reviewer_provider  : {cfg.reviewer_provider}")
            print(f"  gemini_model_name  : {cfg.gemini_model_name}")
            print("  ─────────────────────────────────────\n")
