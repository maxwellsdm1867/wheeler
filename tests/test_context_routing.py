"""Tests that commands and MCP split servers correctly wire graph context.

Two concerns:
1. Commands that should auto-load context (plan, discuss, execute, etc.)
   actually have the right MCP tools in allowed-tools AND instruct their
   use in the body text.
2. MCP split servers expose the right tools for each research task category:
   context loading, querying, mutations, and ops.

These tests catch silent regressions where a tool is removed from
allowed-tools or a body instruction is deleted, breaking context
utilization without any Python error.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

COMMANDS_DIR = Path(__file__).parent.parent / ".claude" / "commands" / "wh"
DATA_DIR = Path(__file__).parent.parent / "wheeler" / "_data" / "commands"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_command(name: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body_text) for a command."""
    path = COMMANDS_DIR / f"{name}.md"
    content = path.read_text()
    parts = content.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2] if len(parts) > 2 else ""
    return frontmatter, body


def _allowed_tools(name: str) -> list[str]:
    fm, _ = _load_command(name)
    return fm.get("allowed-tools", [])


def _body(name: str) -> str:
    _, body = _load_command(name)
    return body


def _has_tool(name: str, tool: str) -> bool:
    """Check if a command has a specific tool or a glob that covers it.

    Handles both exact matches and wildcard patterns like mcp__wheeler_core__*.
    """
    tools = _allowed_tools(name)
    for t in tools:
        if t == tool:
            return True
        # Glob pattern: mcp__wheeler_core__* matches mcp__wheeler_core__graph_context
        if t.endswith("*") and tool.startswith(t[:-1]):
            return True
    return False


# ===================================================================
# 1. Plan command: auto-context search
# ===================================================================


class TestPlanAutoContext:
    """Verify /wh:plan loads graph context when a topic is provided."""

    def test_plan_has_search_context_tool(self):
        """Plan must have search_context in allowed-tools for auto-loading."""
        assert _has_tool("plan", "mcp__wheeler_core__search_context"), (
            "plan.md must include mcp__wheeler_core__search_context"
        )

    def test_plan_has_graph_gaps_tool(self):
        """Plan must have graph_gaps for showing thin coverage areas."""
        assert _has_tool("plan", "mcp__wheeler_core__graph_gaps"), (
            "plan.md must include mcp__wheeler_core__graph_gaps"
        )

    def test_plan_has_graph_context_tool(self):
        """Plan must have graph_context for general context loading."""
        assert _has_tool("plan", "mcp__wheeler_core__graph_context"), (
            "plan.md must include mcp__wheeler_core__graph_context"
        )

    def test_plan_body_instructs_search_context_call(self):
        """Plan body must instruct calling search_context with the topic."""
        body = _body("plan")
        assert "search_context" in body, (
            "plan.md body must reference search_context"
        )

    def test_plan_body_instructs_auto_call_on_arguments(self):
        """Plan body must instruct calling search_context when $ARGUMENTS names a topic."""
        body = _body("plan")
        # The plan command says: "If $ARGUMENTS names a clear research topic,
        # call search_context with it"
        assert "$ARGUMENTS" in body, "plan.md must reference $ARGUMENTS"
        # Verify the instruction links $ARGUMENTS to search_context
        # Find the paragraph containing $ARGUMENTS and check search_context is nearby
        lines = body.split("\n")
        args_lines = [i for i, line in enumerate(lines) if "$ARGUMENTS" in line]
        assert args_lines, "plan.md must have a line referencing $ARGUMENTS"
        for line_idx in args_lines:
            # Check within 5 lines for search_context
            window = "\n".join(lines[max(0, line_idx - 2):line_idx + 5])
            if "search_context" in window:
                return
        pytest.fail(
            "plan.md must instruct calling search_context near the $ARGUMENTS reference"
        )

    def test_plan_body_instructs_graph_gaps_alongside(self):
        """Plan body must instruct using graph_gaps alongside search_context."""
        body = _body("plan")
        assert "graph_gaps" in body, (
            "plan.md body must reference graph_gaps for showing coverage gaps"
        )

    def test_plan_has_query_tools_for_context(self):
        """Plan must have query tools to inspect specific node types."""
        required = [
            "mcp__wheeler_query__query_findings",
            "mcp__wheeler_query__query_hypotheses",
            "mcp__wheeler_query__query_open_questions",
        ]
        for tool in required:
            assert _has_tool("plan", tool), (
                f"plan.md must include {tool} for inspecting prior knowledge"
            )

    def test_plan_has_limited_mutation_tools(self):
        """Plan mode allows ensure_artifact and update_node for graph registration.

        Plan mode needs to register plans as graph nodes and update their
        status on scientist approval. Other mutations (add_finding, etc.)
        are not allowed.
        """
        tools = _allowed_tools("plan")
        mutation_tools = [t for t in tools if "wheeler_mutations" in t]
        allowed_plan_mutations = {
            "mcp__wheeler_mutations__ensure_artifact",
            "mcp__wheeler_mutations__update_node",
        }
        for t in mutation_tools:
            assert t in allowed_plan_mutations, (
                f"plan.md has unexpected mutation tool: {t}"
            )


