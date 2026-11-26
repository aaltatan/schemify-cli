# Python API

Install `schemify-cli` in your project and import `schemify`. Everything the command
line does is available as functions, and as [typer-di](https://pypi.org/project/typer-di/)
dependencies for your own typer apps.

## Ask and check

```python
import schemify

schema = schemify.ask_schema("Person")       # the `generate` questions, returns a dict
person = schemify.ask_data(schema)           # the `fill` questions
people = schemify.ask_list(schema)           # the `list` questions, at least one item
```

| Function | Returns | Raises |
|----------|---------|--------|
| `ask_schema(title=None)` | A Draft 2020-12 schema of an object | `KeyboardInterrupt` on ++ctrl+c++ |
| `ask_data(schema)` | A value matching `schema` | `NotSupportedError` (a part has no prompt), `InvalidDataError` (the whole value fails the schema), `KeyboardInterrupt` |
| `ask_list(schema)` | A list of values, each matching `schema` | the same |
| `check_schema(value)` | `None`, or why `value` is not a valid schema | |
| `check_value(schema, value)` | `None`, or why `value` does not match | |

The check functions never prompt, so they also work in a web view or a test:

```python
from schemify import check_schema, check_value

check_schema({"type": "nope"})                            # "'nope' is not valid under any of the given schemas"
check_value({"type": "integer", "minimum": 0}, -1)        # '-1 is less than the minimum of 0'
check_value({"type": "integer", "minimum": 0}, 5)         # None
```

`check_value` also checks formats (`date`, `email`, `uuid`, `ipv4`, ...).

## In a typer app

`schemify.cli.dependencies.schema` has dependencies that read a schema file, check it,
and ask for its data. Pick the one that matches how the path is given:

| Dependency | The path is | Injects |
|------------|-------------|---------|
| `SchemaArgumentDI` | an argument: `app person.json` | the schema |
| `SchemaOptionDI` | an option: `app --js person.json` (or `--json-schema`) | the schema |
| `FilledDataArgumentDI` | an argument | the data asked with `fill` |
| `FilledDataOptionDI` | an option | the data asked with `fill` |
| `FilledListArgumentDI` | an argument | a list asked with `list` |
| `FilledListOptionDI` | an option | a list asked with `list` |

```python
import typer
from typer_di import TyperDI

from schemify.cli.dependencies.schema import FilledDataOptionDI, FilledListArgumentDI

app = TyperDI()


@app.command()
def greet(person: FilledDataOptionDI) -> None:
    """app greet --js person.schema.json"""
    typer.echo(f"Hello {person['first']}")


@app.command()
def count(people: FilledListArgumentDI) -> None:
    """app count person.schema.json"""
    typer.echo(f"{len(people)} people")
```

Errors come out the way a typer user expects: a bad file or a schema `fill` cannot handle
is a usage error (exit code 2), and ++ctrl+c++ aborts (exit code 1).

When the path is optional, or comes from somewhere else, call the two helpers yourself.
This is what templify and qrbar-cli do for their `-s` option:

```python
from schemify import ask_list
from schemify.cli.dependencies.schema import ask_or_abort, load_schema

schema = load_schema(path)               # typer.BadParameter for a bad file or schema
records = ask_or_abort(schema, ask_list) # typer.BadParameter / typer.Abort
```

## Extending

The types, prompts and output formats are registries. Register a function, and it is
offered everywhere that registry is used, in your app.

| Registry | Maps | Used by |
|----------|------|---------|
| `schemify.generators` | a type name → a function asking about it and returning its schema | `ask_schema` (`generate`) |
| `schemify.fillers` | a schema kind → a function asking for a value | `ask_data`, `ask_list` (`fill`, `list`) |
| `schemify.formatters` | a format name → a function turning data into text | the `-f` option |

Names are case-insensitive. `registry.names` lists them, and an unknown name raises
`NotSupportedError` with the supported ones.

### A new output format

The format name doubles as the [Pygments](https://pygments.org) lexer used to highlight
printed output:

```python
from typing import Any

from schemify import formatters


@formatters.register("markdown")
def to_markdown(data: Any) -> str:
    rows = data if isinstance(data, list) else [data]
    keys = list(dict.fromkeys(key for row in rows for key in row))
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(row.get(key, "")) for key in keys) + " |" for row in rows]
    return "\n".join(lines)
```

```text
| first | age |
|---|---|
| Rama | 25 |
| Omar |  |
```

### A new kind of prompt

A filler gets the sub-schema, its label (the property path), and whether it is
required. It returns the value, or `MISSING` when the user skips an optional one. The
kind is `enum` for choices, else a registered `format`, else the `type`, so registering a
format name gives that format its own prompt:

```python
from typing import Any

import questionary

from schemify import fillers
from schemify.fillers import MISSING


@fillers.register("color")
def fill_color(schema: dict[str, Any], label: str, required: bool) -> Any:
    name = schema.get("title") or label

    if not required and not questionary.confirm(f"Add '{name}'?").unsafe_ask():
        return MISSING

    return questionary.select(name, choices=["red", "green", "blue"]).unsafe_ask()
```

`{"type": "string", "format": "color"}` now asks with a list. The value is still checked
against the whole schema afterwards.

### A new type for `generate`

A generator takes no arguments, asks its questions with questionary, and returns the
sub-schema. `generate_object` then adds the label, description, default and required
questions.

```python
import questionary

from schemify import generators


@generators.register("money")
def generate_money() -> dict:
    currency = questionary.select("Currency:", choices=["USD", "EUR", "SYP"]).unsafe_ask()
    return {"type": "number", "minimum": 0, "multipleOf": 0.01, "description": currency}
```

!!! note "The web editor"
    A type added to schemify itself must be added to the
    [web editor](https://github.com/aaltatan/schemify) too. Types you register in your own
    app only exist in your app.

## Exports

```python
from schemify import (
    InvalidDataError,    # the whole value does not match the schema
    NotSupportedError,   # nothing registered under a name (a type, kind or format)
    Schema,              # the type alias of a schema: dict[str, Any]
    ask_data,
    ask_list,
    ask_schema,
    check_schema,
    check_value,
    fillers,
    formatters,
    generators,
)
```

The package is typed (`py.typed`).
