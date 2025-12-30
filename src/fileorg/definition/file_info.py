"""File and directory information models."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, computed_field


class FileInfo(BaseModel):
    """Single file metadata information."""

    path: Path
    name: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    file_hash: Optional[str] = None  # SHA256, computed on demand

    @computed_field
    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        size = float(self.size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @computed_field
    @property
    def days_since_access(self) -> int:
        """Days since last access."""
        return (datetime.now() - self.accessed_at).days

    @computed_field
    @property
    def days_since_modified(self) -> int:
        """Days since last modification."""
        return (datetime.now() - self.modified_at).days


class DirectoryInfo(BaseModel):
    """Directory information."""

    path: Path
    name: str
    file_count: int = 0
    total_size_bytes: int = 0
    subdirectory_count: int = 0
    depth: int = 0

    @computed_field
    @property
    def is_empty(self) -> bool:
        """Check if directory is empty."""
        return self.file_count == 0 and self.subdirectory_count == 0

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
