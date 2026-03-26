# Knowledge Node Types

All nodes share base fields: `id`, `type`, `tier`, `created`, `updated`, `tags`.
Files are `{id}.json` in the project's `knowledge/` directory.

---

## Finding (F-)

A result from an analysis worth recording.

```json
{"id": "F-3a2b1c4d", "type": "Finding", "tier": "generated",
 "description": "Calcium oscillation frequency scales with cell density...",
 "confidence": 0.85}
```

| Field | Type | Notes |
|-------|------|-------|
| description | str | What was found |
| confidence | float | 0.0–1.0 |

Common relationships: `Analysis -GENERATED-> Finding`, `Finding -SUPPORTS-> Hypothesis`, `Finding -BASED_ON-> Paper`

---

## Hypothesis (H-)

A testable explanation that needs evidence.

```json
{"id": "H-7c1d2e3f", "type": "Hypothesis", "tier": "generated",
 "statement": "ON-pathway bipolar cells use nonlinear spatial summation...",
 "status": "open"}
```

| Field | Type | Notes |
|-------|------|-------|
| statement | str | The hypothesis |
| status | str | open, supported, or rejected |

Common relationships: `Finding -SUPPORTS/CONTRADICTS-> Hypothesis`, `Paper -RELEVANT_TO-> Hypothesis`

---

## OpenQuestion (Q-)

A gap in knowledge that needs investigation.

```json
{"id": "Q-1b8f4a2c", "type": "OpenQuestion", "tier": "generated",
 "question": "What drives the transition from linear to nonlinear summation?",
 "priority": 8}
```

| Field | Type | Notes |
|-------|------|-------|
| question | str | The open question |
| priority | int | 1–10 (10 = highest) |

Common relationships: `OpenQuestion -AROSE_FROM-> Finding`

---

## Paper (P-)

A literature reference. Always `tier: "reference"`.

```json
{"id": "P-a4f20e91", "type": "Paper", "tier": "reference",
 "title": "Nonlinear spatial integration in retinal ganglion cells",
 "authors": "Smith, Johnson", "doi": "10.1234/example", "year": 2023}
```

| Field | Type | Notes |
|-------|------|-------|
| title | str | Paper title |
| authors | str | Comma-separated |
| doi | str | DOI if available |
| year | int | Publication year (0 = unknown) |

Common relationships: `Paper -INFORMED-> Analysis`, `Finding -BASED_ON-> Paper`, `Paper -CITES-> Paper`

---

## Dataset (D-)

A registered data file for provenance tracking.

```json
{"id": "D-9e3b4c5d", "type": "Dataset", "tier": "generated",
 "path": "data/recordings/cell_042.h5", "data_type": "h5",
 "description": "Whole-cell patch recordings from ON bipolar cells"}
```

| Field | Type | Notes |
|-------|------|-------|
| path | str | File path |
| data_type | str | File type (h5, mat, csv, etc.) |
| description | str | What the dataset contains |

Common relationships: `Analysis -USED_DATA-> Dataset`

---

## Document (W-)

A written output (draft, report, section).

```json
{"id": "W-5d2a1b3c", "type": "Document", "tier": "generated",
 "title": "Results: Spike Generation", "path": "results/spike-gen.md",
 "section": "results", "status": "draft"}
```

| Field | Type | Notes |
|-------|------|-------|
| title | str | Document title |
| path | str | File path |
| section | str | results, methods, discussion, abstract, full |
| status | str | draft, revision, final |

Common relationships: `Finding/Paper/Analysis -APPEARS_IN-> Document`

---

## Analysis (A-)

Provenance record for an executed script. The cryptographic receipt.

```json
{"id": "A-2f4a7b8c", "type": "Analysis", "tier": "generated",
 "script_path": "scripts/spatial_summation.py",
 "script_hash": "a1b2c3d4...", "language": "python",
 "language_version": "3.11", "parameters": "threshold=0.8",
 "output_path": "results/summation.csv", "output_hash": "e5f6...",
 "executed_at": "2026-03-26T14:30:00+00:00"}
```

| Field | Type | Notes |
|-------|------|-------|
| script_path | str | Path to the script |
| script_hash | str | SHA-256 at execution time |
| language | str | python, matlab |
| language_version | str | e.g., "3.11", "R2024a" |
| parameters | str | JSON or key=value |
| output_path | str | Path to output |
| output_hash | str | SHA-256 of output |
| executed_at | str | ISO timestamp |

Common relationships: `Analysis -USED_DATA-> Dataset`, `Analysis -GENERATED-> Finding`, `Paper -INFORMED-> Analysis`

---

## ResearchNote (N-)

A scientist's raw thinking — observations, insights, ideas. Like a lab notebook entry.
Created via `/wh:note`.

```json
{"id": "N-4e5f6a7b", "type": "ResearchNote", "tier": "generated",
 "title": "Temperature dependence of calcium oscillations",
 "content": "The oscillation frequency seems to drop when we cool the bath below 30C. Could this be a channel gating effect?",
 "context": "Noticed while reviewing cell_042 recordings"}
```

| Field | Type | Notes |
|-------|------|-------|
| title | str | Short label (~10 words) |
| content | str | The note itself (freeform) |
| context | str | What prompted this (optional) |

Common relationships: `ResearchNote -RELEVANT_TO-> Finding`, `ResearchNote -AROSE_FROM-> Dataset`

---

## Experiment (E-), Plan (PL-), CellType (C-), Task (T-)

Lightweight structural nodes with no content fields beyond base.
Plan has `status`. CellType and Task have only `id` and `tier`.
