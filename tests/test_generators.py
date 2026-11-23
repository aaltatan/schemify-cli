from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from jsonschema import Draft202012Validator
from schemify.generators import (
    FORMAT_PATTERNS,
    SCHEMA_DIALECT,
    ask_schema,
    generators,
)
from schemify.registry import NotSupportedError, Registry

from .conftest import Prompts


class TestRegistry:
    def test_builtin_types(self) -> None:
        assert generators.names == [
            "array",
            "boolean",
            "integer",
            "number",
            "object",
            "string",
        ]

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(NotSupportedError, match="Type 'uuid' is not supported"):
            generators["uuid"]

    def test_register_and_case_insensitive(self) -> None:
        registry = Registry[Callable[[], dict]]("Type")

        @registry.register("fake", "other")
        def generate_fake() -> dict:
            return {}

        assert registry["FAKE"] is generate_fake
        assert "other" in registry
        assert 1 not in registry


class TestFormatPatterns:
    """Without a format checker, like most validators by default, the pattern still checks."""

    @pytest.mark.parametrize(
        ("string_format", "valid", "invalid"),
        [
            ("date", [date(2026, 11, 4).isoformat()], ["2026-13-01", "2026-1-01", "hello"]),
            (
                "date-time",
                [
                    datetime(
                        2026, 11, 4, 10, 30, 0, 123456, timezone(timedelta(hours=3))
                    ).isoformat(),
                    datetime(2026, 11, 4, 10, 30, tzinfo=UTC).isoformat(),
                    "2026-11-04T10:30:00Z",
                ],
                ["2026-11-04 10:30:00Z", "2026-11-04T10:30:00", "2026-11-04T25:00:00Z", "hello"],
            ),
            ("email", ["a@b.co"], ["nope", "a@b", "a b@c.d"]),
            (
                "uuid",
                ["123e4567-e89b-12d3-a456-426614174000"],
                ["123e4567e89b12d3a456426614174000", "hello"],
            ),
        ],
    )
    def test_pattern(self, string_format: str, valid: list[str], invalid: list[str]) -> None:
        validator = Draft202012Validator(
            {"type": "string", "pattern": FORMAT_PATTERNS[string_format]}
        )

        assert all(validator.is_valid(value) for value in valid)
        assert not any(validator.is_valid(value) for value in invalid)


class TestPrimitives:
    def test_without_validators(self, prompts: Prompts) -> None:
        prompts.feed(["none", False, False, False])

        assert generators["string"]() == {"type": "string"}
        assert generators["integer"]() == {"type": "integer"}
        assert generators["number"]() == {"type": "number"}
        assert not prompts.answers

    def test_no_questions(self, prompts: Prompts) -> None:
        assert generators["boolean"]() == {"type": "boolean"}
        assert not prompts.messages

    @pytest.mark.parametrize("string_format", ["date", "date-time", "email", "uuid"])
    def test_string_format(self, prompts: Prompts, string_format: str) -> None:
        prompts.feed([string_format])

        assert generators["string"]() == {
            "type": "string",
            "format": string_format,
            "pattern": FORMAT_PATTERNS[string_format],
        }
        assert not prompts.answers

    def test_string_validators(self, prompts: Prompts) -> None:
        # no format, validators, no choices, not digits, min ("x" rejected), max, pattern, blocked
        prompts.feed(["none", True, False, False, "x", "2", "10", "^[a-z]+$", "root, admin"])

        assert generators["string"]() == {
            "type": "string",
            "minLength": 2,
            "maxLength": 10,
            "pattern": "^[a-z]+$",
            "not": {"enum": ["root", "admin"]},
        }
        assert prompts.rejected == [("x", "'x' is not an integer")]

    def test_string_digits_only_skips_pattern(self, prompts: Prompts) -> None:
        prompts.feed(["none", True, False, True, "", "5", ""])

        assert generators["string"]() == {"type": "string", "pattern": "^[0-9]+$", "maxLength": 5}

    def test_conflicting_bound_is_asked_again(self, prompts: Prompts) -> None:
        # no choices, gt skipped, ge 10, lt "1" rejected then "20", le skipped, multiple of 0.5
        prompts.feed([True, False, "", "10", "1", "20", "", "0.5"])

        assert generators["number"]() == {
            "type": "number",
            "minimum": 10,
            "exclusiveMaximum": 20,
            "multipleOf": 0.5,
        }
        assert prompts.rejected == [("1", "minimum (10) must be less than exclusiveMaximum (1)")]

    def test_string_choices(self, prompts: Prompts) -> None:
        prompts.feed(["none", True, True, "", "red", " red ", "green, blue", ""])

        assert generators["string"]() == {"type": "string", "enum": ["red", "green, blue"]}
        assert prompts.rejected == [
            ("", "Add at least one choice"),
            (" red ", "Choice 'red' already exists"),
        ]

    def test_number_choices(self, prompts: Prompts) -> None:
        prompts.feed([True, True, "x", "1", "2", " 2 ", ""])

        assert generators["integer"]() == {"type": "integer", "enum": [1, 2]}
        assert prompts.rejected == [
            ("x", "'x' is not an integer"),
            (" 2 ", "Choice '2' already exists"),
        ]


class TestContainers:
    def test_array(self, prompts: Prompts) -> None:
        # items type, items format and validators, then array validators: min, max, unique
        prompts.feed(["string", "none", False, True, "1", "", True])

        assert generators["array"]() == {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True,
        }

    def test_object_with_nested_array_of_objects(self, prompts: Prompts) -> None:
        prompts.feed([
            "",  # rejected, no property yet
            "name", "string", "none", False, "", "Full name", "", True,
            "tags", "array", "object",
            "label", "string", "none", True, True, "a", "b", "", "", "", "", True,
            "", True,  # end of the tag object, allow extra properties
            False,  # no array validators
            "Tags", "", "", False,  # tags: label, no description, no default, optional
            "",  # end of the root object
            False,
        ])  # fmt: skip

        assert generators["object"]() == {
            "type": "object",
            "properties": {
                "name": {"description": "Full name", "type": "string"},
                "tags": {
                    "title": "Tags",
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"label": {"type": "string", "enum": ["a", "b"]}},
                        "required": ["label"],
                    },
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        }
        assert prompts.rejected == [("", "Add at least one property")]

    def test_defaults(self, prompts: Prompts) -> None:
        # read as JSON, else as text, the first matching the property schema is kept
        prompts.feed([
            "age", "integer", False, "", "", "x", "30", True,
            "code", "string", "none", False, "", "", "42", False,
            "tags", "array", "string", "none", False, False, "", "", '["a"]', False,
            "",
            False,
        ])  # fmt: skip

        assert generators["object"]()["properties"] == {
            "age": {"type": "integer", "default": 30},
            "code": {"type": "string", "default": "42"},
            "tags": {"type": "array", "items": {"type": "string"}, "default": ["a"]},
        }
        assert prompts.rejected == [("x", "'x' is not of type 'integer'")]

    def test_ask_schema(self, prompts: Prompts) -> None:
        prompts.feed(["done", "boolean", "", "", "", True, "", False])

        assert ask_schema("Task") == {
            "$schema": SCHEMA_DIALECT,
            "title": "Task",
            "type": "object",
            "properties": {"done": {"type": "boolean"}},
            "required": ["done"],
            "additionalProperties": False,
        }
