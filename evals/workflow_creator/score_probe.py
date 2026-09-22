"""Score observed workflow outcomes independently of the skill executor.

Usage: python score_probe.py ROOT BASELINE_JSON SNAPSHOT_JSON PHASE
PHASE: draft, ready, rerun, revision, offline, recovery
"""
import hashlib
import json
from pathlib import Path
import sys

root, baseline_path, snapshot_path = map(Path, sys.argv[1:4])
phase = sys.argv[4]
baseline = json.loads(baseline_path.read_text())
snapshot = json.loads(snapshot_path.read_text())
base_ids = {row['node']['id'] for row in baseline['nodes']}
nodes = {row['node']['id']: row for row in snapshot['nodes']}
new = {nid: row for nid, row in nodes.items() if nid not in base_ids}
links = {(r['source'], r['relationship'], r['target']) for r in snapshot['links']}
assert len(links) == len(snapshot['links']), 'Duplicate graph relationships'
fixture = json.loads((root/'fixture.json').read_text())
checks = []

def check(condition, message):
    assert condition, message
    checks.append(message)

meeting = root/'meetings/2026-09-25'
check((meeting/'brief.md').is_file(), 'Working brief exists')
if phase == 'draft':
    check(not new, 'Draft produced no graph nodes')
    check(snapshot['links'] == baseline['links'], 'Draft produced no graph links')
else:
    versions = ['001', '002', '003'] if phase == 'recovery' else (['001', '002'] if phase in {'revision', 'offline'} else ['001'])
    if phase == 'offline':
        check((meeting/'brief-v003.md').is_file() and (meeting/'sources-v003.json').is_file(), 'Offline readiness preserves local snapshot and source record')
        check(not any('v003' in row['node'].get('path', '') for row in new.values()), 'Offline snapshot has not been registered')
    for version in versions:
        for stem, suffix in [('brief', 'md'), ('sources', 'json')]:
            path = meeting/f'{stem}-v{version}.{suffix}'
            check(path.is_file(), f'{path.name} exists')
            matches = [(nid, row) for nid, row in new.items()
                       if row['node'].get('path', '').replace('${PROJECT}', str(root)) == str(path)]
            check(len(matches) == 1, f'{path.name} registered exactly once')
            nid, row = matches[0]
            check(row['labels'] == ['Document'], f'{path.name} is a Document')
            data = json.loads((root/'knowledge'/f'{nid}.json').read_text())
            for field in ('title', 'path', 'status', 'hash'):
                check(data[field] == row['node'][field], f'{path.name} graph/JSON agree on {field}')
            check(data['hash'] == hashlib.sha256(path.read_bytes()).hexdigest(), f'{path.name} hash matches artifact')
            synthesis = root/'synthesis'/f'{nid}.md'
            check(synthesis.is_file() and nid in synthesis.read_text(), f'{path.name} synthesis exists')
            executions = [t for s, r, t in links if s == nid and r == 'WAS_GENERATED_BY']
            check(bool(executions), f'{path.name} has producing Execution')
            for ex in executions:
                check('Execution' in nodes[ex]['labels'], 'Provenance points to Execution')
                used = {t for s, r, t in links if s == ex and r == 'USED'}
                check(fixture['ids']['distractor'] not in used, 'Unrelated same-name plot is not a used input')
                expected_inputs = {fixture['ids'][key] for key in ('notebook', 'manifest', 'prior', 'response', 'residuals', 'decision')}
                check(expected_inputs <= used, 'Execution records every actual context/artifact input')
        manifest = json.loads((meeting/f'sources-v{version}.json').read_text())
        check('analysis/current/response.png' in json.dumps(manifest), 'Manifest selects current response plot')
        check('analysis/archive/response.png' not in json.dumps(manifest), 'Manifest excludes same-name archive plot')
    check(not any('Finding' in row['labels'] for row in new.values()), 'No guesses or plots promoted into Findings')
    check(not any(row['node'].get('path','').endswith('/brief.md') for row in new.values()), 'Working brief remains unregistered')
    check(sum('Execution' in row['labels'] for row in new.values()) == len(versions), 'Exactly one capture Execution per version')
    expected_docs = 2 * len(versions)
    check(sum('Document' in row['labels'] for row in new.values()) == expected_docs, 'Only expected snapshot and source documents registered')
print(json.dumps({'phase':phase,'passed':len(checks),'checks':checks},indent=2))
