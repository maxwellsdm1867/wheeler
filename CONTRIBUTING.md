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
- New MCP tools that follow the existing patterns in `wheeler/mcp_server.py`
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
