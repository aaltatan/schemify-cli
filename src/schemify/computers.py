"""Computers: functions filling a property from other values instead of asking for it.

A property with the `x-compute` keyword is not asked, it is computed once the data is entered:

```json
"full_name": {"type": "string", "x-compute": {"fn": "join", "from": ["first", "last"]}}
```

- `fn`: a registered computer name.
- `from` (optional): the source paths, a list passed as positional arguments,
  or an `{alias: path}` object passed as keyword arguments (used by `template` and `expr`).
- `options` (optional): extra keyword arguments, like `{"sep": ", "}`.
- `default` (optional): the value when a source is missing, else the property is left out.

Paths are relative to the object owning the property (`name`, `address.city`, `items[0]`),
or to the data root (`$.company`). `items[*].price` gives the list of every item price.
A path ending with `?` gives `None` when missing instead of skipping the computation,
for optional parts like `middle_name?` in a `join`.

Date computers compute today as their date when it is left out or `None`, so `year` with no
source is the current year, and `format_date` from `issued?` is today when `issued` is skipped.
"""

import ast
import calendar
import math
import operator
import re
import statistics
import unicodedata
import uuid as uuid_
from collections.abc import Callable, Iterable
from datetime import date, datetime
from typing import Any

from num2words import num2words

from .models import Schema
from .registry import Registry

type ComputeFn = Callable[..., Any]
"""Called with the source values then the options: `fn(*values, **options)`."""

KEYWORD = "x-compute"

computers = Registry[ComputeFn]("Computer")
"""The default registry, used by `compute`."""

groups: dict[str, list[str]] = {}
"""The built-in computer names by group, in order, for the prompts.

Computers registered elsewhere are not in a group.
"""


def _register(group: str, name: str) -> Callable[[ComputeFn], ComputeFn]:
    """Register a built-in computer under `name`, listed in `group`."""
    groups.setdefault(group, []).append(name)

    return computers.register(name)


class ComputeError(ValueError):
    """Raised when a computed property can not be computed (bad path, bad value, ...)."""


class _MissingError(LookupError):
    """A source path has no value in the data, like a skipped optional property."""


def compute(schema: Schema, data: Any, root: Any = None) -> Any:  # noqa: C901
    """Fill every `x-compute` property of `data` in place, and return it.

    Children are computed first, so a parent can aggregate them (`sum` of `items[*].total`),
    then the object's own computed properties, in order, so one can use an earlier one.

    Raises:
        NotSupportedError: A computer name is not registered.
        ComputeError: A source path is not a property, or the computer rejects its values.

    """
    root = data if root is None else root

    if isinstance(data, list):
        for item in data:
            compute(schema.get("items", {}), item, root)

        return data

    if not isinstance(data, dict):
        return data

    properties: Schema = schema.get("properties", {})

    for name, property_schema in properties.items():
        if name in data and KEYWORD not in property_schema:
            compute(property_schema, data[name], root)

    for name, property_schema in properties.items():
        if KEYWORD not in property_schema:
            continue

        value = _apply(property_schema[KEYWORD], name, data, root, properties)

        if value is not _SKIP:
            data[name] = value

    # computed properties were added last, put every property back in the schema order
    for name in properties:
        if name in data:
            data[name] = data.pop(name)

    return data


_SKIP: Any = object()


def _apply(spec: Schema, name: str, data: dict[str, Any], root: Any, properties: Schema) -> Any:
    """Run the computer of `spec` for the property `name` of `data`."""
    fn = computers[spec["fn"]]
    sources = spec.get("from", [])
    options = spec.get("options", {})

    for path in sources.values() if isinstance(sources, dict) else sources:
        first = re.split(r"[.\[?]", path, maxsplit=1)[0]

        if not path.startswith("$") and first not in properties:
            message = f"Can not compute '{name}': '{path}' is not a property"
            raise ComputeError(message)

    try:
        if isinstance(sources, dict):
            args: list[Any] = []
            kwargs = {alias: resolve(path, data, root) for alias, path in sources.items()}
        else:
            args = [resolve(path, data, root) for path in sources]
            kwargs = {}
    except _MissingError:
        return spec.get("default", _SKIP)

    try:
        return fn(*args, **kwargs, **options)
    except (ValueError, TypeError, ArithmeticError, LookupError, NotImplementedError) as e:
        message = f"Can not compute '{name}' with '{spec['fn']}': {e}"
        raise ComputeError(message) from e


