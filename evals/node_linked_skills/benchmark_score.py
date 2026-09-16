"""Evidence-based scoring for isolated node-linked-skill native-host trials.

The scorer is evaluator-only. Agent declarations never establish application.
Wilson intervals describe trial counts; case-cluster means are also reported
because repeated cases are not independent scientific samples.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shlex


FAMILIES = {"join", "aggregate", "fit", "plot", "export"}


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def jsonlines(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rate(numerator: int, denominator: int) -> dict:
    if not denominator:
        return {"numerator": numerator, "denominator": 0, "rate": None, "wilson_95": None}
    p, z = numerator / denominator, 1.959963984540054
    center = (p + z*z / (2*denominator)) / (1 + z*z/denominator)
    radius = z * math.sqrt(p*(1-p)/denominator + z*z/(4*denominator**2)) / (1+z*z/denominator)
    return {"numerator": numerator, "denominator": denominator, "rate": p,
            "wilson_95": [max(0.0, center-radius), min(1.0, center+radius)]}


def close(actual, expected) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and close(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(close(a, e) for a, e in zip(actual, expected))
    return actual == expected


def request(event: dict) -> dict:
    raw = event.get("argument", event.get("request", ""))
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {"query": raw} if event.get("action") == "sql" else {}


def response(event: dict) -> dict:
    return event.get("result", event.get("response", {}))


def leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from leaves(child)
    else:
        yield value


def numbers(value) -> list[float]:
    values = []
    for leaf in leaves(value):
        if isinstance(leaf, (int, float)) and not isinstance(leaf, bool):
            values.append(float(leaf))
        elif isinstance(leaf, str):
            leaf = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", leaf)
            values.extend(float(v) for v in re.findall(r"(?<![\w])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", leaf))
    return values


def contains_number(value, expected):
    return any(close(number, expected) for number in numbers(value))


def reported_mean(answer, expected):
    if isinstance(answer, dict):
        values = [v for k,v in answer.items() if isinstance(v,(int,float)) and
                  re.search(r"mean|average|response", k) and not re.search(r"reference|within|count|rows|recordings", k)]
        if values:
            return any(close(v,expected) for v in values)
    # A numeric or concise prose answer can be adjudicated directly. Complex
    # free text remains an extraction limitation, surfaced in method notes.
    return contains_number(answer,expected)


def audited_compound(invocation, allowed_command):
    command = invocation.get("command") or invocation.get("input",{}).get("command", "")
    try:
        outer = shlex.split(command)
        if len(outer)==3 and outer[1] in {"-c", "-lc"}:
            command = outer[2]
        lex=shlex.shlex(command,posix=True,punctuation_chars=True)
        lex.whitespace_split=True
        chunks=[[]]
        for token in lex:
            if token in {";", "&&"}:
                chunks.append([])
            else:
                chunks[-1].append(token)
        prefix=shlex.split(allowed_command)
        return all(c[:len(prefix)]==prefix and len(c) in {len(prefix)+1,len(prefix)+2}
                   and not any(t in {"|", "||", ">", ">>", "<", "&", "(", ")"} for t in c) for c in chunks)
    except ValueError:
        return False


def procedure_evidence(events: list[dict]) -> dict:
    """Infer procedure behavior from successful actions, not applied_skill_ids."""
    applied, compliant = set(), set()
    evidence = defaultdict(list)
    for index, event in enumerate(events):
        if event.get("error"):
            continue
        action, req = event.get("action"), request(event)
        if action == "sql":
            query = re.sub(r"\s+", " ", req.get("query", "")).lower()
            if "measurements" in query and "recordings" in query:
                id_join = bool(re.search(r"(?:on|where|and)\s+\w*\.?recording_id\s*=\s*\w*\.?recording_id", query))
                id_join |= bool(re.search(r"using\s*\(\s*recording_id\s*\)", query))
                id_join |= bool(re.search(r"recording_id\s+in\s*\(\s*select\s+(?:\w+\.)?recording_id", query))
                # Two unrelated scalar subqueries are not a table join.
                if id_join or re.search(r"\bjoin\b", query):
                    applied.add("join")
                    evidence["join"].append(index)
                    if id_join:
                        compliant.add("join")
            if re.search(r"group\s+by\s+(?:\w+\.)?recording_id", query) and re.search(r"avg\s*\(", query):
                applied.add("aggregate")
                evidence["aggregate"].append(index)
                # Grouped output may be averaged by the agent; outcome oracle
                # independently checks the final population value.
                compliant.add("aggregate")
        elif action in {"fit", "plot", "export"}:
            applied.add(action)
            evidence[action].append(index)
            if action == "fit" and req.get("group_by") == "cell" and req.get("intercept", True) is True:
                compliant.add(action)
            elif action == "plot" and req.get("group_by") == "cell":
                compliant.add(action)
            elif action == "export" and response(event).get("filename"):
                compliant.add(action)
    return {"applied": sorted(applied), "compliant": sorted(compliant), "event_indices": dict(evidence)}


def transformed(outcome: dict, repetition: int) -> dict:
    out = json.loads(json.dumps(outcome))
    scale, shift = 1 + .07*repetition, 2*repetition
    def walk(value, key=""):
        if isinstance(value, dict):
            return {k: walk(v, k) for k, v in value.items()}
        if key == "means":
            return value
        if key in {"mean", "intercept"} and isinstance(value, (int, float)):
            return value*scale+shift
        if key == "slope":
            return value*scale
        if key == "y":
            return [v*scale+shift for v in value]
        return value
    out = walk(out)
    if "means" in out:
        out["means"] = {key: value*scale+shift for key, value in outcome["means"].items()}
    if "rows" in out and any(str(row[0]) in {"p7", "p9", "m4"} for row in out["rows"]):
        out["rows"] = [[row[0], row[1]*scale+shift] for row in out["rows"]]
    return out


def outcome_checks(directory: Path, public: dict, expected: dict, events: list[dict], answer: dict,
                   case: dict, mapping: dict, phase_number=None) -> list[dict]:
    checks = []
    successful = [e for e in events if not e.get("error")]
    def check(name, passed, evidence=None):
        checks.append({"name": name, "passed": passed, "evidence": evidence})
    def action(name):
        return [e for e in successful if e.get("action") == name]
    sql = action("sql")
    sql_results = [response(e) for e in sql]
    observed_values = defaultdict(list)
    for result in sql_results:
        columns = [c.lower() for c in result.get("columns", [])]
        if "recording_id" in columns and "value" in columns:
            for row in result.get("rows", []):
                observed_values[row[columns.index("recording_id")]].append(row[columns.index("value")])
    derived_means = {key:sum(values)/len(values) for key,values in observed_values.items() if values}
    inspections = action("inspect")
    answer_content = answer.get("answer", answer)
    all_text = json.dumps(answer, sort_keys=True).lower()
    default_path = Path(public["resources"][public["default_resource"]])
    check("finish_recorded", bool(answer))
    if "rows" in expected:
        wanted = expected["rows"]
        matches = []
        for result in sql_results:
            rows = result.get("rows", [])
            if len(rows) != len(wanted):
                continue
            # Project the exact oracle pair from rows with optional extra columns.
            matched = all(any(any(close(x, target[0]) for x in row) and
                              any(close(x, target[1]) for x in row) for row in rows) for target in wanted)
            matches.append(matched)
        check("query_rows", any(matches), wanted)
    if "mean" in expected:
        value = expected["mean"]
        # A final average may be computed from the verified group means.
        computed = any(contains_number(r.get("rows", []), value) for r in sql_results)
        groups = {"p7": 18, "p9": 45, "m4": 90}
        if "means" in expected:
            groups = expected["means"]
        grouped_values = all(any(any(str(k) in row and any(close(v, x) for x in row) for row in r.get("rows", [])) for r in sql_results) for k, v in groups.items())
        check("population_or_row_mean", reported_mean(answer_content, value) and (computed or grouped_values), value)
    if "means" in expected:
        for ident, value in expected["means"].items():
            observed = any(any(ident in row and any(close(value, x) for x in row) for row in r.get("rows", [])) for r in sql_results)
            check("within_recording_mean:" + ident, (observed or close(derived_means.get(ident), value)) and contains_number(answer_content, value), value)
    if "recording_count" in expected:
        check("recording_count_reported", contains_number(answer_content, expected["recording_count"]), expected["recording_count"])
    fits = expected.get("fits") or ({k: expected[k] for k in ("a", "b")} if "a" in expected and "b" in expected else None)
    if fits:
        check("fit_coefficients", any(close(response(e).get("fits"), fits) for e in action("fit")), fits)
    plot = expected.get("plot") or (expected if "xscale" in expected else None)
    if plot:
        keys = ("x", "y", "xscale", "yscale", "xlabel", "ylabel")
        want = {k: plot[k] for k in keys if k in plot}
        check("plot_values_and_axes", any(close(response(e), want) for e in action("plot")), want)
        stored = load(directory / "plot.json", {})
        check("plot_files", close(stored, want) and (directory / "plot.svg").exists())
    if "tables" in expected:
        tables = expected["tables"]
        observed = any(sorted(response(e).get("tables", [])) == sorted(tables) for e in inspections)
        observed |= any(sorted(str(row[0]) for row in r.get("rows", []) if len(row) == 1) == sorted(tables) for r in sql_results)
        check("table_names", observed and all(t in all_text for t in tables))
    if any(k in expected for k in ("stat_equals_actual_bytes", "metadata_equals_stat")):
        current = default_path.stat()
        matches = [response(e) for e in inspections if request(e).get("kind", "stat") == "stat"]
        good = any(r.get("size_bytes") == current.st_size and r.get("mtime_ns") == current.st_mtime_ns and r.get("filename") == default_path.name for r in matches)
        check("filesystem_metadata", good)
        if "stat_equals_actual_bytes" in expected:
            check("byte_count_reported", contains_number(answer_content, current.st_size))
        if "metadata_equals_stat" in expected:
            check("filename_reported", default_path.name in all_text)
    if "imports_equal_ast" in expected:
        parsed = ast.parse(default_path.read_text())
        imports = set()
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add("."*node.level+(node.module or ""))
        check("imports_match_ast", any(set(response(e).get("imports", [])) == imports for e in inspections) and all(i in all_text for i in imports), sorted(imports))
    if "copied_hash_matches" in expected:
        target = directory / "archive" / default_path.name
        check("archive_copy_bytes", target.exists() and target.read_bytes() == default_path.read_bytes())
    if "listing_equals_filesystem" in expected:
        names = sorted(p.name for p in default_path.iterdir())
        check("directory_listing", any(response(e).get("filenames") == names for e in inspections) and all(n in all_text for n in names), names)
    if "created_filename" in expected:
        filename = expected["created_filename"]
        target = default_path / filename
        exports = action("export")
        check("export_filename", any(response(e).get("filename") == filename for e in exports) and target.exists(), filename)
        check("export_contents", target.exists() and load(target, None) == public.get("export_parameters", {}).get("content"))
    if expected.get("old_bytes_unchanged"):
        old = default_path / "D-eval-4c9__population-mean.json"
        check("preexisting_bytes_preserved", old.exists() and old.read_text() == "sentinel-old-output")
    if expected.get("no_overwrite"):
        check("previous_bytes_preserved", (default_path / "previous.json").read_text() == '{"status":"previous"}\n')
    if "per_cell_repeat_counts" in expected:
        with default_path.open() as handle:
            actual = dict(Counter(row["cell"] for row in csv.DictReader(handle)))
        check("fixture_repeat_counts", actual == expected["per_cell_repeat_counts"])
        # Accept a nested mapping, or clearly labeled prose; do not infer counts
        # merely because unrelated numeric values occur in the answer.
        def mapping_found(value):
            if isinstance(value, dict):
                return close(value, actual) or any(mapping_found(v) for v in value.values())
            if isinstance(value, list):
                return any(mapping_found(v) for v in value)
            return False
        text_counts = all(re.search(rf'\b{re.escape(k)}\b[^\d]{{0,30}}{v}\b', all_text) for k,v in actual.items())
        check("repeat_counts_reported", mapping_found(answer_content) or bool(text_counts))
    for key in ("body_reads", "new_body_reads", "old_version_read_count", "old_version_reads"):
        if key in expected:
            reads = action("read")
            if key.startswith("old_version"):
                reads = [e for e in reads if mapping.get(e.get("argument"), {}).get("family") == "aggregate" and mapping.get(e.get("argument"), {}).get("version") == 1]
            check(key, len(reads) == expected[key], len(reads))
    for key in ("sql_calls", "data_reads", "writes", "script_execution_count"):
        if key in expected:
            count = {"sql_calls": len([e for e in events if e.get("action")=="sql"]),
                     "data_reads": len([e for e in events if e.get("action")=="sql" or
                                        (e.get("action")=="inspect" and request(e).get("kind") in {"data","schema"})]),
                     "writes": len(action("plot"))+len(action("export")), "script_execution_count": len([e for e in events if e.get("action")=="fit"])}[key]
            check(key, count == expected[key], count)
    if expected.get("no_artifact_access"):
        check("no_artifact_access", not any(e.get("action") in {"inspect","sql","fit","plot","export"} for e in events))
    if expected.get("no_database_query"):
        check("no_database_query", not any(e.get("action")=="sql" for e in events))
    if expected.get("plot_created") is False:
        check("no_plot_created", not action("plot") and not (directory / "plot.svg").exists())
    if expected.get("label_mentions_row_weighting"):
        check("row_weighting_label", bool(re.search(r"row|measurement", all_text)))
    if expected.get("version") == "v2":
        ids = [e.get("argument") for e in action("read")]
        check("current_revision_read", any(mapping.get(i, {}).get("family") == "aggregate" and mapping.get(i, {}).get("version") == 2 for i in ids))
    if expected.get("acknowledges_unavailable") or expected.get("reports_current_guidance_unavailable"):
        check("unavailable_acknowledged", answer.get("coverage") == "unavailable" or bool(re.search(r"unavailable|cannot.{0,15}load|can.t.{0,15}load", all_text)))
    if expected.get("reports_partial_coverage"):
        check("partial_coverage_acknowledged", answer.get("coverage") == "partial" or bool(re.search(r"truncated|partial|not all|incomplete", all_text)))
    if expected.get("does_not_claim_no_other_skills"):
        check("no_false_exhaustiveness_claim", not bool(re.search(r"no (?:other|additional|more) (?:linked )?skills", all_text)))
    if case["id"] in {"N10", "N11"}:
        check("finding_summary_semantics", None, "Requires human semantic adjudication; nonempty text alone is not a correct-summary oracle.")
    return checks


def discovery_score(case: dict, prepared: dict, context: dict, no_guidance=False) -> dict:
    mapping = prepared["skills"]
    actual = {s["id"] for s in context.get("linked_skills", [])}
    labels = set(case["oracle"]["discovered_skills"])
    if "first_k_accepted" in labels:
        expected = {i for i,m in mapping.items() if m["family"] == "decoy"}
    else:
        expected = set()
        for ident, metadata in mapping.items():
            family = metadata["family"]
            if family in labels or (family + "_v" + str(metadata.get("version"))) in labels:
                expected.add(ident)
    status = context.get("linked_skills_status", "missing")
    excluded = no_guidance or status != "complete"
    return {"status": status, "expected_status": case["oracle"]["discovery_status"],
            "status_correct": None if no_guidance else status == case["oracle"]["discovery_status"],
            "no_guidance_control": no_guidance, "actual_ids": sorted(actual), "expected_ids": sorted(expected),
            "false_positive_ids": [] if no_guidance else sorted(actual-expected),
            "false_negative_ids": [] if excluded else sorted(expected-actual),
            "false_negative_eligible": not excluded,
            "unavailable_or_unchecked_expected_count": len(expected-actual) if excluded and not no_guidance else 0,
            "negative_opportunities": len(set(mapping)-expected), "positive_opportunities": len(expected),
            "truncation_count_correct": (len(actual) == case.get("setup", {}).get("discovery_limit")) if status == "truncated" else None}


def score_trial(directory: Path, spec: dict, prepared_all: dict) -> dict:
    trial = load(directory / "trial.json", {})
    case_id = trial.get("case_id", directory.name.rsplit("-r", 1)[0])
    case = next(c for c in spec["cases"] if c["id"] == case_id)
    prepared = prepared_all["cases"][case_id]
    public = load(directory / "public.json", {})
    host_result = load(directory / "logs/result.json", {})
    events = jsonlines(directory / "events.jsonl")
    mapping = prepared["skills"]
    offered_ids = {s["id"] for s in public.get("context", {}).get("linked_skills", [])}
    # An offered summary is only model-visible after a successful context call.
    encountered = any(e.get("action") == "context" and not e.get("error") for e in events)
    encountered_ids = offered_ids if encountered else set()
    read_ids = {e.get("argument") for e in events if e.get("action") == "read" and not e.get("error")}
    read_families = {mapping.get(i, {}).get("family", "unknown") for i in read_ids}
    offered_families = {mapping.get(i, {}).get("family", "unknown") for i in encountered_ids}
    required = set(case["oracle"]["must_read"])
    negative_ids = {i for i in encountered_ids if mapping.get(i, {}).get("family") in case["oracle"]["must_not_read"]}
    if case_id == "B32":
        negative_ids |= encountered_ids  # Every offered archive decoy is irrelevant.
    procedures = procedure_evidence(events)
    negative_app = set(case["oracle"]["must_not_apply"]) & offered_families
    required_app = set(case["oracle"]["must_apply"])
    eligible_read = required & offered_families
    eligible_app = required_app & offered_families
    denied_ids = {d.get("tool_use_id") for d in host_result.get("permission_denials", [])}
    outside = host_result.get("out_of_contract_tool_invocations", [])
    compound_audited = [item for item in outside if audited_compound(item, host_result.get("allowed_command", ""))]
    executed_outside = [item for item in outside if item.get("id") not in denied_ids and item not in compound_audited]
    valid = (host_result.get("native_completion_event", False)
             and host_result.get("status") in {"completed", "permission_denied"}
             and not executed_outside)
    repetition = trial.get("repetition", int(directory.name.rsplit("-r", 1)[1]))
    expected = transformed(case["oracle"]["outcome"], repetition)
    checks = []
    phase_audit = []
    if "phase1" in expected:
        for phase_number in (1,2):
            phase_events = [e for e in events if e.get("phase",1) == phase_number]
            phase_answer = load(directory / f"answer-phase{phase_number}.json", {})
            pc = outcome_checks(directory, public, expected[f"phase{phase_number}"], phase_events, phase_answer, case, mapping, phase_number)
            for check in pc:
                check["name"] = f"phase{phase_number}:" + check["name"]
            checks.extend(pc)
            phase_audit.append({"phase": phase_number, "read_ids": [e.get("argument") for e in phase_events if e.get("action") == "read"], "procedure_evidence": procedure_evidence(phase_events)})
    else:
        checks = outcome_checks(directory, public, expected, events, load(directory / "answer.json", {}), case, mapping)
    task_pass = all(c["passed"] is True for c in checks)
    unscored = any(c["passed"] is None for c in checks) and not any(c["passed"] is False for c in checks)
    final_answer = load(directory / "answer.json", {})
    discovery = discovery_score(case, prepared, public.get("context", {}), trial.get("no_guidance", False))
    strict_extra = set(procedures["applied"]) & negative_app
    harmless_extra = set()
    # A valid optional join is not an incorrect SQL application. Preserve the
    # pre-registered task-minimal read metric and an extra-procedure metric.
    if case_id == "A06" and task_pass and "join" in procedures["compliant"]:
        harmless_extra.add("join")
    # Computing a labeled reference is different from overriding the requested
    # row estimand. This adjudication depends on independent answer validation.
    if case_id == "A07" and task_pass and "aggregate" in strict_extra:
        harmless_extra.add("aggregate")
    metrics = {
        "strict_extra_procedure_execution_rate": [len(strict_extra), len(negative_app)],
        "unnecessary_read_rate": [len(read_ids & negative_ids), len(negative_ids)],
        "required_read_false_negative_rate": [len(eligible_read-read_families), len(eligible_read)],
        "application_false_positive_rate": [len(strict_extra-harmless_extra), len(negative_app)],
        "application_false_negative_rate": [len(eligible_app-set(procedures["compliant"])), len(eligible_app)],
        "end_to_end_required_read_miss_rate": [len(required-read_families), len(required)],
        "end_to_end_application_miss_rate": [len(required_app-set(procedures["compliant"])), len(required_app)],
    }
    return {"case_id": case_id, "split": case["split"], "category": case["category"],
            "phase": trial.get("phase", directory.parent.parent.name), "host": trial.get("host", directory.parent.name),
            "repetition": repetition, "directory": str(directory), "session_status": host_result.get("status", "missing"),
            "valid_session": valid, "strict_contract_valid": host_result.get("tool_contract_valid",False),
            "native_completion_event": host_result.get("native_completion_event",False),
            "out_of_contract_tool_invocations": outside,
            "executed_out_of_contract_invocations": executed_outside,
            "denied_out_of_contract_attempts": [item for item in outside if item.get("id") in denied_ids],
            "audited_compound_invocations": compound_audited,
            "harmless_extra_procedures": sorted(harmless_extra),
            "no_guidance": trial.get("no_guidance", False), "context_encountered": encountered,
            "offered_ids": sorted(offered_ids), "encountered_ids": sorted(encountered_ids), "read_ids": sorted(read_ids),
            "read_families": sorted(read_families), "skill_revision_mapping": mapping,
            "unauthorized_read_ids": sorted(read_ids-offered_ids), "procedures": procedures,
            "claimed_applied_skill_ids": final_answer.get("applied_skill_ids", []),
            "task_checks": checks, "task_success": task_pass and bool(host_result.get("native_completion_event")),
            "controlled_task_success": task_pass and valid,
            "outcome_status": "unscored" if unscored else ("passed" if task_pass else "failed"),
            "phase_audit": phase_audit, "staged_followup_delivery": "finish tool result, same conversation; not a new user turn" if phase_audit else None,
            "metrics": metrics, "discovery": discovery,
            "model_provenance": {key: host_result.get(key) for key in ("actual_model", "actual_models", "model_evidence", "model_selection", "host_version", "session_id", "stdout_path", "stderr_path", "command_path")},
            "source_trial": trial, "elapsed_seconds": host_result.get("elapsed_seconds")}


def aggregate(trials: list[dict]) -> dict:
    valid = [t for t in trials if t["valid_session"]]
    result = {"attempts": len(trials), "valid_sessions": len(valid),
              "strict_contract_valid_sessions": sum(bool(t["strict_contract_valid"]) for t in trials),
              "native_completed_sessions": sum(bool(t["native_completion_event"]) for t in trials),
              "infrastructure_status_counts": dict(Counter(t["session_status"] for t in trials)),
              "out_of_contract_sessions": sum(bool(t["out_of_contract_tool_invocations"]) for t in trials),
              "unscored_outcomes": sum(t["outcome_status"] == "unscored" for t in trials),
              "task_success_all_attempts": rate(sum(t["task_success"] for t in trials),len(trials)),
              "task_success_valid_sessions": rate(sum(t["task_success"] for t in valid),len(valid)),
              "controlled_task_success_all_attempts": rate(sum(t["controlled_task_success"] for t in trials),len(trials)),
              "executed_out_of_contract_sessions": sum(bool(t["executed_out_of_contract_invocations"]) for t in trials),
              "models": dict(Counter(t["model_provenance"].get("actual_model", "unknown") for t in trials)),
              "coverage_statuses": dict(Counter(t["discovery"]["status"] for t in trials))}
    for name in (trials[0]["metrics"] if trials else {}):
        eligible = trials if name.startswith("end_to_end") else valid
        n = sum(t["metrics"][name][0] for t in eligible)
        d = sum(t["metrics"][name][1] for t in eligible)
        result[name] = rate(n,d)
        clusters = defaultdict(lambda:[0,0])
        for trial in eligible:
            n,d = trial["metrics"][name]
            clusters[trial["case_id"]][0] += n
            clusters[trial["case_id"]][1] += d
        rates = {k:v[0]/v[1] for k,v in clusters.items() if v[1]}
        result[name]["case_cluster_rates"] = rates
        result[name]["case_cluster_mean"] = sum(rates.values())/len(rates) if rates else None
    clusters = defaultdict(list)
    for trial in trials:
        clusters[trial["case_id"]].append(int(trial["task_success"]))
    result["task_success_case_cluster_mean"] = sum(sum(v)/len(v) for v in clusters.values())/len(clusters) if clusters else None
    discovery = [t["discovery"] for t in trials if not t["no_guidance"]]
    result["discovery_false_positive_rate"] = rate(sum(len(d["false_positive_ids"]) for d in discovery),sum(d["negative_opportunities"] for d in discovery))
    result["discovery_false_discovery_fraction"] = rate(sum(len(d["false_positive_ids"]) for d in discovery),sum(len(d["actual_ids"]) for d in discovery))
    complete = [d for d in discovery if d["false_negative_eligible"]]
    result["discovery_false_negative_rate_complete_only"] = rate(sum(len(d["false_negative_ids"]) for d in complete),sum(d["positive_opportunities"] for d in complete))
    result["discovery_status_accuracy"] = rate(sum(bool(d["status_correct"]) for d in discovery),len(discovery))
    # Include the ungated behavior counts so exclusions remain inspectable.
    result["all_completed_read_metrics"] = {}
    completed = [t for t in trials if t["native_completion_event"]]
    for name in ("unnecessary_read_rate", "required_read_false_negative_rate"):
        result["all_completed_read_metrics"][name] = rate(
            sum(t["metrics"][name][0] for t in completed),
            sum(t["metrics"][name][1] for t in completed))
    return result


def score(root: Path, phase: str | None = None) -> dict:
    spec = load(root / "design.json")
    prepared = load(root / "prepared.json")
    paths = sorted((root / "trials").glob(f"{phase or '*' }/*/*/trial.json"))
    trials, errors = [], []
    for path in paths:
        try:
            trials.append(score_trial(path.parent, spec, prepared))
        except (ValueError, KeyError, OSError, TypeError) as exc:
            errors.append({"directory": str(path.parent), "error": repr(exc)})
    groups = defaultdict(list)
    for trial in trials:
        groups[f"{trial['phase']}/{trial['host']}"] .append(trial)
    return {"schema_version":1, "root":str(root), "phase_filter":phase,
            "scorer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "design_sha256":hashlib.sha256((root/'design.json').read_bytes()).hexdigest(),
            "limitations":["Native CLI sessions use a controlled action harness, not an installed live MCP end-to-end session.",
                           "Application detection is conservative SQL syntax plus independent action/output evidence; unsupported equivalent SQL needs adjudication.",
                           "Ambiguous summary semantics are unscored, retained as non-success in conservative task denominators.",
                           "S25/S26 use a tool-delivered staged task in one conversation, not real user turns.",
                           "Wilson intervals are descriptive trial-count intervals; repeated case observations are correlated.",
                           "Discovery responses are pre-materialized per case; repeated native trials do not constitute independent graph retrieval tests.",
                           "Claimed applied_skill_ids are supplementary only; they never establish actual application.",
                           "Strict extra-procedure execution is reported separately from application FP: valid discretionary joins (A06) and correctly labeled reference estimands (A07) are not called harmful overrides.",
                           "Denied out-of-contract attempts are flagged but recovered audited completion remains valid; executed out-of-contract actions invalidate the controlled session."],
            "overall":aggregate(trials), "by_phase_host":{k:aggregate(v) for k,v in groups.items()},
            "trials":trials, "scoring_errors":errors,
            "development_adjudications":[
                "A06 within-recording means may be calculated from returned raw rows; independently verify those means rather than demand one specific SQL result shape.",
                "A06 optional correct ID join remains a strict extra procedure and strict nonminimal read, not harmful application.",
                "A07 scalar COUNT subqueries mentioning both tables are not a JOIN; a verified correctly labeled reference estimand is not a task override.",
                "I23 applied_skill_ids is ignored when no plot was executed.",
                "Comma-separated numerals are normalized for final-answer extraction.",
                "N15 forbidden content-access attempts count even when SQLite rejects the CSV.",
                "Denied compound commands do not imply execution. Only-audited-CLI compound calls are usable evidence with strict-contract deviation retained.",
                "Successful external router-skill reads are controlled-contract deviations, not generic host failures or proof of a wrong task result."
            ],
            "phase_provenance":{p.stem:load(p) for p in sorted((root/'phases').glob('*.json')) if not phase or p.stem==phase}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('output_json',type=Path)
    parser.add_argument('--phase')
    args=parser.parse_args()
    report=score(args.root,args.phase)
    args.output_json.parent.mkdir(parents=True,exist_ok=True)
    args.output_json.write_text(json.dumps(report,indent=2)+'\n')
    for key,group in report['by_phase_host'].items():
        success=group['task_success_all_attempts']
        reads=group.get('unnecessary_read_rate',{})
        misses=group.get('required_read_false_negative_rate',{})
        print(f"{key}: tasks {success['numerator']}/{success['denominator']}; unnecessary reads {reads.get('numerator',0)}/{reads.get('denominator',0)}; required-read misses {misses.get('numerator',0)}/{misses.get('denominator',0)}; unscored {group['unscored_outcomes']}")
    print(f"Scored {len(report['trials'])} trials; scoring errors {len(report['scoring_errors'])}; {args.output_json}")


if __name__=='__main__':
    main()
