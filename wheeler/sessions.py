"""Session management: save and resume REPL conversations."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


_DEFAULT_SESSION_DIR = Path(".wheeler/sessions")


@dataclass
class Turn:
    role: str  # "user" or "assistant"
    content: str
    mode: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class Session:
    session_id: str
    created_at: str
    turns: list[Turn] = field(default_factory=list)
    title: str = ""

    def add_turn(self, role: str, content: str, mode: str) -> None:
        self.turns.append(Turn(role=role, content=content, mode=mode))

    def summary_context(self, max_turns: int = 20) -> str:
        """Build a context string from recent turns for prompt injection."""
        recent = self.turns[-max_turns:]
        if not recent:
            return ""
        lines = ["## Previous Session Context\n"]
        for t in recent:
            prefix = "Scientist" if t.role == "user" else "Wheeler"
            lines.append(f"**{prefix}** [{t.mode}]: {t.content[:500]}")
        return "\n\n".join(lines)


def new_session() -> Session:
    """Create a new session with a unique ID."""
    sid = f"s-{secrets.token_hex(4)}"
    now = datetime.now(timezone.utc).isoformat()
    return Session(session_id=sid, created_at=now)


def _session_dir(base: Path | None = None) -> Path:
    d = base or _DEFAULT_SESSION_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_session(session: Session, base: Path | None = None) -> Path:
    """Save session to a JSON file. Returns the file path."""
    d = _session_dir(base)
    path = d / f"{session.session_id}.json"
    data = {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "title": session.title,
        "turns": [asdict(t) for t in session.turns],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_session(session_id: str, base: Path | None = None) -> Session | None:
    """Load a session by ID. Returns None if not found."""
    d = _session_dir(base)
    path = d / f"{session_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    turns = [Turn(**t) for t in data.get("turns", [])]
    return Session(
        session_id=data["session_id"],
        created_at=data["created_at"],
        turns=turns,
        title=data.get("title", ""),
    )


@dataclass
class SessionSummary:
    session_id: str
    created_at: str
    title: str
    turn_count: int


def list_sessions(base: Path | None = None) -> list[SessionSummary]:
    """List all saved sessions, most recent first."""
    d = _session_dir(base)
    summaries: list[SessionSummary] = []
    for path in sorted(d.glob("s-*.json"), reverse=True):
        try:
            with open(path) as f:
                data = json.load(f)
            summaries.append(SessionSummary(
                session_id=data["session_id"],
                created_at=data["created_at"],
                title=data.get("title", ""),
                turn_count=len(data.get("turns", [])),
            ))
        except (json.JSONDecodeError, KeyError):
            continue
    return summaries
