"""Application settings using pydantic-settings."""

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = ""
    model: str = "qwen-plus"
    timeout: float = 60.0
    temperature: float = 0.7


class ScanSettings(BaseSettings):
    """Scan configuration."""

    model_config = SettingsConfigDict(env_prefix="")

    large_file_threshold_mb: float = Field(default=100.0, alias="LARGE_FILE_THRESHOLD_MB")
    stale_days_threshold: int = Field(default=180, alias="STALE_DAYS_THRESHOLD")
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".DS_Store", ".idea", ".vscode", "*.pyc"
    ])
    max_files_for_hash: int = 10000


class OperationSettings(BaseSettings):
    """Operation configuration."""

    dry_run: bool = True
    require_confirmation: bool = True
    backup_before_delete: bool = True


class AppSettings(BaseSettings):
    """Application global settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    scan: ScanSettings = Field(default_factory=ScanSettings)
    operation: OperationSettings = Field(default_factory=OperationSettings)

    # Paths
    data_dir: Path = Path("./data")
    log_level: str = "INFO"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "fileorg.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"


# Global settings instance
settings = AppSettings()
