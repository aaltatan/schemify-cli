from collections.abc import Callable

import pytest
import questionary
from schemify.computers import computers
from schemify.generators import (
    SCHEMA_DIALECT,
    _computer_choices,
    _options_example,
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
            "date",
            "datetime",
            "enum",
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


class TestPrimitives:
    def test_without_validators(self, prompts: Prompts) -> None:
        prompts.feed([False, False, False])

        assert generators["string"]() == {"type": "string"}
        assert generators["integer"]() == {"type": "integer"}
        assert generators["number"]() == {"type": "number"}
        assert not prompts.answers

    def test_no_questions(self, prompts: Prompts) -> None:
        assert generators["boolean"]() == {"type": "boolean"}
        assert generators["date"]() == {"type": "string", "format": "date"}
        assert generators["datetime"]() == {"type": "string", "format": "date-time"}
        assert not prompts.messages

    def test_string_format(self, prompts: Prompts) -> None:
        prompts.feed([True, "email"])

        assert generators["string"]() == {"type": "string", "format": "email"}

    def test_string_validators(self, prompts: Prompts) -> None:
        # validators, no format, not digits, min ("x" rejected), max, pattern, blocked
        prompts.feed([True, "none", False, "x", "2", "10", "^[a-z]+$", "root, admin"])

        assert generators["string"]() == {
            "type": "string",
            "minLength": 2,
            "maxLength": 10,
            "pattern": "^[a-z]+$",
            "not": {"enum": ["root", "admin"]},
        }
        assert prompts.rejected == [("x", "'x' is not an integer")]

    def test_string_digits_only_skips_pattern(self, prompts: Prompts) -> None:
        prompts.feed([True, "none", True, "", "5", ""])

        assert generators["string"]() == {"type": "string", "pattern": r"^\d+$", "maxLength": 5}

    def test_conflicting_bound_is_asked_again(self, prompts: Prompts) -> None:
        # gt skipped, ge 10, lt "1" rejected then "20", le skipped, multiple of 0.5
        prompts.feed([True, "", "10", "1", "20", "", "0.5"])

        assert generators["number"]() == {
            "type": "number",
            "minimum": 10,
            "exclusiveMaximum": 20,
            "multipleOf": 0.5,
        }
        assert prompts.rejected == [("1", "minimum (10) must be less than exclusiveMaximum (1)")]

    def test_enum(self, prompts: Prompts) -> None:
        prompts.feed(["", "red", " red ", "green, blue", ""])

        assert generators["enum"]() == {"type": "string", "enum": ["red", "green, blue"]}
        assert prompts.rejected == [
            ("", "Add at least one choice"),
            (" red ", "Choice 'red' already exists"),
        ]


class TestContainers:
    def test_array(self, prompts: Prompts) -> None:
        # items type, items validators, then array validators: min, max, unique
        prompts.feed(["string", False, True, "1", "", True])

        assert generators["array"]() == {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True,
        }

    def test_object_with_nested_array_of_objects(self, prompts: Prompts) -> None:
        prompts.feed([
            "",  # rejected, no property yet
            "name", "string", False, "", "Full name", "", True,
            "tags", "array", "object",
            "label", "enum", "a", "b", "", "", "", "", True,
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

    def test_computed(self, prompts: Prompts) -> None:
        prompts.feed([
            "first", "string", False, "", "", "", True,
            "last", "string", False, "", "", "", True,
            "full", "computed", "join", ["first", "last"], "{", '{"sep": ", "}', "string", False,
            "Full name", "", True,
            "",
            False,
        ])  # fmt: skip

        assert generators["object"]()["properties"]["full"] == {
            "title": "Full name",
            "type": "string",
            "x-compute": {"fn": "join", "from": ["first", "last"], "options": {"sep": ", "}},
        }
        assert prompts.rejected[0][0] == "{"

    def test_defaults(self, prompts: Prompts) -> None:
        # read as JSON, else as text, the first matching the property schema is kept
        prompts.feed([
            "age", "integer", False, "", "", "x", "30", True,
            "code", "string", False, "", "", "42", False,
            "tags", "array", "string", False, False, "", "", '["a"]', False,
            "",
            False,
        ])  # fmt: skip

        assert generators["object"]()["properties"] == {
            "age": {"type": "integer", "default": 30},
            "code": {"type": "string", "default": "42"},
            "tags": {"type": "array", "items": {"type": "string"}, "default": ["a"]},
        }
        assert prompts.rejected == [("x", "'x' is not of type 'integer'")]

    def test_computer_choices_are_grouped(self) -> None:
        computers.add(lambda: None, "custom")
        choices = _computer_choices()
        headers = [c.title for c in choices if isinstance(c, questionary.Separator)]

        assert headers[0] == "── Text ──"
        assert headers[-1] == "── Other ──"
        assert choices[-1] == "custom"
        assert sorted(c for c in choices if isinstance(c, str)) == computers.names

    @pytest.mark.parametrize(
        ("name", "sources", "expected"),
        [
            ("join", 2, {"sep": " "}),
            ("upper", 1, None),
            ("upper", 0, {"value": "value"}),
            ("replace", 1, {"old": "text", "new": "text"}),
            ("round", 1, {"digits": 2}),
            ("words", 1, {"lang": "en", "to": "cardinal", "currency": None}),
            ("lookup", 1, {"map": {}, "fallback": "value"}),
            ("expr", 0, {"expr": "text"}),
            ("template", 1, {}),  # takes any named values
            ("today", 0, None),
        ],
    )
    def test_options_example(self, name: str, sources: int, expected: object) -> None:
        assert _options_example(computers[name], sources) == expected

    def test_computed_without_options_is_not_asked_them(self, prompts: Prompts) -> None:
        prompts.feed([
            "name", "string", False, "", "", "", True,
            "loud", "computed", "upper", ["name"], "string", False, "", "", True,
            "",
            False,
        ])  # fmt: skip

        assert generators["object"]()["properties"]["loud"]["x-compute"] == {
            "fn": "upper",
            "from": ["name"],
        }
        assert not any(m.startswith("Options") for m in prompts.messages)

    def test_computed_needs_a_property(self, prompts: Prompts) -> None:
        prompts.feed(["first", "computed"])

        with pytest.raises(AssertionError, match="'computed' not in"):
            generators["object"]()

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
