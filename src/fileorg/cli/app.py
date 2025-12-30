"""Main CLI application using Typer."""

import typer
from rich.console import Console

from .. import __version__

# Create the main app
app = typer.Typer(
    name="fo",
    help="FileOrganizer - AI-powered file organization assistant",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold]FileOrganizer[/bold] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """FileOrganizer - AI-powered file organization assistant for P-type personalities."""
    pass


# Import and register sub-commands
from . import scan  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import clean  # noqa: E402, F401
from . import web  # noqa: E402, F401

app.add_typer(scan.app, name="scan")
app.add_typer(report.app, name="report")
app.add_typer(clean.app, name="clean")
app.add_typer(web.app, name="web")
