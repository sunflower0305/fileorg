"""Scan configuration and result models."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field

from .file_info import FileInfo, DirectoryInfo


class ScanConfig(BaseModel):
    """Scan configuration."""

    target_paths: List[Path]
    recursive: bool = True
    include_hidden: bool = False
    max_depth: Optional[int] = None
    exclude_patterns: List[str] = Field(default_factory=lambda: [
        "__pycache__", ".git", "node_modules", ".venv", "venv",
        ".DS_Store", ".idea", ".vscode"
    ])
    compute_hash: bool = True
    large_file_threshold_mb: float = 100.0
    stale_days_threshold: int = 180


class FileTypeStats(BaseModel):
    """Statistics by file type."""

    extension: str
    count: int
    total_size_bytes: int

    @computed_field
    @property
    def total_size_human(self) -> str:
        """Human-readable total size."""
        size = float(self.total_size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class ScanSummary(BaseModel):
    """Scan summary statistics."""

    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    empty_directories: int = 0
    file_types: List[FileTypeStats] = Field(default_factory=list)
    deepest_depth: int = 0
    scan_duration_seconds: float = 0.0

    @computed_field
    @property
    def total_size_human(self) -> str:
        """Human-readable total size."""
        size = float(self.total_size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class ScanResult(BaseModel):
    """Complete scan result."""

    scan_id: str
    config: ScanConfig
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: ScanSummary = Field(default_factory=ScanSummary)
    files: List[FileInfo] = Field(default_factory=list)
    directories: List[DirectoryInfo] = Field(default_factory=list)

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Check if scan is complete."""
        return self.completed_at is not None
