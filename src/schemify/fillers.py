"""Data fillers: ask the user for a value matching a JSON Schema, picked by the schema kind.

The kind is `enum` when the schema has choices, else its `format` when a filler is
registered for it (`date`, `date-time`), else its `type`.
"""

from collections.abc import Callable
from typing import Any

import questionary

from .models import Schema
from .registry import NotSupportedError, Registry
from .validators import Parser, check_value, to_date, to_datetime, to_int, to_number

type FillFn = Callable[[Schema, str, bool], Any]
"""Asks for a value of a sub-schema, given its label and whether it is required.

An optional value the user skips is returned as `MISSING`.
"""

MISSING: Any = object()
"""Returned by a filler when the user skips an optional value."""

fillers = Registry[FillFn]("Schema kind")
"""The default registry, used by `ask_data`."""


class InvalidDataError(Exception):
    """Raised when the entered data does not match the whole schema.

    Each value is checked as it is entered, this catches the keywords
    no filler asks about (like `allOf` or `dependentRequired`).
    """


def ask_data(schema: Schema) -> Any:
    """Ask the user for data matching `schema`, usually an object, and return it.

    Raises:
        NotSupportedError: A part of the schema has no filler (like `$ref` or `oneOf`).
        InvalidDataError: The data does not match the whole schema.

    """
    data = fill(schema, "")
    error = check_value(schema, data)

    if error is not None:
        raise InvalidDataError(error)

    return data


def kind(schema: Schema) -> str:
    """Return the filler name of `schema`: `enum`, a registered `format`, or its `type`."""
    if "enum" in schema:
        return "enum"

    if schema.get("format") in fillers:
        return schema["format"]

    return str(schema.get("type"))


def fill(schema: Schema, label: str, *, required: bool = True) -> Any:
    """Ask for a value of `schema` with the filler matching its kind.

    Raises:
        NotSupportedError: No filler matches the schema kind.

    """
    try:
        fill_fn = fillers[kind(schema)]
    except NotSupportedError as e:
        message = f"Can not fill '{label or 'data'}': {e}"
        raise NotSupportedError(message) from e

    return fill_fn(schema, label, required)


# -----------------------
# utils
# -----------------------


def _name(schema: Schema, label: str) -> str:
    """The schema `title` when it has one, else the property path."""
    return schema.get("title") or label


def _message(schema: Schema, label: str) -> str:
    name = _name(schema, label)
    description = schema.get("description")

    return f"{name} ({description}):" if description else f"{name}:"


def _skipped(schema: Schema, label: str, *, required: bool) -> bool:
    """Ask whether to add an optional value, `False` for required values."""
    if required:
        return False

    return not questionary.confirm(f"Add '{_name(schema, label)}'?", default=True).unsafe_ask()


# -----------------------
# typed text
# -----------------------


def _text_filler(parse: Parser) -> FillFn:
    """Build a filler asking a text answer, parsed then checked against the schema."""

    def fill_text(schema: Schema, label: str, required: bool) -> Any:  # noqa: FBT001
        def validate(text: str) -> bool | str:
            if not required and not text.strip():
                return True

            try:
                value = parse(text)
            except ValueError as e:
                return str(e)

            error = check_value(schema, value)

            return error is None or error

        answer = questionary.text(_message(schema, label), validate=validate).unsafe_ask()

        if not required and not answer.strip():
            return MISSING

        return parse(answer)

    return fill_text


fillers.add(_text_filler(str), "string")
fillers.add(_text_filler(to_int), "integer")
fillers.add(_text_filler(to_number), "number")
fillers.add(_text_filler(to_date), "date")
fillers.add(_text_filler(to_datetime), "date-time")


# -----------------------
# choices
# -----------------------


@fillers.register("boolean")
def fill_boolean(schema: Schema, label: str, required: bool) -> Any:  # noqa: FBT001
    """Ask yes / no."""
    if _skipped(schema, label, required=required):
        return MISSING

    return questionary.confirm(_message(schema, label), default=False).unsafe_ask()


@fillers.register("enum")
def fill_enum(schema: Schema, label: str, required: bool) -> Any:  # noqa: FBT001
    """Ask to pick one of the `enum` choices, they can be any JSON value."""
    if _skipped(schema, label, required=required):
        return MISSING

    choices = {str(choice): choice for choice in schema["enum"]}
    answer = questionary.select(_message(schema, label), choices=list(choices)).unsafe_ask()

    return choices[answer]


# -----------------------
# containers
# -----------------------


@fillers.register("array")
def fill_array(schema: Schema, label: str, required: bool) -> Any:  # noqa: FBT001
    """Ask items until the user stops, respecting `minItems`, `maxItems` and `uniqueItems`."""
    if _skipped(schema, label, required=required):
        return MISSING

    items_schema = schema.get("items", {})
    min_items = schema.get("minItems", 0)
    max_items = schema.get("maxItems")
    items: list[Any] = []

    while max_items is None or len(items) < max_items:
        if len(items) >= min_items and not questionary.confirm(
            f"Add an item to '{_name(schema, label)}'?", default=True
        ).unsafe_ask():
            break

        item = fill(items_schema, f"{label}[{len(items)}]")

        if schema.get("uniqueItems") and item in items:
            questionary.print(f"{item!r} is already in '{_name(schema, label)}'", style="fg:red")
            continue

        items.append(item)

    return items


@fillers.register("object")
def fill_object(schema: Schema, label: str, required: bool) -> Any:  # noqa: FBT001
    """Ask each property in order, optional ones can be skipped."""
    if _skipped(schema, label, required=required):
        return MISSING

    required_names = set(schema.get("required", []))
    data: dict[str, Any] = {}

    for name, property_schema in schema.get("properties", {}).items():
        path = f"{label}.{name}" if label else name
        value = fill(property_schema, path, required=name in required_names)

        if value is not MISSING:
            data[name] = value

    return data