_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+|\*)\]")


def resolve(path: str, data: Any, root: Any = None) -> Any:
    """Return the value at `path` in `data`, or from `root` when the path starts with `$.`.

    Raises:
        _MissingError: Nothing is at `path`, and it does not end with `?`.

    """
    optional = path.endswith("?")
    path = path.removesuffix("?")
    current, path = (
        (root, path.removeprefix("$").lstrip(".")) if path.startswith("$") else (data, path)
    )
    values = [current]
    spread = False

    for name, index in _TOKEN.findall(path):
        if index == "*":
            values = [item for value in values if isinstance(value, list) for item in value]
            spread = True
            continue

        key: str | int = name or int(index)
        found = [_get(value, key) for value in values]
        # a spread path skips the items missing the value, like an optional item price
        values = [value for value in found if value is not _SKIP] if spread else found

    if spread:
        return values

    if values[0] is _SKIP:
        if optional:
            return None

        raise _MissingError(path)

    return values[0]


def _get(container: Any, key: str | int) -> Any:
    try:
        return container[key]
    except (KeyError, IndexError, TypeError):
        return _SKIP


# -----------------------
# utils
# -----------------------


def _flat(values: Iterable[Any]) -> list[Any]:
    """Spread lists one level, so `sum(a, items[*].price)` sums every value."""
    return [item for value in values for item in (value if isinstance(value, list) else [value])]


def _present(values: Iterable[Any]) -> list[Any]:
    """Drop `None` and empty strings, like a skipped optional source."""
    return [value for value in _flat(values) if value is not None and value != ""]


def _date(value: str) -> date:
    """Parse an ISO date or datetime string."""
    return datetime.fromisoformat(value).date()


def _date_or_today(value: str | None) -> date:
    """Parse an ISO date, computing today's when there is none, so it is never a stale default."""
    return _date(value) if value else date.today()  # noqa: DTZ011


# -----------------------
# text
# -----------------------


@_register("Text", "join")
def join(*values: Any, sep: str = " ") -> str:
    """Join the non-empty values: `join("Rama", None, "Ali") == "Rama Ali"`."""
    return sep.join(str(value) for value in _present(values))


@_register("Text", "concat")
def concat(*values: Any) -> str:
    """Join the non-empty values with nothing between them."""
    return join(*values, sep="")


@_register("Text", "template")
def template(template: str, **values: Any) -> str:
    """Format `template` with the named sources: `"{first} {last}"`."""
    return template.format_map(values)


@_register("Text", "upper")
def upper(value: Any) -> str:
    """Upper case."""
    return str(value).upper()


@_register("Text", "lower")
def lower(value: Any) -> str:
    """Lower case."""
    return str(value).lower()


@_register("Text", "title")
def title(value: Any) -> str:
    """Capitalize each word."""
    return str(value).title()


@_register("Text", "capitalize")
def capitalize(value: Any) -> str:
    """Capitalize the first letter."""
    return str(value).capitalize()


@_register("Text", "trim")
def trim(value: Any) -> str:
    """Strip the surrounding whitespace."""
    return str(value).strip()


@_register("Text", "replace")
def replace(value: Any, old: str, new: str) -> str:
    """Replace every `old` with `new`."""
    return str(value).replace(old, new)


@_register("Text", "slice")
def slice_(value: Any, start: int = 0, end: int | None = None) -> Any:
    """Part of a string or a list: `slice("2026-11-04", end=4) == "2026"`."""
    return value[start:end]


