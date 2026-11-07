import inspect
import re
from collections.abc import Callable
from datetime import date
from typing import Any, ClassVar

import pytest
from schemify.computers import ComputeError, compute, computers, resolve
from schemify.registry import NotSupportedError


class TestComputers:
    @pytest.mark.parametrize(
        ("name", "args", "options", "expected"),
        [
            # text
            ("join", ["Rama", None, "", "Ali"], {}, "Rama Ali"),
            ("join", [["a", "b"], "c"], {"sep": ", "}, "a, b, c"),
            ("concat", ["ab", 1], {}, "ab1"),
            ("upper", ["abc"], {}, "ABC"),
            ("lower", ["ABC"], {}, "abc"),
            ("title", ["rama ali"], {}, "Rama Ali"),
            ("capitalize", ["rama ali"], {}, "Rama ali"),
            ("trim", ["  x "], {}, "x"),
            ("replace", ["a-b-c"], {"old": "-", "new": "/"}, "a/b/c"),
            ("slice", ["2026-11-04"], {"end": 4}, "2026"),
            ("slice", [[1, 2, 3]], {"start": 1}, [2, 3]),
            ("initials", ["rama ali", "x"], {}, "RAX"),
            ("slug", ["  Hello, World! "], {}, "hello-world"),
            ("slug", ["مرحبا بالعالم"], {}, "مرحبا-بالعالم"),
            ("length", ["abc"], {}, 3),
            ("length", [[1, 2]], {}, 2),
            ("pad", [42], {"width": 5}, "00042"),
            ("mask", ["12345678"], {}, "****5678"),
            ("mask", ["12"], {}, "12"),
            # numbers
            ("sum", [1, [2, 3]], {}, 6),
            ("subtract", [10, 3, [2]], {}, 5),
            ("multiply", [2, [3, 4]], {}, 24),
            ("divide", [1, 4], {}, 0.25),
            ("average", [[1, 2, 3]], {}, 2),
            ("min", [[3, 1], 2], {}, 1),
            ("max", [[3, 1], 2], {}, 3),
            ("abs", [-2], {}, 2),
            ("round", [2.3456], {}, 2.35),
            ("round", [2.3456], {"digits": 0}, 2),
            ("percent", [1, 4], {}, 25),
            ("percent_of", [200, 15], {}, 30),
            # words
            ("words", [12], {}, "twelve"),
            ("words", [2], {"to": "ordinal"}, "second"),
            ("words", [1.5], {"to": "currency", "currency": "USD"}, "one dollar, fifty cents"),
            ("words", [3], {"lang": "ar"}, "ثلاثة"),
            # dates
            ("add_days", ["2026-12-31"], {"days": 1}, "2027-01-01"),
            ("add_days", ["2026-11-04T10:00:00+03:00"], {"days": -4}, "2026-10-31"),
            ("add_months", ["2026-01-31"], {"months": 1}, "2026-02-28"),
            ("add_months", ["2026-01-15"], {"months": -2}, "2025-11-15"),
            ("add_years", ["2028-02-29"], {"years": 1}, "2029-02-28"),
            ("days_between", ["2026-01-01", "2026-03-01"], {}, 59),
            ("age", ["2000-11-05"], {"on": "2026-11-04"}, 25),
            ("age", ["2000-11-04"], {"on": "2026-11-04"}, 26),
            ("year", ["2026-11-04"], {}, 2026),
            ("month", ["2026-11-04"], {}, 11),
            ("day", ["2026-11-04"], {}, 4),
            ("weekday", ["2026-11-04"], {}, "Wednesday"),
            ("format_date", ["2026-11-04"], {}, "04/11/2026"),
            ("format_date", ["2026-11-04T10:30:00"], {"fmt": "%H:%M"}, "10:30"),
            ("start_of_month", ["2026-11-04"], {}, "2026-11-01"),
            ("end_of_month", ["2028-02-04"], {}, "2028-02-29"),
            # logic, lookup and misc
            ("coalesce", [None, "", 0, 1], {}, 0),
            ("if_else", [True, "a", "b"], {}, "a"),
            ("if_else", [0, "a", "b"], {}, "b"),
            ("equals", [1, 1], {}, True),
            ("lookup", ["SY"], {"map": {"SY": "Syria"}}, "Syria"),
            ("lookup", [1], {"map": {"1": "one"}}, "one"),
            ("lookup", ["XX"], {"map": {}, "fallback": "?"}, "?"),
            ("constant", [], {"value": 7}, 7),
            ("count", [[1, 2]], {}, 2),
            ("count_if", [["a", "b", "a"], "a"], {}, 2),
            ("unique", [[2, 1, 2]], {}, [2, 1]),
        ],
    )
    def test_computer(self, name: str, args: list[Any], options: dict, expected: Any) -> None:
        assert computers[name](*args, **options) == expected

    @pytest.mark.parametrize(
        ("name", "pattern"),
        [
            ("today", r"^\d{4}-\d{2}-\d{2}$"),
            ("now", r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"),
            ("uuid", r"^[0-9a-f-]{36}$"),
        ],
    )
    def test_no_arguments(self, name: str, pattern: str) -> None:
        assert re.match(pattern, computers[name]())

    def test_today_is_today(self) -> None:
        assert computers["today"]() == date.today().isoformat()  # noqa: DTZ011

    def test_template(self) -> None:
        assert computers["template"]("{n} @ {c}", n="Rama", c="Acme") == "Rama @ Acme"

    @pytest.mark.parametrize(
        ("fn", "error"),
        [
            (lambda: computers["divide"](1, 0), ZeroDivisionError),
            (lambda: computers["coalesce"](None, ""), ValueError),
            (lambda: computers["lookup"]("XX", map={}), ValueError),
            (computers["average"], ValueError),
            (lambda: computers["words"](1, lang="ar", currency="SYP"), ValueError),
            (lambda: computers["words"](1, lang="ar", to="currency", currency="SYP"), ValueError),
        ],
    )
    def test_errors(self, fn: Callable[[], Any], error: type[Exception]) -> None:
        with pytest.raises(error):
            fn()

    @pytest.mark.parametrize("name", computers.names)
    def test_signature_is_stable_across_runs(self, name: str) -> None:
        assert " at 0x" not in str(inspect.signature(computers[name]))


class TestExpr:
    @pytest.mark.parametrize(
        ("expression", "values", "expected"),
        [
            ("q * p", {"q": 2, "p": 3}, 6),
            ("round(q * p * 1.15, 2)", {"q": 3, "p": 9.99}, 34.47),
            ("-a + b // 2 - b % 3 + 2 ** 3", {"a": 1, "b": 7}, 9),
            ("max(a, b) if a > 0 and not b == 0 else 0", {"a": 1, "b": 5}, 5),
            ("1 < a <= 3", {"a": 3}, True),
            ("sum(xs) / 2", {"xs": [2, 4]}, 3),
            ("min([a, b])", {"a": 2, "b": 1}, 1),
            ("'big' if a > 10 or b else 'small'", {"a": 1, "b": 0}, "small"),
        ],
    )
    def test_evaluates(self, expression: str, values: dict[str, Any], expected: Any) -> None:
        assert computers["expr"](expression, **values) == expected

    @pytest.mark.parametrize(
        "expression",
        [
            "__import__('os').system('echo hi')",
            "a.__class__",
            "open('x')",
            "unknown + 1",
            "[x for x in a]",
            "a[0]",
            "lambda: 1",
            "2 ** a",
            "1 +",
        ],
    )
    def test_rejects(self, expression: str) -> None:
        with pytest.raises(ValueError, match=r"not allowed|too large|Invalid expression"):
            computers["expr"](expression, a=10**6)


class TestResolve:
    data: ClassVar[dict[str, Any]] = {
        "name": "Rama",
        "address": {"city": "Homs"},
        "items": [{"p": 1}, {}, {"p": 3}],
    }

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("name", "Rama"),
            ("address.city", "Homs"),
            ("items[0].p", 1),
            ("items[*].p", [1, 3]),
            ("$.company", "Acme"),
            ("middle?", None),
            ("address.zip?", None),
        ],
    )
    def test_paths(self, path: str, expected: Any) -> None:
        assert resolve(path, self.data, {"company": "Acme"}) == expected

    @pytest.mark.parametrize("path", ["middle", "items[5]", "items[1].p", "name.first"])
    def test_missing(self, path: str) -> None:
        with pytest.raises(LookupError):
            resolve(path, self.data, self.data)


