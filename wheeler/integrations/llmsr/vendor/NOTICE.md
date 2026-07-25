# Third-party notice: this directory is not Wheeler's work

Everything in `wheeler/integrations/llmsr/vendor/` is a **vendored, refactored
subset of other people's research code**. Wheeler did not invent the LLM-SR
method, the evolutionary search, or the island-model buffer. If you use this and
publish, cite the papers below, not Wheeler's copy of them.

**For the full, canonical, actively maintained version, go upstream.** What
lives here is deliberately partial, trimmed to what Wheeler can drive from
Claude Code. Anyone doing serious work with LLM-SR should start at the original
repository, which has the complete pipeline, the samplers, the benchmark
problems, and the authors' own documentation.

## Upstream projects

### LLM-SR (the direct source of this code)

- **Repository:** https://github.com/deep-symbolic-mathematics/LLM-SR
- **License:** MIT, reproduced here as `LICENSE.llm-sr-mit.txt`
- **Paper:** Shojaee, P., Meidani, K., Gupta, S., Barati Farimani, A., and
  Reddy, C. K. "LLM-SR: Scientific Equation Discovery via Programming with Large
  Language Models." ICLR 2025 (Oral). arXiv:2404.18400

```bibtex
@article{shojaee2024llm,
  title={LLM-SR: Scientific Equation Discovery via Programming with Large Language Models},
  author={Shojaee, Parshin and Meidani, Kazem and Gupta, Shashank and Farimani, Amir Barati and Reddy, Chandan K},
  journal={arXiv preprint arXiv:2404.18400},
  year={2024}
}
```

Note: `LICENSE.llm-sr-mit.txt` is reproduced verbatim from upstream, including
their copyright line, which reads `Copyright (c) 2024 [Your Name or
Organization]`. That placeholder is upstream's own and is preserved rather than
filled in, because it is not Wheeler's place to assign authorship of their work.
The credit belongs to the LLM-SR authors named above.

### FunSearch (what LLM-SR itself builds on)

Four files here (`buffer.py`, `code_manipulation.py`, `config.py`,
`evaluator.py`) descend from Google DeepMind's FunSearch and retain their
original Apache-2.0 headers.

- **Repository:** https://github.com/google-deepmind/funsearch
- **License:** Apache License 2.0, included here as
  `LICENSE.funsearch-apache-2.0.txt`
- **Copyright:** 2023 DeepMind Technologies Limited
- **Paper:** Romera-Paredes, B., Barekatain, M., Novikov, A., Balog, M.,
  Kumar, M. P., Dupont, E., Ruiz, F. J. R., Ellenberg, J., Wang, P., Fawzi, O.,
  Kohli, P., and Fawzi, A. "Mathematical discoveries from program search with
  large language models." *Nature* (2023). doi:10.1038/s41586-023-06924-6

```bibtex
@Article{FunSearch2023,
  author  = {Romera-Paredes, Bernardino and Barekatain, Mohammadamin and Novikov, Alexander and Balog, Matej and Kumar, M. Pawan and Dupont, Emilien and Ruiz, Francisco J. R. and Ellenberg, Jordan and Wang, Pengming and Fawzi, Omar and Kohli, Pushmeet and Fawzi, Alhussein},
  journal = {Nature},
  title   = {Mathematical discoveries from program search with large language models},
  year    = {2023},
  doi     = {10.1038/s41586-023-06924-6}
}
```

## What Wheeler changed, and why

Per Apache-2.0 section 4(b), the modified files carry a notice stating they were
changed. The changes are mechanical or environmental, not scientific: the search
algorithm, the island model, the scoring, and the program-manipulation logic are
upstream's.

**Files not vendored at all.** Upstream `llmsr/` has eight modules; this
directory has six. `sampler.py` and `pipeline.py` are deliberately excluded:

- `sampler.py` holds the LLM call sites (an OpenAI client and a local HF
  server). Wheeler never uses an API key, so candidate equations are proposed by
  a Claude Code sub-agent or an external CLI instead. See `../cli.py`.
- `pipeline.py` is upstream's own orchestration loop. Wheeler drives the loop
  from the outside (`wheeler llmsr init / prompt / submit / best`) so Claude Code
  stays the orchestrator.

**Per-file changes:**

| File | Change |
|---|---|
| all | `from llmsr import X` rewritten to package-relative `from . import X`, so the subset imports without upstream's package layout |
| `code_manipulation.py` | `from absl import logging` to stdlib `logging` (drops the absl dependency). `ast.Str` to `ast.Constant`, removed in Python 3.12 |
| `evaluator_accelerate.py` | `ast.NameConstant` to `ast.Constant`, removed in Python 3.12 |
| `config.py` | dropped `ClassConfig`, which typed `llm_class` and `sandbox_class` against the un-vendored `sampler` module |
| `evaluator.py` | sandboxed fits run under an explicit `fork` multiprocessing context. Upstream targeted Linux, where fork is the default; on macOS with Python 3.12+ the default is `spawn`, which re-imports the interpreter per sample (roughly 14x slower) and cannot re-import a `__main__` launched from stdin. Falls back to the platform default where fork is unavailable |
| `profile.py` | dropped the TensorBoard writer (and with it the `torch` dependency), keeping the stdlib JSON sample logging. The public surface (`register_function`) is unchanged so the vendored buffer and evaluator pass a profiler unmodified |
| `buffer.py` | `scipy.special.softmax` replaced with the equivalent numpy expression, verified bit-identical. scipy is an optional Wheeler extra, and a module-top-level import of it made the whole CLI unavailable on installs without it (Wheeler issue #88) |

None of these touch the method. If you want to understand or extend LLM-SR
itself, read upstream's code, not this copy.