# ===================================================================
# 2. Context tool access: every command that references context
#    in its body must have the tool in allowed-tools
# ===================================================================


# Map of body references to the MCP tool that implements them
CONTEXT_TOOL_MAP = {
    "search_context": "mcp__wheeler_core__search_context",
    "graph_context": "mcp__wheeler_core__graph_context",
    "graph_gaps": "mcp__wheeler_core__graph_gaps",
    "search_findings": "mcp__wheeler_core__search_findings",
    "detect_stale": "mcp__wheeler_ops__detect_stale",
    "validate_citations": "mcp__wheeler_ops__validate_citations",
    "run_cypher": "mcp__wheeler_core__run_cypher",
}

# All commands (excluding internal-only and CLAUDE.md)
ALL_COMMANDS = [
    p.stem for p in COMMANDS_DIR.glob("*.md") if p.name != "CLAUDE.md"
]


class TestContextToolConsistency:
    """If a command body says 'call search_context', allowed-tools must include it."""

    @pytest.mark.parametrize("cmd", ALL_COMMANDS)
    def test_body_tool_references_have_access(self, cmd):
        """Every tool named in the body text must be in allowed-tools."""
        body = _body(cmd)
        tools = _allowed_tools(cmd)

        for body_ref, mcp_tool in CONTEXT_TOOL_MAP.items():
            # Check if the body references this tool (as a function call or instruction)
            # Match patterns like: "call search_context", "use graph_context",
            # "`search_context`", "search_context(", etc.
            pattern = rf"(?:call|use|invoke|run)\s+`?{body_ref}`?"
            backtick_pattern = rf"`{body_ref}`"
            bare_pattern = rf"\b{body_ref}\b"

            # Only check if the body actually references this tool
            if not re.search(bare_pattern, body):
                continue

            assert _has_tool(cmd, mcp_tool), (
                f"{cmd}.md body references '{body_ref}' but allowed-tools "
                f"does not include '{mcp_tool}' (or a glob covering it)"
            )


# ===================================================================
# 3. Research task categories: the right tools for the right job
# ===================================================================


# Commands grouped by what they need to do with the graph
CONTEXT_LOADERS = [
    "plan", "discuss", "execute", "pair", "resume", "reconvene",
    "handoff", "pause", "close", "start",
]

QUERY_READERS = [
    "plan", "discuss", "ask", "chat", "compile", "dream",
    "report", "status", "close", "pause", "resume", "reconvene",
    "handoff", "note",
]

MUTATORS = [
    "execute", "add", "note", "ingest", "dream", "compile",
    "close", "write", "pair", "chat",
]

OPS_USERS = [
    "dream", "close", "status", "reconvene", "write", "compile", "report",
    "resume",
]


