import json
import re
from pathlib import Path

import typer
from schemify.cli.dependencies.schema import FilledDataArgumentDI, FilledDataOptionDI
from schemify.cli.main import app
from typer.testing import CliRunner
from typer_di import TyperDI

from .conftest import Prompts

runner = CliRunner(env={"COLUMNS": "1000"})

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer", "minimum": 0}},
    "required": ["name", "age"],
}


def invoke(*args: str | Path, stdin: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, [str(arg) for arg in args], input=stdin)

    return result.exit_code, ANSI_ESCAPE.sub("", result.output)


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")

    return path


class TestGenerate:
    def test_saves_schema(self, prompts: Prompts, tmp_path: Path) -> None:
        prompts.feed(["done", "boolean", "", "", True, "", False])
        output = tmp_path / "out" / "task.json"
        code, text = invoke("g", "-t", "Task", "-o", output)

        assert code == 0, text
        assert json.loads(output.read_text(encoding="utf-8"))["title"] == "Task"

    def test_prints_schema(self, prompts: Prompts) -> None:
        prompts.feed(["done", "boolean", "", "", True, "", False])
        code, text = invoke("generate")

        assert code == 0, text
        assert '"done"' in text

    def test_overwrite_declined_aborts_before_asking(
        self, prompts: Prompts, tmp_path: Path
    ) -> None:
        output = write_json(tmp_path / "s.json", {})
        code, _ = invoke("g", "-o", output, stdin="n\n")

        assert code == 1
        assert not prompts.messages
        assert output.read_text(encoding="utf-8") == "{}"


class TestFill:
    def test_saves_data(self, prompts: Prompts, tmp_path: Path) -> None:
        schema = write_json(tmp_path / "s.json", SCHEMA)
        output = tmp_path / "data.json"
        prompts.feed(["Rama", "-1", "25"])
        code, text = invoke("f", schema, "-o", output)

        assert code == 0, text
        assert json.loads(output.read_text(encoding="utf-8")) == {"name": "Rama", "age": 25}
        assert prompts.rejected == [("-1", "-1 is less than the minimum of 0")]

    def test_invalid_json(self, tmp_path: Path) -> None:
        schema = tmp_path / "s.json"
        schema.write_text("{", encoding="utf-8")
        code, text = invoke("fill", schema)

        assert code == 2
        assert "Could not read schema file" in text

    def test_invalid_schema(self, tmp_path: Path) -> None:
        code, text = invoke("fill", write_json(tmp_path / "s.json", {"type": "nope"}))

        assert code == 2
        assert "Invalid schema file" in text

    def test_unsupported_schema(self, tmp_path: Path) -> None:
        schema = {"type": "object", "properties": {"x": {"$ref": "#/$defs/x"}}}
        code, text = invoke("fill", write_json(tmp_path / "s.json", schema))

        assert code == 2
        assert "Can not fill 'x'" in text


class TestReusableDependencies:
    """The dependencies another app (like templify) imports."""

    def make_app(self) -> TyperDI:
        other = TyperDI()

        @other.command("by-argument")
        def by_argument(data: FilledDataArgumentDI) -> None:
            typer.echo(data["name"])

        @other.command("by-option")
        def by_option(data: FilledDataOptionDI) -> None:
            typer.echo(data["name"])

        return other

    def test_argument(self, prompts: Prompts, tmp_path: Path) -> None:
        prompts.feed(["Rama", "25"])
        schema = write_json(tmp_path / "s.json", SCHEMA)
        result = runner.invoke(self.make_app(), ["by-argument", str(schema)])

        assert result.exit_code == 0, result.output
        assert result.output.strip() == "Rama"

    def test_option(self, prompts: Prompts, tmp_path: Path) -> None:
        prompts.feed(["Rama", "25"])
        schema = write_json(tmp_path / "s.json", SCHEMA)
        result = runner.invoke(self.make_app(), ["by-option", "--schema", str(schema)])

        assert result.exit_code == 0, result.output
        assert result.output.strip() == "Rama"
