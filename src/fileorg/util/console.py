"""Rich console utilities."""

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Global console instance
console = Console()


def create_scan_progress() -> Progress:
    """Create a progress bar for scanning."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def print_scan_summary(
    total_files: int,
    total_dirs: int,
    total_size: str,
    duration: float,
    empty_dirs: int = 0,
) -> None:
    """Print scan summary in a nice table."""
    table = Table(title="Scan Summary", show_header=False, box=None)
    table.add_column("Label", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Files", str(total_files))
    table.add_row("Total Directories", str(total_dirs))
    table.add_row("Total Size", total_size)
    table.add_row("Empty Directories", str(empty_dirs))
    table.add_row("Scan Duration", f"{duration:.1f}s")

    panel = Panel(table, title="[bold]Scan Complete[/bold]", border_style="green")
    console.print(panel)


def print_issues_summary(
    duplicates: int,
    large_files: int,
    stale_files: int,
    empty_dirs: int,
    wasted_space: str = "",
) -> None:
    """Print issues summary with color coding."""
    console.print()
    console.print("[bold]Issues Found:[/bold]")

    if duplicates > 0:
        console.print(f"  [red]Duplicates:[/red] {duplicates} groups", end="")
        if wasted_space:
            console.print(f" (wasting {wasted_space})")
        else:
            console.print()

    if large_files > 0:
        console.print(f"  [yellow]Large Files (>100MB):[/yellow] {large_files}")

    if stale_files > 0:
        console.print(f"  [dim]Stale Files (>180 days):[/dim] {stale_files}")

    if empty_dirs > 0:
        console.print(f"  [dim]Empty Directories:[/dim] {empty_dirs}")

    if not any([duplicates, large_files, stale_files, empty_dirs]):
        console.print("  [green]No issues found![/green]")


def print_file_types(types: list, top_n: int = 10) -> None:
    """Print file type statistics."""
    table = Table(title=f"Top {top_n} File Types by Size")
    table.add_column("Extension", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Size", justify="right", style="green")

    for t in types[:top_n]:
        table.add_row(t.extension, str(t.count), t.total_size_human)

    console.print(table)


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    from rich.prompt import Confirm
    return Confirm.ask(message, default=default)
