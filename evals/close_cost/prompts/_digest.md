Your final message must end with exactly ONE line of this form, and nothing
after it:

    DIGEST <json>

where `<json>` is a single-line JSON object with exactly these keys:

```
{"since": "<iso timestamp from step 1>",
 "malformed_closes": <int>,
 "window_ids": ["<id>", ...],
 "orphan_ids": ["<id>", ...],
 "inventory": {"Finding": <int>, "Hypothesis": <int>, "OpenQuestion": <int>, "Plan": <int>, "Execution": <int>, "Document": <int>},
 "stale": ["<script id>", ...],
 "citations": {"total": <int>, "valid": <int>},
 "consistency_ok": true|false}
```

No code fence, no trailing prose, no line breaks inside the JSON.
