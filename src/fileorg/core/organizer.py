"""Smart file organizer - groups files based on user habits."""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from ..definition.file_info import FileInfo
from ..definition.scan_result import ScanResult


class OrganizationRule:
    """A rule for organizing files."""

    def __init__(
        self,
        name: str,
        description: str,
        target_folder: str,
        match_func,
    ):
        self.name = name
        self.description = description
        self.target_folder = target_folder
        self.match_func = match_func


class SmartOrganizer:
    """Smart file organizer that learns from user habits."""

    # Default organization rules by file type
    TYPE_FOLDERS = {
        # Documents
        ".pdf": "Documents/PDFs",
        ".doc": "Documents/Word",
        ".docx": "Documents/Word",
        ".txt": "Documents/Text",
        ".md": "Documents/Markdown",
        ".rtf": "Documents/Text",
        # Spreadsheets
        ".xls": "Documents/Spreadsheets",
        ".xlsx": "Documents/Spreadsheets",
        ".csv": "Documents/Spreadsheets",
        # Presentations
        ".ppt": "Documents/Presentations",
        ".pptx": "Documents/Presentations",
        # Images
        ".jpg": "Images",
        ".jpeg": "Images",
        ".png": "Images",
        ".gif": "Images",
        ".bmp": "Images",
        ".svg": "Images",
        ".webp": "Images",
        # Screenshots
        ".screenshot": "Images/Screenshots",
        # Videos
        ".mp4": "Videos",
        ".avi": "Videos",
        ".mkv": "Videos",
        ".mov": "Videos",
        ".wmv": "Videos",
        ".webm": "Videos",
        # Audio
        ".mp3": "Audio",
        ".wav": "Audio",
        ".flac": "Audio",
        ".aac": "Audio",
        ".m4a": "Audio",
        # Archives
        ".zip": "Archives",
        ".rar": "Archives",
        ".7z": "Archives",
        ".tar": "Archives",
        ".gz": "Archives",
        # Code
        ".py": "Code/Python",
        ".js": "Code/JavaScript",
        ".ts": "Code/TypeScript",
        ".java": "Code/Java",
        ".cpp": "Code/C++",
        ".c": "Code/C",
        ".go": "Code/Go",
        ".rs": "Code/Rust",
        ".html": "Code/Web",
        ".css": "Code/Web",
        # Executables
        ".exe": "Programs",
        ".msi": "Programs",
        ".dmg": "Programs",
        ".app": "Programs",
        # Data
        ".json": "Data",
        ".xml": "Data",
        ".yaml": "Data",
        ".yml": "Data",
    }

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self.custom_rules: List[OrganizationRule] = []
        self._learned_patterns: Dict[str, str] = {}

    def analyze_and_suggest(
        self,
        scan_result: ScanResult,
    ) -> Dict[str, List[Tuple[FileInfo, str]]]:
        """Analyze files and suggest organization.

        Args:
            scan_result: The scan result with file metadata.

        Returns:
            Dict mapping target folders to list of (file, reason) tuples.
        """
        suggestions: Dict[str, List[Tuple[FileInfo, str]]] = defaultdict(list)

        # Learn patterns from existing file structure
        self._learn_patterns(scan_result)

        for file in scan_result.files:
            target, reason = self._suggest_folder(file)
            if target:
                suggestions[target].append((file, reason))

        return dict(suggestions)

    def _learn_patterns(self, scan_result: ScanResult) -> None:
        """Learn organization patterns from existing structure."""
        # Learn from project-like directories
        project_indicators = [
            "package.json", "pyproject.toml", "Cargo.toml",
            "pom.xml", "build.gradle", ".git",
        ]

        for directory in scan_result.directories:
            dir_path = directory.path
            # Check if this looks like a project directory
            for indicator in project_indicators:
                if (dir_path / indicator).exists():
                    # This is a project directory
                    project_name = dir_path.name
                    self._learned_patterns[project_name] = str(dir_path)
                    break

    def _suggest_folder(self, file: FileInfo) -> Tuple[Optional[str], str]:
        """Suggest a target folder for a file.

        Returns:
            Tuple of (target_folder, reason) or (None, "") if no suggestion.
        """
        # Strategy 1: Match by project name in filename
        for project_name, project_path in self._learned_patterns.items():
            if project_name.lower() in file.name.lower():
                return f"Projects/{project_name}", f"Matches project '{project_name}'"

        # Strategy 2: Match by date pattern in filename
        date_match = self._extract_date_pattern(file.name)
        if date_match:
            year, month = date_match
            return f"Archives/{year}/{month:02d}", f"Date pattern detected: {year}-{month:02d}"

        # Strategy 3: Match by file type
        if file.extension in self.TYPE_FOLDERS:
            return self.TYPE_FOLDERS[file.extension], f"File type: {file.extension}"

        # Strategy 4: Screenshots detection
        if self._is_screenshot(file):
            date_str = file.created_at.strftime("%Y-%m")
            return f"Images/Screenshots/{date_str}", "Screenshot detected"

        # Strategy 5: Downloads cleanup
        if "download" in str(file.path.parent).lower():
            if file.days_since_access > 30:
                return "Archives/Old Downloads", "Old download (>30 days)"

        return None, ""

    def _extract_date_pattern(self, filename: str) -> Optional[Tuple[int, int]]:
        """Extract date pattern from filename.

        Returns:
            Tuple of (year, month) if found, None otherwise.
        """
        # Pattern: 2024-01-15, 20240115, 2024_01_15
        patterns = [
            r"(20\d{2})[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])",
            r"(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])",
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                return (year, month)

        return None

    def _is_screenshot(self, file: FileInfo) -> bool:
        """Check if file is likely a screenshot."""
        name_lower = file.name.lower()
        screenshot_patterns = [
            "screenshot", "screen shot", "capture",
            "snip", "截图", "屏幕截图",
        ]
        if any(p in name_lower for p in screenshot_patterns):
            return True

        # macOS/Windows screenshot patterns
        if re.match(r"screen\s*shot.*\d{4}", name_lower):
            return True
        if re.match(r"截屏\d{4}", name_lower):
            return True

        return False

    def get_organization_plan(
        self,
        scan_result: ScanResult,
        target_base: Optional[Path] = None,
    ) -> List[Dict]:
        """Generate a complete organization plan.

        Args:
            scan_result: The scan result.
            target_base: Base path for organized files.

        Returns:
            List of move operations.
        """
        suggestions = self.analyze_and_suggest(scan_result)
        base = target_base or self.base_path

        plan = []
        for target_folder, files in suggestions.items():
            target_path = base / target_folder
            for file, reason in files:
                plan.append({
                    "source": file.path,
                    "target": target_path / file.name,
                    "reason": reason,
                    "size": file.size_bytes,
                })

        return plan

    def print_organization_summary(
        self,
        scan_result: ScanResult,
    ) -> str:
        """Generate a human-readable organization summary."""
        suggestions = self.analyze_and_suggest(scan_result)

        lines = ["# Organization Plan\n"]

        total_files = 0
        for target_folder, files in sorted(suggestions.items()):
            lines.append(f"\n## {target_folder}")
            lines.append(f"*{len(files)} files*\n")

            for file, reason in files[:5]:
                lines.append(f"- `{file.name}` ({reason})")

            if len(files) > 5:
                lines.append(f"- ... and {len(files) - 5} more")

            total_files += len(files)

        lines.insert(1, f"\nTotal: {total_files} files to organize into {len(suggestions)} folders\n")

        return "\n".join(lines)