class TestResearchTaskToolAccess:
    """Verify commands have the right tools for their research task category."""

    @pytest.mark.parametrize("cmd", CONTEXT_LOADERS)
    def test_context_loaders_have_graph_context(self, cmd):
        """Commands that load context must have graph_context."""
        assert _has_tool(cmd, "mcp__wheeler_core__graph_context"), (
            f"{cmd}.md is a context-loading command but lacks graph_context"
        )

    @pytest.mark.parametrize("cmd", QUERY_READERS)
    def test_query_readers_have_at_least_one_query_tool(self, cmd):
        """Commands that read the graph must have at least one query tool."""
        query_tools = [
            "mcp__wheeler_query__query_findings",
            "mcp__wheeler_query__query_hypotheses",
            "mcp__wheeler_query__query_open_questions",
            "mcp__wheeler_query__query_datasets",
            "mcp__wheeler_query__query_papers",
            "mcp__wheeler_query__query_documents",
            "mcp__wheeler_query__query_notes",
        ]
        has_any = any(_has_tool(cmd, t) for t in query_tools)
        # Also check for wildcard pattern
        tools = _allowed_tools(cmd)
        has_glob = any(t == "mcp__wheeler_query__*" for t in tools)
        assert has_any or has_glob, (
            f"{cmd}.md is a graph-reading command but has no query tools"
        )

    @pytest.mark.parametrize("cmd", MUTATORS)
    def test_mutators_have_at_least_one_mutation_tool(self, cmd):
        """Commands that modify the graph must have at least one mutation tool."""
        tools = _allowed_tools(cmd)
        has_mutation = any("wheeler_mutations" in t for t in tools)
        assert has_mutation, (
            f"{cmd}.md is a mutation command but has no mutation tools"
        )

    @pytest.mark.parametrize("cmd", OPS_USERS)
    def test_ops_users_have_at_least_one_ops_tool(self, cmd):
        """Commands that need ops capabilities must have at least one ops tool."""
        tools = _allowed_tools(cmd)
        has_ops = any("wheeler_ops" in t for t in tools)
        assert has_ops, (
            f"{cmd}.md needs ops tools but has none in allowed-tools"
        )


# ===================================================================
# 4. MCP split server tool coverage
# ===================================================================


class TestMCPSplitServerTools:
    """Verify MCP split servers register the tools commands reference."""

    @pytest.fixture(scope="class")
    def split_server_tools(self):
        """Load tool names from all four split servers."""
        import asyncio
        from unittest.mock import patch
        with patch.dict("os.environ", {"WHEELER_YAML": "/dev/null"}, clear=False):
            try:
                import wheeler.mcp_core as core
                import wheeler.mcp_query as query
                import wheeler.mcp_mutations as mutations
                import wheeler.mcp_ops as ops
                result = {}
                for name, mod in [("core", core), ("query", query),
                                  ("mutations", mutations), ("ops", ops)]:
                    tools = asyncio.run(mod.mcp.list_tools())
                    result[name] = {t.name for t in tools}
                return result
            except Exception:
                pytest.skip("Cannot import split servers")

    def test_core_has_context_tools(self, split_server_tools):
        """Core server must register all context-loading tools."""
        core = split_server_tools["core"]
        for tool in ["graph_context", "graph_gaps", "search_context", "search_findings"]:
            assert tool in core, f"Core server missing {tool}"

    def test_core_has_infrastructure_tools(self, split_server_tools):
        """Core server must register health, status, cypher, schema tools."""
        core = split_server_tools["core"]
        for tool in ["graph_health", "graph_status", "run_cypher", "init_schema"]:
            assert tool in core, f"Core server missing {tool}"

    def test_query_has_all_type_queries(self, split_server_tools):
        """Query server must register queries for all node types."""
        query = split_server_tools["query"]
        for tool in [
            "query_findings", "query_hypotheses", "query_open_questions",
            "query_datasets", "query_papers", "query_documents", "query_notes",
        ]:
            assert tool in query, f"Query server missing {tool}"

    def test_mutations_has_all_add_tools(self, split_server_tools):
        """Mutations server must register all add_* tools."""
        mutations = split_server_tools["mutations"]
        for tool in [
            "add_finding", "add_hypothesis", "add_question",
            "add_dataset", "add_paper", "add_document", "add_note",
        ]:
            assert tool in mutations, f"Mutations server missing {tool}"

    def test_mutations_has_relationship_tools(self, split_server_tools):
        """Mutations server must register link, unlink, delete tools."""
        mutations = split_server_tools["mutations"]
        for tool in ["link_nodes", "unlink_nodes", "delete_node", "set_tier"]:
            assert tool in mutations, f"Mutations server missing {tool}"

    def test_ops_has_provenance_tools(self, split_server_tools):
        """Ops server must register provenance and validation tools."""
        ops = split_server_tools["ops"]
        for tool in ["detect_stale", "hash_file", "validate_citations", "extract_citations"]:
            assert tool in ops, f"Ops server missing {tool}"


