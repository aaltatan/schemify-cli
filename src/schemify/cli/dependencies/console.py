"""The rich console used for command output."""

from typing import Annotated

from rich.console import Console
from typer_di import Depends

ConsoleDI = Annotated[Console, Depends(lambda: Console(color_system="truecolor"))]
"""Injects a truecolor rich console."""
