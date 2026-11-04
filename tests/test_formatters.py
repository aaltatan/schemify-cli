import ast
import json
from typing import Any

import pytest
from schemify.formatters import formatters, to_javascript, to_json, to_python
from schemify.registry import NotSupportedError

DATA: dict[str, Any] = {
    "name": "رواء",
    "done": True,
    "note": None,
    "first-name": "Rama",
    "tags": ["a", "b"],
    "address": {"city": "Homs", "rooms": []},
    "empty": {},
}


def test_registry() -> None:
    assert formatters.names == ["javascript", "json", "python"]

    with pytest.raises(NotSupportedError, match="Format 'yaml' is not supported"):
        formatters["yaml"]


def test_json_round_trips() -> None:
    text = to_json(DATA)

    assert json.loads(text) == DATA
    assert "رواء" in text


def test_python_is_a_python_literal() -> None:
    text = to_python(DATA)

    assert ast.literal_eval(text) == DATA
    assert "True" in text
    assert "None" in text


def test_javascript() -> None:
    assert to_javascript(DATA) == (
        "{\n"
        '  name: "رواء",\n'
        "  done: true,\n"
        "  note: null,\n"
        '  "first-name": "Rama",\n'
        "  tags: [\n"
        '    "a",\n'
        '    "b"\n'
        "  ],\n"
        "  address: {\n"
        '    city: "Homs",\n'
        "    rooms: []\n"
        "  },\n"
        "  empty: {}\n"
        "}"
    )


@pytest.mark.parametrize("value", [1, 1.5, "x", None, [], {}])
def test_javascript_scalars_are_json(value: Any) -> None:
    assert to_javascript(value) == json.dumps(value)