# ===================================================================
# 5. Command tool references resolve to the correct split server
# ===================================================================


# Which server prefix owns which tool namespace
SERVER_PREFIXES = {
    "mcp__wheeler_core__": "core",
    "mcp__wheeler_query__": "query",
    "mcp__wheeler_mutations__": "mutations",
    "mcp__wheeler_ops__": "ops",
}


class TestToolServerMapping:
    """Verify tool references in commands point to the correct split server."""

    @pytest.fixture(scope="class")
    def all_server_tools(self):
        """Map of server_name -> set of tool names."""
        import asyncio
        from unittest.mock import patch
        with patch.dict("os.environ", {"WHEELER_YAML": "/dev/null"}, clear=False):
            try:
                import wheeler.mcp_core as core
                import wheeler.mcp_query as query
                import wheeler.mcp_mutations as mutations
                import wheeler.mcp_ops as ops
                result = {}
                for name, mod in [("core", core), ("query", query),
                                  ("mutations", mutations), ("ops", ops)]:
                    tools = asyncio.run(mod.mcp.list_tools())
                    result[name] = {t.name for t in tools}
                return result
            except Exception:
                pytest.skip("Cannot import split servers")

    @pytest.mark.parametrize("cmd", ALL_COMMANDS)
    def test_tool_references_resolve_to_server(self, cmd, all_server_tools):
        """Every explicit MCP tool in allowed-tools must exist on its server.

        Wildcards (mcp__wheeler_core__*) are skipped since they match any tool.
        """
        tools = _allowed_tools(cmd)
        for tool in tools:
            # Skip non-MCP tools and wildcards
            if not tool.startswith("mcp__wheeler_"):
                continue
            if tool.endswith("*"):
                continue

            # Find which server this tool claims to be on
            matched_server = None
            tool_name = None
            for prefix, server in SERVER_PREFIXES.items():
                if tool.startswith(prefix):
                    matched_server = server
                    tool_name = tool[len(prefix):]
                    break

            if matched_server is None:
                pytest.fail(
                    f"{cmd}.md references '{tool}' which doesn't match any "
                    f"known server prefix: {list(SERVER_PREFIXES.keys())}"
                )

            server_tools = all_server_tools[matched_server]
            assert tool_name in server_tools, (
                f"{cmd}.md references '{tool}' but '{tool_name}' is not "
                f"registered on the {matched_server} server. "
                f"Available: {sorted(server_tools)}"
            )


# ===================================================================
# 6. Both command trees stay in sync for context tools
# ===================================================================


class TestContextToolTreeSync:
    """Verify .claude/ and _data/ trees have identical context tool access."""

    @pytest.mark.parametrize("cmd", ALL_COMMANDS)
    def test_allowed_tools_identical(self, cmd):
        """allowed-tools must be identical between .claude/ and _data/ copies."""
        claude_path = COMMANDS_DIR / f"{cmd}.md"
        data_path = DATA_DIR / f"{cmd}.md"
        if not data_path.exists():
            pytest.skip(f"No _data mirror for {cmd}")

        claude_fm, _ = _load_command(cmd)
        data_content = data_path.read_text()
        data_parts = data_content.split("---", 2)
        data_fm = yaml.safe_load(data_parts[1])

        claude_tools = set(claude_fm.get("allowed-tools", []))
        data_tools = set(data_fm.get("allowed-tools", []))

        assert claude_tools == data_tools, (
            f"{cmd}.md allowed-tools differ:\n"
            f"  .claude only: {claude_tools - data_tools}\n"
            f"  _data only:   {data_tools - claude_tools}"
        )


