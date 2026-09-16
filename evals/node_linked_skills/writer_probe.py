"""Native lesson-writer probe using production core/query/mutations MCP servers.

Each host/case has its own project and unique graph tag. The evaluator's manifest
and expected outcomes stay outside those projects. No host call happens during
setup. Graph cleanup only deletes the recorded probe namespaces.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
PYTHON = REPO / '.venv/bin/python'
sys.path.insert(0,str(REPO))

ORIGINAL_NAME = 'recording-joins'
ORIGINAL_BODY = (
    'Use this workflow when retrieving measurement rows by recording metadata from this database. '
    'Join recordings to measurements on recording_id, never basename: filenames can be duplicated '
    'across recordings. Apply cell_type filters to recordings before selecting measurement rows. '
    'Check that the joined row count equals the measurements for the selected recording IDs, '
    'then return every measurement unless aggregation was explicitly requested. Report the selected '
    'recording IDs so another researcher can reproduce the selection. Do not apply this workflow '
    'to file-size checks, schema inspection, or unrelated databases.'
)
CASES = {
    'added_check': {
        'correction': 'Wheeler, remember one more check for retrieving cell-type measurements from this database: after selecting recordings, explicitly report any selected recording with zero measurements instead of silently dropping it. Keep the existing ID-based join, cell-type filter, full measurement rows, and scope exclusions.',
        'expected_action': 'revision',
    },
    'renamed_paraphrase': {
        'correction': 'Wheeler, remember this safe-cell-lookup procedure for the same database: choose the requested cell type from recording metadata, link measurements using recording_id rather than the repeated filename, and validate the returned measurement count. I mean the same lookup workflow we already use, just describing it in different words.',
        'expected_action': 'revision_or_idempotent',
    },
    'distinct_workflow': {
        'correction': 'Wheeler, remember a separate reusable workflow for releasing a snapshot of this database. Select a consistent read snapshot, create a new versioned copy without overwriting an earlier release, reopen the copy and run PRAGMA integrity_check, and record its checksum in a release manifest. This concerns packaging releases, not querying cell measurements. Save the workflow now; do not create a database copy or run the release today.',
        'expected_action': 'new',
    },
    'candidate_revision': {
        'correction': 'Wheeler, remember this stable-cell-rows workflow for the recordings database. Select cell-type measurements using stable recording IDs and validate the returned count. Also explicitly report selected recordings that have zero measurements. I endorse saving this procedure now.',
        'expected_action': 'revision',
        'initial_state': 'candidate',
    },
    'enforceable_invariant': {
        'correction': 'Wheeler, remember that before editing the query-helper script the agent must read the current file. This is a mandatory file-access invariant and should be enforced by a hook or tool precondition. Identify the concrete implementation change we need; do not pretend it is enforced today.',
        'expected_action': 'no_skill',
    },
}


def dump(path: Path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str)+'\n')


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_for(project: Path, uri: str, tag: str):
    from wheeler.config import WheelerConfig
    return WheelerConfig(project_root=str(project),search={'enabled':False},synthesis_enabled=False,
        neo4j={'uri':uri,'username':'neo4j','database':'neo4j','project_tag':tag,
               'password':''})


def mcp_config(project: Path, uri: str):
    env = {'WHEELER_PROJECT_ROOT':str(project),'PYTHONPATH':str(REPO),'WHEELER_NO_KEYCHAIN':'1',
           'NEO4J_URI':uri,'NEO4J_USERNAME':'neo4j','NEO4J_DATABASE':'neo4j',
           'NEO4J_PASSWORD':''}
    servers={}
    for name,tools in {
        'wheeler_core':['show_node','graph_health','search_context'],
        'wheeler_query':['query_documents'],
        'wheeler_mutations':['capture_lesson','accept_skill','retire_skill'],
    }.items():
        servers[name]={'command':str(PYTHON),'args':['-m','wheeler.mcp_'+name.removeprefix('wheeler_')],
                       'env':env,'enabled_tools':tools}
    return {'mcpServers':servers}


async def snapshot(project: Path, config) -> dict:
    from wheeler.tools.graph_tools import _get_backend
    backend=await _get_backend(config)
    rows=await backend.run_cypher('MATCH (n {_wheeler_project:$tag}) RETURN labels(n) AS labels, properties(n) AS properties ORDER BY n.id',{'tag':config.neo4j.project_tag})
    edges=await backend.run_cypher('MATCH (a {_wheeler_project:$tag})-[r]->(b {_wheeler_project:$tag}) RETURN a.id AS source, type(r) AS type, b.id AS target ORDER BY source,type,target',{'tag':config.neo4j.project_tag})
    files={str(path.relative_to(project)):{'sha256':digest(path),'bytes':path.stat().st_size}
           for path in sorted((project/'.notes/lessons').rglob('*')) if path.is_file()}
    return {'nodes':rows,'edges':edges,'files':files}


async def setup(root: Path, uri: str):
    from wheeler.tools.graph_tools import execute_tool
    parsed=urlparse(uri)
    if parsed.scheme not in {'bolt','neo4j'} or parsed.hostname not in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Only explicitly isolated loopback Neo4j is supported')
    root.mkdir(parents=True,exist_ok=True)
    manifest_path=root/'private-manifest.json'
    if manifest_path.exists():
        raise ValueError('Use a new writer-probe root')
    act_path=REPO/'wheeler/_data/commands/lesson.md'
    act=act_path.read_text()
    manifest={'kind':'native-writer-probe','uri':uri,'cases':{},'fixture_tags':[],
              'lesson_act':act,'lesson_act_sha256':digest(act_path),'original_body':ORIGINAL_BODY,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()}
    dump(manifest_path,manifest)
    for host in ('claude','codex'):
        for case_id,case in CASES.items():
            project=root/'projects'/host/case_id
            project.mkdir(parents=True)
            tag='native-writer-probe-'+uuid4().hex
            manifest['fixture_tags'].append({'tag':tag,'project':str(project)})
            dump(manifest_path,manifest)
            config=config_for(project,uri,tag)
            (project/'wheeler.yaml').write_text(config.model_dump_json(indent=2))
            database=project/'recordings.sqlite'
            import sqlite3
            with sqlite3.connect(database) as db:
                db.executescript('CREATE TABLE recordings(recording_id TEXT PRIMARY KEY, basename TEXT, cell_type TEXT); CREATE TABLE measurements(recording_id TEXT, value REAL);')
            script=project/'query_helper.py'
            script.write_text('"""Query helper; enforceable read-before-edit behavior belongs in the agent tool layer."""\n')
            database_id,script_id='D-'+uuid4().hex[:8],'S-'+uuid4().hex[:8]
            for tool,args in [
                ('add_dataset',{'id':database_id,'path':str(database),'type':'sqlite','description':'Recording metadata and measurements database'}),
                ('add_script',{'id':script_id,'path':str(script),'language':'python','description':'Query helper for the recordings database'}),
            ]:
                result=json.loads(await execute_tool(tool,args,config))
                if result.get('error'):
                    raise RuntimeError(result)
            original=json.loads(await execute_tool('capture_lesson',{
                'name':ORIGINAL_NAME,'description':'Retrieve cell-type measurements by joining recording metadata to this database. Not for schema or file metadata inspection.',
                'instructions':ORIGINAL_BODY,'target_ids':[database_id],
                'source_excerpt':'Use stable recording identities when retrieving cell-type measurements; filenames may repeat.',
                'problem_statement':'Duplicate filenames can contaminate cell-type measurement selection.',
                'benchmark_task':'Retrieve measurements for selected recordings with duplicate filenames; verify IDs and row counts. Skip metadata-only tasks and unrelated databases.',
                'accepted':case.get('initial_state')!='candidate','author_model':'unknown','author_environment':'Synthetic initial fixture, authored locally by evaluator',
            },config))
            if original.get('error') or original.get('status') in {None,'incomplete'}:
                raise RuntimeError(original)
            before=await snapshot(project,config)
            prompt=(
                'Use the following current canonical Wheeler lesson act to handle the scientist request. '
                'Its body is supplied verbatim because this evaluates the writer rather than router installation. '
                'Use live Wheeler MCP tools and native file reads as needed. Work only in this fixture project and its returned graph artifacts. '
                'Do not read evaluator manifests, sibling cases, snapshots, or logs. Do not claim a benchmark ran; no execution result has been supplied. '
                'Complete the authorized capture if appropriate and give the saved IDs and versions, or explain the proper implementation handoff if no skill belongs here.\n\n'
                +act+'\n\nCurrent artifact context:\n'
                +f'Recordings database: {database_id}, {database}\nQuery-helper script: {script_id}, {script}\n'
                +'Scientist request:\n'+case['correction']
            )
            entry={'host':host,'case_id':case_id,'project':str(project),'tag':tag,'database_id':database_id,
                   'script_id':script_id,'original':original,'before':before,'prompt':prompt,
                   'mcpconfig':mcp_config(project,uri),'expected_action':case['expected_action'],'correction':case['correction']}
            manifest['cases'][f'{host}/{case_id}']=entry
            dump(manifest_path,manifest)
    return {'manifest':str(manifest_path),'cases':list(manifest['cases'])}


def checks_for(entry: dict, after: dict, active: dict, result: dict):
    checks=[]
    def check(name,passed,evidence=None):
        checks.append({'name':name,'passed':passed,'evidence':evidence})
    before=entry['before']
    original=entry['original']
    old_id=original['node_id']
    nodes=[row['properties'] for row in after['nodes'] if row['properties'].get('skill_name')]
    new=[node for node in nodes if node['id']!=old_id]
    active_ids={s['id'] for s in active.get('linked_skills',[])}
    expected=entry['expected_action']
    check('discovery_complete',active.get('linked_skills_status')=='complete')
    check('original_files_immutable',all(after['files'].get(path)==metadata for path,metadata in before['files'].items()))
    check('original_history_preserved',any(n['id']==old_id for n in nodes))
    if expected in {'revision','revision_or_idempotent'}:
        idempotent=expected=='revision_or_idempotent' and not new
        check('one_current_workflow',len(active_ids)==1)
        check('single_revision_or_idempotent',len(new)==1 or idempotent,len(new))
        check('reuse_name',all(n.get('skill_name')==ORIGINAL_NAME for n in new))
        check('revision_parent',all(n.get('skill_supersedes')==old_id for n in new))
        check('reuse_target_scope',all(n.get('skill_target_ids')==[entry['database_id']] for n in new))
    elif expected=='new':
        check('new_distinct_workflow',len(new)==1 and all(n.get('skill_name')!=ORIGINAL_NAME and not n.get('skill_supersedes') for n in new))
        check('both_workflows_active',old_id in active_ids and len(active_ids)==2)
    else:
        check('no_new_skill',not new)
        check('existing_skill_stays_active',active_ids=={old_id})
        text=result.get('final_response','').lower()
        check('implementation_handoff_identified',bool(re.search(r'hook|precondition|invariant',text)))
        check('does_not_claim_enforcement',not bool(re.search(r'(?:implemented|installed|enabled|enforced) (?:the |a )?(?:hook|precondition)',text)))
    bodies=[]
    for node in new:
        skill_path=Path(node['path'])
        if not skill_path.is_absolute():
            skill_path=Path(entry['project']) / str(skill_path).removeprefix('${PROJECT}/')
        manifest=json.loads((skill_path.parent/'capture.json').read_text())
        body=manifest['instructions']
        words=len(body.split())
        bodies.append({'id':node['id'],'instructions':body,'word_count':words,
                       'ratio_to_original':words/len(ORIGINAL_BODY.split()),'capture':manifest})
        check('accepted:'+node['id'],node.get('skill_state')=='accepted')
        check('source_and_problem_retained:'+node['id'],bool(manifest.get('source_excerpt')) and bool(manifest.get('problem_statement')))
        check('benchmark_task_recorded:'+node['id'],bool(manifest.get('benchmark_task')))
        check('no_fabricated_test_run:'+node['id'],not any(manifest.get(k) for k in ('tested_model','tested_environment','benchmark_result_ids')))
        actual=set(result.get('actual_models',[]))|{result.get('actual_model','unknown'),'unknown'}
        check('honest_model_provenance:'+node['id'],manifest.get('author_model') in actual,manifest.get('author_model'))
        check('environment_recorded:'+node['id'],bool(manifest.get('author_environment')) and manifest.get('author_environment')!='unknown',manifest.get('author_environment'))
        check('no_incident_log_in_procedure:'+node['id'],not bool(re.search(r'(?im)^\s*(?:incident log|incident history|conversation transcript|yesterday we|on 20\d\d-)',body)))
        edges=after['edges']
        generated=[edge['target'] for edge in edges if edge['source']==node['id'] and edge['type']=='WAS_GENERATED_BY']
        check('execution_provenance:'+node['id'],bool(generated) and any(edge['source'] in generated and edge['type']=='USED' for edge in edges))
        if expected in {'revision','revision_or_idempotent'}:
            text=body.lower()
            check('preserves_identity_and_selection:'+node['id'],'recording_id' in text and 'basename' in text and bool(re.search(r'cell[_ ]type',text)))
            check('preserves_full_rows:'+node['id'],bool(re.search(r'every (?:(?:matching|linked|selected|individual) )?measurement|all (?:measurement|matched|matching) (?:rows|measurements)|all measurements',text)))
            check('preserves_scope_exclusions:'+node['id'],'schema' in text and bool(re.search(r'file.size|file size|metadata',text)))
            if entry['case_id'] in {'added_check','candidate_revision'}:
                check('added_missing_measurement_check:'+node['id'],bool(re.search(r'zero|no measurement|missing measurement|without measurement',text)))
    return {'checks':checks,'passed':all(c['passed'] is True for c in checks),
            'skill_count_before':1,'skill_count_after':len(nodes),'active_count_after':len(active_ids),
            'new_skill_ids':[n['id'] for n in new],'bodies':bodies,
            'minimality_note':'Word counts and growth ratios are descriptive; semantic concision requires review, not an arbitrary production word quota.'}


def writer_trace(logs: Path, original_path: str):
    events=[]
    stream=logs/'stdout.jsonl'
    if stream.exists():
        for line in stream.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    inventory_calls=[]
    body_read_evidence=[]
    for index,event in enumerate(events):
        if event.get('type')=='assistant':
            for block in event.get('message',{}).get('content',[]):
                if block.get('type')!='tool_use':
                    continue
                args=block.get('input',{})
                if block.get('name','').endswith('show_node') and args.get('skill_inventory') is True:
                    inventory_calls.append({'event_index':index,'arguments':args})
                if block.get('name')=='Read' and original_path in json.dumps(args):
                    body_read_evidence.append({'event_index':index,'tool':'Read','arguments':args})
        item=event.get('item',{})
        if event.get('type')=='item.completed' and item.get('type')=='mcp_tool_call':
            args=item.get('arguments',{})
            if isinstance(args,str):
                try:
                    args=json.loads(args)
                except ValueError:
                    args={}
            if item.get('tool')=='show_node' and args.get('skill_inventory') is True:
                inventory_calls.append({'event_index':index,'arguments':args})
        if event.get('type')=='item.completed' and item.get('type')=='command_execution':
            command=item.get('command','')
            if original_path in command:
                body_read_evidence.append({'event_index':index,'tool':'command_execution','command':command})
    return {'inventory_calls':inventory_calls,'original_body_read_evidence':body_read_evidence}


async def score_one(root: Path, key: str):
    from wheeler.skill_discovery import discover_skills
    manifest=json.loads((root/'private-manifest.json').read_text())
    entry=manifest['cases'][key]
    project=Path(entry['project'])
    config=config_for(project,manifest['uri'],entry['tag'])
    after=await snapshot(project,config)
    active=await discover_skills([entry['database_id']],config)
    result=json.loads((root/'logs'/key/'result.json').read_text())
    scored=checks_for(entry,after,active,result)
    trace=writer_trace(root/'logs'/key,entry['original']['path'])
    if entry['expected_action']!='no_skill':
        scored['checks'].append({'name':'writer_inventory_called','passed':bool(trace['inventory_calls'])})
        scored['passed']=all(c['passed'] is True for c in scored['checks'])
    report={'case':key,'host_result':result,'after_snapshot':after,'active_discovery':active,
            'source_act_sha256':manifest['lesson_act_sha256'],'writer_probe_sha256':digest(Path(__file__)),'writer_trace':trace,**scored}
    dump(root/'scores'/f"{key.replace('/','-')}.json",report)
    return {'case':key,'passed':scored['passed'],'failed_checks':[c for c in scored['checks'] if c['passed'] is not True]}


async def score_all(root: Path, keys: list[str]):
    from wheeler.graph.driver import close_async_driver
    try:
        return [await score_one(root,key) for key in keys]
    finally:
        await close_async_driver()


def run_one(root: Path, key: str, timeout_seconds=210, authorize_fixture_mutations=False):
    from live_host_probe import run_host
    manifest=json.loads((root/'private-manifest.json').read_text())
    entry=manifest['cases'][key]
    logs=root/'logs'/key
    if logs.exists() and any(logs.iterdir()):
        raise FileExistsError('Preserve the prior attempt: run a fresh writer-probe project instead of overwriting logs')
    overrides=[]
    if entry['host']=='codex' and authorize_fixture_mutations:
        # Explicit per-tool consent only for the fixture server configured above;
        # does not bypass the host sandbox or approve unrelated servers/tools.
        overrides=[f'mcp_servers.wheeler_mutations.tools.{name}.approval_mode="approve"'
                   for name in ('capture_lesson','accept_skill')]
    return run_host(entry['host'],Path(entry['project']),entry['prompt'],root/'logs'/key,
                    entry['mcpconfig'],timeout_seconds,codex_config=overrides)


async def cleanup(root: Path):
    from wheeler.tools.graph_tools import _get_backend
    manifest=json.loads((root/'private-manifest.json').read_text())
    if manifest.get('kind')!='native-writer-probe':
        raise ValueError('Not a writer probe manifest')
    removed=[]
    for item in manifest['fixture_tags']:
        if not item['tag'].startswith('native-writer-probe-'):
            raise ValueError('Refusing non-probe namespace')
        backend=await _get_backend(config_for(Path(item['project']),manifest['uri'],item['tag']))
        await backend.run_cypher('MATCH (n {_wheeler_project:$tag}) DETACH DELETE n',{'tag':item['tag']})
        removed.append(item['tag'])
    return {'removed_fixture_tags':removed}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    subs=parser.add_subparsers(dest='command',required=True)
    prep=subs.add_parser('setup')
    prep.add_argument('--uri',required=True)
    run=subs.add_parser('run')
    run.add_argument('key')
    run.add_argument('--timeout',type=int,default=210)
    run.add_argument('--approve-fixture-mutations',action='store_true')
    scoring=subs.add_parser('score')
    scoring.add_argument('key',nargs='?')
    subs.add_parser('cleanup')
    args=parser.parse_args()
    if args.command=='setup':
        result=asyncio.run(setup(args.root,args.uri))
    elif args.command=='run':
        result=run_one(args.root,args.key,args.timeout,args.approve_fixture_mutations)
    elif args.command=='score':
        all_keys=list(json.loads((args.root/'private-manifest.json').read_text())['cases'])
        keys=[args.key] if args.key else [key for key in all_keys if (args.root/'logs'/key/'result.json').exists()]
        result=asyncio.run(score_all(args.root,keys))
    else:
        result=asyncio.run(cleanup(args.root))
    print(json.dumps(result,indent=2,default=str))


if __name__=='__main__':
    main()
