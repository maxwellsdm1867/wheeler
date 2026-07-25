"""Vendored core of LLM-SR (Shojaee et al., ICLR 2025 Oral).

NOT Wheeler's work. Upstream: https://github.com/deep-symbolic-mathematics/LLM-SR
(MIT). Built on FunSearch (Apache-2.0), whose headers are retained in the
individual files. See NOTICE.md in this directory for the full attribution,
both license texts, BibTeX for both papers, and an itemized list of what
Wheeler changed. Published results should cite LLM-SR and FunSearch, not
Wheeler, and anyone extending the method should work from upstream.

Wheeler vendors only the search mechanics (the island-model experience buffer,
the sandbox evaluator, program manipulation, config, and JSON profiling) so they
ship with the package and can be driven by Claude Code. The upstream LLM call
sites (the OpenAI and local-HF-server samplers) are deliberately NOT vendored:
Wheeler generates candidates via a sub-agent (or an external CLI), never an API
key. See ../cli.py for the driver and ../metrics.py for the scoring registry.
"""
