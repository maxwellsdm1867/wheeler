"""Wheeler CLI: REPL loop with mode switching and streaming output."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.theme import Theme

from wheeler import __version__
from wheeler.config import load_config
from wheeler.engine import run_query
from wheeler.workspace import scan_workspace, format_workspace_context
from wheeler.modes import Mode
from wheeler.sessions import (
    Session,
    list_sessions,
    load_session,
    new_session,
    save_session,
)
from wheeler.validation.citations import (
    CitationStatus,
    extract_citations,
    validate_citations,
)
from wheeler.validation.ledger import create_entry, store_entry

theme = Theme({
    "mode": "bold cyan",
    "prompt": "bold green",
    "error": "bold red",
    "info": "dim",
})
console = Console(theme=theme)

# --- Config directory ---
_CONFIG_DIR = Path.home() / ".wheeler"
_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
_HISTORY_FILE = _CONFIG_DIR / "history"

# --- Global mutable mode ---
_current_mode: Mode = Mode.CHAT


def get_mode() -> Mode:
    return _current_mode


def set_mode(mode: Mode) -> None:
    global _current_mode
    _current_mode = mode


# --- Slash commands ---
_SLASH_COMMANDS = [
    "/chat",
    "/planning",
    "/writing",
    "/execute",
    "/mode",
    "/help",
    "/save",
    "/sessions",
    "/resume",
    "/graph",
    "/init",
    "/quit",
    "/exit",
]


def _get_completer() -> FuzzyWordCompleter:
    """Build a fuzzy completer for slash commands."""
    return FuzzyWordCompleter(_SLASH_COMMANDS, WORD=True)


def _get_toolbar():
    """Bottom toolbar showing mode and shortcuts."""
    mode = _current_mode.value
    return HTML(
        f"  <b>[{mode}]</b>"
        "  <style fg='ansigray'>Enter: send</style>"
        "  <style fg='ansigray'>| Ctrl+R: history search</style>"
        "  <style fg='ansigray'>| /help: commands</style>"
    )


def _get_pt_style() -> PTStyle:
    """prompt_toolkit style for the input prompt."""
    return PTStyle.from_dict({
        "prompt": "#00cc66 bold",
        "mode": "#00bbcc bold",
        "bottom-toolbar": "bg:#1a1a2e #aaaaaa",
        "completion-menu.completion": "bg:#333333 #ffffff",
        "completion-menu.completion.current": "bg:#0077cc #ffffff",
        "auto-suggestion": "#666666",
    })


def _build_prompt_text() -> list:
    """Build prompt_toolkit formatted text."""
    return [
        ("class:mode", f"[{_current_mode.value}]"),
        ("class:prompt", " >>> "),
    ]


def _create_keybindings() -> KeyBindings:
    """Custom key bindings."""
    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):
        """Alt+Enter inserts a newline for multi-line input."""
        event.current_buffer.insert_text("\n")

    return kb


def _create_session() -> PromptSession:
    """Create a prompt_toolkit session with all UX features."""
    return PromptSession(
        completer=_get_completer(),
        complete_while_typing=False,
        history=FileHistory(str(_HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
        key_bindings=_create_keybindings(),
        bottom_toolbar=_get_toolbar,
        style=_get_pt_style(),
        mouse_support=True,
    )


def _handle_command(text: str, session: Session | None = None) -> bool:
    """Handle slash commands. Returns True if the input was a command."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd in ("/quit", "/exit"):
        if session and session.turns:
            try:
                save_session(session)
                console.print(
                    f"[info]Session saved: {session.session_id}[/info]"
                )
            except Exception:
                pass
        console.print("Goodbye!", style="info")
        raise SystemExit(0)

    # Mode shortcuts: /chat, /planning, /writing, /execute
    for m in Mode:
        if cmd == f"/{m.value}":
            set_mode(m)
            console.print(f"Switched to [mode]{m.value}[/mode] mode.")
            return True

    if cmd == "/mode":
        if len(parts) < 2:
            table = Table(show_header=False, box=None, padding=(0, 2))
            for m in Mode:
                marker = "[bold green]>[/bold green]" if m == _current_mode else " "
                table.add_row(marker, f"[cyan]{m.value}[/cyan]", _mode_description(m))
            console.print(table)
            return True
        name = parts[1].strip().lower()
        for m in Mode:
            if m.value == name:
                set_mode(m)
                console.print(f"Switched to [mode]{m.value}[/mode] mode.")
                return True
        console.print(f"[error]Unknown mode:[/error] {name}", style="error")
        return True

    if cmd == "/save":
        if session:
            if len(parts) > 1:
                session.title = parts[1].strip()
            save_session(session)
            console.print(
                f"[green]Session saved:[/green] {session.session_id}"
                + (f" — {session.title}" if session.title else "")
            )
        else:
            console.print("[yellow]No active session.[/yellow]")
        return True

    if cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print("[yellow]No saved sessions.[/yellow]")
            return True
        table = Table(title="Saved Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Turns", justify="right")
        table.add_column("Created")
        for s in sessions:
            table.add_row(
                s.session_id,
                s.title or "[dim]untitled[/dim]",
                str(s.turn_count),
                s.created_at[:16],
            )
        console.print(table)
        return True

    if cmd == "/resume":
        if len(parts) < 2:
            console.print("[yellow]Usage: /resume <session-id>[/yellow]")
        return True

    if cmd == "/graph":
        console.print("[info]Querying knowledge graph status...[/info]")
        return True

    if cmd == "/init":
        try:
            config = load_config()
            console.print("[info]Scanning workspace...[/info]")
            summary = scan_workspace(config.workspace)

            # Display results
            table = Table(title="Workspace Scan Results")
            table.add_column("Category", style="cyan")
            table.add_column("Count", justify="right")
            table.add_column("Files")
            table.add_row(
                "Scripts",
                str(len(summary.scripts)),
                ", ".join(f.path for f in summary.scripts[:10])
                + (", ..." if len(summary.scripts) > 10 else ""),
            )
            table.add_row(
                "Data files",
                str(len(summary.data_files)),
                ", ".join(f.path for f in summary.data_files[:10])
                + (", ..." if len(summary.data_files) > 10 else ""),
            )
            table.add_row("Total", str(summary.total_files), "")
            console.print(table)

            context = format_workspace_context(summary)
            if context:
                console.print(f"\n[dim]{context}[/dim]")
        except Exception as exc:
            console.print(f"[error]Workspace scan failed:[/error] {exc}")
        return True

    if cmd == "/help":
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            title="[bold]Wheeler Commands[/bold]",
            title_style="cyan",
        )
        table.add_column(style="bold green")
        table.add_column()
        table.add_row("/chat", "Switch to chat mode (read-only)")
        table.add_row("/planning", "Switch to planning mode")
        table.add_row("/writing", "Switch to writing mode (strict citations)")
        table.add_row("/execute", "Switch to execute mode (full access)")
        table.add_row("/mode", "Show current mode")
        table.add_row("/save [title]", "Save current session")
        table.add_row("/sessions", "List saved sessions")
        table.add_row("/resume <id>", "Resume a saved session")
        table.add_row("/init", "Scan workspace, show scripts & data files")
        table.add_row("/quit", "Exit Wheeler")
        console.print(table)
        console.print(
            "\n[dim]Tab: autocomplete | Ctrl+R: search history | "
            "Alt+Enter: new line[/dim]"
        )
        return True

    return False


