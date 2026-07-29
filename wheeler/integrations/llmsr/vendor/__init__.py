"""Search core adapted from LLM-SR (Shojaee et al., ICLR 2025 Oral).

This is a PLUG-IN for LLM-SR, not a Wheeler implementation of it. Upstream:
https://github.com/deep-symbolic-mathematics/LLM-SR (MIT), building on FunSearch
(Apache-2.0), whose headers are retained in the individual files. The method is
theirs; Wheeler contributes the driver and the provenance. See NOTICE.md in this
directory for the full attribution, both license texts, BibTeX for both papers,
and an itemized list of what the adapter changes. Published results should cite
LLM-SR and FunSearch, not Wheeler, and anyone extending the method should work
from upstream.

The adapter carries only the search mechanics (the island-model experience
buffer, the sandbox evaluator, program manipulation, config, and JSON profiling)
so they ship with the package and can be driven from Claude Code. Upstream's LLM
call sites (the OpenAI and local-HF-server samplers) are deliberately absent:
Wheeler generates candidates via a sub-agent (or an external CLI), never an API
key. That substitution is the whole reason this adaptation exists. See ../cli.py
for the driver and ../metrics.py for the scoring registry.
"""
