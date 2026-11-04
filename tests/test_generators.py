import pytest
from schemify.generators import SCHEMA_DIALECT, ask_schema, generators
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
        registry = Registry("Type")

        @registry.register("fake", "other")
        def generate_fake() -> dict:
            return {}

        assert registry["FAKE"] is generate_fake
        assert "other" in registry
        assert 1 not in registry


class TestPrimitives:
    def test_without_validators(self, prompts: Prompts) -> None:
        prompts.feed(False, False, False)

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
        prompts.feed(True, "email")

        assert generators["string"]() == {"type": "string", "format": "email"}

    def test_string_validators(self, prompts: Prompts) -> None:
        # validators, no format, not digits, min ("x" rejected), max, pattern, blocked
        prompts.feed(True, "none", False, "x", "2", "10", "^[a-z]+$", "root, admin")

        assert generators["string"]() == {
            "type": "string",
            "minLength": 2,
            "maxLength": 10,
            "pattern": "^[a-z]+$",
            "not": {"enum": ["root", "admin"]},
        }
        assert prompts.rejected == [("x", "'x' is not an integer")]

    def test_string_digits_only_skips_pattern(self, prompts: Prompts) -> None:
        prompts.feed(True, "none", True, "", "5", "")

        assert generators["string"]() == {"type": "string", "pattern": r"^\d+$", "maxLength": 5}

    def test_number_bounds_asked_again_when_unsatisfiable(self, prompts: Prompts) -> None:
        # first round: minimum 10 > maximum 1, second round: minimum 1, multiple of 0.5
        prompts.feed(True, "", "10", "", "1", "", "", "1", "", "", "0.5")

        assert generators["number"]() == {"type": "number", "minimum": 1, "multipleOf": 0.5}

    def test_enum(self, prompts: Prompts) -> None:
        prompts.feed("a, a", "red, green")

        assert generators["enum"]() == {"type": "string", "enum": ["red", "green"]}
        assert prompts.rejected == [("a, a", "Choices must be unique")]


class TestContainers:
    def test_array(self, prompts: Prompts) -> None:
        # items type, items validators, then array validators: min, max, unique
        prompts.feed("string", False, True, "1", "", True)

        assert generators["array"]() == {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "uniqueItems": True,
        }

    def test_object_with_nested_array_of_objects(self, prompts: Prompts) -> None:
        prompts.feed(
            "",  # rejected, no property yet
            "name", "string", False, "Full name", True,
            "tags", "array", "object",
            "label", "enum", "a, b", "", True,
            "", True,  # end of the tag object, allow extra properties
            False,  # no array validators
            "", False,  # tags: no description, optional
            "",  # end of the root object
            False,
        )  # fmt: skip

        assert generators["object"]() == {
            "type": "object",
            "properties": {
                "name": {"description": "Full name", "type": "string"},
                "tags": {
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

    def test_ask_schema(self, prompts: Prompts) -> None:
        prompts.feed("done", "boolean", "", True, "", False)

        assert ask_schema("Task") == {
            "$schema": SCHEMA_DIALECT,
            "title": "Task",
            "type": "object",
            "properties": {"done": {"type": "boolean"}},
            "required": ["done"],
            "additionalProperties": False,
        }
