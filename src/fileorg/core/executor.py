"""Safe file operation executor with confirmation."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger


class OperationLog:
    """Log of file operations for potential rollback."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.operations: List[Dict[str, Any]] = []

    def log_move(self, source: Path, target: Path) -> None:
        """Log a move operation."""
        self.operations.append({
            "type": "move",
            "source": str(source),
            "target": str(target),
            "timestamp": datetime.now().isoformat(),
        })
        self._write_log()

    def log_delete(self, path: Path, backup_path: Optional[Path] = None) -> None:
        """Log a delete operation."""
        self.operations.append({
            "type": "delete",
            "path": str(path),
            "backup": str(backup_path) if backup_path else None,
            "timestamp": datetime.now().isoformat(),
        })
        self._write_log()

    def _write_log(self) -> None:
        """Write operations to log file."""
        import json
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.operations, f, indent=2, ensure_ascii=False)


class FileExecutor:
    """Execute file operations safely."""

    def __init__(
        self,
        dry_run: bool = True,
        backup_dir: Optional[Path] = None,
        log_path: Optional[Path] = None,
    ):
        self.dry_run = dry_run
        self.backup_dir = backup_dir or Path("./data/backup")
        self.log = OperationLog(log_path or Path("./data/operations.log"))

    def move_file(self, source: Path, target: Path) -> bool:
        """Move a file to target location.

        Args:
            source: Source file path.
            target: Target file path.

        Returns:
            True if successful (or dry run), False otherwise.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would move: {source} -> {target}")
            return True

        try:
            # Create target directory
            target.parent.mkdir(parents=True, exist_ok=True)

            # Handle name conflicts
            final_target = self._resolve_conflict(target)

            # Move file
            shutil.move(str(source), str(final_target))
            self.log.log_move(source, final_target)
            logger.info(f"Moved: {source} -> {final_target}")
            return True

        except Exception as e:
            logger.error(f"Failed to move {source}: {e}")
            return False

    def delete_file(self, path: Path, backup: bool = True) -> bool:
        """Delete a file, optionally backing up first.

        Args:
            path: File path to delete.
            backup: Whether to backup before deleting.

        Returns:
            True if successful (or dry run), False otherwise.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: {path}")
            return True

        try:
            backup_path = None
            if backup:
                backup_path = self._backup_file(path)

            path.unlink()
            self.log.log_delete(path, backup_path)
            logger.info(f"Deleted: {path}" + (f" (backed up to {backup_path})" if backup_path else ""))
            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False

    def delete_directory(self, path: Path) -> bool:
        """Delete an empty directory.

        Args:
            path: Directory path to delete.

        Returns:
            True if successful (or dry run), False otherwise.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete directory: {path}")
            return True

        try:
            path.rmdir()
            logger.info(f"Deleted directory: {path}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete directory {path}: {e}")
            return False

    def execute_organization_plan(
        self,
        plan: List[Dict],
        confirm_each: bool = False,
    ) -> Dict[str, int]:
        """Execute an organization plan.

        Args:
            plan: List of move operations from SmartOrganizer.
            confirm_each: Whether to confirm each operation.

        Returns:
            Stats dict with success/failure counts.
        """
        stats = {"success": 0, "failed": 0, "skipped": 0}

        for op in plan:
            source = Path(op["source"])
            target = Path(op["target"])

            if confirm_each:
                from rich.prompt import Confirm
                if not Confirm.ask(f"Move {source.name} to {target.parent}?"):
                    stats["skipped"] += 1
                    continue

            if self.move_file(source, target):
                stats["success"] += 1
            else:
                stats["failed"] += 1

        return stats

    def _resolve_conflict(self, target: Path) -> Path:
        """Resolve naming conflict by adding suffix."""
        if not target.exists():
            return target

        base = target.stem
        ext = target.suffix
        parent = target.parent
        counter = 1

        while True:
            new_name = f"{base}_{counter}{ext}"
            new_target = parent / new_name
            if not new_target.exists():
                return new_target
            counter += 1

    def _backup_file(self, path: Path) -> Path:
        """Backup a file before deletion."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_{timestamp}{path.suffix}"
        backup_path = self.backup_dir / backup_name

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(backup_path))

        return backup_path
