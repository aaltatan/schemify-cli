"""Replay every documented session in `examples/sessions/` and compare with `examples/`."""

import json
import shutil
from pathlib import Path

import pytest
from schemify.cli.main import app
from schemify.validators import check_schema
from typer.testing import CliRunner

from .conftest import Prompts

EXAMPLES = Path(__file__).parent.parent / "examples"

SESSIONS = sorted((EXAMPLES / "sessions").glob("*.json"))


@pytest.mark.parametrize("path", SESSIONS, ids=[path.stem for path in SESSIONS])
def test_session(
    path: Path, prompts: Prompts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = json.loads(path.read_text(encoding="utf-8"))

    shutil.copytree(EXAMPLES, tmp_path, dirs_exist_ok=True)

    output = tmp_path / session["output"]

    output.unlink(missing_ok=True)  # the session writes it, an existing file would be confirmed

    monkeypatch.chdir(tmp_path)

    prompts.feed(session["answers"])

    result = CliRunner().invoke(app, session["args"])

    assert result.exit_code == 0, result.output
    assert not prompts.answers, f"answers left over: {list(prompts.answers)}"

    expected = (EXAMPLES / session["output"]).read_text(encoding="utf-8")

    assert output.read_text(encoding="utf-8") == expected


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.schema.json")), ids=lambda p: p.name)
def test_example_schema_is_valid(path: Path) -> None:
    assert check_schema(json.loads(path.read_text(encoding="utf-8"))) is None
