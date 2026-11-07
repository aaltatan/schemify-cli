"""Schema generators: ask the user about a type and return its JSON Schema, picked by type name."""

import inspect
import json
from collections.abc import Callable, Sequence
from typing import Any, get_origin

import questionary

from .computers import KEYWORD, computers, groups
from .models import Schema
from .registry import Registry
from .validators import (
    ARRAY_CONSTRAINTS,
    NUMBER_CONSTRAINTS,
    STRING_CONSTRAINTS,
    Constraint,
    default_parser,
    is_choice,
    is_property_name,
    optional,
    validator,
    within_bounds,
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


def _ask_type(message: str, extra: Sequence[str] = ()) -> str:
    choices = [*generators.names, *extra]

    return questionary.select(message, choices=choices, default="string").unsafe_ask()


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
    """Ask for a string limited to choices, one per prompt."""
    choices: list[str] = []

    while choice := (
        questionary.text("Choice (empty to finish):", validate=is_choice(choices))
        .unsafe_ask()
        .strip()
    ):
        choices.append(choice)

    return {"type": "string", "enum": choices}


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
        # a computed property needs earlier properties to compute from
        type_name = _ask_type(f"Type of '{name}':", ["computed"] if properties else [])
        property_schema = (
            _generate_computed(list(properties))
            if type_name == "computed"
            else generators[type_name]()
        )
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

        # a computed property sets its own `default` in `x-compute`
        if type_name != "computed":
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


def _to_options(text: str) -> dict[str, Any]:
    """Parse computer options, a JSON object: `{"sep": ", "}`."""
    try:
        options = json.loads(text)
    except json.JSONDecodeError as e:
        message = f"Invalid JSON: {e.msg}"
        raise ValueError(message) from None

    if not isinstance(options, dict):
        message = "Options must be a JSON object"
        raise ValueError(message)  # noqa: TRY004 - prompt validators catch ValueError

    return options


def _computer_choices() -> list[str | questionary.Separator]:
    """List the computers under a header per group, the ungrouped ones last under 'Other'."""
    grouped = {name for names in groups.values() for name in names}
    other = [name for name in computers.names if name not in grouped]
    choices: list[str | questionary.Separator] = []

    for group, names in {**groups, "Other": other}.items():
        if names:
            choices += [questionary.Separator(f"── {group} ──"), *names]

    return choices


_PLACEHOLDERS: dict[Any, Any] = {str: "text", int: 1, float: 1.5, bool: True, dict: {}, list: []}
_JSON_TYPES = (str, int, float, bool, dict, list, type(None))


def options_example(fn: Callable[..., Any], sources: int) -> dict[str, Any] | None:
    """Return example options of `fn` once `sources` values fill its first parameters.

    An option with a default shows it, a required one a placeholder of its type.
    `None` when `fn` takes no options.
    """
    example: dict[str, Any] = {}
    takes_any = False

    for param in inspect.signature(fn).parameters.values():
        if param.kind is param.VAR_POSITIONAL:
            sources = 0  # it takes the remaining sources
        elif param.kind is param.VAR_KEYWORD:
            takes_any = True
        elif sources and param.kind is not param.KEYWORD_ONLY:
            sources -= 1
        elif param.default is not param.empty and isinstance(param.default, _JSON_TYPES):
            example[param.name] = param.default
        else:
            kind = get_origin(param.annotation) or param.annotation  # `dict[str, Any]` -> `dict`
            example[param.name] = _PLACEHOLDERS.get(kind, "value")

    return example if example or takes_any else None


def _describe(name: str, fn: Callable[..., Any]) -> None:
    """Print the computer signature and summary, so the user knows its sources and options."""
    summary = (inspect.getdoc(fn) or "").split("\n\n")[0]
    questionary.print(f"{name}{inspect.signature(fn)}", style="bold")

    if summary:
        questionary.print(f"  {summary}", style="italic")


def _generate_computed(names: list[str]) -> Schema:
    """Ask how a property is computed from the earlier `names`, and the type of its result.

    Keyword sources (`{"alias": "path"}`), `$.` / `[*]` paths and `default` are written by hand.
    """
    fn = questionary.select("Compute with:", choices=_computer_choices()).unsafe_ask()
    _describe(fn, computers[fn])
    sources = questionary.checkbox("Computed from (in order):", choices=names).unsafe_ask()
    example = options_example(computers[fn], len(sources))
    spec: Schema = {"fn": fn}

    if sources:
        spec["from"] = sources

    if example is not None:
        hint = json.dumps(example, ensure_ascii=False)
        options = questionary.text(
            f"Options as JSON (optional), like {hint}:", validate=optional(validator(_to_options))
        ).unsafe_ask()

        if options.strip():
            spec["options"] = _to_options(options)

    return {**generators[_ask_type("Result type:")](), KEYWORD: spec}
