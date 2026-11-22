from collections.abc import Callable
from typing import TypeVar

from rich.console import Console

T = TypeVar("T")


class Progress:
    def run(self, message: str, action: Callable[[], T]) -> T:
        return action()

    def done(self, message: str) -> None:
        return None

    def done_error(self, message: str) -> None:
        return None


class ConsoleProgress(Progress):
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def run(self, message: str, action: Callable[[], T]) -> T:
        try:
            with self._console.status(f"[cyan]{message}[/cyan]"):
                result = action()
        except Exception:
            self._console.print(f"[red]✗[/red] {message}")
            raise
        self._console.print(f"[green]✓[/green] {message}")
        return result

    def done(self, message: str) -> None:
        self._console.print(f"[green]✓[/green] {message}")

    def done_error(self, message: str) -> None:
        self._console.print(f"[red]{message}[/red]")
