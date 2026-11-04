"""The schema options: `--schema`, and the data the user fills from it.

Other typer-di apps can reuse them, a command taking `FilledDataDI` gets a `--schema`
option and the data the user entered:

```python
@app.command()
def fill_template(data: FilledDataDI) -> None: ...
```
"""

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from typer_di import Depends

from schemify.fillers import InvalidDataError, ask_data
from schemify.models import Schema
from schemify.registry import NotSupportedError
from schemify.validators import check_schema

# -----------------------
# schema
# -----------------------


def _read_schema(
    path: Annotated[
        Path,
        typer.Option(
            "-s",
            "--schema",
            help="Path to the JSON Schema file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
        ),
    ],
) -> Schema:
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


# -----------------------
# filled data
# -----------------------


def _fill(schema: Annotated[Schema, Depends(_read_schema)]) -> Any:
    try:
        return ask_data(schema)
    except (NotSupportedError, InvalidDataError) as e:
        raise typer.BadParameter(str(e)) from e
    except KeyboardInterrupt:
        raise typer.Abort from None


# -----------------------
# DI
# -----------------------

SchemaDI = Annotated[Schema, Depends(_read_schema)]
"""Injects the valid JSON Schema read from `--schema`."""

FilledDataDI = Annotated[Any, Depends(_fill)]
"""Injects the data the user entered, matching the `--schema` file."""