@_register("Text", "initials")
def initials(*values: Any, sep: str = "") -> str:
    """Return the first letter of each word: `initials("Rama Ali") == "RA"`."""
    words = [word for value in _present(values) for word in str(value).split()]

    return sep.join(word[0].upper() for word in words)


@_register("Text", "slug")
def slug(value: Any) -> str:
    """Make a URL slug, keeping non latin letters: `slug("Hello World!") == "hello-world"`."""
    text = unicodedata.normalize("NFKC", str(value)).lower()

    return re.sub(r"[\W_]+", "-", text).strip("-")


@_register("Text", "length")
def length(value: Any) -> int:
    """Return the length of a string or a list."""
    return len(value)


@_register("Text", "pad")
def pad(value: Any, width: int, char: str = "0") -> str:
    """Pad on the left: `pad(42, 5) == "00042"`."""
    return str(value).rjust(width, char)


@_register("Text", "mask")
def mask(value: Any, keep: int = 4, char: str = "*") -> str:
    """Hide all but the last `keep` characters: `mask("12345678") == "****5678"`."""
    text = str(value)
    hidden = max(len(text) - keep, 0)

    return char * hidden + text[hidden:]


# -----------------------
# numbers
# -----------------------


@_register("Numbers", "sum")
def total(*values: Any) -> Any:
    """Add the values, lists are spread: `sum(items[*].price)`."""
    return sum(_flat(values))


@_register("Numbers", "subtract")
def subtract(value: Any, *values: Any) -> Any:
    """Subtract the other values from the first one."""
    return value - sum(_flat(values))


@_register("Numbers", "multiply")
def multiply(*values: Any) -> Any:
    """Multiply the values, lists are spread."""
    return math.prod(_flat(values))


@_register("Numbers", "divide")
def divide(value: Any, divisor: Any) -> float:
    """Divide, a zero divisor is an error."""
    return value / divisor


@_register("Numbers", "average")
def average(*values: Any) -> float:
    """Return the mean of the values, lists are spread."""
    return statistics.fmean(_flat(values))


@_register("Numbers", "min")
def minimum(*values: Any) -> Any:
    """Return the smallest value, lists are spread."""
    return min(_flat(values))


@_register("Numbers", "max")
def maximum(*values: Any) -> Any:
    """Return the largest value, lists are spread."""
    return max(_flat(values))


@_register("Numbers", "abs")
def absolute(value: Any) -> Any:
    """Return the absolute value."""
    return abs(value)


@_register("Numbers", "round")
def round_(value: Any, digits: int = 2) -> Any:
    """Round to `digits` decimals."""
    return round(value, digits)


@_register("Numbers", "percent")
def percent(part: Any, whole: Any) -> float:
    """How many percent `part` is of `whole`: `percent(1, 4) == 25`."""
    return part / whole * 100


@_register("Numbers", "percent_of")
def percent_of(value: Any, rate: Any) -> float:
    """`rate` percent of `value`, like a tax: `percent_of(200, 15) == 30`."""
    return value * rate / 100


_BINARY: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_UNARY: dict[type, Callable[[Any], Any]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Not: operator.not_,
}

_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "round": round,
    "min": min,
    "max": max,
    "abs": abs,
    "sum": sum,
}

_MAX_EXPONENT = 1000
"""Stops entered values from hanging the expression, like `x ** y` with a huge `y`."""


