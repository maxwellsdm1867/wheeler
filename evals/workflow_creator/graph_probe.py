"""Isolated MCP harness for workflow-skill behavioral trials.

Usage: python graph_probe.py ROOT setup|snapshot|schema|call [SERVER TOOL ARGS_JSON_FILE]
The caller must create ROOT/config.json with an isolated loopback Neo4j config.
No production configuration or credentials are used. Calls and outcomes are audited.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import socket
from pathlib import Path
import sys
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.environ['WHEELER_NO_KEYCHAIN'] = '1'


async def main():
    root = Path(sys.argv[1]).resolve()
    action = sys.argv[2]
    raw = json.loads((root / 'config.json').read_text())
    if Path(raw['project_root']).resolve() != root:
        raise ValueError('Test project_root must match the supplied temporary root')
    uri = urlparse(raw['neo4j']['uri'])
    if uri.hostname not in {'127.0.0.1', 'localhost'} or uri.port != 17687:
        raise ValueError('This probe only permits the dedicated loopback test port 17687')
    if not raw['neo4j'].get('project_tag', '').startswith('creator-test-'):
        raise ValueError('An isolated creator-test namespace is required')
    os.chdir(root)
    from wheeler.config import WheelerConfig
    from wheeler.graph.driver import close_async_driver
    from wheeler.tools import graph_tools
    from wheeler import mcp_shared
    from wheeler.request_log import RequestLogger

    config = WheelerConfig.model_validate(raw)
    # Fault injection uses a real refused loopback connection, never a fake backend.
    offline = action == 'call' and (root / 'offline.flag').exists()
    if offline:
        with socket.socket() as check:
            check.settimeout(0.2)
            if check.connect_ex(('127.0.0.1', 17688)) == 0:
                raise RuntimeError('Fault port 17688 is in use; refusing to contact that service')
        config.neo4j.uri = 'bolt://127.0.0.1:17688'
        os.environ['WHEELER_NEO4J_CONNECT_TIMEOUT'] = '1'
        os.environ['WHEELER_NEO4J_ACQUISITION_TIMEOUT'] = '1'
        os.environ['WHEELER_NEO4J_RETRY_ATTEMPTS'] = '1'
    mcp_shared._config = config
    mcp_shared._request_logger = RequestLogger(config.resolved_wheeler_dir)
    servers = {}
    for name in ('core', 'query', 'mutations', 'ops'):
        module = importlib.import_module(f'wheeler.mcp_{name}')
        module._config = config
        servers[name] = module
    try:
        if action == 'schema':
            result = {name: [{'name': t.name, 'description': t.description, 'parameters': t.parameters} for t in await mod.mcp.list_tools()]
                      for name, mod in servers.items()}
        elif action == 'call':
            server, tool, argfile = sys.argv[3:6]
            if tool in {'delete_node', 'merge_nodes'}:
                raise ValueError('Destructive operations are not exposed in this trial')
            args = json.loads(Path(argfile).read_text())
            try:
                response = await servers[server].mcp.call_tool(tool, args)
                result = json.loads(response.content[0].text)
            except Exception as exc:
                result = {'error': str(exc), 'exception_type': type(exc).__name__}
            with (root / 'calls.jsonl').open('a') as stream:
                stream.write(json.dumps({'server': server, 'tool': tool, 'args': args,
                                         'result': result, 'offline': offline}, default=str) + '\n')
        elif action in {'setup', 'snapshot'}:
            backend = await graph_tools._get_backend(config)
            if action == 'setup':
                result = await servers['core'].init_schema()
            else:
                result = {'nodes': await backend.run_cypher(
                    'MATCH (n {_wheeler_project: $tag}) RETURN labels(n) AS labels, properties(n) AS node',
                    {'tag': config.neo4j.project_tag}),
                    'links': await backend.run_cypher(
                    'MATCH (a {_wheeler_project: $tag})-[r]->(b) RETURN a.id AS source, type(r) AS relationship, b.id AS target',
                    {'tag': config.neo4j.project_tag})}
        else:
            raise ValueError(action)
        print(json.dumps(result, default=str))
    finally:
        await close_async_driver()


if __name__ == '__main__':
    asyncio.run(main())
