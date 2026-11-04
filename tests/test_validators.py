import pytest
from schemify.validators import (
    NUMBER_CONSTRAINTS,
    check_bounds,
    check_schema,
    check_value,
    is_choice,
    is_property_name,
    optional,
    to_choices,
    to_date,
    to_datetime,
    to_int,
    to_non_negative_int,
    to_number,
    to_positive_number,
    to_regex,
    validator,
    within_bounds,
)


class TestParsers:
    def test_to_int(self) -> None:
        assert to_int(" 42 ") == 42

        with pytest.raises(ValueError, match="not an integer"):
            to_int("4.2")

    def test_to_number_keeps_integers(self) -> None:
        assert to_number("42") == 42
        assert isinstance(to_number("42"), int)
        assert to_number("4.5") == 4.5

    @pytest.mark.parametrize("text", ["abc", "nan", "inf", "1e400"])
    def test_to_number_rejects(self, text: str) -> None:
        with pytest.raises(ValueError, match="number"):
            to_number(text)

    def test_to_non_negative_int(self) -> None:
        assert to_non_negative_int("0") == 0

        with pytest.raises(ValueError, match="0 or more"):
            to_non_negative_int("-1")

    def test_to_positive_number(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            to_positive_number("0")

    def test_to_regex(self) -> None:
        assert to_regex(r"^\d+$") == r"^\d+$"

        with pytest.raises(ValueError, match="Invalid regular expression"):
            to_regex("(")

    def test_to_choices(self) -> None:
        assert to_choices(" red, green ,, blue") == ["red", "green", "blue"]

        with pytest.raises(ValueError, match="at least one"):
            to_choices(" , ")

        with pytest.raises(ValueError, match="unique"):
            to_choices("a, a")

    def test_to_date(self) -> None:
        assert to_date("2026-11-04") == "2026-11-04"

        with pytest.raises(ValueError):
            to_date("2026-13-01")

    def test_to_datetime_adds_the_local_offset(self) -> None:
        assert to_datetime("2026-11-04T10:30:00+03:00") == "2026-11-04T10:30:00+03:00"
        assert to_datetime("2026-11-04T10:30:00")[-6] in "+-"


class TestPromptValidators:
    def test_validator(self) -> None:
        validate = validator(to_int)

        assert validate("1") is True
        assert validate("x") == "'x' is not an integer"

    def test_optional_accepts_empty(self) -> None:
        validate = optional(validator(to_int))

        assert validate("  ") is True
        assert validate("x") == "'x' is not an integer"

    def test_is_choice(self) -> None:
        assert is_choice([])("") == "Add at least one choice"
        assert is_choice(["red"])("") is True
        assert is_choice(["red"])(" red ") == "Choice 'red' already exists"
        assert is_choice(["red"])("green") is True

    def test_is_property_name(self) -> None:
        assert is_property_name({})("") == "Add at least one property"
        assert is_property_name({"name": {}})("") is True
        assert is_property_name({"name": {}})("name") == "Property 'name' already exists"
        assert is_property_name({"name": {}})("age") is True


class TestChecks:
    @pytest.mark.parametrize(
        ("schema", "ok"),
        [
            ({"minLength": 2, "maxLength": 2}, True),
            ({"minLength": 3, "maxLength": 2}, False),
            ({"minimum": 5, "maximum": 1}, False),
            ({"exclusiveMinimum": 1, "exclusiveMaximum": 1}, False),
            ({"minimum": 1, "exclusiveMaximum": 2}, True),
            ({"minItems": 4, "maxItems": 1}, False),
            ({"minimum": 5}, True),
        ],
    )
    def test_check_bounds(self, schema: dict, ok: bool) -> None:  # noqa: FBT001
        assert (check_bounds(schema) is None) is ok

    def test_within_bounds(self) -> None:
        constraint = NUMBER_CONSTRAINTS[3]  # maximum
        validate = within_bounds({"minimum": 10}, constraint)

        assert validate("x") == "'x' is not a number"
        assert validate("5") == "minimum (10) must be less than maximum (5)"
        assert validate("10") is True

    def test_check_schema(self) -> None:
        assert check_schema({"type": "string"}) is None
        assert check_schema({"type": "nope"}) is not None
        assert check_schema([]) == "A schema must be a JSON object"

    def test_check_value(self) -> None:
        schema = {"type": "string", "minLength": 2}

        assert check_value(schema, "ab") is None
        assert check_value(schema, "a") == "'a' is too short"
        assert check_value({"format": "email"}, "nope") is not None
        assert check_value({"format": "date"}, "2026-02-30") is not None
