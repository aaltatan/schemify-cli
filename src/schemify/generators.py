"""Schema generators: ask the user about a type and return its JSON Schema, picked by type name."""

from collections.abc import Callable

import questionary

from .models import Schema
from .registry import Registry
from .validators import (
    ARRAY_CONSTRAINTS,
    NUMBER_CONSTRAINTS,
    STRING_CONSTRAINTS,
    Constraint,
    check_bounds,
    is_property_name,
    optional,
    to_choices,
    validator,
)

type GenerateFn = Callable[[], Schema]

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

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
    """Ask each constraint (empty answer skips it), again until the bounds are satisfiable."""
    while True:
        schema: Schema = {}

        for keyword, question, parse, validate in constraints:
            answer = questionary.text(
                f"{question} (optional):", validate=optional(validate)
            ).unsafe_ask()

            if answer.strip():
                schema[keyword] = parse(answer)

        error = check_bounds(schema)

        if error is None:
            return schema

        questionary.print(f"{error}, try again", style="fg:red")


# -----------------------
# primitive types
# -----------------------


@generators.register("string")
def generate_string() -> Schema:
    """Ask for a string: format (email, uuid), digits only, length, pattern, blocked values."""
    schema: Schema = {"type": "string"}

    if not _wants_validators():
        return schema

    string_format = questionary.select("Format:", choices=["none", "email", "uuid"]).unsafe_ask()

    if string_format != "none":
        return {**schema, "format": string_format}

    constraints = STRING_CONSTRAINTS

    if questionary.confirm("Digits only?", default=False).unsafe_ask():
        schema["pattern"] = r"^\d+$"
        constraints = [c for c in STRING_CONSTRAINTS if c[0] != "pattern"]

    return {**schema, **_ask_constraints(constraints)}


def _number_generator(number_type: str) -> GenerateFn:
    def generate() -> Schema:
        """Ask for an integer or a number: bounds and a multiple."""
        schema: Schema = {"type": number_type}

        if not _wants_validators():
            return schema

        return {**schema, **_ask_constraints(NUMBER_CONSTRAINTS)}

    return generate


generators.add(_number_generator("integer"), "integer")
generators.add(_number_generator("number"), "number")


@generators.register("boolean")
def generate_boolean() -> Schema:
    """Return a boolean."""
    return {"type": "boolean"}


@generators.register("date")
def generate_date() -> Schema:
    """Return an ISO date string: `2026-11-04`."""
    return {"type": "string", "format": "date"}


@generators.register("datetime")
def generate_datetime() -> Schema:
    """Return an RFC 3339 datetime string: `2026-11-04T10:30:00+03:00`."""
    return {"type": "string", "format": "date-time"}


@generators.register("enum")
def generate_enum() -> Schema:
    """Ask for a string limited to choices."""
    answer = questionary.text(
        "Choices, comma separated:", validate=validator(to_choices)
    ).unsafe_ask()

    return {"type": "string", "enum": to_choices(answer)}


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
    """Ask for an object: each property name, type, label, description and if it is required.

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

        if questionary.confirm(f"Is '{name}' required?", default=True).unsafe_ask():
            required.append(name)

    schema: Schema = {"type": "object", "properties": properties}

    if required:
        schema["required"] = required

    if not questionary.confirm("Allow extra properties?", default=False).unsafe_ask():
        schema["additionalProperties"] = False

    return schema
