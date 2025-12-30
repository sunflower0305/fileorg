"""Report command implementation."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ..config import setup_logging
from ..config.settings import settings
from ..core.scanner import FileScanner
from ..core.analyzer import FileAnalyzer
from ..core.organizer import SmartOrganizer
from ..definition.scan_result import ScanConfig
from ..report.markdown import generate_markdown_report
from ..util.console import console, print_info, print_success, print_error, print_warning

app = typer.Typer(help="Generate analysis reports.")


@app.callback(invoke_without_command=True)
def report(
    paths: list[Path] = typer.Argument(
        default=None,
        help="Paths to scan. Defaults to current directory.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path.",
    ),
    ai: bool = typer.Option(
        False,
        "--ai",
        help="Include AI-powered analysis and suggestions.",
    ),
    organize: bool = typer.Option(
        False,
        "--organize",
        help="Include smart organization suggestions.",
    ),
) -> None:
    """Generate a detailed analysis report.

    Examples:
        fo report                   # Generate markdown report
        fo report --ai              # Include AI analysis
        fo report --organize        # Include organization plan
        fo report -o my-report.md   # Custom output path
    """
    setup_logging()

    # Default paths
    if not paths:
        paths = [Path.cwd()]

    # Default output
    if not output:
        output = Path("./data/reports") / f"report_{_timestamp()}.md"

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
        print_warning("AI analysis requires LLM_API_KEY in .env file")
        print_info("Falling back to basic analysis")
        ai = False

    # Run analysis
    scan_result, analysis, ai_analysis, org_plan = asyncio.run(
        _run_full_analysis(valid_paths, ai, organize)
    )

    # Generate report
    content = generate_markdown_report(
        scan_result=scan_result,
        analysis_result=analysis,
        ai_analysis=ai_analysis,
        output_path=output,
    )

    # Append organization plan if requested
    if organize and org_plan:
        org_section = f"\n\n---\n\n{org_plan}"
        output.write_text(content + org_section, encoding="utf-8")
        content += org_section

    print_success(f"Report saved to: {output}")

    # Print summary
    console.print()
    console.print("[bold]Report Summary:[/bold]")
    console.print(f"  Files scanned: {scan_result.summary.total_files}")
    console.print(f"  Issues found: {sum(analysis.issue_summary.values())}")
    if ai_analysis:
        console.print(f"  AI suggestions: {len(ai_analysis.suggestions)}")
    if organize:
        console.print("  Organization plan: Included")


def _timestamp() -> str:
    """Generate timestamp for filename."""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def _run_full_analysis(paths: list[Path], include_ai: bool, include_org: bool):
    """Run complete analysis pipeline."""
    from ..ai.habit_analyzer import HabitAnalyzer

    # Create config
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

    # Phase 1: Scan
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scanning..."),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        scan_result = await scanner.scan()

    # Phase 2: Analyze
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Analyzing issues..."),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        analysis = await analyzer.analyze(scan_result, compute_hashes=True)

    # Phase 3: AI Analysis (optional)
    ai_analysis = None
    if include_ai:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Running AI analysis..."),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("", total=None)
            habit_analyzer = HabitAnalyzer()
            ai_analysis = await habit_analyzer.analyze(scan_result, analysis)

    # Phase 4: Organization Plan (optional)
    org_plan = None
    if include_org:
        organizer = SmartOrganizer()
        org_plan = organizer.print_organization_summary(scan_result)

    return scan_result, analysis, ai_analysis, org_plan
