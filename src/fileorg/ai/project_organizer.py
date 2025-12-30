"""AI-powered project-based file organizer."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

from ..definition.file_info import FileInfo
from ..definition.scan_result import ScanResult
from .llm_client import get_llm_client
from .prompts import PROJECT_ORGANIZE_SYSTEM, PROJECT_ORGANIZE_PROMPT


class AIProjectOrganizer:
    """Use AI to organize files by project/topic."""

    def __init__(self):
        self.client = get_llm_client()

    async def analyze_and_group(
        self,
        scan_result: ScanResult,
        custom_instruction: str = "",
    ) -> Dict[str, List[Tuple[FileInfo, str]]]:
        """Analyze files and group them by project/topic using AI.

        Args:
            scan_result: The scan result with file metadata.
            custom_instruction: Custom instruction for how to organize files.

        Returns:
            Dict mapping folder names to list of (file, reason) tuples.
        """
        if not scan_result.files:
            return {}

        # Prepare file list for AI
        file_list = "\n".join([
            f"- {f.name} ({f.extension}, {f.size_human})"
            for f in scan_result.files
        ])

        # Build filename to FileInfo mapping
        file_map: Dict[str, FileInfo] = {f.name: f for f in scan_result.files}

        prompt = PROJECT_ORGANIZE_PROMPT.format(file_list=file_list)

        # Add custom instruction if provided
        if custom_instruction:
            prompt = f"用户要求：{custom_instruction}\n\n{prompt}"

        try:
            response = await self.client.chat(
                message=prompt,
                system_prompt=PROJECT_ORGANIZE_SYSTEM,
            )

            # Parse AI response
            groups = self._parse_response(response, file_map)
            return groups

        except Exception as e:
            logger.error(f"AI project organization failed: {e}")
            return {}

    def _parse_response(
        self,
        response: str,
        file_map: Dict[str, FileInfo],
    ) -> Dict[str, List[Tuple[FileInfo, str]]]:
        """Parse AI response into organization groups."""
        try:
            # Extract JSON from response
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            data = json.loads(json_str)

            result: Dict[str, List[Tuple[FileInfo, str]]] = {}

            for group in data.get("groups", []):
                folder = group.get("folder", "Other")
                name = group.get("name", folder)
                reason = group.get("reason", "AI 分组")
                files = group.get("files", [])

                if not files:
                    continue

                result[folder] = []
                for filename in files:
                    # Try exact match first
                    if filename in file_map:
                        result[folder].append((file_map[filename], f"{name}: {reason}"))
                    else:
                        # Try fuzzy match
                        for key, file_info in file_map.items():
                            if filename in key or key in filename:
                                result[folder].append((file_info, f"{name}: {reason}"))
                                break

            # Handle ungrouped files
            ungrouped = data.get("ungrouped", [])
            if ungrouped:
                result["Other"] = []
                for filename in ungrouped:
                    if filename in file_map:
                        result["Other"].append((file_map[filename], "未分类"))

            return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return {}

    def get_organization_plan(
        self,
        groups: Dict[str, List[Tuple[FileInfo, str]]],
        base_path: Path,
    ) -> List[Dict]:
        """Generate organization plan from AI groups.

        Args:
            groups: AI-generated groups.
            base_path: Base path for organized files.

        Returns:
            List of move operations.
        """
        plan = []
        for folder, files in groups.items():
            target_path = base_path / folder
            for file_info, reason in files:
                plan.append({
                    "source": file_info.path,
                    "target": target_path / file_info.name,
                    "reason": reason,
                    "size": file_info.size_bytes,
                })
        return plan
