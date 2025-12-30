"""Web UI command."""

import typer
from rich.console import Console

console = Console()

app = typer.Typer(help="Start the web interface.")


@app.callback(invoke_without_command=True)
def web(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind to.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind to.",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open/--no-open",
        help="Open browser automatically.",
    ),
) -> None:
    """Start the FileOrganizer web interface.

    Examples:
        fo web                  # Start on http://127.0.0.1:8000
        fo web -p 3000          # Use custom port
        fo web --no-open        # Don't open browser
    """
    import uvicorn
    import webbrowser
    import threading

    from ..web.app import create_app

    console.print()
    console.print("[bold]🗂️  FileOrganizer Web UI[/bold]")
    console.print()
    console.print(f"Starting server at [cyan]http://{host}:{port}[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Open browser after a short delay
    if open_browser:
        def open_browser_delayed():
            import time
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Create and run app
    application = create_app()
    uvicorn.run(application, host=host, port=port, log_level="warning")
