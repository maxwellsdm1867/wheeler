"""LLM-SR equation-discovery service for Wheeler.

Wraps the vendored LLM-SR search (``vendor/``) as a provenance-tracked Wheeler
service: a model-free mechanics CLI (``cli.py``: init / prompt / submit / best)
that Claude Code drives via a sub-agent, a pluggable metric registry
(``metrics.py``), and a marshal-out ingest (``discover.py``) that lands the full
generated program as a hashed Script plus the fit metric as a Finding.

Imports here stay lazy: the vendored core needs numpy + scipy, so the service is
an optional extra. Callers (the CLI sub-app mount, the ingest) import submodules
locally so a missing dependency degrades to "service unavailable" rather than
breaking package import.
"""
