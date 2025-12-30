"""Scan command implementation."""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..config import setup_logging
from ..config.settings import settings
from ..core.scanner import FileScanner
from ..core.analyzer import FileAnalyzer
from ..definition.scan_result import ScanConfig
from ..util.console import (
    console,
    print_scan_summary,
    print_file_types,
    print_issues_summary,
    print_error,
    print_info,
)

app = typer.Typer(help="Scan directories for files and issues.")


@app.callback(invoke_without_command=True)
def scan(
    paths: List[Path] = typer.Argument(
        default=None,
        help="Paths to scan. Defaults to current directory.",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r/-R",
        help="Recursively scan subdirectories.",
    ),
    include_hidden: bool = typer.Option(
        False,
        "--hidden",
        "-H",
        help="Include hidden files and directories.",
    ),
    max_depth: Optional[int] = typer.Option(
        None,
        "--depth",
        "-d",
        help="Maximum depth to scan.",
    ),
    no_hash: bool = typer.Option(
        False,
        "--no-hash",
        help="Skip hash computation for faster scanning.",
    ),
    show_types: bool = typer.Option(
        True,
        "--types/--no-types",
        help="Show file type statistics.",
    ),
) -> None:
    """Scan directories and show summary.

    Examples:
        fo scan                     # Scan current directory
        fo scan ~/Downloads         # Scan Downloads folder
        fo scan . --depth 2         # Scan with max depth of 2
        fo scan . --no-hash         # Quick scan without hash
    """
    # Setup logging
    setup_logging()

    # Default to current directory if no paths provided
    if not paths:
        paths = [Path.cwd()]

    # Validate paths
    valid_paths = []
    for p in paths:
        if not p.exists():
            print_error(f"Path does not exist: {p}")
        else:
            valid_paths.append(p.resolve())

    if not valid_paths:
        raise typer.Exit(1)

    # Create scan config
    config = ScanConfig(
        target_paths=valid_paths,
        recursive=recursive,
        include_hidden=include_hidden,
        max_depth=max_depth,
        exclude_patterns=settings.scan.exclude_patterns,
        compute_hash=not no_hash,
        large_file_threshold_mb=settings.scan.large_file_threshold_mb,
        stale_days_threshold=settings.scan.stale_days_threshold,
    )

    # Display scan targets
    console.print()
    console.print("[bold]Scanning:[/bold]")
    for p in valid_paths:
        console.print(f"  {p}")
    console.print()

    # Run scan and analysis with progress
    result, analysis = asyncio.run(_run_scan_and_analyze(config, not no_hash))

    # Print summary
    print_scan_summary(
        total_files=result.summary.total_files,
        total_dirs=result.summary.total_directories,
        total_size=result.summary.total_size_human,
        duration=result.summary.scan_duration_seconds,
        empty_dirs=result.summary.empty_directories,
    )

    # Print file types
    if show_types and result.summary.file_types:
        console.print()
        print_file_types(result.summary.file_types)

    # Print issues summary
    if analysis.has_issues:
        wasted = _format_size(analysis.total_wasted_by_duplicates) if analysis.duplicates else ""
        print_issues_summary(
            duplicates=len(analysis.duplicates),
            large_files=len(analysis.large_files),
            stale_files=len(analysis.stale_files),
            empty_dirs=len(analysis.empty_directories),
            wasted_space=wasted,
        )

    # Hint for next steps
    console.print()
    print_info("Run [bold]fo report[/bold] to generate a detailed report")
    print_info("Run [bold]fo report --ai[/bold] to get AI-powered insights")


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


async def _run_scan_and_analyze(config: ScanConfig, compute_hashes: bool = True):
    """Run scan and analysis with progress display."""
    scanner = FileScanner(config)
    analyzer = FileAnalyzer(
        large_threshold_mb=config.large_file_threshold_mb,
        stale_days_threshold=config.stale_days_threshold,
    )

    # Phase 1: Scan
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning..."),
        TextColumn("[dim]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=None)

        def update_progress(current: int, total: int, path: str) -> None:
            display_path = path
            if len(display_path) > 50:
                display_path = "..." + display_path[-47:]
            progress.update(task, description=f"[{current} files] {display_path}")

        result = await scanner.scan(progress_callback=update_progress)

    # Phase 2: Analyze
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Analyzing..."),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Detecting issues", total=None)
        analysis = await analyzer.analyze(result, compute_hashes=compute_hashes)

    return result, analysis
