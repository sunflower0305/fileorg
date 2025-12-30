"""AI analysis and suggestion models."""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class WorkPattern(BaseModel):
    """Work pattern analysis."""

    peak_hours: List[int] = Field(default_factory=list)  # [22, 23, 0, 1] for night owl
    peak_days: List[str] = Field(default_factory=list)  # ["Saturday", "Sunday"]
    activity_description: str = ""  # "You're a night owl, often modifying files late at night"


class FileHabit(BaseModel):
    """File usage habits."""

    most_used_types: List[str] = Field(default_factory=list)  # [".pdf", ".docx", ".py"]
    frequent_locations: List[str] = Field(default_factory=list)  # Common directories
    naming_style: str = ""  # "Prefer date prefix" / "Project name + version"
    organization_score: int = Field(default=50, ge=0, le=100)  # Organization score


class PersonalityInsight(BaseModel):
    """P-type personality insight."""

    chaos_level: Literal["low", "medium", "high", "extreme"] = "medium"
    strengths: List[str] = Field(default_factory=list)  # ["Creative", "Flexible"]
    challenges: List[str] = Field(default_factory=list)  # ["Files pile up", "Forget temp files"]


class Suggestion(BaseModel):
    """Single suggestion."""

    priority: Literal["high", "medium", "low"] = "medium"
    category: str = ""  # "cleanup", "organize", "backup", "naming"
    title: str = ""
    description: str = ""
    action_command: Optional[str] = None  # Executable command
    estimated_benefit: str = ""  # "Can free up 2.3GB of space"


class AIAnalysis(BaseModel):
    """Complete AI analysis result."""

    analyzed_at: datetime = Field(default_factory=datetime.now)
    work_pattern: WorkPattern = Field(default_factory=WorkPattern)
    file_habit: FileHabit = Field(default_factory=FileHabit)
    personality_insight: PersonalityInsight = Field(default_factory=PersonalityInsight)
    suggestions: List[Suggestion] = Field(default_factory=list)
    summary: str = ""  # Overall summary
    encouragement: str = ""  # Encouragement message for P-type personality
    gains: str = ""  # "Your gains" section
