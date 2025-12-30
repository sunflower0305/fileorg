"""File hash computation."""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict

from loguru import logger


class FileHasher:
    """Compute file hashes with caching support."""

    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self._cache: Dict[str, str] = {}  # path -> hash

    async def compute_hash(self, path: Path) -> Optional[str]:
        """Compute SHA256 hash of a file.

        Args:
            path: Path to the file.

        Returns:
            SHA256 hash as hex string, or None if failed.
        """
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            file_hash = await asyncio.to_thread(self._compute_hash_sync, path)
            if file_hash:
                self._cache[cache_key] = file_hash
            return file_hash
        except Exception as e:
            logger.warning(f"Failed to compute hash for {path}: {e}")
            return None

    def _compute_hash_sync(self, path: Path) -> Optional[str]:
        """Synchronous hash computation."""
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(self.chunk_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.warning(f"Cannot read file {path}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the hash cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Return the number of cached hashes."""
        return len(self._cache)


async def compute_file_hash(path: Path) -> Optional[str]:
    """Convenience function to compute hash for a single file."""
    hasher = FileHasher()
    return await hasher.compute_hash(path)
