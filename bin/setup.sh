#!/usr/bin/env bash
# Wheeler one-time setup — idempotent, safe to re-run.

set -euo pipefail

WHEELER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WHEELER_DIR"

AMBER='\033[38;2;212;160;100m'
GREEN='\033[38;2;52;211;153m'
DIM='\033[38;2;85;85;85m'
RED='\033[38;2;239;68;68m'
BOLD='\033[1m'
RESET='\033[0m'

step() { echo -e "  ${GREEN}→${RESET} $1"; }
warn() { echo -e "  ${AMBER}!${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1" >&2; exit 1; }

echo ""
echo -e "  ${AMBER}${BOLD}Wheeler${RESET} ${DIM}setup${RESET}"
echo ""

# ── Python venv ────────────────────────────────────────────────────
PYTHON="${WHEELER_PYTHON:-/opt/homebrew/bin/python3.14}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    PYTHON="$(command -v python3.11 || command -v python3.12 || command -v python3.13 || command -v python3.14 || true)"
    [[ -n "$PYTHON" ]] || fail "Python 3.11+ not found. Install via Homebrew: brew install python@3.14"
fi
step "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

if [[ ! -d .venv ]]; then
    step "Creating virtual environment..."
    "$PYTHON" -m venv .venv
else
    step "Virtual environment exists"
fi

source .venv/bin/activate

step "Installing wheeler (editable + test deps)..."
pip install -e ".[test]" --quiet

# ── .logs/ directory ───────────────────────────────────────────────
if [[ ! -d .logs ]]; then
    mkdir -p .logs
    step "Created .logs/ directory"
else
    step ".logs/ directory exists"
fi

# ── Neo4j ──────────────────────────────────────────────────────────
if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'wheeler-neo4j'; then
        step "Neo4j container running"
    elif docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q 'wheeler-neo4j'; then
        step "Starting existing Neo4j container..."
        docker start wheeler-neo4j
    else
        step "Starting Neo4j in Docker..."
        docker run -d \
            --name wheeler-neo4j \
            -p 7687:7687 -p 7474:7474 \
            -e NEO4J_AUTH=neo4j/research-graph \
            neo4j:community
        echo -e "  ${DIM}  Waiting for Neo4j to start...${RESET}"
        sleep 5
    fi
else
    warn "Docker not found — install Docker and run Neo4j manually"
    warn "  docker run -d -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/research-graph neo4j:community"
fi

# ── Graph schema ───────────────────────────────────────────────────
step "Initializing graph schema..."
.venv/bin/wheeler-tools graph init 2>/dev/null || warn "Could not init schema (Neo4j may not be running yet)"

# ── Claude Code check ──────────────────────────────────────────────
if command -v claude >/dev/null 2>&1; then
    step "Claude Code CLI found"
else
    warn "Claude Code CLI not found — install: npm install -g @anthropic-ai/claude-code"
fi

# ── Git hooks ─────────────────────────────────────────────────────
if [[ -d "$WHEELER_DIR/.git" ]]; then
    cp "$WHEELER_DIR/.githooks/pre-commit" "$WHEELER_DIR/.git/hooks/pre-commit"
    cp "$WHEELER_DIR/.githooks/pre-push" "$WHEELER_DIR/.git/hooks/pre-push"
    chmod +x "$WHEELER_DIR/.git/hooks/pre-commit" "$WHEELER_DIR/.git/hooks/pre-push"
    step "Git hooks installed (pre-commit + pre-push)"
else
    warn "Not a git repo — skipping hook installation"
fi

# ── wh launcher ────────────────────────────────────────────────────
chmod +x "$WHEELER_DIR/bin/wh"
if [[ -L /usr/local/bin/wh ]] || [[ -f /usr/local/bin/wh ]]; then
    step "wh launcher symlinked"
else
    warn "To install the wh launcher globally:"
    echo -e "  ${DIM}  sudo ln -sf $WHEELER_DIR/bin/wh /usr/local/bin/wh${RESET}"
fi

# ── Zsh completions ──────────────────────────────────────────────
COMP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions"
mkdir -p "$COMP_DIR"
cat > "$COMP_DIR/_wh" << 'ZSHCOMP'
#compdef wh

_wh() {
    local -a subcommands
    subcommands=(
        'queue:Queue a background task (sonnet)'
        'quick:Fast one-shot task (haiku)'
        'status:Graph status check (haiku)'
        'hooks:Git hook management'
        'help:Show usage'
    )
    _describe 'subcommand' subcommands
}

_wh "$@"
ZSHCOMP
step "Zsh completions installed to $COMP_DIR/_wh"

echo ""
echo -e "  ${GREEN}${BOLD}Done.${RESET} Run ${AMBER}claude${RESET} in this directory, then use ${AMBER}/wh:plan${RESET} to start Wheeler."
echo -e "  ${DIM}For zsh completions, ensure $COMP_DIR is in your \$fpath${RESET}"
echo ""
