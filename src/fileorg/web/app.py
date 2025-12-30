"""FastAPI backend for FileOrganizer Web UI."""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from ..config import setup_logging
from ..config.settings import settings
from ..core.scanner import FileScanner
from ..core.analyzer import FileAnalyzer
from ..core.executor import FileExecutor
from ..ai.project_organizer import AIProjectOrganizer
from ..definition.scan_result import ScanConfig

setup_logging()

app = FastAPI(title="FileOrganizer", description="AI-powered file organization")

# Static files
STATIC_DIR = Path(__file__).parent / "static"


class ScanRequest(BaseModel):
    path: str
    use_ai: bool = True


class OrganizeRequest(BaseModel):
    path: str
    custom_prompt: str = ""
    execute: bool = False


class ScanResponse(BaseModel):
    total_files: int
    total_size: str
    file_types: list
    issues: dict
    ai_analysis: Optional[dict] = None


class OrganizeResponse(BaseModel):
    groups: list
    total_files: int
    executed: bool = False
    stats: Optional[dict] = None


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    html_file = STATIC_DIR / "index.html"
    return FileResponse(html_file)


@app.post("/api/scan", response_model=ScanResponse)
async def scan_directory(request: ScanRequest):
    """Scan a directory and return statistics with AI analysis."""
    path = Path(request.path).expanduser().resolve()

    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    config = ScanConfig(
        target_paths=[path],
        exclude_patterns=settings.scan.exclude_patterns,
    )

    scanner = FileScanner(config)
    analyzer = FileAnalyzer()

    result = await scanner.scan()
    analysis = await analyzer.analyze(result, compute_hashes=False)

    # AI analysis if enabled and API key available
    ai_analysis = None
    if request.use_ai and settings.llm.api_key:
        try:
            from ..ai.habit_analyzer import HabitAnalyzer
            habit_analyzer = HabitAnalyzer()
            ai_result = await habit_analyzer.analyze(result, analysis)
            ai_analysis = {
                "summary": ai_result.summary,
                "encouragement": ai_result.encouragement,
                "gains": ai_result.gains,
                # Work pattern
                "work_pattern": {
                    "peak_hours": ai_result.work_pattern.peak_hours if ai_result.work_pattern else [],
                    "peak_days": ai_result.work_pattern.peak_days if ai_result.work_pattern else [],
                    "description": ai_result.work_pattern.activity_description if ai_result.work_pattern else "",
                },
                # File habit
                "file_habit": {
                    "most_used_types": ai_result.file_habit.most_used_types if ai_result.file_habit else [],
                    "naming_style": ai_result.file_habit.naming_style if ai_result.file_habit else "",
                    "organization_score": ai_result.file_habit.organization_score if ai_result.file_habit else 0,
                },
                # Personality
                "personality": {
                    "chaos_level": ai_result.personality_insight.chaos_level if ai_result.personality_insight else "unknown",
                    "strengths": ai_result.personality_insight.strengths if ai_result.personality_insight else [],
                    "challenges": ai_result.personality_insight.challenges if ai_result.personality_insight else [],
                },
                # Suggestions
                "suggestions": [
                    {
                        "title": s.title,
                        "description": s.description,
                        "priority": s.priority,
                        "category": s.category,
                        "benefit": s.estimated_benefit,
                    }
                    for s in ai_result.suggestions
                ],
            }
        except Exception as e:
            ai_analysis = {"error": str(e)}

    return ScanResponse(
        total_files=result.summary.total_files,
        total_size=result.summary.total_size_human,
        file_types=[
            {"ext": ft.extension, "count": ft.count, "size": ft.total_size_human}
            for ft in result.summary.file_types[:10]
        ],
        issues={
            "duplicates": len(analysis.duplicates),
            "large_files": len(analysis.large_files),
            "stale_files": len(analysis.stale_files),
            "empty_dirs": len(analysis.empty_directories),
        },
        ai_analysis=ai_analysis,
    )


@app.post("/api/organize", response_model=OrganizeResponse)
async def organize_directory(request: OrganizeRequest):
    """Get AI organization suggestions or execute them."""
    path = Path(request.path).expanduser().resolve()

    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    if not settings.llm.api_key:
        raise HTTPException(status_code=400, detail="AI requires LLM_API_KEY in .env")

    config = ScanConfig(
        target_paths=[path],
        exclude_patterns=settings.scan.exclude_patterns,
    )

    scanner = FileScanner(config)
    result = await scanner.scan()

    organizer = AIProjectOrganizer()
    groups = await organizer.analyze_and_group(result, request.custom_prompt)

    # Format groups for response
    formatted_groups = []
    for folder, files in sorted(groups.items(), key=lambda x: -len(x[1])):
        formatted_groups.append({
            "folder": folder,
            "count": len(files),
            "files": [f[0].name for f in files[:5]],
            "has_more": len(files) > 5,
        })

    total_files = sum(len(files) for files in groups.values())

    # Execute if requested
    stats = None
    if request.execute and groups:
        executor = FileExecutor(dry_run=False)
        plan = organizer.get_organization_plan(groups, path)
        stats = executor.execute_organization_plan(plan)

    return OrganizeResponse(
        groups=formatted_groups,
        total_files=total_files,
        executed=request.execute,
        stats=stats,
    )


@app.get("/api/status")
async def status():
    """Check API status."""
    return {
        "status": "ok",
        "ai_enabled": bool(settings.llm.api_key),
    }


def create_app():
    """Create and configure the app."""
    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
