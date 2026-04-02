FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY wheeler/ wheeler/
COPY tests/ tests/
COPY .claude/ .claude/
COPY ARCHITECTURE.md CLAUDE.md README.md ./

RUN pip install -e ".[test]"

CMD ["python", "-m", "pytest", "tests/", "-v", "--ignore=tests/e2e"]
