"""Analysis result models for problem detection."""

from datetime import datetime
from pathlib import Path
from typing import List, Literal
from pydantic import BaseModel, Field, computed_field


class DuplicateGroup(BaseModel):
    """Group of duplicate files."""

    file_hash: str
    size_bytes: int
    files: List[Path]

    @computed_field
    @property
    def count(self) -> int:
        """Number of duplicate files."""
        return len(self.files)

    @computed_field
    @property
    def wasted_bytes(self) -> int:
        """Wasted bytes = (count - 1) * size."""
        return (self.count - 1) * self.size_bytes

    @computed_field
    @property
    def wasted_human(self) -> str:
        """Human-readable wasted space."""
        size = float(self.wasted_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class LargeFile(BaseModel):
    """Large file detected."""

    path: Path
    size_bytes: int
    extension: str
    modified_at: datetime

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


class StaleFile(BaseModel):
    """File that hasn't been accessed for a long time."""

    path: Path
    size_bytes: int
    last_accessed: datetime
    days_stale: int
    extension: str

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


class ChaoticNaming(BaseModel):
    """File with chaotic naming."""

    path: Path
    issues: List[str]  # ["contains special chars", "too long", "meaningless numbers"]


class EmptyDirectory(BaseModel):
    """Empty directory."""

    path: Path
    depth: int


IssueType = Literal["duplicate", "large_file", "stale", "chaotic_naming", "empty_dir"]


class AnalysisResult(BaseModel):
    """Complete analysis result."""

    scan_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # Problem detection results
    duplicates: List[DuplicateGroup] = Field(default_factory=list)
    large_files: List[LargeFile] = Field(default_factory=list)
    stale_files: List[StaleFile] = Field(default_factory=list)
    chaotic_naming: List[ChaoticNaming] = Field(default_factory=list)
    empty_directories: List[EmptyDirectory] = Field(default_factory=list)

    @computed_field
    @property
    def total_wasted_by_duplicates(self) -> int:
        """Total bytes wasted by duplicates."""
        return sum(d.wasted_bytes for d in self.duplicates)

    @computed_field
    @property
    def total_large_files_size(self) -> int:
        """Total size of large files."""
        return sum(f.size_bytes for f in self.large_files)

    @computed_field
    @property
    def total_stale_files_size(self) -> int:
        """Total size of stale files."""
        return sum(f.size_bytes for f in self.stale_files)

    @computed_field
    @property
    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return any([
            self.duplicates,
            self.large_files,
            self.stale_files,
            self.chaotic_naming,
            self.empty_directories
        ])

    @computed_field
    @property
    def issue_summary(self) -> dict[str, int]:
        """Summary of issues by type."""
        return {
            "duplicates": len(self.duplicates),
            "large_files": len(self.large_files),
            "stale_files": len(self.stale_files),
            "chaotic_naming": len(self.chaotic_naming),
            "empty_directories": len(self.empty_directories),
        }