@_register("Numbers", "expr")
def expr(expr: str, **values: Any) -> Any:
    """Evaluate a safe expression of the named sources: `"round(qty * price * 1.15, 2)"`.

    Allows numbers, strings, arithmetic, comparisons, `and` / `or` / `not`, `a if c else b`
    and the functions round, min, max, abs and sum. Anything else is an error, nothing is `eval`ed.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        message = f"Invalid expression '{expr}': {e.msg}"
        raise ValueError(message) from None

    return _evaluate(tree.body, values)


def _evaluate(node: ast.AST, names: dict[str, Any]) -> Any:  # noqa: C901, PLR0911
    match node:
        case ast.Constant(value=value) if isinstance(value, int | float | str):
            return value

        case ast.Name(id=name) if name in names:
            return names[name]

        case ast.BinOp(left=left, op=op, right=right) if type(op) in _BINARY:
            right_value = _evaluate(right, names)

            if isinstance(op, ast.Pow) and abs(right_value) > _MAX_EXPONENT:
                message = f"Exponent {right_value} is too large"
                raise ValueError(message)

            return _BINARY[type(op)](_evaluate(left, names), right_value)

        case ast.UnaryOp(op=op, operand=operand) if type(op) in _UNARY:
            return _UNARY[type(op)](_evaluate(operand, names))

        case ast.Compare(left=left, ops=ops, comparators=comparators) if all(
            type(op) in _BINARY for op in ops
        ):
            values = [_evaluate(left, names), *(_evaluate(c, names) for c in comparators)]

            return all(
                _BINARY[type(op)](a, b) for op, a, b in zip(ops, values, values[1:], strict=False)
            )

        case ast.BoolOp(op=ast.And(), values=values):
            return all(_evaluate(value, names) for value in values)

        case ast.BoolOp(op=ast.Or(), values=values):
            return any(_evaluate(value, names) for value in values)

        case ast.IfExp(test=test, body=body, orelse=orelse):
            return _evaluate(body if _evaluate(test, names) else orelse, names)

        case ast.Call(func=ast.Name(id=fn), args=args, keywords=[]) if fn in _FUNCTIONS:
            return _FUNCTIONS[fn](*(_evaluate(arg, names) for arg in args))

        case ast.List(elts=items) | ast.Tuple(elts=items):
            return [_evaluate(item, names) for item in items]

    message = f"'{ast.unparse(node)}' is not allowed in an expression"
    raise ValueError(message)


# -----------------------
# number to words
# -----------------------


@_register("Number to words", "words")
def words(value: Any, lang: str = "en", prefix: str = "", suffix: str = "") -> str:
    """Spell a number: `words(12, prefix="only", suffix="USD") == "only twelve USD"`.

    `lang` is like `en`, `ar` or `fr`.
    """
    return join(prefix, num2words(value, lang=lang), suffix)


# -----------------------
# dates
# -----------------------


@_register("Dates", "today")
def today() -> str:
    """Today's ISO date: `2026-11-04`."""
    return date.today().isoformat()  # noqa: DTZ011


