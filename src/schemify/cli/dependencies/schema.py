"""The schema file, and the data the user fills from it, as an option or an argument.

Other typer-di apps can reuse them, pick the version matching how the path is given:

```python
@app.command()
def fill_template(data: FilledDataOptionDI) -> None: ...  # app --js person.json


@app.command()
def fill_template(data: FilledDataArgumentDI) -> None: ...  # app person.json


@app.command()
def fill_many(items: FilledListArgumentDI) -> None: ...  # app person.json, a list of people
```
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from typer_di import Depends

from schemify.fillers import InvalidDataError, ask_data, ask_list
from schemify.models import Schema
from schemify.registry import NotSupportedError
from schemify.validators import check_schema

_PATH_HELP = "Path to the JSON Schema file"

# -----------------------
# schema
# -----------------------


def _load_schema(path: Path) -> Schema:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        msg = f"Could not read schema file '{path.name}': {e}"
        raise typer.BadParameter(msg) from e

    error = check_schema(schema)

    if error is not None:
        msg = f"Invalid schema file '{path.name}': {error}"
        raise typer.BadParameter(msg)

    return schema


def _schema_from_option(
    path: Annotated[
        Path,
        typer.Option(
            "--js",
            "--json-schema",
            help=_PATH_HELP,
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
) -> Schema:
    return _load_schema(path)


def _schema_from_argument(
    path: Annotated[
        Path,
        typer.Argument(
            help=_PATH_HELP,
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
) -> Schema:
    return _load_schema(path)


# -----------------------
# filled data
# -----------------------


def _filled_data(
    read_schema: Callable[..., Schema], ask: Callable[[Schema], Any] = ask_data
) -> Callable[..., Any]:
    """Build a dependency asking (with `ask`) for data matching the schema `read_schema` injects."""

    def fill(schema: Annotated[Schema, Depends(read_schema)]) -> Any:
        try:
            return ask(schema)
        except (NotSupportedError, InvalidDataError) as e:
            raise typer.BadParameter(str(e)) from e
        except KeyboardInterrupt:
            raise typer.Abort from None

    return fill


# -----------------------
# DI
# -----------------------

SchemaOptionDI = Annotated[Schema, Depends(_schema_from_option)]
"""Injects the valid JSON Schema read from the `--js` / `--json-schema` option."""

SchemaArgumentDI = Annotated[Schema, Depends(_schema_from_argument)]
"""Injects the valid JSON Schema read from the `PATH` argument."""

FilledDataOptionDI = Annotated[Any, Depends(_filled_data(_schema_from_option))]
"""Injects the data the user entered, matching the `--js` / `--json-schema` file."""

FilledDataArgumentDI = Annotated[Any, Depends(_filled_data(_schema_from_argument))]
"""Injects the data the user entered, matching the `PATH` argument file."""

FilledListOptionDI = Annotated[list[Any], Depends(_filled_data(_schema_from_option, ask_list))]
"""Injects the list of items the user entered, each matching the `--js` / `--json-schema` file."""

FilledListArgumentDI = Annotated[list[Any], Depends(_filled_data(_schema_from_argument, ask_list))]
"""Injects the list of items the user entered, each matching the `PATH` argument file."""
