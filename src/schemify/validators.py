"""Validators and parsers for prompt answers and values, they never prompt.

Prompt validators follow the questionary `validate=` contract:
they return `True` when the answer is valid, else the error message.
"""

import math
import re
from collections.abc import Callable, Collection
from datetime import date, datetime
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from .models import Schema

type Parser = Callable[[str], Any]
"""Turns a prompt answer into a value, raises `ValueError` with a readable message."""

type PromptValidator = Callable[[str], bool | str]
"""Returns `True` for a valid answer, else the error message."""

type Constraint = tuple[str, str, Parser, PromptValidator]
"""A schema keyword, its question, the answer parser and the answer validator."""

# -----------------------
# parsers
# -----------------------


def to_int(text: str) -> int:
    """Parse an integer: `"42"`."""
    try:
        return int(text.strip())
    except ValueError:
        message = f"'{text}' is not an integer"
        raise ValueError(message) from None


def to_number(text: str) -> int | float:
    """Parse a finite number, keeping integers as `int`: `"42"`, `"4.2"`."""
    try:
        return to_int(text)
    except ValueError:
        pass

    try:
        number = float(text.strip())
    except ValueError:
        message = f"'{text}' is not a number"
        raise ValueError(message) from None

    if not math.isfinite(number):
        message = f"'{text}' is not a finite number"
        raise ValueError(message)

    return number


def to_non_negative_int(text: str) -> int:
    """Parse an integer that is 0 or more, like a length."""
    number = to_int(text)

    if number < 0:
        message = f"'{text}' must be 0 or more"
        raise ValueError(message)

    return number


def to_positive_number(text: str) -> int | float:
    """Parse a number greater than 0, like `multipleOf`."""
    number = to_number(text)

    if number <= 0:
        message = f"'{text}' must be greater than 0"
        raise ValueError(message)

    return number


def to_regex(text: str) -> str:
    """Check `text` compiles as a regular expression and return it unchanged."""
    try:
        re.compile(text)
    except re.error as e:
        message = f"Invalid regular expression: {e}"
        raise ValueError(message) from None

    return text


def to_choices(text: str) -> list[str]:
    """Parse comma separated choices: `"red, green"` -> `["red", "green"]`."""
    choices = [choice.strip() for choice in text.split(",") if choice.strip()]

    if not choices:
        message = "Enter at least one choice"
        raise ValueError(message)

    if len(set(choices)) != len(choices):
        message = "Choices must be unique"
        raise ValueError(message)

    return choices


def to_date(text: str) -> str:
    """Parse an ISO date, returned as an ISO string: `"2026-11-04"`."""
    return date.fromisoformat(text.strip()).isoformat()


def to_datetime(text: str) -> str:
    """Parse an ISO datetime, returned as an RFC 3339 string.

    A datetime without offset is taken as local time, RFC 3339 requires the offset.
    """
    value = datetime.fromisoformat(text.strip())

    return (value if value.tzinfo else value.astimezone()).isoformat()


# -----------------------
# prompt validators
# -----------------------


def validator(parse: Parser) -> PromptValidator:
    """Build a prompt validator accepting the answers `parse` accepts."""

    def validate(text: str) -> bool | str:
        try:
            parse(text)
        except ValueError as e:
            return str(e)

        return True

    return validate


def optional(validate: PromptValidator) -> PromptValidator:
    """Accept an empty answer (to skip), else run `validate`."""
    return lambda text: not text.strip() or validate(text)


def is_property_name(existing: Collection[str]) -> PromptValidator:
    """Accept a new property name, or an empty answer to finish once one property exists."""

    def validate(text: str) -> bool | str:
        name = text.strip()

        if not name:
            return bool(existing) or "Add at least one property"

        return name not in existing or f"Property '{name}' already exists"

    return validate


# -----------------------
# constraints
# -----------------------

STRING_CONSTRAINTS: list[Constraint] = [
    ("minLength", "Minimum length", to_non_negative_int, validator(to_non_negative_int)),
    ("maxLength", "Maximum length", to_non_negative_int, validator(to_non_negative_int)),
    ("pattern", "Regular expression pattern", to_regex, validator(to_regex)),
    (
        "not",
        "Blocked values, comma separated",
        lambda text: {"enum": to_choices(text)},
        validator(to_choices),
    ),
]
"""The validators asked for a string, mapped to JSON Schema keywords."""

NUMBER_CONSTRAINTS: list[Constraint] = [
    ("exclusiveMinimum", "Greater than", to_number, validator(to_number)),
    ("minimum", "Greater than or equal to", to_number, validator(to_number)),
    ("exclusiveMaximum", "Less than", to_number, validator(to_number)),
    ("maximum", "Less than or equal to", to_number, validator(to_number)),
    ("multipleOf", "Multiple of", to_positive_number, validator(to_positive_number)),
]
"""The validators asked for an integer or a number, mapped to JSON Schema keywords."""

ARRAY_CONSTRAINTS: list[Constraint] = [
    ("minItems", "Minimum items", to_non_negative_int, validator(to_non_negative_int)),
    ("maxItems", "Maximum items", to_non_negative_int, validator(to_non_negative_int)),
]
"""The validators asked for an array, mapped to JSON Schema keywords."""

_BOUNDS = [
    # (lower keyword, upper keyword, can they be equal)
    ("minLength", "maxLength", True),
    ("minItems", "maxItems", True),
    ("minimum", "maximum", True),
    ("minimum", "exclusiveMaximum", False),
    ("exclusiveMinimum", "maximum", False),
    ("exclusiveMinimum", "exclusiveMaximum", False),
]


def check_bounds(schema: Schema) -> str | None:
    """Return why no value can satisfy the bounds of `schema`, or `None` when they can."""
    for low, high, equal_ok in _BOUNDS:
        if low not in schema or high not in schema:
            continue

        if schema[low] > schema[high] or (not equal_ok and schema[low] == schema[high]):
            return f"{low} ({schema[low]}) must be less than {high} ({schema[high]})"

    return None


# -----------------------
# json schema
# -----------------------


def check_schema(schema: Any) -> str | None:
    """Return why `schema` is not a valid JSON Schema object, or `None` when it is."""
    if not isinstance(schema, dict):
        return "A schema must be a JSON object"

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        return e.message

    return None


def check_value(schema: Schema, value: Any) -> str | None:
    """Return why `value` does not match `schema`, or `None` when it does.

    Formats are checked when jsonschema supports them without extras (date, email, uuid, ...).
    """
    validator_ = Draft202012Validator(schema, format_checker=FormatChecker())
    error = next(validator_.iter_errors(value), None)

    return None if error is None else error.message
