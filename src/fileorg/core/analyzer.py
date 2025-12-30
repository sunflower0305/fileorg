"""File analyzer for problem detection."""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

from ..definition.file_info import FileInfo, DirectoryInfo
from ..definition.scan_result import ScanResult
from ..definition.analysis import (
    AnalysisResult,
    DuplicateGroup,
    LargeFile,
    StaleFile,
    ChaoticNaming,
    EmptyDirectory,
)
from .hasher import FileHasher


class FileAnalyzer:
    """Analyze scanned files for problems."""

    def __init__(
        self,
        large_threshold_mb: float = 100.0,
        stale_days_threshold: int = 180,
    ):
        self.large_threshold_bytes = int(large_threshold_mb * 1024 * 1024)
        self.stale_days_threshold = stale_days_threshold
        self.hasher = FileHasher()

    async def analyze(
        self,
        scan_result: ScanResult,
        compute_hashes: bool = True,
    ) -> AnalysisResult:
        """Analyze scan result and detect problems.

        Args:
            scan_result: The scan result to analyze.
            compute_hashes: Whether to compute file hashes for duplicate detection.

        Returns:
            AnalysisResult with all detected problems.
        """
        result = AnalysisResult(scan_id=scan_result.scan_id)

        # Detect large files
        result.large_files = self._detect_large_files(scan_result.files)
        logger.debug(f"Detected {len(result.large_files)} large files")

        # Detect stale files
        result.stale_files = self._detect_stale_files(scan_result.files)
        logger.debug(f"Detected {len(result.stale_files)} stale files")

        # Detect chaotic naming
        result.chaotic_naming = self._detect_chaotic_naming(scan_result.files)
        logger.debug(f"Detected {len(result.chaotic_naming)} files with chaotic naming")

        # Detect empty directories
        result.empty_directories = self._detect_empty_directories(scan_result.directories)
        logger.debug(f"Detected {len(result.empty_directories)} empty directories")

        # Detect duplicates (requires hash computation)
        if compute_hashes:
            result.duplicates = await self._detect_duplicates(scan_result.files)
            logger.debug(f"Detected {len(result.duplicates)} duplicate groups")

        return result

    def _detect_large_files(self, files: List[FileInfo]) -> List[LargeFile]:
        """Detect files larger than threshold."""
        large_files = []
        for f in files:
            if f.size_bytes >= self.large_threshold_bytes:
                large_files.append(LargeFile(
                    path=f.path,
                    size_bytes=f.size_bytes,
                    extension=f.extension,
                    modified_at=f.modified_at,
                ))
        return sorted(large_files, key=lambda x: x.size_bytes, reverse=True)

    def _detect_stale_files(self, files: List[FileInfo]) -> List[StaleFile]:
        """Detect files not accessed for a long time."""
        stale_files = []
        for f in files:
            if f.days_since_access >= self.stale_days_threshold:
                stale_files.append(StaleFile(
                    path=f.path,
                    size_bytes=f.size_bytes,
                    last_accessed=f.accessed_at,
                    days_stale=f.days_since_access,
                    extension=f.extension,
                ))
        return sorted(stale_files, key=lambda x: x.days_stale, reverse=True)

    def _detect_chaotic_naming(self, files: List[FileInfo]) -> List[ChaoticNaming]:
        """Detect files with chaotic naming patterns."""
        chaotic = []

        for f in files:
            issues = self._check_naming_issues(f.name)
            if issues:
                chaotic.append(ChaoticNaming(path=f.path, issues=issues))

        return chaotic

    def _check_naming_issues(self, name: str) -> List[str]:
        """Check for naming issues in a file name."""
        issues = []
        name_without_ext = Path(name).stem

        # Check for special characters (excluding common ones)
        if re.search(r'[^\w\s\-_.\(\)\[\]]', name_without_ext):
            issues.append("contains special characters")

        # Check for too long names
        if len(name) > 100:
            issues.append("name too long")

        # Check for meaningless number sequences
        if re.match(r'^[\d_\-\s]+$', name_without_ext):
            issues.append("meaningless number sequence")

        # Check for copy patterns like "file (1)", "file - Copy"
        if re.search(r'\s*[\(\[]?\d+[\)\]]?$', name_without_ext):
            issues.append("copy pattern detected")
        if re.search(r'\s*-?\s*(copy|副本|复制)\s*\d*$', name_without_ext, re.IGNORECASE):
            issues.append("copy pattern detected")

        # Check for temp patterns
        if re.search(r'^(temp|tmp|~)', name_without_ext, re.IGNORECASE):
            issues.append("temporary file pattern")

        return issues

    def _detect_empty_directories(
        self,
        directories: List[DirectoryInfo],
    ) -> List[EmptyDirectory]:
        """Detect empty directories."""
        return [
            EmptyDirectory(path=d.path, depth=d.depth)
            for d in directories
            if d.is_empty
        ]

    async def _detect_duplicates(
        self,
        files: List[FileInfo],
    ) -> List[DuplicateGroup]:
        """Detect duplicate files by hash.

        First groups by size, then computes hashes only for same-size files.
        """
        # Group by size first (optimization)
        size_groups: dict[int, List[FileInfo]] = defaultdict(list)
        for f in files:
            if f.size_bytes > 0:  # Skip empty files
                size_groups[f.size_bytes].append(f)

        # Only compute hashes for files with same size
        duplicates = []
        hash_groups: dict[str, List[Path]] = defaultdict(list)

        for size, same_size_files in size_groups.items():
            if len(same_size_files) < 2:
                continue

            # Compute hashes for potential duplicates
            for f in same_size_files:
                file_hash = await self.hasher.compute_hash(f.path)
                if file_hash:
                    hash_groups[file_hash].append(f.path)

        # Create duplicate groups
        for file_hash, paths in hash_groups.items():
            if len(paths) >= 2:
                # Get size from first file
                size = next(
                    (f.size_bytes for f in files if f.path == paths[0]),
                    0
                )
                duplicates.append(DuplicateGroup(
                    file_hash=file_hash,
                    size_bytes=size,
                    files=paths,
                ))

        return sorted(duplicates, key=lambda x: x.wasted_bytes, reverse=True)


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
