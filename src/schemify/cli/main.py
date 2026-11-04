"""The schemify command line application."""

from pathlib import Path
from typing import Annotated

import typer
from rich.syntax import Syntax
from typer_di import TyperDI
from typer_swissknife import command

from schemify.cli.dependencies.console import ConsoleDI
from schemify.cli.dependencies.schema import FilledDataArgumentDI, FilledListArgumentDI
from schemify.formatters import formatters, to_json
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
        help="Path to save the output to, printed when missing",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        callback=_confirm_overwrite,
    ),
]


def _check_if_format_is_supported(name: str) -> str:
    if name not in formatters:
        supported = ", ".join(formatters.names)
        message = f"Format '{name}' is not supported, supported: {supported}"
        raise typer.BadParameter(message)

    return name.lower()


FormatOption = Annotated[
    str,
    typer.Option(
        "-f",
        "--format",
        help=f"Output format ({', '.join(formatters.names)})",
        callback=_check_if_format_is_supported,
    ),
]


def _output(console: ConsoleDI, text: str, lexer: str, output: Path | None) -> None:
    if output is None:
        console.print(Syntax(text, lexer, background_color="default"))
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

    _output(console, to_json(schema), "json", output)


@command(
    app,
    name="fill",
    aliases=("f",),
    no_args_is_help=True,
    help="Ask for data matching a JSON Schema",
)
def fill_data(
    console: ConsoleDI,
    data: FilledDataArgumentDI,
    output: OutputOption = None,
    output_format: FormatOption = "json",
) -> None:
    """Ask for data matching a JSON Schema."""
    _output(console, formatters[output_format](data), output_format, output)


@command(
    app,
    name="list",
    aliases=("l",),
    no_args_is_help=True,
    help="Ask for a list of items, each matching a JSON Schema",
)
def fill_list(
    console: ConsoleDI,
    items: FilledListArgumentDI,
    output: OutputOption = None,
    output_format: FormatOption = "json",
) -> None:
    """Ask for a list of items, each matching a JSON Schema."""
    _output(console, formatters[output_format](items), output_format, output)


def main() -> None:
    """Run the schemify command line application."""
    app()


if __name__ == "__main__":
    main()
