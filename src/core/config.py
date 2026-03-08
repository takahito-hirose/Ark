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
        """Validated ARK runtime configuration."""

        model_config = SettingsConfigDict(
            env_prefix="ARK_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # --- LLM 基本設定 ---
        model_name: str = "qwen2.5-coder:7b"
        api_endpoint: str = "http://localhost:11434"
        workspace_path: Path = _project_root() / "workspace"

        # --- エージェントごとのプロバイダー設定 ---
        # 有効な値: "ollama" | "gemini" | "mock"
        architect_provider: str = "ollama"
        coder_provider: str = "ollama"
        reviewer_provider: str = "ollama"
        reflector_provider: str = "ollama"  # 👈 New!

        # --- モデル指定 (Ollama/General) ---
        architect_model: str = "gemma3:4b"
        coder_model: str = "qwen2.5-coder:7b"
        reviewer_model: str = "llama3.2:3b"
        reflector_model: str = "llama3.2:3b"  # 👈 New!

        # --- Gemini 設定 ---
        gemini_api_key: str = ""
        gemini_model_name: str = "gemini-2.0-flash"
        
        # ロールごとのGeminiモデル指定
        architect_model_gemini: str = "gemini-2.0-flash"  # 👈 Updated to 2.0
        coder_model_gemini: str = "gemini-2.0-flash"
        reviewer_model_gemini: str = "gemini-2.0-flash"
        reflector_model_gemini: str = "gemini-2.0-flash" # 👈 New!

        @field_validator("workspace_path", mode="before")
        @classmethod
        def _resolve_workspace(cls, v: Any) -> Path:
            return Path(v).resolve()

        @field_validator("api_endpoint", mode="before")
        @classmethod
        def _strip_trailing_slash(cls, v: Any) -> str:
            return str(v).rstrip("/")

    class ConfigLoader:
        """Factory that constructs a validated :class:`ARKConfig`."""

        @staticmethod
        def load(config_path: Path | None = None) -> ARKConfig:
            path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            yaml_values: dict[str, Any] = {}

            if path.is_file():
                if not _YAML_AVAILABLE:
                    import warnings
                    warnings.warn("pyyaml is not installed; ignoring config.yaml.", stacklevel=2)
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
            print(f"  workspace_path     : {cfg.workspace_path}")
            print(f"  architect_provider : {cfg.architect_provider} ({cfg.architect_model})")
            print(f"  coder_provider     : {cfg.coder_provider} ({cfg.coder_model})")
            print(f"  reviewer_provider  : {cfg.reviewer_provider} ({cfg.reviewer_model})")
            print(f"  reflector_provider : {cfg.reflector_provider} ({cfg.reflector_model})")
            print("  ─────────────────────────────────────\n")


# ---------------------------------------------------------------------------
# Lightweight fallback (no pydantic-settings)
# ---------------------------------------------------------------------------

else:  # pragma: no cover

    import dataclasses

    @dataclasses.dataclass
    class ARKConfig:  # type: ignore[no-redef]
        """Minimal ARK configuration (pydantic-settings not available)."""

        model_name: str = "qwen2.5-coder:7b"
        api_endpoint: str = "http://localhost:11434"
        workspace_path: Path = dataclasses.field(
            default_factory=lambda: _project_root() / "workspace"
        )

        architect_provider: str = "ollama"
        coder_provider: str = "ollama"
        reviewer_provider: str = "ollama"
        reflector_provider: str = "ollama"

        architect_model: str = "gemma3:4b"
        coder_model: str = "qwen2.5-coder:7b"
        reviewer_model: str = "llama3.2:3b"
        reflector_model: str = "llama3.2:3b"

        gemini_api_key: str = ""
        gemini_model_name: str = "gemini-2.0-flash"
        architect_model_gemini: str = "gemini-2.0-flash"
        coder_model_gemini: str = "gemini-2.0-flash"
        reviewer_model_gemini: str = "gemini-2.0-flash"
        reflector_model_gemini: str = "gemini-2.0-flash"

        def __post_init__(self) -> None:
            self.workspace_path = Path(self.workspace_path).resolve()
            self.api_endpoint = str(self.api_endpoint).rstrip("/")

    class ConfigLoader:  # type: ignore[no-redef]
        """Fallback ConfigLoader using only pyyaml + env-vars."""

        _FIELD_MAP: dict[str, str] = {
            "model_name":         "ARK_MODEL_NAME",
            "api_endpoint":       "ARK_API_ENDPOINT",
            "workspace_path":     "ARK_WORKSPACE_PATH",
            "architect_provider": "ARK_ARCHITECT_PROVIDER",
            "coder_provider":     "ARK_CODER_PROVIDER",
            "reviewer_provider":  "ARK_REVIEWER_PROVIDER",
            "reflector_provider": "ARK_REFLECTOR_PROVIDER",
            "architect_model":    "ARK_ARCHITECT_MODEL",
            "coder_model":        "ARK_CODER_MODEL",
            "reviewer_model":     "ARK_REVIEWER_MODEL",
            "reflector_model":    "ARK_REFLECTOR_MODEL",
            "gemini_api_key":     "ARK_GEMINI_API_KEY",
            "gemini_model_name":  "ARK_GEMINI_MODEL_NAME",
            "architect_model_gemini": "ARK_ARCHITECT_MODEL_GEMINI",
            "coder_model_gemini":     "ARK_CODER_MODEL_GEMINI",
            "reviewer_model_gemini":  "ARK_REVIEWER_MODEL_GEMINI",
            "reflector_model_gemini": "ARK_REFLECTOR_MODEL_GEMINI",
        }

        @staticmethod
        def load(config_path: Path | None = None) -> ARKConfig:
            path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            values: dict[str, Any] = {}

            if path.is_file() and _YAML_AVAILABLE:
                with path.open("r", encoding="utf-8") as fh:
                    values = yaml.safe_load(fh) or {}

            for field, env_key in ConfigLoader._FIELD_MAP.items():
                env_val = os.environ.get(env_key)
                if env_val is not None:
                    values[field] = env_val

            return ARKConfig(**values)

        @staticmethod
        def display(cfg: ARKConfig) -> None:
            print("\n⚙️   ARK Configuration (Fallback)")
            print("  ─────────────────────────────────────")
            print(f"  model_name         : {cfg.model_name}")
            print(f"  architect_provider : {cfg.architect_provider} ({cfg.architect_model})")
            print(f"  coder_provider     : {cfg.coder_provider} ({cfg.coder_model})")
            print(f"  reviewer_provider  : {cfg.reviewer_provider} ({cfg.reviewer_model})")
            print(f"  reflector_provider : {cfg.reflector_provider} ({cfg.reflector_model})")
            print("  ─────────────────────────────────────\n")