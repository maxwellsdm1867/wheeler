# Contributing to Wheeler

Thanks for your interest in contributing to Wheeler! This project is a thinking partner for scientists, and we welcome contributions that make it better at that job.

## Development Setup

Wheeler uses [uv](https://docs.astral.sh/uv/) for environment management. The
`uv.lock` checked into the repo pins every transitive dependency.

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
uv sync --extra dev          # creates .venv/, installs core + dev deps from uv.lock
```

That's it. `uv run wheeler --version` should now print the installed version.

### Project-local Codex development

To expose this checkout's 39 Wheeler skills and four MCP servers to Codex,
generate machine-local wiring from the repository root:

```bash
python scripts/configure-codex-dev.py
```

On Windows, the generator uses native `uv` when available and otherwise falls
back to WSL. You can select WSL explicitly from PowerShell:

```powershell
python scripts/configure-codex-dev.py --host wsl --wsl-distro Ubuntu
```

The generated `.agents/skills` link and `.codex/config.toml` are excluded only
in this checkout. The MCP commands use `uv run --frozen` against the editable
source tree. WSL gets a distro-local environment outside the mounted checkout,
so it cannot replace a Windows `.venv`. Credentials are read at runtime and are
never written to the generated Codex configuration.

After restarting Codex in the project, run the strict certificate. It requires
all 39 skills, the exact 53-tool MCP surface, the Codex `start` act, an
authenticated Neo4j `RETURN 1`, and a real E2E run with no skips:

```bash
uv run --frozen --extra dev python scripts/certify-codex-dev.py
```

When Windows is using the WSL fallback because native `uv` is unavailable, run
the certifier with the checkout's already-synced Windows development Python. It
will reuse the generated WSL launcher for MCP and E2E execution:

```powershell
.\.venv\Scripts\python.exe scripts\certify-codex-dev.py
```

The local E2E defaults are `bolt://localhost:7687`, user `neo4j`, database
`neo4j`, and the development password used by `bin/setup.sh`. Override the
standard `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE`
environment variables when your local service differs.

For the full bootstrap (Neo4j in Docker, schema init, git hooks, zsh
completions) the bundled script still works:

```bash
bash bin/setup.sh
```

Manual pip path (no uv):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Neo4j (required for graph features)
docker run -d -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/research-graph neo4j:community

wheeler graph init
```

## Running Tests

```bash
uv run pytest tests/ -q                       # all unit tests
uv run pytest tests/e2e/ -v                   # live-Neo4j e2e tests
uv run pytest tests/test_merge.py -v          # one file
```

Or with the pip workflow: `source .venv/bin/activate && python -m pytest tests/`.

Tests run automatically on pre-commit and pre-push hooks. Install hooks with:

```bash
wh hooks install
```

## Code Style

- Python 3.11+ with type hints on public APIs
- Formatting: `uv run ruff format wheeler/`
- Linting: `uv run ruff check wheeler/`
- Type checking: `uv run mypy wheeler/ --ignore-missing-imports`

Pre-commit hooks enforce these automatically.

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Make your changes
4. Run tests (`python -m pytest tests/ -v`)
5. Commit with a clear message
6. Push to your fork and open a Pull Request

## Hard Rules

- **No direct API calls to Anthropic.** Wheeler runs on Claude Max subscription. Never import the anthropic SDK or reference API key environment variables. If you need programmatic LLM access, use `subprocess.run(["claude", "-p", prompt])`.
- **Everything is a reference.** Factual claims cite graph nodes. Citation validation is deterministic (regex + Cypher), never LLM self-judgment.
- **Pre-commit hooks must pass.** They check for API key leaks, run tests, and lint. Don't skip them.

## What to Contribute

- Bug fixes and test improvements
- New MCP tools that follow the existing patterns in the split servers (`wheeler/mcp_core.py`, `mcp_query.py`, `mcp_mutations.py`, `mcp_ops.py`)
- Documentation improvements
- Graph schema enhancements
- Better citation validation patterns

## What to Discuss First

Open an issue before starting work on:

- New slash commands (`/wh:*`)
- Changes to the knowledge graph schema
- New dependencies
- Architectural changes

## Reporting Bugs

Open an issue with:

1. What you expected to happen
2. What actually happened
3. Steps to reproduce
4. Your environment (Python version, OS, Neo4j version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
