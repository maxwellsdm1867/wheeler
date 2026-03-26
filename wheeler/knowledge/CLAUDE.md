# knowledge/ — File-backed knowledge store

The source of truth for all node content. One JSON file per knowledge
node in the project's `knowledge/` directory.

## File Format

```json
{
  "id": "F-3a2b1c4d",
  "type": "Finding",
  "tier": "generated",
  "description": "...",
  "confidence": 0.85,
  "created": "2026-03-26T14:30:00+00:00",
  "updated": "2026-03-26T14:30:00+00:00",
  "tags": []
}
```

The `type` field is a Pydantic discriminator — determines which model
class to use. IDs are `{PREFIX}-{8 hex chars}` (e.g., F-3a2b1c4d).

## Modules

- `store.py` — `write_node`, `read_node`, `list_nodes`, `delete_node`, `node_exists`
  - Atomic writes (tmp + rename)
  - Depends only on `wheeler.models` (no graph imports)
- `render.py` — `render_node` renders any model as markdown for `wh show`
  - Depends only on `wheeler.models`
- `migrate.py` — `migrate()` exports existing graph nodes to JSON files
  - Depends on `wheeler.models` + `wheeler.graph.backend`

## Store API

```python
from pathlib import Path
from wheeler.knowledge.store import write_node, read_node, list_nodes

write_node(Path("knowledge"), model)     # atomic write, returns path
node = read_node(Path("knowledge"), "F-3a2b1c4d")  # returns typed model
nodes = list_nodes(Path("knowledge"), type_filter="Finding")  # filtered list
```