# ===================================================================
# 7. Specific research task scenarios
# ===================================================================


class TestResearchScenarioToolAccess:
    """Scenario-driven tests: for each research task, verify the command
    and MCP tools form a complete chain from intent to graph operation."""

    def test_plan_investigation_chain(self):
        """Planning an investigation: need context, gaps, query, and limited mutations for graph registration."""
        tools = _allowed_tools("plan")
        # Must be able to load context
        assert _has_tool("plan", "mcp__wheeler_core__search_context")
        assert _has_tool("plan", "mcp__wheeler_core__graph_gaps")
        # Must be able to query existing knowledge
        assert _has_tool("plan", "mcp__wheeler_query__query_findings")
        assert _has_tool("plan", "mcp__wheeler_query__query_hypotheses")
        # Must be able to query plans for dedup
        assert _has_tool("plan", "mcp__wheeler_query__query_plans")
        # Must be able to write plan files
        assert "Write" in tools
        # Must have ensure_artifact and update_node for graph registration
        assert _has_tool("plan", "mcp__wheeler_mutations__ensure_artifact")
        assert _has_tool("plan", "mcp__wheeler_mutations__update_node")

    def test_execute_investigation_chain(self):
        """Executing an investigation: need full access to all servers."""
        tools = _allowed_tools("execute")
        # Needs context
        assert _has_tool("execute", "mcp__wheeler_core__graph_context")
        # Needs mutations to record findings
        assert _has_tool("execute", "mcp__wheeler_mutations__add_finding")
        assert _has_tool("execute", "mcp__wheeler_mutations__link_nodes")
        # Needs code execution
        assert "Bash" in tools
        assert "Edit" in tools

    def test_discuss_sharpening_chain(self):
        """Discussing/sharpening a question: context + gaps, limited mutations."""
        assert _has_tool("discuss", "mcp__wheeler_core__graph_context")
        assert _has_tool("discuss", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("discuss", "mcp__wheeler_query__query_findings")
        assert _has_tool("discuss", "mcp__wheeler_query__query_open_questions")

    def test_write_drafting_chain(self):
        """Drafting text: context, citations, document creation."""
        assert _has_tool("write", "mcp__wheeler_core__graph_context")
        assert _has_tool("write", "mcp__wheeler_query__query_findings")
        assert _has_tool("write", "mcp__wheeler_mutations__add_document")
        assert _has_tool("write", "mcp__wheeler_ops__validate_citations")
        assert _has_tool("write", "mcp__wheeler_ops__extract_citations")

    def test_dream_consolidation_chain(self):
        """Graph consolidation: full read access + tier mutations + ops."""
        assert _has_tool("dream", "mcp__wheeler_core__graph_context")
        assert _has_tool("dream", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("dream", "mcp__wheeler_mutations__set_tier")
        assert _has_tool("dream", "mcp__wheeler_mutations__link_nodes")
        assert _has_tool("dream", "mcp__wheeler_ops__detect_stale")

    def test_resume_context_restoration_chain(self):
        """Resuming a session: need context + gaps + queries to restore state."""
        assert _has_tool("resume", "mcp__wheeler_core__graph_context")
        assert _has_tool("resume", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("resume", "mcp__wheeler_query__query_findings")
        assert _has_tool("resume", "mcp__wheeler_ops__detect_stale")

    def test_close_session_chain(self):
        """Closing a session: sweep for orphans, check staleness."""
        assert _has_tool("close", "mcp__wheeler_core__graph_context")
        assert _has_tool("close", "mcp__wheeler_core__run_cypher")
        assert _has_tool("close", "mcp__wheeler_mutations__link_nodes")
        assert _has_tool("close", "mcp__wheeler_ops__detect_stale")

    def test_add_ingest_chain(self):
        """Adding content to graph: search for duplicates, then create."""
        assert _has_tool("add", "mcp__wheeler_core__search_findings")
        assert _has_tool("add", "mcp__wheeler_core__graph_context")
        assert _has_tool("add", "mcp__wheeler_mutations__add_finding")
        assert _has_tool("add", "mcp__wheeler_mutations__add_paper")
        assert _has_tool("add", "mcp__wheeler_mutations__link_nodes")
        assert _has_tool("add", "mcp__wheeler_core__index_node")

    def test_note_capture_chain(self):
        """Quick note capture: graph context + add + link."""
        assert _has_tool("note", "mcp__wheeler_core__graph_context")
        assert _has_tool("note", "mcp__wheeler_mutations__add_note")
        assert _has_tool("note", "mcp__wheeler_mutations__link_nodes")

    def test_compile_synthesis_chain(self):
        """Compiling synthesis: full read + document creation + citations."""
        assert _has_tool("compile", "mcp__wheeler_core__graph_context")
        assert _has_tool("compile", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("compile", "mcp__wheeler_core__search_findings")
        assert _has_tool("compile", "mcp__wheeler_query__query_findings")
        assert _has_tool("compile", "mcp__wheeler_mutations__add_document")
        assert _has_tool("compile", "mcp__wheeler_ops__validate_citations")

    def test_reconvene_review_chain(self):
        """Reconvening after handoff: context + gaps + staleness check."""
        assert _has_tool("reconvene", "mcp__wheeler_core__graph_context")
        assert _has_tool("reconvene", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("reconvene", "mcp__wheeler_ops__detect_stale")
        assert _has_tool("reconvene", "mcp__wheeler_ops__validate_citations")

    def test_ask_query_chain(self):
        """Querying the graph: broad read access, no mutations."""
        tools = _allowed_tools("ask")
        assert _has_tool("ask", "mcp__wheeler_core__graph_context")
        assert _has_tool("ask", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("ask", "mcp__wheeler_core__run_cypher")
        # ask should have multiple query tools
        query_count = sum(1 for t in tools if "wheeler_query" in t)
        assert query_count >= 5, (
            f"ask.md should have broad query access, has only {query_count} query tools"
        )
        # ask should NOT have mutation tools
        mutation_count = sum(1 for t in tools if "wheeler_mutations" in t)
        assert mutation_count == 0, "ask.md should not have mutation tools"

    def test_status_overview_chain(self):
        """Checking status: health + gaps + staleness."""
        assert _has_tool("status", "mcp__wheeler_core__graph_health")
        assert _has_tool("status", "mcp__wheeler_core__graph_status")
        assert _has_tool("status", "mcp__wheeler_core__graph_gaps")
        assert _has_tool("status", "mcp__wheeler_ops__detect_stale")


# ===================================================================
# 8. Graph-as-source-of-truth enforcement (v0.7.0)
#
# Every act that reads plan state must query the graph first via
# query_plans, not scan .plans/ as the primary lookup. Filesystem
# fallback is allowed only as a secondary on-ramp for unregistered
# plans. Status transitions must go through update_node, not just
# file frontmatter edits.
# ===================================================================


class TestGraphFirstToolAccess:
    """Acts that reference plans must have query_plans in allowed-tools."""

    # Acts that need to discover plans by status
    @pytest.mark.parametrize("cmd", [
        "execute", "handoff", "reconvene", "resume", "status", "compile", "report",
    ])
    def test_plan_querying_acts_have_query_plans(self, cmd):
        assert _has_tool(cmd, "mcp__wheeler_query__query_plans"), (
            f"{cmd}.md must have query_plans for graph-first plan lookup"
        )

    # Acts that need to transition plan status
    @pytest.mark.parametrize("cmd", ["execute", "handoff"])
    def test_execution_acts_have_update_node(self, cmd):
        assert _has_tool(cmd, "mcp__wheeler_mutations__update_node"), (
            f"{cmd}.md must have update_node for graph-authoritative status transitions"
        )

    def test_plan_act_has_ensure_artifact(self):
        """/wh:plan must have ensure_artifact for mandatory graph registration."""
        assert _has_tool("plan", "mcp__wheeler_mutations__ensure_artifact")

    def test_plan_act_has_query_plans(self):
        """/wh:plan must have query_plans for dedup check before writing."""
        assert _has_tool("plan", "mcp__wheeler_query__query_plans")


class TestGraphFirstPromptText:
    """The body text of acts must instruct graph-first, not filesystem-first."""

    def test_execute_queries_graph_before_glob(self):
        """execute.md must call query_plans before falling back to Glob."""
        body = _body("execute")
        graph_pos = body.find("query_plans")
        glob_pos = body.find("Glob")
        assert graph_pos != -1, "execute.md must reference query_plans"
        assert graph_pos < glob_pos, (
            "execute.md must call query_plans BEFORE falling back to Glob"
        )

    def test_execute_calls_query_plans_for_approved_and_in_progress(self):
        """execute.md must query for both approved and in-progress plans."""
        body = _body("execute")
        assert 'query_plans(status="approved")' in body
        assert 'query_plans(status="in-progress")' in body

    def test_execute_update_node_for_status_transitions(self):
        """execute.md must use update_node for plan status changes."""
        body = _body("execute")
        assert "update_node" in body
        assert 'status="in-progress"' in body or "in-progress" in body

    def test_resume_queries_graph_first(self):
        """resume.md step 0 must be query_plans, not STATE.md read."""
        body = _body("resume")
        # Step 0 should mention query_plans
        step0_match = re.search(r"## Step 0.*?\n(.*?)(?=\n## Step|\Z)", body, re.DOTALL)
        assert step0_match, "resume.md must have a Step 0"
        step0_text = step0_match.group(1)
        assert "query_plans" in step0_text, (
            "resume.md Step 0 must use query_plans as the primary lookup"
        )

    def test_resume_state_md_is_fallback_not_primary(self):
        """resume.md must treat STATE.md as fallback, not the authoritative source."""
        body = _body("resume")
        assert "Fall back" in body or "fall back" in body, (
            "resume.md must mark STATE.md as a fallback, not the primary source"
        )

    def test_status_queries_graph_first(self):
        """status.md must call query_plans before scanning .plans/."""
        body = _body("status")
        assert "query_plans" in body, "status.md must reference query_plans"

    def test_status_graph_wins_over_state_md(self):
        """status.md must declare graph as authoritative over STATE.md."""
        body = _body("status")
        assert "graph wins" in body.lower() or "graph is authoritative" in body.lower() or "graph disagree" in body.lower(), (
            "status.md must declare graph wins when it disagrees with STATE.md"
        )

    def test_reconvene_queries_graph_first(self):
        """reconvene.md step 0 must use query_plans."""
        body = _body("reconvene")
        step0_match = re.search(r"### Step 0.*?\n(.*?)(?=\n### Step|\Z)", body, re.DOTALL)
        assert step0_match, "reconvene.md must have a Step 0"
        step0_text = step0_match.group(1)
        assert "query_plans" in step0_text, (
            "reconvene.md Step 0 must use query_plans"
        )

    def test_handoff_queries_graph_not_filesystem(self):
        """handoff.md must call query_plans, not check .plans/ directly."""
        body = _body("handoff")
        assert "query_plans" in body, "handoff.md must reference query_plans"
        # Should NOT have "Check .plans/" as the primary instruction
        assert "Check `.plans/`" not in body, (
            "handoff.md should not scan .plans/ as primary plan lookup"
        )

    def test_plan_has_graph_registration_section(self):
        """plan.md must have a mandatory graph registration section."""
        body = _body("plan")
        assert "Graph registration" in body, (
            "plan.md must have a 'Graph registration' section"
        )
        assert "mandatory" in body.lower() or "MUST" in body, (
            "plan.md graph registration must be described as mandatory"
        )

    def test_plan_frontmatter_includes_graph_node(self):
        """plan.md template frontmatter must include graph_node field."""
        body = _body("plan")
        assert "graph_node:" in body, (
            "plan.md plan template must include graph_node: field"
        )


class TestGraphNativeSessionState:
    """Pause/resume use graph-native session state, not just files."""

    def test_pause_has_add_note(self):
        """/wh:pause must have add_note for continuation context."""
        assert _has_tool("pause", "mcp__wheeler_mutations__add_note")

    def test_pause_has_add_execution(self):
        """/wh:pause must have add_execution for process provenance."""
        assert _has_tool("pause", "mcp__wheeler_mutations__add_execution")

    def test_pause_has_link_nodes(self):
        """/wh:pause must have link_nodes to connect notes/executions to plans."""
        assert _has_tool("pause", "mcp__wheeler_mutations__link_nodes")

    def test_pause_has_query_plans(self):
        """/wh:pause must find active plan via graph query."""
        assert _has_tool("pause", "mcp__wheeler_query__query_plans")

    def test_pause_body_creates_graph_note(self):
        """pause.md must instruct creating a graph note for continuation."""
        body = _body("pause")
        assert "add_note" in body, "pause.md must instruct add_note for continuation"
        assert "session-continuation" in body, (
            "pause.md must use session-continuation context pattern"
        )

    def test_pause_body_creates_execution_node(self):
        """pause.md must record the pause as an Execution node."""
        body = _body("pause")
        assert "add_execution" in body
        assert "pause" in body.lower()

    def test_resume_has_query_notes(self):
        """/wh:resume must have query_notes to find continuation context."""
        assert _has_tool("resume", "mcp__wheeler_query__query_notes")

    def test_resume_body_queries_continuation_notes(self):
        """resume.md must look for session-continuation notes."""
        body = _body("resume")
        assert "query_notes" in body or "session-continuation" in body, (
            "resume.md must look for continuation notes from the graph"
        )


class TestProcessProvenance:
    """Close and handoff record process events in the graph."""

    def test_close_has_consistency_check(self):
        """/wh:close must have graph_consistency_check for drift detection."""
        assert _has_tool("close", "mcp__wheeler_ops__graph_consistency_check")

    def test_close_body_runs_consistency_check(self):
        """close.md body must instruct running graph_consistency_check."""
        body = _body("close")
        assert "graph_consistency_check" in body or "consistency" in body.lower()

    def test_handoff_has_add_execution(self):
        """/wh:handoff must have add_execution for handoff provenance."""
        assert _has_tool("handoff", "mcp__wheeler_mutations__add_execution")

    def test_handoff_has_link_nodes(self):
        """/wh:handoff must have link_nodes to connect executions to plans."""
        assert _has_tool("handoff", "mcp__wheeler_mutations__link_nodes")

    def test_handoff_body_creates_execution_nodes(self):
        """handoff.md must instruct creating Execution nodes for handoff waves."""
        body = _body("handoff")
        assert "add_execution" in body
        assert "WAS_INFORMED_BY" in body


class TestGraphFirstReporting:
    """Compile and report use graph queries, not filesystem reads."""

    def test_compile_has_query_plans(self):
        assert _has_tool("compile", "mcp__wheeler_query__query_plans")

    def test_compile_has_query_executions(self):
        assert _has_tool("compile", "mcp__wheeler_query__query_executions")

    def test_compile_body_queries_plans(self):
        """compile.md status mode must call query_plans for plan status."""
        body = _body("compile")
        assert "query_plans" in body

    def test_report_has_query_plans(self):
        assert _has_tool("report", "mcp__wheeler_query__query_plans")

    def test_report_body_queries_plans(self):
        """report.md must use query_plans for investigation state."""
        body = _body("report")
        assert "query_plans" in body

    def test_report_references_change_log(self):
        """report.md must reference change_log for status transition history."""
        body = _body("report")
        assert "change_log" in body, (
            "report.md must use change_log field for plan status transitions"
        )
