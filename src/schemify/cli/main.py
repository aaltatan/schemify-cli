"""The schemify command line application."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from typer_di import TyperDI
from typer_swissknife import command

from schemify.cli.dependencies.console import ConsoleDI
from schemify.cli.dependencies.schema import FilledDataDI
from schemify.generators import ask_schema

app = TyperDI(
    name="schemify",
    help="Build JSON Schemas interactively, and fill JSON data from them",
    no_args_is_help=True,
)


def _confirm_overwrite(output: Path | None) -> Path | None:
    """Ask before the long interactive session, not after it."""
    if output is not None and output.exists():
        typer.confirm(f"'{output.name}' already exists, overwrite it?", abort=True)

    return output


OutputOption = Annotated[  # not a `type` alias, typer can not read through those
    Path | None,
    typer.Option(
        "-o",
        "--output",
        help="Path to save the JSON to, printed when missing",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        callback=_confirm_overwrite,
    ),
]


def _output(console: ConsoleDI, value: Any, output: Path | None) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False)

    if output is None:
        console.print_json(text)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{text}\n", encoding="utf-8")
    console.print(f"[green]Saved to:[/] {output}")


@command(
    app,
    name="generate",
    aliases=("g",),
    help="Ask for the properties of an object and build its JSON Schema",
)
def generate_schema(
    console: ConsoleDI,
    output: OutputOption = None,
    title: Annotated[
        str | None,
        typer.Option("-t", "--title", help="Title of the schema"),
    ] = None,
) -> None:
    """Ask for the properties of an object and build its JSON Schema."""
    try:
        schema = ask_schema(title)
    except KeyboardInterrupt:
        raise typer.Abort from None

    _output(console, schema, output)


@command(
    app,
    name="fill",
    aliases=("f",),
    no_args_is_help=True,
    help="Ask for data matching a JSON Schema",
)
def fill_data(console: ConsoleDI, data: FilledDataDI, output: OutputOption = None) -> None:
    """Ask for data matching a JSON Schema."""
    _output(console, data, output)


def main() -> None:
    """Run the schemify command line application."""
    app()


if __name__ == "__main__":
    main()
