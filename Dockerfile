# Wheeler container image.
#
# Two targets:
#   test     (default) runs the unit suite, which is what CI wants.
#   runtime  a deployable Wheeler with the four MCP servers and the CLI on PATH.
#
# Build:
#   docker build --target runtime -t wheeler:runtime .
#   docker build --target test    -t wheeler:test    .
#
# IMPORTANT, and easy to get half-right: Wheeler's state lives in TWO places and
# neither is complete alone.
#
#   * Node CONTENT lives only in knowledge/*.json. The graph stores just a
#     ~100-char title, and regenerating the JSON from the graph is not supported.
#   * Graph EDGES live only in Neo4j. The node JSON has no relationships field.
#
# So a container needs a durable volume for the project tree AND a durable volume
# for the Neo4j store. Persist one and you lose half the graph. `.dockerignore`
# deliberately excludes knowledge/, .wheeler/, .plans/ and friends so the image
# can never carry stale state: it arrives by volume mount or `wheeler restore`.
# See docker-compose.yml for a wiring that gets this right.

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

# uv gives us fast, reproducible installs and is also how the published plugin
# launches the MCP servers (uvx --from wheeler ...).
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy only what the install needs first, so dependency layers cache across
# source edits.
COPY pyproject.toml README.md ./
COPY wheeler/ wheeler/

# ---------------------------------------------------------------------------
FROM base AS test

# The test extra pulls in the llmsr extra (scipy) so the equation-discovery
# tests actually run rather than skip.
RUN uv pip install --system --no-cache -e ".[test]"

COPY tests/ tests/
COPY .claude/ .claude/
COPY ARCHITECTURE.md CLAUDE.md ./

# tests/e2e needs a live Neo4j, so it is excluded here. Run it against the
# compose stack instead: see docker-compose.yml.
CMD ["python", "-m", "pytest", "tests/", "-v", "--ignore=tests/e2e"]

# ---------------------------------------------------------------------------
FROM base AS runtime

RUN uv pip install --system --no-cache .

# Where the project tree (knowledge/, synthesis/, .wheeler/, .plans/) is mounted.
# Wheeler resolves its paths from here rather than from an incidental CWD.
ENV WHEELER_PROJECT_ROOT=/project
WORKDIR /project

# No credentials are baked in. Supply these at run time, or use `wheeler login`.
# Defaults point at the compose service name, not localhost, because inside a
# container localhost is the container itself.
ENV NEO4J_URI=bolt://neo4j:7687 \
    NEO4J_USERNAME=neo4j \
    NEO4J_DATABASE=neo4j \
    PYTHONUNBUFFERED=1

RUN groupadd --system wheeler \
    && useradd --system --gid wheeler --create-home wheeler \
    && mkdir -p /project \
    && chown -R wheeler:wheeler /project
USER wheeler

# Default to something inspectable rather than a server on stdio: an MCP server
# started with no client attached just sits there looking broken. Override with
# e.g. `wheeler serve core` (stdio) when a host is actually driving it.
CMD ["wheeler", "doctor"]
