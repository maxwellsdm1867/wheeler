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


# ---------------------------------------------------------------------------
# add_finding -- title field round-trip (figure triple-lock)
# ---------------------------------------------------------------------------


class TestAddFindingTitleField:
    """Verify the new title field on Finding propagates through add_finding."""

    @pytest.mark.asyncio
    async def test_add_finding_persists_title_on_graph_node(self) -> None:
        """add_finding writes the title onto the backend node props."""
        from wheeler.tools.graph_tools.mutations import add_finding

        captured: dict = {}

        class FakeBackend:
            async def create_node(self, label: str, props: dict) -> bool:
                captured["label"] = label
                captured["props"] = props
                return True

        await add_finding(FakeBackend(), {
            "description": "F theta0 vs delta scatter",
            "confidence": 0.8,
            "title": "fig_F_theta0_vs_delta",
            "artifact_type": "figure",
            "path": "/tmp/fig_F_theta0_vs_delta.png",
        })

        assert captured["label"] == "Finding"
        assert captured["props"]["title"] == "fig_F_theta0_vs_delta"
        # display_name should prefer title when present (matches filename slug)
        assert captured["props"]["display_name"] == "fig_F_theta0_vs_delta"

    @pytest.mark.asyncio
    async def test_add_finding_without_title_defaults_to_empty(self) -> None:
        """Existing callers that omit title still work; field defaults to empty."""
        from wheeler.tools.graph_tools.mutations import add_finding

        captured: dict = {}

        class FakeBackend:
            async def create_node(self, label: str, props: dict) -> bool:
                captured["props"] = props
                return True

        await add_finding(FakeBackend(), {
            "description": "Backward-compat finding without title",
            "confidence": 0.5,
        })

        assert captured["props"]["title"] == ""
        # display_name falls back to description prefix when title is absent
        assert captured["props"]["display_name"] == "Backward-compat finding without title"

    def test_finding_model_round_trips_title(self) -> None:
        """FindingModel accepts title and survives a JSON round trip."""
        from wheeler.models import FindingModel, KNOWLEDGE_NODE_ADAPTER

        m = FindingModel(
            id="F-deadbeef",
            description="F vs delta scatter",
            confidence=0.9,
            title="fig_F_vs_delta",
            path="/tmp/fig_F_vs_delta.png",
            artifact_type="figure",
        )
        assert m.title == "fig_F_vs_delta"

        # Round-trip through the discriminated-union adapter (used by store.py)
        payload = m.model_dump()
        restored = KNOWLEDGE_NODE_ADAPTER.validate_python(payload)
        assert isinstance(restored, FindingModel)
        assert restored.title == "fig_F_vs_delta"

    def test_finding_model_legacy_json_without_title_loads(self) -> None:
        """Existing knowledge/F-*.json files predating the title field still load."""
        from wheeler.models import FindingModel

        # Legacy payload: no title key at all.
        legacy = {
            "id": "F-cafebabe",
            "type": "Finding",
            "description": "Legacy finding",
            "confidence": 0.6,
        }
        m = FindingModel.model_validate(legacy)
        assert m.title == ""
        assert m.description == "Legacy finding"
