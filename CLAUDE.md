# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FileOrganizer (`fo`) is an AI-powered CLI tool for file organization, targeting users with "P-type personalities" (those who tend to accumulate disorganized files). It scans directories, detects issues (duplicates, large files, stale files, chaotic naming), and provides AI-powered suggestions for organization.

## Commands

```bash
# Install dependencies
uv sync

# Run the CLI
fo scan                      # Scan current directory
fo scan ~/Downloads --depth 2  # Scan with max depth
fo report --ai               # Generate report with AI analysis (requires LLM_API_KEY)
fo clean --dry-run           # Interactive cleanup preview
fo clean --execute           # Actually execute cleanup

# Development
uv run pytest                # Run all tests
uv run pytest tests/test_scanner.py -v  # Run specific test file
uv run mypy src/fileorg      # Type checking
```

## Architecture

The codebase follows a layered architecture:

- **CLI Layer** (`src/fileorg/cli/`): Typer-based commands (`scan.py`, `report.py`, `clean.py`) that orchestrate workflows with Rich progress displays
- **Core Layer** (`src/fileorg/core/`):
  - `scanner.py`: Async file scanner with progress callbacks
  - `analyzer.py`: Problem detection (duplicates via hash, large/stale files, chaotic naming)
  - `organizer.py`: Smart organization suggestions based on file types
  - `executor.py`: Safe file operations with dry-run mode and backup support
- **AI Layer** (`src/fileorg/ai/`): OpenAI-compatible LLM client (supports DashScope, DeepSeek) for habit analysis
- **Definition Layer** (`src/fileorg/definition/`): Pydantic models for all data structures

## Key Patterns

- All file operations are async using `asyncio.to_thread` for blocking I/O
- Settings loaded via pydantic-settings from `.env` (see `config/settings.py`)
- File executor defaults to dry-run mode; use `--execute` to make actual changes
- LLM client is OpenAI-compatible, configured via `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` env vars

## Environment Variables

```bash
LLM_API_KEY=your_key          # Required for AI features
LLM_BASE_URL=https://...      # OpenAI-compatible endpoint (default: DashScope)
LLM_MODEL=qwen-plus           # Model to use
LARGE_FILE_THRESHOLD_MB=100   # Files larger than this flagged as "large"
STALE_DAYS_THRESHOLD=180      # Files not accessed in this many days flagged as "stale"
```
