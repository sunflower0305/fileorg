"""Main entry point for the CLI."""

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .cli.app import app

if __name__ == "__main__":
    app()
