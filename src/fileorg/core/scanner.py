"""Asynchronous file scanner."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional, List
from uuid import uuid4

from loguru import logger

from ..definition.file_info import FileInfo, DirectoryInfo
from ..definition.scan_result import ScanConfig, ScanResult, ScanSummary, FileTypeStats


# Type alias for progress callback
ProgressCallback = Callable[[int, int, str], None]  # (current, total_estimate, current_path)


class FileScanner:
    """Asynchronous file scanner."""

    def __init__(self, config: ScanConfig):
        self.config = config
        self._file_count = 0
        self._dir_count = 0
        self._total_size = 0
        self._deepest_depth = 0
        self._type_stats: dict[str, FileTypeStats] = {}

    def _should_exclude(self, name: str) -> bool:
        """Check if path should be excluded."""
        for pattern in self.config.exclude_patterns:
            if pattern.startswith("*"):
                # Glob pattern like *.pyc
                if name.endswith(pattern[1:]):
                    return True
            else:
                # Direct name match
                if pattern in name:
                    return True
        return False

    def _update_type_stats(self, extension: str, size: int) -> None:
        """Update file type statistics."""
        ext = extension.lower() if extension else "(no ext)"
        if ext not in self._type_stats:
            self._type_stats[ext] = FileTypeStats(
                extension=ext,
                count=0,
                total_size_bytes=0,
            )
        # Create new instance with updated values
        old = self._type_stats[ext]
        self._type_stats[ext] = FileTypeStats(
            extension=ext,
            count=old.count + 1,
            total_size_bytes=old.total_size_bytes + size,
        )

    async def scan_file(self, path: Path) -> Optional[FileInfo]:
        """Scan a single file and return its info."""
        try:
            stat = await asyncio.to_thread(os.stat, path)
            extension = path.suffix.lower()

            return FileInfo(
                path=path,
                name=path.name,
                extension=extension,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                accessed_at=datetime.fromtimestamp(stat.st_atime),
            )
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.warning(f"Cannot access file {path}: {e}")
            return None

    async def scan_directory(
        self,
        path: Path,
        depth: int = 0,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> AsyncGenerator[FileInfo | DirectoryInfo, None]:
        """Recursively scan a directory.

        Yields FileInfo and DirectoryInfo objects as they are found.
        """
        # Check max depth
        if self.config.max_depth is not None and depth > self.config.max_depth:
            return

        # Track deepest depth
        if depth > self._deepest_depth:
            self._deepest_depth = depth

        # Get directory entries
        try:
            entries = await asyncio.to_thread(list, path.iterdir())
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.warning(f"Cannot access directory {path}: {e}")
            return

        file_count = 0
        dir_count = 0
        total_size = 0

        for entry in entries:
            # Skip hidden files if not included
            if not self.config.include_hidden and entry.name.startswith("."):
                continue

            # Skip excluded patterns
            if self._should_exclude(entry.name):
                continue

            if entry.is_file():
                file_info = await self.scan_file(entry)
                if file_info:
                    file_count += 1
                    total_size += file_info.size_bytes
                    self._file_count += 1
                    self._total_size += file_info.size_bytes
                    self._update_type_stats(file_info.extension, file_info.size_bytes)

                    if progress_callback:
                        progress_callback(
                            self._file_count,
                            0,  # Unknown total
                            str(file_info.path),
                        )

                    yield file_info

            elif entry.is_dir() and self.config.recursive:
                dir_count += 1
                self._dir_count += 1

                # Recursively scan subdirectory
                async for item in self.scan_directory(
                    entry,
                    depth + 1,
                    progress_callback,
                ):
                    if isinstance(item, FileInfo):
                        total_size += item.size_bytes
                    yield item

        # Yield directory info after scanning all contents
        dir_info = DirectoryInfo(
            path=path,
            name=path.name,
            file_count=file_count,
            total_size_bytes=total_size,
            subdirectory_count=dir_count,
            depth=depth,
        )
        yield dir_info

    async def scan(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ScanResult:
        """Perform a complete scan and return the result.

        Args:
            progress_callback: Optional callback for progress updates.
                              Receives (current_count, total_estimate, current_path).

        Returns:
            ScanResult with all files and directories.
        """
        scan_id = str(uuid4())[:8]
        started_at = datetime.now()

        files: List[FileInfo] = []
        directories: List[DirectoryInfo] = []

        for target_path in self.config.target_paths:
            if not target_path.exists():
                logger.warning(f"Target path does not exist: {target_path}")
                continue

            if target_path.is_file():
                file_info = await self.scan_file(target_path)
                if file_info:
                    files.append(file_info)
                    self._file_count += 1
                    self._total_size += file_info.size_bytes
                    self._update_type_stats(file_info.extension, file_info.size_bytes)
            else:
                async for item in self.scan_directory(
                    target_path,
                    depth=0,
                    progress_callback=progress_callback,
                ):
                    if isinstance(item, FileInfo):
                        files.append(item)
                    else:
                        directories.append(item)

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Count empty directories
        empty_dirs = sum(1 for d in directories if d.is_empty)

        # Sort type stats by size
        type_stats = sorted(
            self._type_stats.values(),
            key=lambda x: x.total_size_bytes,
            reverse=True,
        )

        summary = ScanSummary(
            total_files=self._file_count,
            total_directories=self._dir_count,
            total_size_bytes=self._total_size,
            empty_directories=empty_dirs,
            file_types=type_stats[:20],  # Top 20 types
            deepest_depth=self._deepest_depth,
            scan_duration_seconds=duration,
        )

        return ScanResult(
            scan_id=scan_id,
            config=self.config,
            started_at=started_at,
            completed_at=completed_at,
            summary=summary,
            files=files,
            directories=directories,
        )


async def quick_scan(
    paths: List[Path],
    include_hidden: bool = False,
    max_depth: Optional[int] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> ScanResult:
    """Convenience function for quick scanning.

    Args:
        paths: List of paths to scan.
        include_hidden: Whether to include hidden files.
        max_depth: Maximum depth to scan.
        progress_callback: Optional progress callback.

    Returns:
        ScanResult with all files and directories.
    """
    config = ScanConfig(
        target_paths=paths,
        include_hidden=include_hidden,
        max_depth=max_depth,
        compute_hash=False,  # Skip hash for quick scan
    )
    scanner = FileScanner(config)
    return await scanner.scan(progress_callback)