def _computed(fn: str, **spec: Any) -> dict[str, Any]:
    return {"x-compute": {"fn": fn, **spec}}


class TestCompute:
    def test_invoice(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "company": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "qty": {"type": "integer"},
                            "price": {"type": "number"},
                            "line": _computed(
                                "expr",
                                **{
                                    "from": {"q": "qty", "p": "price"},
                                    "options": {"expr": "q * p"},
                                },
                            ),
                            "label": _computed(
                                "template",
                                **{"from": {"c": "$.company"}, "options": {"template": "{c} item"}},
                            ),
                        },
                    },
                },
                "total": _computed("sum", **{"from": ["items[*].line"]}),
                "words": _computed("words", **{"from": ["total"]}),
                "count": _computed("count", **{"from": ["items"]}),
            },
        }
        data = {"company": "Acme", "items": [{"qty": 2, "price": 5}, {"qty": 1, "price": 3}]}

        assert compute(schema, data) == {
            "company": "Acme",
            "items": [
                {"qty": 2, "price": 5, "line": 10, "label": "Acme item"},
                {"qty": 1, "price": 3, "line": 3, "label": "Acme item"},
            ],
            "total": 13,
            "words": "thirteen",
            "count": 2,
        }

    def test_keeps_the_schema_order(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "full": _computed("join", **{"from": ["first", "last"]}),
                "first": {"type": "string"},
                "last": {"type": "string"},
            },
        }

        assert list(compute(schema, {"first": "A", "last": "B"})) == ["full", "first", "last"]

    @pytest.mark.parametrize(
        ("spec", "expected"),
        [
            ({"from": ["first", "middle", "last"]}, {}),
            ({"from": ["first", "middle", "last"], "default": "?"}, {"full": "?"}),
            ({"from": ["first", "middle?", "last"]}, {"full": "A B"}),
        ],
    )
    def test_missing_source(self, spec: dict[str, Any], expected: dict[str, Any]) -> None:
        schema = {
            "type": "object",
            "properties": {
                "first": {"type": "string"},
                "middle": {"type": "string"},
                "last": {"type": "string"},
                "full": _computed("join", **spec),
            },
        }

        assert compute(schema, {"first": "A", "last": "B"}) == {
            "first": "A",
            "last": "B",
            **expected,
        }

    def test_unknown_property(self) -> None:
        schema = {"type": "object", "properties": {"x": _computed("upper", **{"from": ["nmae"]})}}

        with pytest.raises(ComputeError, match="'nmae' is not a property"):
            compute(schema, {})

    def test_bad_value(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "x": _computed("divide", **{"from": ["a", "a"]}),
            },
        }

        with pytest.raises(ComputeError, match="Can not compute 'x' with 'divide'"):
            compute(schema, {"a": 0})

    def test_unknown_computer(self) -> None:
        with pytest.raises(NotSupportedError, match="Computer 'nope'"):
            compute({"type": "object", "properties": {"x": _computed("nope")}}, {})
