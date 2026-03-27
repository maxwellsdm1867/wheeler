# knowledge/ — Graph metadata store

JSON files that serve as the graph index. One file per knowledge node.
These are structured metadata — the graph catalog, not the books.

See `node-types.md` for the full schema of each node type.

## Two kinds of content

**Graph nodes** (`knowledge/*.json`) — structured metadata for the system:
- Finding, Hypothesis, Question, Paper, Dataset, Analysis, etc.
- JSON is correct here — it's machine data the graph indexes

**Research artifacts** — the scientist's actual writing:
- Notes → `.notes/*.md` (created by `/wh:note`)
- Drafts → wherever the scientist puts them (e.g., `docs/`)
- Scripts → wherever they live (e.g., `scripts/`)
- Graph nodes *point to* these via `file_path`

The graph node is the index card. The markdown/script file is the real work.

## Modules

- `store.py` — `write_node`, `read_node`, `list_nodes`, `delete_node`, `node_exists`
  - Atomic writes (tmp + rename)
  - Depends only on `wheeler.models` (no graph imports)
- `render.py` — `render_node` renders any model as markdown for `wh show`
- `migrate.py` — `migrate()` exports existing graph nodes to JSON files

## Store API

```python
from pathlib import Path
from wheeler.knowledge.store import write_node, read_node, list_nodes

write_node(Path("knowledge"), model)     # atomic write, returns path
node = read_node(Path("knowledge"), "F-3a2b1c4d")  # returns typed model
nodes = list_nodes(Path("knowledge"), type_filter="Finding")  # filtered list
```
