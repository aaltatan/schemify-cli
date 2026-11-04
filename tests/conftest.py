from collections import deque
from dataclasses import dataclass, field
from typing import Any

import pytest
import questionary


@dataclass
class Prompts:
    """Scripted questionary answers, like a user typing them in order.

    An answer the prompt validator rejects is recorded in `rejected`,
    and the next answer is tried, like the user typing again.
    """

    answers: deque[Any] = field(default_factory=deque)
    messages: list[str] = field(default_factory=list)
    rejected: list[tuple[Any, str]] = field(default_factory=list)

    def feed(self, *answers: Any) -> None:
        self.answers.extend(answers)


class _FakeQuestion:
    def __init__(self, prompts: Prompts, validate: Any, choices: list[str] | None) -> None:
        self._prompts = prompts
        self._validate = validate
        self._choices = choices

    def unsafe_ask(self) -> Any:
        while True:
            answer = self._prompts.answers.popleft()

            if self._choices is not None:
                assert answer in self._choices, f"{answer!r} not in {self._choices}"

            result = True if self._validate is None else self._validate(answer)

            if result is True:
                return answer

            self._prompts.rejected.append((answer, result))


@pytest.fixture
def prompts(monkeypatch: pytest.MonkeyPatch) -> Prompts:
    scripted = Prompts()

    def ask(message: str, choices: list[str] | None = None, **kwargs: Any) -> _FakeQuestion:
        scripted.messages.append(message)

        return _FakeQuestion(scripted, kwargs.get("validate"), choices)

    for name in ("text", "select", "confirm"):
        monkeypatch.setattr(questionary, name, ask)

    monkeypatch.setattr(questionary, "print", lambda *_, **__: None)

    return scripted
