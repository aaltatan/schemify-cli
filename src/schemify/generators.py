"""Schema generators: ask the user about a type and return its JSON Schema, picked by type name."""

from collections.abc import Callable
from typing import Any

import questionary

from .models import Schema
from .registry import Registry
from .validators import (
    ARRAY_CONSTRAINTS,
    NUMBER_CONSTRAINTS,
    STRING_CONSTRAINTS,
    Constraint,
    Parser,
    default_parser,
    is_choice,
    is_property_name,
    optional,
    to_int,
    to_number,
    validator,
    within_bounds,
)

type GenerateFn = Callable[[], Schema]

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

_DATE = r"[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])"

# `format` is only an annotation in 2020-12, most validators skip it unless told to check
# formats, but every one checks `pattern`: ASCII classes, no lookaround, so it reads the same
# in JS, Python, Go (RE2), Rust, Java and .NET.
# shortcut: dates are not checked against the calendar (02-31 passes), format checking does that
FORMAT_PATTERNS = {
    "date": rf"^{_DATE}$",
    "date-time": (
        rf"^{_DATE}[Tt]([01][0-9]|2[0-3]):[0-5][0-9]:([0-5][0-9]|60)(\.[0-9]+)?"
        r"([Zz]|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$"
    ),
    "email": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
}

DIGITS_ONLY = r"^[0-9]+$"


def _formatted(string_format: str) -> Schema:
    return {"type": "string", "format": string_format, "pattern": FORMAT_PATTERNS[string_format]}


generators = Registry[GenerateFn]("Type")
"""The default registry, every registered type is offered in the type prompts."""


def ask_schema(title: str | None = None) -> Schema:
    """Ask the user for the properties of an object and return its JSON Schema."""
    header = {"$schema": SCHEMA_DIALECT, "title": title} if title else {"$schema": SCHEMA_DIALECT}

    return {**header, **generators["object"]()}


# -----------------------
# utils
# -----------------------


def _ask_type(message: str) -> str:
    return questionary.select(message, choices=generators.names, default="string").unsafe_ask()


def _wants_validators() -> bool:
    return questionary.confirm("Add validators?", default=False).unsafe_ask()


def _ask_constraints(constraints: list[Constraint]) -> Schema:
    """Ask each constraint, an empty answer skips it, a conflicting bound is asked again."""
    schema: Schema = {}

    for constraint in constraints:
        keyword, question, parse, _ = constraint
        answer = questionary.text(
            f"{question} (optional):", validate=optional(within_bounds(schema, constraint))
        ).unsafe_ask()

        if answer.strip():
            schema[keyword] = parse(answer)

    return schema


def _wants_choices() -> bool:
    return questionary.confirm("Limit to choices?", default=False).unsafe_ask()


def _ask_choices(parse: Parser) -> list[Any]:
    """Ask for choices, one per prompt, each parsed with `parse`."""
    choices: list[Any] = []

    while answer := (
        questionary.text("Choice (empty to finish):", validate=is_choice(choices, parse))
        .unsafe_ask()
        .strip()
    ):
        choices.append(parse(answer))

    return choices


# -----------------------
# primitive types
# -----------------------


@generators.register("string")
def generate_string() -> Schema:
    """Ask for a string: format (date, email, ...), choices, digits only, length, pattern."""
    string_format = questionary.select(
        "Format:", choices=["none", "date", "date-time", "email", "uuid"]
    ).unsafe_ask()

    if string_format != "none":
        return _formatted(string_format)

    schema: Schema = {"type": "string"}

    if not _wants_validators():
        return schema

    if _wants_choices():
        return {**schema, "enum": _ask_choices(str.strip)}

    constraints = STRING_CONSTRAINTS

    if questionary.confirm("Digits only?", default=False).unsafe_ask():
        schema["pattern"] = DIGITS_ONLY
        constraints = [c for c in STRING_CONSTRAINTS if c[0] != "pattern"]

    return {**schema, **_ask_constraints(constraints)}


def _number_generator(number_type: str, parse: Parser) -> GenerateFn:
    def generate() -> Schema:
        """Ask for an integer or a number: choices, or bounds and a multiple."""
        schema: Schema = {"type": number_type}

        if not _wants_validators():
            return schema

        if _wants_choices():
            return {**schema, "enum": _ask_choices(parse)}

        return {**schema, **_ask_constraints(NUMBER_CONSTRAINTS)}

    return generate


generators.add(_number_generator("integer", to_int), "integer")
generators.add(_number_generator("number", to_number), "number")


@generators.register("boolean")
def generate_boolean() -> Schema:
    """Return a boolean."""
    return {"type": "boolean"}


# -----------------------
# container types
# -----------------------


@generators.register("array")
def generate_array() -> Schema:
    """Ask for a list of items of one type: size and unique items."""
    items = generators[_ask_type("Items type:")]()
    schema: Schema = {"type": "array", "items": items}

    if not _wants_validators():
        return schema

    schema = {**schema, **_ask_constraints(ARRAY_CONSTRAINTS)}

    if questionary.confirm("Unique items?", default=False).unsafe_ask():
        schema["uniqueItems"] = True

    return schema


@generators.register("object")
def generate_object() -> Schema:
    """Ask for an object: each property name, type, label, description, default, and if required.

    The label is saved as the JSON Schema `title`, fillers show it instead of the property name.
    """
    properties: Schema = {}
    required: list[str] = []

    while (
        name := questionary.text(
            "Property name (empty to finish):", validate=is_property_name(properties)
        )
        .unsafe_ask()
        .strip()
    ):
        property_schema = generators[_ask_type(f"Type of '{name}':")]()
        annotations = {
            "title": questionary.text(f"Label shown instead of '{name}' when filling (optional):")
            .unsafe_ask()
            .strip(),
            "description": questionary.text(f"Description of '{name}' (optional):")
            .unsafe_ask()
            .strip(),
        }

        properties[name] = {
            **{keyword: value for keyword, value in annotations.items() if value},
            **property_schema,
        }

        parse = default_parser(property_schema)
        default = questionary.text(
            f"Default value of '{name}' (optional):", validate=optional(validator(parse))
        ).unsafe_ask()

        if default.strip():
            properties[name]["default"] = parse(default)

        if questionary.confirm(f"Is '{name}' required?", default=True).unsafe_ask():
            required.append(name)

        questionary.print("")  # separate each property's questions from the next

    schema: Schema = {"type": "object", "properties": properties}

    if required:
        schema["required"] = required

    if not questionary.confirm("Allow extra properties?", default=False).unsafe_ask():
        schema["additionalProperties"] = False

    return schema
