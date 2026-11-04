"""A registry of functions picked by name, used by the schema generators and data fillers."""

from collections.abc import Callable
from typing import Any


class NotSupportedError(Exception):
    """Raised when no function is registered under a name."""


class Registry[F: Callable[..., Any]]:
    """Maps names (case-insensitive) to functions.

    Example:
    ```python
    generators = Registry[Callable[[], Schema]]("Type")


    @generators.register("string")
    def generate_string() -> Schema: ...


    schema = generators["string"]()
    ```

    """

    def __init__(self, kind: str) -> None:
        """Create an empty registry, `kind` names its entries in error messages."""
        self._kind = kind
        self._fns: dict[str, F] = {}

    def __contains__(self, name: object) -> bool:
        """Whether a function is registered under `name`."""
        return isinstance(name, str) and name.lower() in self._fns

    def __getitem__(self, name: str) -> F:
        """Return the function registered under `name`.

        Raises:
            NotSupportedError: Nothing is registered under `name`.

        """
        if name not in self:
            supported = ", ".join(self.names)
            message = f"{self._kind} '{name}' is not supported, supported: {supported}"
            raise NotSupportedError(message)

        return self._fns[name.lower()]

    @property
    def names(self) -> list[str]:
        """The registered names, sorted."""
        return sorted(self._fns)

    def register(self, *names: str) -> Callable[[F], F]:
        """Register the decorated function under `names`."""

        def decorator(fn: F) -> F:
            for name in names:
                self.add(fn, name)

            return fn

        return decorator

    def add(self, fn: F, name: str) -> None:
        """Register `fn` under `name`, replacing any existing one."""
        self._fns[name.lower()] = fn
