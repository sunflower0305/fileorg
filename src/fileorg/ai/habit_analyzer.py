"""AI-powered habit analyzer."""

import json
import re
from collections import Counter
from datetime import datetime
from typing import Optional

from loguru import logger

from ..definition.scan_result import ScanResult
from ..definition.analysis import AnalysisResult
from ..definition.suggestion import (
    AIAnalysis,
    WorkPattern,
    FileHabit,
    PersonalityInsight,
    Suggestion,
)
from .llm_client import get_llm_client
from .prompts import HABIT_ANALYSIS_SYSTEM, HABIT_ANALYSIS_PROMPT


class HabitAnalyzer:
    """Analyze user file habits using AI."""

    def __init__(self):
        self.client = get_llm_client()

    async def analyze(
        self,
        scan_result: ScanResult,
        analysis_result: AnalysisResult,
    ) -> AIAnalysis:
        """Analyze file habits and generate insights.

        Args:
            scan_result: The scan result with file metadata.
            analysis_result: The analysis result with detected issues.

        Returns:
            AIAnalysis with work patterns, habits, and suggestions.
        """
        # Prepare data for the prompt
        prompt_data = self._prepare_prompt_data(scan_result, analysis_result)

        # Format the prompt
        prompt = HABIT_ANALYSIS_PROMPT.format(**prompt_data)

        try:
            # Call LLM
            response = await self.client.chat(
                message=prompt,
                system_prompt=HABIT_ANALYSIS_SYSTEM,
            )

            # Parse response
            ai_analysis = self._parse_response(response)
            return ai_analysis

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Return default analysis
            return self._create_default_analysis(scan_result, analysis_result)

    def _prepare_prompt_data(
        self,
        scan_result: ScanResult,
        analysis_result: AnalysisResult,
    ) -> dict:
        """Prepare data for the prompt."""
        # Format file types
        file_types_str = "\n".join([
            f"- {ft.extension}: {ft.count} files, {ft.total_size_human}"
            for ft in scan_result.summary.file_types[:10]
        ])

        # Calculate modification time distribution
        mod_stats = self._calculate_modification_stats(scan_result)

        # Calculate wasted space
        wasted = self._format_size(analysis_result.total_wasted_by_duplicates)

        return {
            "total_files": scan_result.summary.total_files,
            "total_directories": scan_result.summary.total_directories,
            "total_size": scan_result.summary.total_size_human,
            "empty_directories": scan_result.summary.empty_directories,
            "scan_duration": f"{scan_result.summary.scan_duration_seconds:.1f}",
            "file_types": file_types_str or "No file types detected",
            "duplicate_count": len(analysis_result.duplicates),
            "duplicate_wasted": wasted,
            "large_file_count": len(analysis_result.large_files),
            "stale_file_count": len(analysis_result.stale_files),
            "empty_dir_count": len(analysis_result.empty_directories),
            "modification_stats": mod_stats,
        }

    def _calculate_modification_stats(self, scan_result: ScanResult) -> str:
        """Calculate file modification time statistics."""
        if not scan_result.files:
            return "No files to analyze"

        # Count by hour
        hour_counts = Counter()
        day_counts = Counter()

        for f in scan_result.files:
            hour_counts[f.modified_at.hour] += 1
            day_counts[f.modified_at.strftime("%A")] += 1

        # Format top hours
        top_hours = hour_counts.most_common(5)
        hours_str = ", ".join([f"{h}:00 ({c} files)" for h, c in top_hours])

        # Format top days
        top_days = day_counts.most_common(3)
        days_str = ", ".join([f"{d} ({c} files)" for d, c in top_days])

        return f"Peak hours: {hours_str}\nPeak days: {days_str}"

    def _parse_response(self, response: str) -> AIAnalysis:
        """Parse LLM response into AIAnalysis."""
        try:
            # Extract JSON from response
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_str = response

            data = json.loads(json_str)

            # Parse work pattern
            wp_data = data.get("work_pattern", {})
            work_pattern = WorkPattern(
                peak_hours=wp_data.get("peak_hours", []),
                peak_days=wp_data.get("peak_days", []),
                activity_description=wp_data.get("activity_description", ""),
            )

            # Parse file habit
            fh_data = data.get("file_habit", {})
            file_habit = FileHabit(
                most_used_types=fh_data.get("most_used_types", []),
                frequent_locations=fh_data.get("frequent_locations", []),
                naming_style=fh_data.get("naming_style", ""),
                organization_score=fh_data.get("organization_score", 50),
            )

            # Parse personality insight
            pi_data = data.get("personality_insight", {})
            personality_insight = PersonalityInsight(
                chaos_level=pi_data.get("chaos_level", "medium"),
                strengths=pi_data.get("strengths", []),
                challenges=pi_data.get("challenges", []),
            )

            # Parse suggestions
            suggestions = []
            for s in data.get("suggestions", []):
                suggestions.append(Suggestion(
                    priority=s.get("priority", "medium"),
                    category=s.get("category", "organize"),
                    title=s.get("title", ""),
                    description=s.get("description", ""),
                    estimated_benefit=s.get("estimated_benefit", ""),
                ))

            return AIAnalysis(
                work_pattern=work_pattern,
                file_habit=file_habit,
                personality_insight=personality_insight,
                suggestions=suggestions,
                summary=data.get("summary", ""),
                encouragement=data.get("encouragement", ""),
                gains=data.get("gains", ""),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            # Return default with raw response as summary
            return AIAnalysis(summary=response[:500] if response else "Analysis failed")

    def _create_default_analysis(
        self,
        scan_result: ScanResult,
        analysis_result: AnalysisResult,
    ) -> AIAnalysis:
        """Create a default analysis when AI fails."""
        suggestions = []

        if analysis_result.duplicates:
            wasted = self._format_size(analysis_result.total_wasted_by_duplicates)
            suggestions.append(Suggestion(
                priority="high",
                category="cleanup",
                title="Clean up duplicate files",
                description=f"Found {len(analysis_result.duplicates)} groups of duplicate files.",
                estimated_benefit=f"Can free up {wasted}",
            ))

        if analysis_result.large_files:
            suggestions.append(Suggestion(
                priority="medium",
                category="cleanup",
                title="Review large files",
                description=f"Found {len(analysis_result.large_files)} large files (>100MB).",
                estimated_benefit="Free up significant space",
            ))

        if analysis_result.stale_files:
            suggestions.append(Suggestion(
                priority="low",
                category="organize",
                title="Archive stale files",
                description=f"Found {len(analysis_result.stale_files)} files not accessed in 180+ days.",
                estimated_benefit="Reduce clutter",
            ))

        return AIAnalysis(
            suggestions=suggestions,
            summary="Basic analysis completed. Enable AI for personalized insights.",
            encouragement="Every step towards organization is a win!",
            gains="A cleaner workspace leads to clearer thinking.",
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
