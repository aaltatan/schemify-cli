"""Data formatters: turn filled data into source text, picked by format name.

Each format name is also its pygments lexer name, used to highlight the printed output.
"""

import json
import pprint
import re
from collections.abc import Callable
from typing import Any

from .registry import Registry

type FormatFn = Callable[[Any], str]

formatters = Registry[FormatFn]("Format")
"""The default registry, used by the `fill --format` option."""


@formatters.register("json")
def to_json(data: Any) -> str:
    """Format as indented JSON, keeping non-ASCII characters."""
    return json.dumps(data, indent=2, ensure_ascii=False)


@formatters.register("python")
def to_python(data: Any) -> str:
    """Format as a Python literal: `{'done': True, 'note': None}`."""
    return pprint.pformat(data, sort_dicts=False)


@formatters.register("javascript")
def to_javascript(data: Any) -> str:
    """Format as a JavaScript object literal, quoting only the keys that need it."""
    return _javascript(data, 0)


# -----------------------
# utils
# -----------------------

_JS_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def _javascript_key(key: str) -> str:
    return key if _JS_IDENTIFIER.fullmatch(key) else json.dumps(key, ensure_ascii=False)


def _javascript(value: Any, level: int) -> str:
    indent = "  " * (level + 1)
    closing_indent = "  " * level

    if isinstance(value, dict) and value:
        lines = [
            f"{indent}{_javascript_key(k)}: {_javascript(v, level + 1)}" for k, v in value.items()
        ]

        return "{\n" + ",\n".join(lines) + f"\n{closing_indent}}}"

    if isinstance(value, list) and value:
        lines = [f"{indent}{_javascript(item, level + 1)}" for item in value]

        return "[\n" + ",\n".join(lines) + f"\n{closing_indent}]"

    # scalars, `{}` and `[]`: JSON is valid JavaScript
    return json.dumps(value, ensure_ascii=False)
