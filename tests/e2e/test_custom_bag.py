"""E2E test for the generic custom-bag core enabler against live Neo4j.

Verifies the flatten-on-write / reassemble-on-read round trip end to end:
  1. create_node with custom={...} stores discrete custom_<key> scalar props
  2. get_node / query_nodes reassemble custom_<key> back into a custom dict
  3. the flattened props are queryable in Cypher
     (WHERE n.custom_relevance_score > 0.8 finds the node)

Run: python -m pytest tests/e2e/test_custom_bag.py -v
Requires: Neo4j running on localhost:7687
"""

from __future__ import annotations

import pytest

from tests.e2e.conftest import E2E_TAG


class TestCustomBagRoundTrip:
    @pytest.mark.asyncio
    async def test_custom_round_trips_and_is_queryable(self, e2e_config):
        from wheeler.graph.backend import get_backend
        from wheeler.graph.driver import get_async_driver

        backend = get_backend(e2e_config)
        await backend.initialize()

        node_id = await backend.create_node("Paper", {
            "id": "P-e2ecustom",
            "title": "Custom bag round trip",
            "tier": "reference",
            "custom": {"relevance_score": 0.87, "venue": "NeurIPS"},
        })
        assert node_id == "P-e2ecustom"

        driver = get_async_driver(e2e_config)
        db = e2e_config.neo4j.database
        async with driver.session(database=db) as session:
            await session.run(
                "MATCH (n {id: $id}) SET n.e2e_tag = $tag",
                id=node_id, tag=E2E_TAG,
            )

        # 1. get_node reassembles the custom bag.
        node = await backend.get_node("Paper", node_id)
        assert node is not None
        assert node["custom"] == {"relevance_score": 0.87, "venue": "NeurIPS"}
        # The flat keys must not leak to the top level.
        assert "custom_relevance_score" not in node
        assert "custom_venue" not in node
        # Round-trips cleanly against the Pydantic model.
        from wheeler.models import PaperModel
        model = PaperModel.model_validate(node)
        assert model.custom["relevance_score"] == 0.87

        # 2. The flattened scalar is queryable in Cypher.
        async with driver.session(database=db) as session:
            result = await session.run(
                "MATCH (n:Paper {id: $id}) "
                "WHERE n.custom_relevance_score > 0.8 RETURN n.id AS id",
                id=node_id,
            )
            rec = await result.single()
        assert rec is not None
        assert rec["id"] == node_id

        # 3. A below-threshold filter does NOT match.
        async with driver.session(database=db) as session:
            result = await session.run(
                "MATCH (n:Paper {id: $id}) "
                "WHERE n.custom_relevance_score > 0.95 RETURN n.id AS id",
                id=node_id,
            )
            rec = await result.single()
        assert rec is None

        # 4. query_nodes (the list read path) also reassembles custom.
        rows = await backend.query_nodes("Paper", filters={"id": node_id}, limit=5)
        assert rows
        assert rows[0]["custom"] == {"relevance_score": 0.87, "venue": "NeurIPS"}
