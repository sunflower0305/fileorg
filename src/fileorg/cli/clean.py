"""Clean command implementation - interactive file cleanup and organization."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..config import setup_logging
from ..config.settings import settings
from ..core.scanner import FileScanner
from ..core.analyzer import FileAnalyzer
from ..core.organizer import SmartOrganizer
from ..core.executor import FileExecutor
from ..definition.scan_result import ScanConfig
from ..util.console import console, print_info, print_success, print_warning, print_error

app = typer.Typer(help="Interactive file cleanup and organization.")


@app.callback(invoke_without_command=True)
def clean(
    paths: list[Path] = typer.Argument(
        default=None,
        help="Paths to clean. Defaults to current directory.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Dry run mode (default) or execute changes.",
    ),
    ai: bool = typer.Option(
        False,
        "--ai",
        help="Use AI to organize files by project/topic.",
    ),
    prompt: str = typer.Option(
        "",
        "--prompt",
        "-p",
        help="Custom instruction for AI organization (e.g., '按时间分类', '按工作项目分类').",
    ),
    organize: bool = typer.Option(
        False,
        "--organize",
        "-O",
        help="Organize files into folders based on file types.",
    ),
    duplicates: bool = typer.Option(
        False,
        "--duplicates",
        "-D",
        help="Clean duplicate files only.",
    ),
    large: bool = typer.Option(
        False,
        "--large",
        "-L",
        help="Clean large files only.",
    ),
    stale: bool = typer.Option(
        False,
        "--stale",
        "-S",
        help="Clean stale files only.",
    ),
    empty: bool = typer.Option(
        False,
        "--empty",
        "-E",
        help="Clean empty directories only.",
    ),
) -> None:
    """Interactive file cleanup and organization wizard.

    By default, runs in dry-run mode (no actual changes).
    Use --execute to make actual changes (with confirmation).

    Examples:
        fo clean                     # Interactive cleanup (dry-run)
        fo clean --ai                # AI-powered project organization
        fo clean --organize          # Organize by file types
        fo clean --duplicates        # Clean duplicates only
        fo clean --execute           # Actually execute changes
        fo clean --execute --ai      # Execute AI organization
    """
    setup_logging()

    # Default paths
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

    # Check API key for AI mode
    if ai and not settings.llm.api_key:
        print_warning("AI mode requires LLM_API_KEY in .env file")
        print_info("Falling back to rule-based organization")
        ai = False
        organize = True

    # Show mode
    console.print()
    mode_text = "[green]DRY RUN[/green]" if dry_run else "[red]EXECUTE MODE[/red]"
    ai_text = " + [cyan]AI[/cyan]" if ai else ""
    console.print(f"Mode: {mode_text}{ai_text}")
    if dry_run:
        console.print("[dim]No files will be modified. Use --execute to make changes.[/dim]")
    console.print()

    # Run analysis
    scan_result, analysis = asyncio.run(_run_analysis(valid_paths))

    # Determine what to clean
    clean_all = not any([ai, organize, duplicates, large, stale, empty])

    executor = FileExecutor(dry_run=dry_run)

    # AI organization mode
    if ai or prompt:
        asyncio.run(_handle_ai_organization(scan_result, executor, dry_run, valid_paths[0], prompt))
    # Rule-based organization mode
    elif organize or clean_all:
        _handle_organization(scan_result, executor, dry_run)

    # Duplicates
    if (duplicates or clean_all) and analysis.duplicates:
        _handle_duplicates(analysis.duplicates, executor)

    # Large files
    if (large or clean_all) and analysis.large_files:
        _handle_large_files(analysis.large_files)

    # Stale files
    if (stale or clean_all) and analysis.stale_files:
        _handle_stale_files(analysis.stale_files)

    # Empty directories
    if (empty or clean_all) and analysis.empty_directories:
        _handle_empty_dirs(analysis.empty_directories, executor)

    # Summary
    console.print()
    if dry_run:
        print_info("This was a dry run. Use [bold]--execute[/bold] to apply changes.")
    else:
        print_success("Cleanup complete!")


async def _run_analysis(paths: list[Path]):
    """Run scan and analysis."""
    config = ScanConfig(
        target_paths=paths,
        exclude_patterns=settings.scan.exclude_patterns,
        large_file_threshold_mb=settings.scan.large_file_threshold_mb,
        stale_days_threshold=settings.scan.stale_days_threshold,
    )

    scanner = FileScanner(config)
    analyzer = FileAnalyzer(
        large_threshold_mb=config.large_file_threshold_mb,
        stale_days_threshold=config.stale_days_threshold,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning and analyzing..."),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        scan_result = await scanner.scan()
        analysis = await analyzer.analyze(scan_result, compute_hashes=True)

    return scan_result, analysis


def _handle_organization(scan_result, executor: FileExecutor, dry_run: bool) -> None:
    """Handle smart file organization."""
    organizer = SmartOrganizer()
    suggestions = organizer.analyze_and_suggest(scan_result)

    if not suggestions:
        print_info("No organization suggestions.")
        return

    console.print()
    console.print("[bold]Smart Organization Plan[/bold]")
    console.print()

    total_files = sum(len(files) for files in suggestions.values())
    console.print(f"Found {total_files} files to organize into {len(suggestions)} folders:")
    console.print()

    # Show summary by folder
    table = Table(title="Organization Summary")
    table.add_column("Target Folder", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Sample Files", style="dim")

    for folder, files in sorted(suggestions.items()):
        sample = ", ".join(f.name[:20] for f, _ in files[:3])
        if len(files) > 3:
            sample += f" +{len(files) - 3} more"
        table.add_row(folder, str(len(files)), sample)

    console.print(table)
    console.print()

    if dry_run:
        print_info("Use [bold]--execute --organize[/bold] to apply organization")
        return

    # Confirm before executing
    if not Confirm.ask("Apply this organization plan?", default=False):
        print_info("Organization cancelled.")
        return

    # Execute
    plan = organizer.get_organization_plan(scan_result)
    stats = executor.execute_organization_plan(plan)

    print_success(f"Organized {stats['success']} files, {stats['failed']} failed, {stats['skipped']} skipped")


def _handle_duplicates(duplicates, executor: FileExecutor) -> None:
    """Handle duplicate file cleanup."""
    console.print()
    console.print("[bold]Duplicate Files[/bold]")

    total_wasted = sum(d.wasted_bytes for d in duplicates)
    console.print(f"Found {len(duplicates)} groups, wasting {_format_size(total_wasted)}")
    console.print()

    for i, dup in enumerate(duplicates[:5], 1):
        panel_content = []
        for j, path in enumerate(dup.files):
            marker = "[green]KEEP[/green]" if j == 0 else "[red]DELETE[/red]"
            panel_content.append(f"{marker} {path}")

        console.print(Panel(
            "\n".join(panel_content),
            title=f"Group {i}: {dup.count} files, {dup.wasted_human} wasted",
            border_style="yellow",
        ))

    if len(duplicates) > 5:
        console.print(f"... and {len(duplicates) - 5} more groups")


def _handle_large_files(large_files) -> None:
    """Handle large file review."""
    console.print()
    console.print("[bold]Large Files (>100MB)[/bold]")

    table = Table()
    table.add_column("File", style="cyan")
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Modified", style="dim")

    for f in large_files[:10]:
        table.add_row(
            f.path.name[:40],
            f.size_human,
            f.modified_at.strftime("%Y-%m-%d"),
        )

    console.print(table)
    if len(large_files) > 10:
        console.print(f"... and {len(large_files) - 10} more")


def _handle_stale_files(stale_files) -> None:
    """Handle stale file review."""
    console.print()
    console.print("[bold]Stale Files (Not accessed in 180+ days)[/bold]")

    table = Table()
    table.add_column("File", style="cyan")
    table.add_column("Days Stale", justify="right", style="red")
    table.add_column("Size", justify="right")

    for f in stale_files[:10]:
        table.add_row(
            f.path.name[:40],
            str(f.days_stale),
            f.size_human,
        )

    console.print(table)
    if len(stale_files) > 10:
        console.print(f"... and {len(stale_files) - 10} more")


def _handle_empty_dirs(empty_dirs, executor: FileExecutor) -> None:
    """Handle empty directory cleanup."""
    console.print()
    console.print("[bold]Empty Directories[/bold]")

    for d in empty_dirs[:10]:
        console.print(f"  [dim]{d.path}[/dim]")

    if len(empty_dirs) > 10:
        console.print(f"  ... and {len(empty_dirs) - 10} more")

    console.print()
    if executor.dry_run:
        print_info(f"Found {len(empty_dirs)} empty directories to clean")
    else:
        if Confirm.ask(f"Delete {len(empty_dirs)} empty directories?", default=False):
            for d in empty_dirs:
                executor.delete_directory(d.path)
            print_success(f"Deleted {len(empty_dirs)} empty directories")


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


async def _handle_ai_organization(
    scan_result,
    executor: FileExecutor,
    dry_run: bool,
    base_path: Path,
    custom_prompt: str = "",
) -> None:
    """Handle AI-powered project organization."""
    from ..ai.project_organizer import AIProjectOrganizer

    console.print()
    console.print("[bold]AI Project Organization[/bold]")
    if custom_prompt:
        console.print(f"[dim]Custom instruction: {custom_prompt}[/dim]")
    console.print("[dim]Analyzing files with AI...[/dim]")
    console.print()

    organizer = AIProjectOrganizer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]AI analyzing..."),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        groups = await organizer.analyze_and_group(scan_result, custom_prompt)

    if not groups:
        print_info("AI could not generate organization suggestions.")
        return

    # Calculate totals
    total_files = sum(len(files) for files in groups.values())

    console.print(f"AI suggests organizing {total_files} files into {len(groups)} project folders:")
    console.print()

    # Show summary table
    table = Table(title="AI Organization Plan")
    table.add_column("Project Folder", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Sample Files", style="dim")

    for folder, files in sorted(groups.items(), key=lambda x: -len(x[1])):
        sample = ", ".join(f[0].name[:25] for f in files[:2])
        if len(files) > 2:
            sample += f" +{len(files) - 2} more"
        table.add_row(folder, str(len(files)), sample)

    console.print(table)
    console.print()

    if dry_run:
        print_info("Use [bold]--execute --ai[/bold] to apply AI organization")
        return

    # Confirm before executing
    if not Confirm.ask("Apply this AI organization plan?", default=False):
        print_info("Organization cancelled.")
        return

    # Execute
    plan = organizer.get_organization_plan(groups, base_path)
    stats = executor.execute_organization_plan(plan)

    print_success(f"Organized {stats['success']} files, {stats['failed']} failed, {stats['skipped']} skipped")
