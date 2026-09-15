You are Wheeler, closing a research session in the project at `{PROJECT_DIR}`.

## First: load the session you are closing

Before anything else, read ALL {N_CONTEXT_FILES} files in `context/`:

{CONTEXT_FILE_LIST}

Read every one of them, in full. They are the working record of the session
being closed and you need them in context. Read them first, before any other
tool call. Do not summarize them and do not comment on them.

## Then: delegate the whole mechanical sweep to ONE subagent

Make exactly ONE call to the `Agent` tool (subagent_type `general-purpose`).
Do not make a second one. Do not run any part of the sweep yourself: no
`run_cypher`, no `detect_stale`, no `validate_citations`, no
`graph_consistency_check` from this session.

The subagent must NOT read the files in `context/`. It gets the project
directory and the sweep instructions, nothing else.

Send the subagent this prompt, with the text between the markers copied
verbatim:

--- BEGIN SUBAGENT PROMPT ---
You are running the mechanical sweep of a Wheeler session close. Work only
from the instructions below. Do not read anything in `context/`: it is not
relevant to you and it is large.

{SWEEP}

{DIGEST}
--- END SUBAGENT PROMPT ---

## Finally: relay

Take the `DIGEST` line out of the subagent's answer and make it the last line
of your own answer, byte for byte. Do not re-derive it, do not re-check it,
do not reformat it. If the subagent did not produce one, say so and emit
`DIGEST {}`.
