# docs/ -- Project documentation

## Files

- `GETTING-STARTED.md` -- User-facing setup guide. Covers Neo4j Desktop install, Wheeler install, config, graph schema, Claude Code MCP setup, project install, workflow orientation, graph browsing, and troubleshooting. This is the primary onboarding document for new users.
- `PROJECT-SPEC.md` -- Original project specification and design goals.
- `prov-agent-research.md` -- Research notes from W3C PROV-DM schema design (v0.5.0).
- `asta-integration.md` -- 850-line analysis of AllenAI Asta agent-baselines and integration plan (not yet implemented).
- `field-data-contracts.md` -- Design doc for field-level validation in mutation tools (shipped in v0.6.0).

## Conventions

- Never use em dashes. Use colons, commas, periods, parentheses.
- Docs are standalone markdown. No build step.
- `GETTING-STARTED.md` should be kept in sync with actual defaults in `config.py`, `wheeler.yaml.example`, and `installer.py`. If connection defaults, directory structure, or the install process change, update the guide.