def _mode_description(mode: Mode) -> str:
    """Short description for each mode."""
    return {
        Mode.CHAT: "Discuss, query graph (read-only)",
        Mode.PLANNING: "Design research plans (no execution)",
        Mode.WRITING: "Draft text with strict citations",
        Mode.EXECUTE: "Run analyses, update graph",
    }[mode]


def _display_validation_summary(results: list) -> None:
    """Show compact citation validation results."""
    if not results:
        return
    indicators = {
        CitationStatus.VALID: "[green]\u2713[/green]",
        CitationStatus.NOT_FOUND: "[red]\u2717[/red]",
        CitationStatus.MISSING_PROVENANCE: "[yellow]![/yellow]",
        CitationStatus.STALE: "[yellow]~[/yellow]",
    }
    parts = []
    for r in results:
        indicator = indicators.get(r.status, "?")
        parts.append(f"{indicator} {r.node_id}")
    console.print(f"[info]Citations: {' | '.join(parts)}[/info]")


async def repl(resume_id: str | None = None) -> None:
    """Main read-eval-print loop."""
    config = load_config()

    # Session management
    session: Session
    if resume_id:
        loaded = load_session(resume_id)
        if loaded:
            session = loaded
            console.print(
                f"[green]Resumed session:[/green] {session.session_id}"
                + (f" — {session.title}" if session.title else "")
                + f" ({len(session.turns)} turns)",
                style="info",
            )
        else:
            console.print(
                f"[yellow]Session {resume_id} not found, starting new.[/yellow]"
            )
            session = new_session()
    else:
        session = new_session()

    # Welcome banner
    console.print(
        Panel(
            f"[bold cyan]Wheeler[/bold cyan] v{__version__} — "
            f"thinking partner for scientists\n"
            f"[dim]Session: {session.session_id}[/dim]",
            border_style="dim",
            expand=False,
        )
    )
    console.print(
        "[dim]Tab: autocomplete commands | /help for all commands | "
        "/quit to exit[/dim]\n",
    )

    # prompt_toolkit session with autocomplete + history
    pt_session = _create_session()

    while True:
        try:
            user_input = await pt_session.prompt_async(_build_prompt_text)
        except (EOFError, KeyboardInterrupt):
            if session.turns:
                try:
                    save_session(session)
                    console.print(
                        f"\n[info]Session saved: {session.session_id}[/info]"
                    )
                except Exception:
                    pass
            console.print("Goodbye!", style="info")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith("/"):
            # Handle /resume inline
            cmd_parts = text.strip().split(maxsplit=1)
            if cmd_parts[0].lower() == "/resume" and len(cmd_parts) > 1:
                rid = cmd_parts[1].strip()
                loaded = load_session(rid)
                if loaded:
                    session = loaded
                    console.print(
                        f"[green]Resumed session:[/green] {session.session_id}"
                        + (f" — {session.title}" if session.title else "")
                        + f" ({len(session.turns)} turns)",
                    )
                else:
                    console.print(f"[red]Session not found:[/red] {rid}")
                continue
            if _handle_command(text, session):
                continue

        # Record user turn
        session.add_turn("user", text, _current_mode.value)

        # Build session context for resumed sessions
        session_context = session.summary_context() if len(session.turns) > 1 else ""

        # Stream the response with a spinner until first chunk arrives
        try:
            full_response = ""
            first_chunk = True
            spinner = console.status(
                "[dim]Thinking...[/dim]", spinner="dots"
            )
            spinner.start()

            async for chunk in run_query(
                text, _current_mode, get_mode,
                config=config, session_context=session_context,
            ):
                if first_chunk:
                    spinner.stop()
                    first_chunk = False
                full_response += chunk
                console.print(chunk, end="", highlight=False)

            if first_chunk:
                # No chunks received
                spinner.stop()
            console.print()  # trailing newline
        except Exception as exc:
            if first_chunk:
                spinner.stop()
            console.print(f"[error]Error:[/error] {exc}")
            continue

        # Record assistant turn
        session.add_turn("assistant", full_response, _current_mode.value)

        # Post-response citation validation + ledger
        try:
            citations = extract_citations(full_response)
            if citations:
                results = await validate_citations(full_response, config)
                _display_validation_summary(results)
                entry = create_entry(_current_mode.value, text, results)
                await store_entry(entry, config)
        except Exception:
            pass  # validation/ledger failure shouldn't break REPL


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
