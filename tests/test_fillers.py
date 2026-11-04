from typing import Any

import pytest
from jsonschema import validate
from schemify.fillers import MISSING, InvalidDataError, ask_data, fill, fillers, kind
from schemify.generators import ask_schema
from schemify.registry import NotSupportedError

from .conftest import Prompts


class TestKind:
    @pytest.mark.parametrize(
        ("schema", "expected"),
        [
            ({"type": "string"}, "string"),
            ({"type": "string", "format": "date"}, "date"),
            ({"type": "string", "format": "email"}, "string"),
            ({"type": "integer", "enum": [1, 2]}, "enum"),
            ({"$ref": "#/x"}, "None"),
        ],
    )
    def test_kind(self, schema: dict[str, Any], expected: str) -> None:
        assert kind(schema) == expected

    def test_unsupported_names_the_path(self) -> None:
        schema = {"type": "object", "properties": {"x": {"oneOf": []}}}

        with pytest.raises(NotSupportedError, match="Can not fill 'x'"):
            fill(schema, "")


class TestLeaves:
    @pytest.mark.parametrize(
        ("schema", "answers", "expected"),
        [
            ({"type": "string", "minLength": 2}, ["a", "ab"], "ab"),
            ({"type": "string", "format": "email"}, ["nope", "a@b.c"], "a@b.c"),
            ({"type": "integer", "minimum": 18}, ["x", "17", "18"], 18),
            ({"type": "number", "exclusiveMaximum": 1}, ["1", "0.5"], 0.5),
            ({"type": "string", "format": "date"}, ["2026-02-30", "2026-02-28"], "2026-02-28"),
            (
                {"type": "string", "format": "date-time"},
                ["noon", "2026-11-04T12:00:00+00:00"],
                "2026-11-04T12:00:00+00:00",
            ),
        ],
    )
    def test_rejects_until_valid(
        self, prompts: Prompts, schema: dict[str, Any], answers: list[str], expected: Any
    ) -> None:
        prompts.feed(*answers)

        assert fill(schema, "field") == expected
        assert len(prompts.rejected) == len(answers) - 1

    def test_optional_text_can_be_skipped(self, prompts: Prompts) -> None:
        prompts.feed("")

        assert fill({"type": "integer"}, "age", required=False) is MISSING

    def test_required_string_can_be_empty_when_schema_allows(self, prompts: Prompts) -> None:
        prompts.feed("")

        assert fill({"type": "string"}, "note") == ""

    def test_boolean_and_enum(self, prompts: Prompts) -> None:
        prompts.feed(True, "2")

        assert fill({"type": "boolean"}, "ok") is True
        assert fill({"enum": [1, 2]}, "level") == 2

    def test_optional_choice_asks_first(self, prompts: Prompts) -> None:
        prompts.feed(False)

        assert fill({"type": "boolean"}, "ok", required=False) is MISSING


class TestContainers:
    def test_array_respects_min_max_and_unique(self, prompts: Prompts) -> None:
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 2,
            "uniqueItems": True,
        }
        # first item asked without confirm (minItems), duplicate dropped, stops at maxItems
        prompts.feed("a", True, "a", True, "b")

        assert fill(schema, "tags") == ["a", "b"]
        assert not prompts.answers

    def test_object_skips_missing_optional(self, prompts: Prompts) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "address": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
            "required": ["name"],
        }
        prompts.feed("Rama", "", True, "Homs")

        assert fill(schema, "") == {"name": "Rama", "address": {"city": "Homs"}}
        assert prompts.messages[-1] == "address.city:"

    def test_title_replaces_the_path(self, prompts: Prompts) -> None:
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "title": "Address",
                    "properties": {"city": {"type": "string", "title": "City"}},
                },
            },
        }
        prompts.feed(True, "Homs")

        assert fill(schema, "") == {"address": {"city": "Homs"}}
        assert prompts.messages == ["Add 'Address'?", "City:"]

    def test_description_in_message(self, prompts: Prompts) -> None:
        prompts.feed("x")
        fill({"type": "string", "description": "Full name"}, "name")

        assert prompts.messages == ["name (Full name):"]


class TestAskData:
    def test_whole_schema_is_checked(self, prompts: Prompts) -> None:
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["a"],
            "minProperties": 2,
        }
        prompts.feed("x")

        with pytest.raises(InvalidDataError):
            ask_data(schema)

    def test_round_trip(self, prompts: Prompts) -> None:
        prompts.feed(
            "name", "string", True, "none", False, "2", "", "", "", "Full name", "", True,
            "born", "date", "", "", True,
            "role", "enum", "admin, user", "", "", False,
            "", False,
        )  # fmt: skip
        schema = ask_schema("Person")

        # "R" is too short, role is optional so it is confirmed first
        prompts.feed("R", "Rawaa", "1993-01-01", True, "user")
        data = ask_data(schema)

        assert data == {"name": "Rawaa", "born": "1993-01-01", "role": "user"}
        assert prompts.messages[-4:] == ["Full name:", "born:", "Add 'role'?", "role:"]
        validate(data, schema)


def test_custom_filler(prompts: Prompts) -> None:
    fillers.add(lambda _schema, _label, _required: "custom", "fake-format")

    assert fill({"type": "string", "format": "fake-format"}, "x") == "custom"
