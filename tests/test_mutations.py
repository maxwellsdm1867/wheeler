"""Unit tests for mutation handlers in wheeler.tools.graph_tools.mutations.

Focused on Wave 1 additions: rel_props pass-through on link_nodes.
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# link_nodes -- rel_props pass-through
# ---------------------------------------------------------------------------


class TestLinkNodesRelProps:
    """Verify that link_nodes passes rel_props to the backend."""

    @pytest.mark.asyncio
    async def test_link_nodes_without_rel_props_succeeds(self) -> None:
        """link_nodes works as before when rel_props is absent."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        calls: list[dict] = []

        class FakeBackend:
            async def create_relationship(
                self,
                src_label: str,
                src_id: str,
                rel_type: str,
                tgt_label: str,
                tgt_id: str,
            ) -> bool:
                calls.append({
                    "src_id": src_id,
                    "rel": rel_type,
                    "tgt_id": tgt_id,
                })
                return True

        result = json.loads(await link_nodes(FakeBackend(), {
            "source_id": "F-aabb1122",
            "target_id": "S-ccdd3344",
            "relationship": "WAS_GENERATED_BY",
        }))
        assert result["status"] == "linked"
        assert "rel_props" not in result
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_link_nodes_passes_rel_props_to_backend(self) -> None:
        """link_nodes forwards rel_props dict to backend.create_relationship."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        received_kwargs: list[dict] = []

        class FakeBackendWithRelProps:
            async def create_relationship(
                self,
                src_label: str,
                src_id: str,
                rel_type: str,
                tgt_label: str,
                tgt_id: str,
                rel_props: dict | None = None,
            ) -> bool:
                received_kwargs.append({"rel_props": rel_props})
                return True

        result = json.loads(await link_nodes(FakeBackendWithRelProps(), {
            "source_id": "X-aabb1122",
            "target_id": "D-ccdd3344",
            "relationship": "USED",
            "rel_props": {"purpose": "training", "weight": 0.8},
        }))
        assert result["status"] == "linked"
        assert result["rel_props"] == {"purpose": "training", "weight": 0.8}
        assert len(received_kwargs) == 1
        assert received_kwargs[0]["rel_props"] == {"purpose": "training", "weight": 0.8}

    @pytest.mark.asyncio
    async def test_link_nodes_ignores_empty_rel_props(self) -> None:
        """An empty rel_props dict is treated as absent (no kwarg passed)."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        calls: list[dict] = []

        class FakeBackend:
            async def create_relationship(
                self,
                src_label: str,
                src_id: str,
                rel_type: str,
                tgt_label: str,
                tgt_id: str,
            ) -> bool:
                calls.append({"rel": rel_type})
                return True

        result = json.loads(await link_nodes(FakeBackend(), {
            "source_id": "H-aabb1122",
            "target_id": "F-ccdd3344",
            "relationship": "SUPPORTS",
            "rel_props": {},
        }))
        assert result["status"] == "linked"
        assert "rel_props" not in result

    @pytest.mark.asyncio
    async def test_link_nodes_ignores_non_dict_rel_props(self) -> None:
        """A non-dict rel_props value is silently ignored."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        calls: list[dict] = []

        class FakeBackend:
            async def create_relationship(
                self,
                src_label: str,
                src_id: str,
                rel_type: str,
                tgt_label: str,
                tgt_id: str,
            ) -> bool:
                calls.append({"rel": rel_type})
                return True

        result = json.loads(await link_nodes(FakeBackend(), {
            "source_id": "H-aabb1122",
            "target_id": "F-ccdd3344",
            "relationship": "SUPPORTS",
            "rel_props": "not-a-dict",
        }))
        assert result["status"] == "linked"
        assert "rel_props" not in result

    @pytest.mark.asyncio
    async def test_link_nodes_invalid_relationship_rejected(self) -> None:
        """Invalid relationship types are still rejected regardless of rel_props."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        class FakeBackend:
            async def create_relationship(self, *a, **kw) -> bool:
                return True

        result = json.loads(await link_nodes(FakeBackend(), {
            "source_id": "F-aabb1122",
            "target_id": "D-ccdd3344",
            "relationship": "INVALID_TYPE",
            "rel_props": {"key": "value"},
        }))
        assert "error" in result

    @pytest.mark.asyncio
    async def test_link_nodes_node_not_found(self) -> None:
        """Backend returning False maps to an error result (unchanged behaviour)."""
        from wheeler.tools.graph_tools.mutations import link_nodes

        class FakeBackend:
            async def create_relationship(self, *a, **kw) -> bool:
                return False

        result = json.loads(await link_nodes(FakeBackend(), {
            "source_id": "F-aabb1122",
            "target_id": "S-ccdd3344",
            "relationship": "WAS_GENERATED_BY",
            "rel_props": {"note": "test"},
        }))
        assert "error" in result
