# Contributing to Wheeler

Thanks for your interest in contributing to Wheeler! This project is a thinking partner for scientists, and we welcome contributions that make it better at that job.

## Development Setup

```bash
git clone https://github.com/maxwellsdm1867/wheeler.git
cd wheeler
bash bin/setup.sh
```

Or manually:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"

# Neo4j (required for graph features)
docker run -d -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/research-graph neo4j:community

wheeler-tools graph init
```

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Tests run automatically on pre-commit and pre-push hooks. Install hooks with:

```bash
wh hooks install
```

## Code Style

- Python 3.10+ with type hints on public APIs
- Formatting: `ruff format wheeler/`
- Linting: `ruff check wheeler/`
- Type checking: `mypy wheeler/`

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