@_register("Dates", "now")
def now() -> str:
    """Return the current local RFC 3339 datetime: `2026-11-04T10:30:00+03:00`."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


@_register("Dates", "add_days")
def add_days(value: str | None = None, days: int = 0) -> str:
    """Add (or subtract) days to an ISO date (today by default)."""
    return date.fromordinal(_date_or_today(value).toordinal() + days).isoformat()


@_register("Dates", "add_months")
def add_months(value: str | None = None, months: int = 0) -> str:
    """Add months to a date (today by default), clamping to the month end.

    `add_months("2026-01-31", 1) == "2026-02-28"`.
    """
    day = _date_or_today(value)
    years, month = divmod(day.month - 1 + months, 12)
    year = day.year + years
    last_day = calendar.monthrange(year, month + 1)[1]

    return day.replace(year=year, month=month + 1, day=min(day.day, last_day)).isoformat()


@_register("Dates", "add_years")
def add_years(value: str | None = None, years: int = 0) -> str:
    """Add years to a date (today by default), Feb 29 becomes Feb 28 on a non leap year."""
    return add_months(value, years * 12)


@_register("Dates", "days_between")
def days_between(start: str, end: str | None = None) -> int:
    """Days from `start` to `end` (today by default), negative when `end` is before."""
    return (_date_or_today(end) - _date(start)).days


@_register("Dates", "age")
def age(birth_date: str, on: str | None = None) -> int:
    """Whole years from `birth_date` to `on` (today by default)."""
    born = _date(birth_date)
    day = _date_or_today(on)

    return day.year - born.year - ((day.month, day.day) < (born.month, born.day))


@_register("Dates", "year")
def year(value: str | None = None) -> int:
    """Return the year of an ISO date (today by default)."""
    return _date_or_today(value).year


@_register("Dates", "month")
def month(value: str | None = None) -> int:
    """Return the month (1 to 12) of an ISO date (today by default)."""
    return _date_or_today(value).month


@_register("Dates", "day")
def day(value: str | None = None) -> int:
    """Return the day of the month of an ISO date (today by default)."""
    return _date_or_today(value).day


@_register("Dates", "weekday")
def weekday(value: str | None = None, fmt: str = "%A") -> str:
    """Return the weekday name of an ISO date (today by default): `Wednesday`."""
    return _date_or_today(value).strftime(fmt)


@_register("Dates", "format_date")
def format_date(value: str | None = None, fmt: str = "%d/%m/%Y") -> str:
    """Format an ISO date or datetime (now by default) with `strftime` codes."""
    return datetime.fromisoformat(value or now()).strftime(fmt)


@_register("Dates", "start_of_month")
def start_of_month(value: str | None = None) -> str:
    """Return the first day of the month of an ISO date (today by default)."""
    return _date_or_today(value).replace(day=1).isoformat()


@_register("Dates", "end_of_month")
def end_of_month(value: str | None = None) -> str:
    """Return the last day of the month of an ISO date (today by default)."""
    day = _date_or_today(value)

    return day.replace(day=calendar.monthrange(day.year, day.month)[1]).isoformat()


# -----------------------
# logic, lookup and misc
# -----------------------


@_register("Logic, lookup and misc", "coalesce")
def coalesce(*values: Any) -> Any:
    """Return the first non-empty value, use `?` paths so missing ones are `None`."""
    present = _present(values)

    if not present:
        message = "All values are empty"
        raise ValueError(message)

    return present[0]


@_register("Logic, lookup and misc", "if_else")
def if_else(condition: Any, then: Any, otherwise: Any) -> Any:
    """`then` when `condition` is truthy, else `otherwise`."""
    return then if condition else otherwise


@_register("Logic, lookup and misc", "equals")
def equals(value: Any, other: Any) -> bool:
    """Whether both values are equal."""
    return value == other


class _NoFallback:
    """A default shown in signatures, which reach users and `meta.json`, so its text is stable."""

    def __repr__(self) -> str:
        return "<no fallback>"


_NO_FALLBACK: Any = _NoFallback()


@_register("Logic, lookup and misc", "lookup")
def lookup(key: Any, map: dict[str, Any], fallback: Any = _NO_FALLBACK) -> Any:  # noqa: A002
    """Map a value through `map`: `{"SY": "Syria"}`, keys are compared as strings."""
    if str(key) in map:
        return map[str(key)]

    if fallback is _NO_FALLBACK:
        message = f"'{key}' is not in the lookup map"
        raise ValueError(message)

    return fallback


@_register("Logic, lookup and misc", "constant")
def constant(value: Any) -> Any:
    """Return `value` from the options, always the same."""
    return value


@_register("Logic, lookup and misc", "count")
def count(values: list[Any]) -> int:
    """Return the number of items."""
    return len(values)


@_register("Logic, lookup and misc", "count_if")
def count_if(values: list[Any], value: Any) -> int:
    """How many items equal `value`."""
    return values.count(value)


@_register("Logic, lookup and misc", "unique")
def unique(values: list[Any]) -> list[Any]:
    """Return the items without duplicates, in order."""
    return list(dict.fromkeys(values))


@_register("Logic, lookup and misc", "uuid")
def uuid() -> str:
    """Return a random UUID."""
    return str(uuid_.uuid4())
