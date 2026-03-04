"""Wheeler CLI: REPL loop with mode switching and streaming output."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
import threading
import time
from pathlib import Path

# --- API key guardrail (must happen before any SDK import) ---
# Wheeler runs on Max subscription. Strip API key so the Claude CLI subprocess
# uses OAuth/Max auth instead of API billing.
if os.environ.pop("ANTHROPIC_API_KEY", None):
    print("  [wheeler] Stripped ANTHROPIC_API_KEY — using Max subscription")

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

from wheeler import __version__
from wheeler.config import WheelerConfig, load_config
from wheeler.modes import Mode
from wheeler.sessions import (
    Session,
    list_sessions,
    load_session,
    new_session,
    save_session,
)

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

# --- Thinking verbs (Claude Code inspired) ---
_THINKING_VERBS = [
    "Thinking", "Reasoning", "Considering", "Analyzing", "Pondering",
    "Cogitating", "Reflecting", "Evaluating", "Examining", "Weighing",
    "Contemplating", "Synthesizing", "Processing", "Deducing", "Inferring",
    "Hypothesizing", "Investigating", "Deliberating", "Formulating", "Assessing",
    "Correlating", "Integrating", "Interpreting", "Calibrating", "Distilling",
    "Cross-referencing", "Mapping", "Connecting", "Probing", "Triangulating",
]


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
    "/handoff",
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
    "/handoff": "Propose tasks for independent execution",
    "/quit": "Exit Wheeler",
    "/exit": "Exit Wheeler",
}

_COMMAND_GROUPS = {
    "Modes": ["/chat", "/planning", "/writing", "/execute", "/mode"],
    "Session": ["/save", "/sessions", "/resume"],
    "Tools": ["/init", "/graph"],
    "Workflow": ["/handoff"],
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


def _get_rprompt(session: Session | None = None) -> HTML:
    """Right-side prompt: turn count + session hint."""
    color = _MODE_COLORS.get(_current_mode, _AMBER)
    turn_count = len(session.turns) // 2 if session else 0
    if turn_count > 0:
        return HTML(
            f"<style fg='#333333'>turn {turn_count}</style>"
        )
    return HTML("")


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
        complete_in_thread=True,
    )


# --- Display helpers ---

def _display_welcome(session: Session) -> None:
    """Print welcome banner."""
    console.print()
    title = Text()
    title.append("Wheeler", style=f"bold {_AMBER}")
    title.append(f" v{__version__}", style=_DIM)
    subtitle = Text()
    subtitle.append(f"Session {session.session_id}", style=_DIM)
    subtitle.append("  |  ", style=_MUTED)
    subtitle.append("Type ", style=_DIM)
    subtitle.append("/", style=f"bold {_AMBER}")
    subtitle.append(" for commands", style=_DIM)
    subtitle.append("  |  ", style=_MUTED)
    mode_color = _MODE_COLORS[_current_mode]
    subtitle.append(f"{_current_mode.value}", style=f"bold {mode_color}")

    console.print(Panel(
        Text.assemble(title, "\n", subtitle),
        border_style=_DIM,
        padding=(0, 1),
    ))


def _get_mode_model(mode: Mode, config: WheelerConfig | None = None) -> str:
    """Get the model name for a mode from config."""
    try:
        if config is None:
            config = load_config()
        mode_to_field = {
            Mode.CHAT: config.models.chat,
            Mode.PLANNING: config.models.planning,
            Mode.WRITING: config.models.writing,
            Mode.EXECUTE: config.models.execute,
        }
        return mode_to_field.get(mode, "sonnet")
    except Exception:
        return "sonnet"


def _display_mode_switch(mode: Mode, config: WheelerConfig | None = None) -> None:
    """Show mode switch confirmation with capability hint."""
    color = _MODE_COLORS[mode]
    hints = {
        Mode.CHAT: "read-only, graph queries",
        Mode.PLANNING: "read + write, graph, paper search",
        Mode.WRITING: "read + write + edit, strict citations",
        Mode.EXECUTE: "full access, logs to graph",
    }
    hint = hints.get(mode, "")
    model = _get_mode_model(mode, config)
    console.print(
        f"  [{color}]●[/{color}] [{color} bold]{mode.value}[/{color} bold]"
        f"  [{_DIM}]{hint}[/{_DIM}]  [{_MUTED}]{model}[/{_MUTED}]"
    )


def _display_mode_list(config: WheelerConfig | None = None) -> None:
    """Show all modes with indicators."""
    console.print()
    for m in Mode:
        color = _MODE_COLORS[m]
        if m == _current_mode:
            marker = f"[{color}]●[/{color}]"
        else:
            marker = f"[{_DIM}]○[/{_DIM}]"
        desc = _mode_description(m)
        model = _get_mode_model(m, config)
        console.print(
            f"  {marker} [{color} bold]{m.value:<10}[/{color} bold]"
            f" [{_MUTED}]{desc:<40}[/{_MUTED}]"
            f" [{_DIM}]{model}[/{_DIM}]"
        )
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


async def _display_graph_status_async(config: WheelerConfig | None = None) -> None:
    """Query and display knowledge graph node counts."""
    try:
        from wheeler.graph.schema import get_status
        if config is None:
            config = load_config()
        counts = await get_status(config)
        total = sum(counts.values())
        if total == 0:
            console.print(f"  [{_MUTED}]Graph is empty. Use /init or add nodes in execute mode.[/{_MUTED}]")
            return

        console.print()
        tree = Tree(
            f"[{_AMBER} bold]Knowledge Graph[/{_AMBER} bold] [{_DIM}]({total} nodes)[/{_DIM}]",
            guide_style=_DIM,
        )
        for label, count in sorted(counts.items()):
            if count > 0:
                tree.add(f"[{_FG}]{label}[/{_FG}] [{_DIM}]{count}[/{_DIM}]")
        console.print(tree)
        console.print()
    except Exception as exc:
        console.print(f"  [wheeler.error]Graph query failed:[/wheeler.error] {exc}")


def _display_init() -> None:
    """Scan workspace and display as a tree."""
    try:
        config = load_config()
        from wheeler.workspace import scan_workspace, invalidate_workspace_cache
        invalidate_workspace_cache()  # Force fresh scan on /init
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
    from wheeler.validation.citations import CitationStatus
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


def _format_duration(seconds: float) -> str:
    """Format seconds as compact duration string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{int(seconds // 60)}m {int(seconds % 60)}s"


def _format_count(n: int) -> str:
    """Format character count compactly."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _start_escape_listener(cancel_event: threading.Event) -> threading.Thread:
    """Listen for Escape key press in a background thread.

    Sets cancel_event when Escape (0x1b) is detected, allowing the
    streaming loop to break cleanly.
    """
    import tty
    import termios

    def _listen():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while not cancel_event.is_set():
                ch = sys.stdin.read(1)
                if ch == "\x1b":  # Escape
                    cancel_event.set()
                    break
        except Exception:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    t = threading.Thread(target=_listen, daemon=True)
    t.start()
    return t


async def _prewarm(config) -> None:
    """Pre-warm expensive resources while user reads welcome banner."""
    try:
        from wheeler.workspace import scan_workspace
        scan_workspace(config.workspace)
    except Exception:
        pass
    try:
        from wheeler.graph.context import prewarm_driver
        await prewarm_driver(config)
    except Exception:
        pass
    try:
        from wheeler.engine import _ensure_sdk
        _ensure_sdk()
    except Exception:
        pass


def _mode_description(mode: Mode) -> str:
    """Short description for each mode."""
    return {
        Mode.CHAT: "Discuss, query graph (read-only)",
        Mode.PLANNING: "Design research plans (no execution)",
        Mode.WRITING: "Draft text with strict citations",
        Mode.EXECUTE: "Run analyses, update graph",
    }[mode]


def _load_handoff_prompt() -> str | None:
    """Load handoff.md and wrap it as an in-session instruction."""
    handoff_path = Path(__file__).parent.parent / ".claude" / "commands" / "handoff.md"
    if not handoff_path.exists():
        return None
    instructions = handoff_path.read_text().strip()
    return (
        f"[HANDOFF MODE — assess this conversation and propose independent tasks]\n\n"
        f"{instructions}\n\n"
        f"Review our conversation above and produce a handoff proposal. "
        f"After approval, write the tasks to .logs/handoff-queue.sh as a runnable script "
        f"(each line: wh queue \"self-contained prompt\"). "
        f"The scientist runs `source .logs/handoff-queue.sh` — no copy-paste."
    )


# --- Command handling ---

def _handle_command(
    text: str, session: Session | None = None, config: WheelerConfig | None = None,
) -> bool | str:
    """Handle slash commands. Returns True if handled, a string for async commands, False otherwise."""
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
            _display_mode_switch(m, config)
            return True

    if cmd == "/mode":
        if len(parts) < 2:
            _display_mode_list(config)
            return True
        name = parts[1].strip().lower()
        for m in Mode:
            if m.value == name:
                set_mode(m)
                _display_mode_switch(m, config)
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
        # Handled async in the REPL loop
        return "graph"

    if cmd == "/init":
        _display_init()
        return True

    if cmd == "/handoff":
        return "handoff"

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

    # Pre-warm expensive resources while user reads the welcome banner
    asyncio.create_task(_prewarm(config))

    pt_session = _create_session()

    while True:
        try:
            user_input = await pt_session.prompt_async(
                _build_prompt_text,
                rprompt=lambda: _get_rprompt(session),
            )
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
            result = _handle_command(text, session, config)
            if result == "graph":
                await _display_graph_status_async(config)
                continue
            if result == "handoff":
                # Inject handoff prompt into the conversation (keeps session context)
                handoff_prompt = _load_handoff_prompt()
                if handoff_prompt:
                    text = handoff_prompt
                    # Fall through to normal query processing below
                else:
                    console.print(f"  [{_MUTED}]Handoff prompt not found.[/{_MUTED}]")
                    continue
            elif result:
                continue

        # Record user turn
        session.add_turn("user", text, _current_mode.value)

        # Build session context for resumed sessions
        session_context = session.summary_context() if len(session.turns) > 1 else ""

        # Stream the response with live markdown rendering.
        # Ctrl+C or Escape interrupts cleanly, keeping any partial response.
        _tick_stop = threading.Event()
        _cancel = threading.Event()
        live: Live | None = None
        first_chunk = True
        full_response = ""
        interrupted = False
        try:
            verb = random.choice(_THINKING_VERBS)
            t_start = time.monotonic()
            t_first_token = None
            spinner = console.status(
                f"  [{_DIM}]{verb}...[/{_DIM}]",
                spinner="dots",
                spinner_style=_AMBER,
            )
            spinner.start()

            # Thread-based tick: updates spinner with elapsed time every 500ms.
            # Must be a thread because the SDK blocks the event loop during thinking.
            def _tick():
                while not _tick_stop.wait(0.5):
                    elapsed = time.monotonic() - t_start
                    try:
                        spinner.update(
                            f"  [{_DIM}]{verb}... ({_format_duration(elapsed)})[/{_DIM}]"
                        )
                    except Exception:
                        break

            tick_thread = threading.Thread(target=_tick, daemon=True)
            tick_thread.start()

            # Listen for Escape key to cancel mid-stream
            _esc_thread = _start_escape_listener(_cancel)

            # Throttle live markdown re-renders (expensive for large responses)
            _last_render = 0.0
            _RENDER_INTERVAL = 0.25  # seconds between re-renders

            from wheeler.engine import run_query
            async for chunk in run_query(
                text, _current_mode, get_mode,
                config=config, session_context=session_context,
            ):
                if _cancel.is_set():
                    interrupted = True
                    break
                if first_chunk:
                    t_first_token = time.monotonic()
                    _tick_stop.set()
                    spinner.stop()
                    live = Live(
                        Markdown(chunk),
                        console=console,
                        refresh_per_second=4,
                    )
                    live.start()
                    first_chunk = False
                full_response += chunk
                now = time.monotonic()
                if now - _last_render >= _RENDER_INTERVAL:
                    live.update(Markdown(full_response))
                    _last_render = now

            _tick_stop.set()
            _cancel.set()  # stop escape listener
            if first_chunk:
                spinner.stop()
            if live:
                if full_response:
                    live.update(Markdown(full_response))
                live.stop()
                live = None
            if interrupted:
                console.print(f"  [{_YELLOW}]interrupted[/{_YELLOW}]")

        except KeyboardInterrupt:
            interrupted = True
            _tick_stop.set()
            _cancel.set()
            if first_chunk:
                spinner.stop()
            if live:
                if full_response:
                    live.update(Markdown(full_response))
                live.stop()
                live = None
            console.print(f"  [{_YELLOW}]interrupted[/{_YELLOW}]")

        except Exception as exc:
            _tick_stop.set()
            _cancel.set()
            if first_chunk:
                spinner.stop()
            if live:
                try:
                    live.stop()
                except Exception:
                    pass
                live = None
            console.print(f"  [wheeler.error]Error:[/wheeler.error] {exc}")
            continue

        # Post-response summary line
        t_end = time.monotonic()
        total_s = t_end - t_start
        think_s = (t_first_token - t_start) if t_first_token else total_s
        stream_s = total_s - think_s
        char_count = _format_count(len(full_response))
        parts = [f"{_format_duration(total_s)}"]
        if full_response:
            parts.append(f"\u2191 {char_count} chars")
        if think_s >= 1 and stream_s >= 1:
            parts.append(f"thought for {_format_duration(think_s)}")
        if interrupted:
            parts.append("interrupted")
        console.print(f"  [{_DIM}]{' \u00b7 '.join(parts)}[/{_DIM}]")

        # Record assistant turn
        session.add_turn("assistant", full_response, _current_mode.value)

        # Post-response citation validation + ledger
        # Runs on every response: validates cited nodes, flags ungrounded responses,
        # and logs the result to the provenance ledger in Neo4j.
        try:
            from wheeler.validation.citations import extract_citations, validate_citations
            from wheeler.validation.ledger import create_entry, store_entry
            cited = extract_citations(full_response)
            if cited:
                results = await validate_citations(full_response, config)
                _display_validation_summary(results)
                entry = create_entry(_current_mode.value, text, results)
                await store_entry(entry, config)
            elif full_response and len(full_response) > 80:
                # Non-trivial response with zero citations — log as ungrounded
                entry = create_entry(_current_mode.value, text, [])
                await store_entry(entry, config)
                console.print(
                    f"  [{_DIM}]citations[/{_DIM}]  [{_YELLOW}]none — ungrounded[/{_YELLOW}]"
                )
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
    # Log to ~/.wheeler/wheeler.log — captures SDK stderr, MCP failures, etc.
    log_file = _CONFIG_DIR / "wheeler.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        asyncio.run(repl())
    except SystemExit:
        pass


if __name__ == "__main__":
    app()
