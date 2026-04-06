# knowledge/ -- Graph metadata store + synthesis

## Three file layers

**Graph nodes** (`knowledge/*.json`): structured metadata for the system.
One file per knowledge node. Machine-readable.

**Synthesis** (`synthesis/*.md`): human-readable Obsidian-compatible
markdown with YAML frontmatter and [[backlinks]]. Auto-generated
alongside JSON by the triple-write system.

**Research artifacts** (`.notes/*.md`, scripts, figures): the scientist's
actual writing and data. Graph nodes point to these via `path` fields.

## Modules

- `store.py`: `write_node`, `read_node`, `list_nodes`, `delete_node`, `node_exists`, `write_synthesis`
  - Atomic writes (tmp + rename)
  - Depends only on `wheeler.models` (no graph imports)
- `render.py`: `render_node` (CLI display), `render_synthesis` (Obsidian markdown with YAML frontmatter)
- `migrate.py`: `migrate()` exports existing graph nodes to JSON files

## Store API

```python
from pathlib import Path
from wheeler.knowledge.store import write_node, read_node, write_synthesis

write_node(Path("knowledge"), model)     # atomic JSON write
node = read_node(Path("knowledge"), "F-3a2b1c4d")  # returns typed model
write_synthesis(Path("synthesis"), "F-3a2b", markdown)  # atomic MD write
```

## Synthesis Render

```python
from wheeler.knowledge.render import render_synthesis

md = render_synthesis(model, relationships=[...])
# Returns markdown with YAML frontmatter, [[backlinks]], artifact embeds
```

The `relationships` parameter adds a Relationships section listing
all connected nodes with their types and directions.
