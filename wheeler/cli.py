"""Wheeler CLI: REPL loop with mode switching and streaming output."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.theme import Theme

from wheeler import __version__
from wheeler.engine import run_query
from wheeler.modes import Mode

theme = Theme({
    "mode": "bold cyan",
    "prompt": "bold green",
    "error": "bold red",
    "info": "dim",
})
console = Console(theme=theme)

# Global mutable mode — the hook reads this via get_mode closure
_current_mode: Mode = Mode.CHAT


def get_mode() -> Mode:
    return _current_mode


def set_mode(mode: Mode) -> None:
    global _current_mode
    _current_mode = mode


def _build_prompt() -> str:
    return f"[mode]\\[{_current_mode.value}][/mode] [prompt]>>> [/prompt]"


def _handle_command(text: str) -> bool:
    """Handle slash commands. Returns True if the input was a command."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd in ("/quit", "/exit"):
        console.print("Goodbye!", style="info")
        raise SystemExit(0)

    if cmd == "/mode":
        if len(parts) < 2:
            console.print(
                f"Current mode: [mode]{_current_mode.value}[/mode].  "
                f"Available: {', '.join(m.value for m in Mode)}",
            )
            return True
        name = parts[1].strip().lower()
        for m in Mode:
            if m.value == name:
                set_mode(m)
                console.print(f"Switched to [mode]{m.value}[/mode] mode.")
                return True
        console.print(f"[error]Unknown mode:[/error] {name}", style="error")
        return True

    if cmd == "/help":
        console.print(
            "[info]Commands:[/info]\n"
            "  /mode <name>  — switch mode (chat, planning, writing, execute)\n"
            "  /mode         — show current mode\n"
            "  /quit         — exit Wheeler",
        )
        return True

    return False


async def repl() -> None:
    """Main read-eval-print loop."""
    console.print(
        f"[bold]Wheeler[/bold] v{__version__} — research assistant",
        style="info",
    )
    console.print(
        "Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.\n",
        style="info",
    )

    while True:
        try:
            user_input = console.input(_build_prompt())
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!", style="info")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith("/"):
            if _handle_command(text):
                continue

        # Stream the response
        try:
            first = True
            async for chunk in run_query(text, _current_mode, get_mode):
                if first:
                    first = False
                console.print(chunk, end="", highlight=False)
            console.print()  # trailing newline
        except Exception as exc:
            console.print(f"[error]Error:[/error] {exc}")


app = typer.Typer(
    name="wheeler",
    help="Wheeler: a CLI research assistant for scientists.",
    add_completion=False,
)


@app.command()
def main() -> None:
    """Start the Wheeler REPL."""
    try:
        asyncio.run(repl())
    except SystemExit:
        pass


if __name__ == "__main__":
    app()
