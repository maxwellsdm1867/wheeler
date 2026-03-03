"""Wheeler CLI: REPL loop with mode switching and streaming output."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

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

# --- Theme: warm amber/gold primary, muted grays ---
_AMBER = "#D4A064"
_GOLD = "#E8C547"
_DIM = "#555555"
_MUTED = "#888888"
_FG = "#CCCCCC"
_GREEN = "#22C55E"
_RED = "#EF4444"
_YELLOW = "#EAB308"
_BLUE = "#60A5FA"

_MODE_COLORS = {
    Mode.CHAT: "#60A5FA",      # blue
    Mode.PLANNING: "#A78BFA",  # purple
    Mode.WRITING: "#34D399",   # emerald
    Mode.EXECUTE: "#F97316",   # orange
}

theme = Theme({
    "wheeler": f"bold {_AMBER}",
    "wheeler.dim": _DIM,
    "wheeler.muted": _MUTED,
    "wheeler.cmd": f"bold {_AMBER}",
    "wheeler.desc": _MUTED,
    "wheeler.success": _GREEN,
    "wheeler.error": _RED,
    "wheeler.warn": _YELLOW,
    "wheeler.accent": _BLUE,
    "mode.chat": f"bold {_MODE_COLORS[Mode.CHAT]}",
    "mode.planning": f"bold {_MODE_COLORS[Mode.PLANNING]}",
    "mode.writing": f"bold {_MODE_COLORS[Mode.WRITING]}",
    "mode.execute": f"bold {_MODE_COLORS[Mode.EXECUTE]}",
})
console = Console(theme=theme, highlight=False)

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

_COMMAND_META = {
    "/chat": "Switch to chat mode (read-only)",
    "/planning": "Switch to planning mode",
    "/writing": "Switch to writing mode (strict citations)",
    "/execute": "Switch to execute mode (full access)",
    "/mode": "Show or switch current mode",
    "/help": "Show all commands",
    "/save": "Save current session",
    "/sessions": "List saved sessions",
    "/resume": "Resume a saved session",
    "/graph": "Knowledge graph status",
    "/init": "Scan workspace, discover files",
    "/quit": "Exit Wheeler",
    "/exit": "Exit Wheeler",
}

_COMMAND_GROUPS = {
    "Modes": ["/chat", "/planning", "/writing", "/execute", "/mode"],
    "Session": ["/save", "/sessions", "/resume"],
    "Tools": ["/init", "/graph"],
    "": ["/help", "/quit"],
}


class SlashCommandCompleter(Completer):
    """Shows all commands when '/' is typed, with descriptions."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if not text.startswith("/"):
            return
        query = text.lower()
        for cmd, desc in _COMMAND_META.items():
            if cmd.startswith(query):
                yield Completion(
                    cmd,
                    start_position=-len(text),
                    display=cmd,
                    display_meta=desc,
                )


def _mode_style() -> str:
    return f"mode.{_current_mode.value}"


def _get_toolbar():
    """Bottom toolbar."""
    color = _MODE_COLORS.get(_current_mode, _AMBER)
    return HTML(
        f"  <style fg='{color}' bold='true'>{_current_mode.value}</style>"
        f"  <style fg='#555555'>  /: commands  |  Alt+Enter: newline  |  Ctrl+R: history</style>"
    )


def _get_pt_style() -> PTStyle:
    """prompt_toolkit style."""
    return PTStyle.from_dict({
        "prompt": f"{_AMBER} bold",
        "bottom-toolbar": "bg:#111111 #555555",
        # Completion menu
        "completion-menu": "bg:#1a1a2e #cccccc",
        "completion-menu.completion": "bg:#1a1a2e #cccccc",
        "completion-menu.completion.current": "bg:#2a2a4e #ffffff bold",
        "completion-menu.meta": "bg:#1a1a2e #666688",
        "completion-menu.meta.completion": "bg:#1a1a2e #666688",
        "completion-menu.meta.completion.current": "bg:#2a2a4e #9999bb",
        "auto-suggestion": "#333333",
        "scrollbar.background": "bg:#1a1a2e",
        "scrollbar.button": "bg:#333355",
    })


