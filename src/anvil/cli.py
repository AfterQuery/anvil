"""Anvil CLI - SWE-Bench Pro evaluation toolkit."""

from pathlib import Path
from typing import Sequence

import typer

from . import __version__
from .publish import publish_images
from .run_evals import run_evals
from .wizard.commands import add_task, init_dataset, validate_dataset
from .wizard.converters import convert_dataset

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parents[3] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

app = typer.Typer(help="AQ Project Anvil - SWE-Bench Pro Tasks", no_args_is_help=True)
app.command("publish-images", no_args_is_help=True)(publish_images)
app.command("run-evals", no_args_is_help=True)(run_evals)

# Task creation wizard commands
app.command("init-dataset", no_args_is_help=True)(init_dataset)
app.command("add-task", no_args_is_help=True)(add_task)
app.command("convert-dataset", no_args_is_help=True)(convert_dataset)
app.command("validate-dataset", no_args_is_help=True)(validate_dataset)


def version_callback(v: bool) -> None:
    if v:
        typer.echo(f"v{__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False, "-v", "--version", is_eager=True, callback=version_callback
    )
) -> None:
    pass


def main(argv: Sequence[str] | None = None) -> int:
    return app(
        args=list(argv) if argv is not None else None,
        standalone_mode=False,
    )