def _build_prompt_text() -> list:
    """Build prompt_toolkit formatted text."""
    color = _MODE_COLORS.get(_current_mode, _AMBER)
    return [
        ("", " "),
        (f"fg:{color} bold", f"{_current_mode.value}"),
        ("", " "),
        (f"fg:{_AMBER} bold", "> "),
    ]


def _create_keybindings() -> KeyBindings:
    """Custom key bindings."""
    kb = KeyBindings()

    @kb.add("escape", "enter")
    def _(event):
        event.current_buffer.insert_text("\n")

    return kb


def _create_session() -> PromptSession:
    """Create a prompt_toolkit session with all UX features."""
    return PromptSession(
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        history=FileHistory(str(_HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=True,
        key_bindings=_create_keybindings(),
        bottom_toolbar=_get_toolbar,
        style=_get_pt_style(),
        mouse_support=True,
    )


# --- Display helpers ---

def _display_welcome(session: Session) -> None:
    """Print welcome banner."""
    console.print()
    title = Text()
    title.append("Wheeler", style=f"bold {_AMBER}")
    title.append(f" v{__version__}", style=_DIM)
    console.print(title)
    console.print(
        f"[{_DIM}]Session {session.session_id}  "
        f"[{_MUTED}]|[/{_MUTED}]  Type [bold]/[/bold] for commands[/{_DIM}]"
    )
    console.print(Rule(style=_DIM))


def _display_mode_switch(mode: Mode) -> None:
    """Show mode switch confirmation."""
    color = _MODE_COLORS[mode]
    console.print(f"  [{color}]●[/{color}] Switched to [{color} bold]{mode.value}[/{color} bold]")


def _display_mode_list() -> None:
    """Show all modes with indicators."""
    console.print()
    for m in Mode:
        color = _MODE_COLORS[m]
        if m == _current_mode:
            marker = f"[{color}]●[/{color}]"
        else:
            marker = f"[{_DIM}]○[/{_DIM}]"
        desc = _mode_description(m)
        console.print(f"  {marker} [{color} bold]{m.value:<10}[/{color} bold] [{_MUTED}]{desc}[/{_MUTED}]")
    console.print()


def _display_help() -> None:
    """Show grouped command help."""
    console.print()
    for group, cmds in _COMMAND_GROUPS.items():
        if group:
            console.print(f"  [{_MUTED}]{group}[/{_MUTED}]")
        for cmd in cmds:
            desc = _COMMAND_META.get(cmd, "")
            console.print(f"    [{_AMBER} bold]{cmd:<14}[/{_AMBER} bold] [{_DIM}]{desc}[/{_DIM}]")
        if group:
            console.print()
    console.print(f"  [{_DIM}]Type / to see commands inline. Alt+Enter for newline.[/{_DIM}]")
    console.print()


def _display_sessions() -> None:
    """Show saved sessions table."""
    sessions = list_sessions()
    if not sessions:
        console.print(f"  [{_MUTED}]No saved sessions.[/{_MUTED}]")
        return
    table = Table(
        show_header=True,
        header_style=f"bold {_MUTED}",
        border_style=_DIM,
        box=None,
        padding=(0, 2),
    )
    table.add_column("ID", style=_AMBER)
    table.add_column("Title", style=_FG)
    table.add_column("Turns", justify="right", style=_MUTED)
    table.add_column("Created", style=_DIM)
    for s in sessions:
        table.add_row(
            s.session_id,
            s.title or f"[{_DIM}]untitled[/{_DIM}]",
            str(s.turn_count),
            s.created_at[:16],
        )
    console.print(table)


def _display_init() -> None:
    """Scan workspace and display as a tree."""
    try:
        config = load_config()
        summary = scan_workspace(config.workspace)

        if summary.total_files == 0:
            console.print(f"  [{_MUTED}]No files found in workspace.[/{_MUTED}]")
            return

        tree = Tree(
            f"[{_AMBER} bold]Workspace[/{_AMBER} bold] [{_DIM}]{summary.project_dir}[/{_DIM}]",
            guide_style=_DIM,
        )

        # Group scripts by directory
        if summary.scripts:
            scripts_branch = tree.add(
                f"[{_BLUE}]Scripts[/{_BLUE}] [{_DIM}]({len(summary.scripts)})[/{_DIM}]"
            )
            dirs: dict[str, list] = {}
            for f in summary.scripts:
                parent = str(Path(f.path).parent)
                dirs.setdefault(parent, []).append(f)
            for d, files in sorted(dirs.items()):
                if len(files) <= 5:
                    for f in files:
                        scripts_branch.add(f"[{_FG}]{f.path}[/{_FG}]")
                else:
                    scripts_branch.add(
                        f"[{_FG}]{d}/[/{_FG}] [{_DIM}]({len(files)} files)[/{_DIM}]"
                    )

        # Group data files by directory
        if summary.data_files:
            data_branch = tree.add(
                f"[{_GREEN}]Data[/{_GREEN}] [{_DIM}]({len(summary.data_files)})[/{_DIM}]"
            )
            dirs = {}
            for f in summary.data_files:
                parent = str(Path(f.path).parent)
                dirs.setdefault(parent, []).append(f)
            for d, files in sorted(dirs.items()):
                for f in files:
                    size = f.size_bytes
                    if size > 1_000_000:
                        size_str = f"{size / 1_000_000:.1f}MB"
                    elif size > 1_000:
                        size_str = f"{size / 1_000:.0f}KB"
                    else:
                        size_str = f"{size}B"
                    data_branch.add(
                        f"[{_FG}]{f.path}[/{_FG}] [{_DIM}]{size_str}[/{_DIM}]"
                    )

        console.print()
        console.print(tree)
        console.print()
    except Exception as exc:
        console.print(f"  [wheeler.error]Workspace scan failed:[/wheeler.error] {exc}")


def _display_validation_summary(results: list) -> None:
    """Show compact citation validation bar."""
    if not results:
        return
    parts = []
    for r in results:
        if r.status == CitationStatus.VALID:
            parts.append(f"[{_GREEN}]{r.node_id}[/{_GREEN}]")
        elif r.status == CitationStatus.NOT_FOUND:
            parts.append(f"[{_RED}]{r.node_id}[/{_RED}]")
        elif r.status == CitationStatus.STALE:
            parts.append(f"[{_YELLOW}]{r.node_id}~[/{_YELLOW}]")
        elif r.status == CitationStatus.MISSING_PROVENANCE:
            parts.append(f"[{_YELLOW}]{r.node_id}![/{_YELLOW}]")
        else:
            parts.append(f"[{_DIM}]{r.node_id}?[/{_DIM}]")
    console.print(f"  [{_DIM}]citations[/{_DIM}]  {' '.join(parts)}")


def _mode_description(mode: Mode) -> str:
    """Short description for each mode."""
    return {
        Mode.CHAT: "Discuss, query graph (read-only)",
        Mode.PLANNING: "Design research plans (no execution)",
        Mode.WRITING: "Draft text with strict citations",
        Mode.EXECUTE: "Run analyses, update graph",
    }[mode]


# --- Command handling ---

def _handle_command(text: str, session: Session | None = None) -> bool:
    """Handle slash commands. Returns True if the input was a command."""
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()

    if cmd in ("/quit", "/exit"):
        if session and session.turns:
            try:
                save_session(session)
                console.print(f"  [{_DIM}]Session saved: {session.session_id}[/{_DIM}]")
            except Exception:
                pass
        console.print(f"  [{_DIM}]Goodbye.[/{_DIM}]")
        raise SystemExit(0)

    # Mode shortcuts
    for m in Mode:
        if cmd == f"/{m.value}":
            set_mode(m)
            _display_mode_switch(m)
            return True

    if cmd == "/mode":
        if len(parts) < 2:
            _display_mode_list()
            return True
        name = parts[1].strip().lower()
        for m in Mode:
            if m.value == name:
                set_mode(m)
                _display_mode_switch(m)
                return True
        console.print(f"  [wheeler.error]Unknown mode:[/wheeler.error] {name}")
        return True

    if cmd == "/save":
        if session:
            if len(parts) > 1:
                session.title = parts[1].strip()
            save_session(session)
            title_part = f" \u2014 {session.title}" if session.title else ""
            console.print(f"  [{_GREEN}]Saved[/{_GREEN}] [{_DIM}]{session.session_id}{title_part}[/{_DIM}]")
        else:
            console.print(f"  [{_MUTED}]No active session.[/{_MUTED}]")
        return True

    if cmd == "/sessions":
        _display_sessions()
        return True

    if cmd == "/resume":
        if len(parts) < 2:
            console.print(f"  [{_MUTED}]Usage: /resume <session-id>[/{_MUTED}]")
        return True

    if cmd == "/graph":
        console.print(f"  [{_DIM}]Querying knowledge graph status...[/{_DIM}]")
        return True

    if cmd == "/init":
        _display_init()
        return True

    if cmd == "/help":
        _display_help()
        return True

    return False


# --- REPL ---

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
                f"  [{_GREEN}]Resumed[/{_GREEN}] [{_DIM}]{session.session_id}"
                + (f" \u2014 {session.title}" if session.title else "")
                + f" ({len(session.turns)} turns)[/{_DIM}]",
            )
        else:
            console.print(f"  [{_YELLOW}]Session {resume_id} not found, starting new.[/{_YELLOW}]")
            session = new_session()
    else:
        session = new_session()

    _display_welcome(session)

    pt_session = _create_session()

    while True:
        try:
            user_input = await pt_session.prompt_async(_build_prompt_text)
        except (EOFError, KeyboardInterrupt):
            if session.turns:
                try:
                    save_session(session)
                    console.print(f"\n  [{_DIM}]Session saved: {session.session_id}[/{_DIM}]")
                except Exception:
                    pass
            console.print(f"  [{_DIM}]Goodbye.[/{_DIM}]")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.startswith("/"):
            cmd_parts = text.strip().split(maxsplit=1)
            if cmd_parts[0].lower() == "/resume" and len(cmd_parts) > 1:
                rid = cmd_parts[1].strip()
                loaded = load_session(rid)
                if loaded:
                    session = loaded
                    console.print(
                        f"  [{_GREEN}]Resumed[/{_GREEN}] [{_DIM}]{session.session_id}"
                        + (f" \u2014 {session.title}" if session.title else "")
                        + f" ({len(session.turns)} turns)[/{_DIM}]",
                    )
                else:
                    console.print(f"  [wheeler.error]Session not found:[/wheeler.error] {rid}")
                continue
            if _handle_command(text, session):
                continue

        # Record user turn
        session.add_turn("user", text, _current_mode.value)

        # Build session context for resumed sessions
        session_context = session.summary_context() if len(session.turns) > 1 else ""

        # Stream the response
        try:
            full_response = ""
            first_chunk = True
            spinner = console.status(
                f"  [{_DIM}]thinking...[/{_DIM}]", spinner="dots",
                spinner_style=_AMBER,
            )
            spinner.start()

            async for chunk in run_query(
                text, _current_mode, get_mode,
                config=config, session_context=session_context,
            ):
                if first_chunk:
                    spinner.stop()
                    console.print()
                    first_chunk = False
                full_response += chunk
                console.print(chunk, end="", highlight=False)

            if first_chunk:
                spinner.stop()
            console.print()
        except Exception as exc:
            if first_chunk:
                spinner.stop()
            console.print(f"  [wheeler.error]Error:[/wheeler.error] {exc}")
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
            pass


app = typer.Typer(
    name="wheeler",
    help="Wheeler: a thinking partner for scientists.",
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
