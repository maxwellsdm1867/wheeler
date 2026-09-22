"""Create synthetic lab-meeting artifacts and seed a dedicated test graph."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

root = Path(sys.argv[1]).resolve()
probe = Path(__file__).with_name('graph_probe.py').resolve()

def call(server, tool, **args):
    argfile = root / 'seed-args.json'
    argfile.write_text(json.dumps(args))
    proc = subprocess.run([sys.executable, str(probe), str(root), 'call', server, tool, str(argfile)], check=True, capture_output=True, text=True)
    result = json.loads(proc.stdout)
    assert 'error' not in result, result
    return result

def png(path, value):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    rows = []
    for y in range(64):
        row = b''.join(bytes((35, 95, 150) if 20 < x < 45 and y > 64 - value else (255, 255, 255)) for x in range(64))
        rows.append(b'\x00' + row)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 64, 64, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))

for name in ('analysis/current', 'analysis/archive', 'meetings/2026-09-18'):
    (root/name).mkdir(parents=True, exist_ok=True)
notebook = root/'analysis/current/calcium.ipynb'
notebook.write_text(json.dumps({'nbformat':4,'nbformat_minor':5,'metadata':{},'cells':[{'cell_type':'markdown','id':'summary','metadata':{},'source':['Synthetic run ca-0922. Smoothing window 5. Peak response 1.2. This is a fixture result, not a validated scientific finding.']}]}))
for name,value in [('response.png',40),('residuals.png',20)]:
    png(root/'analysis/current'/name,value)
png(root/'analysis/archive/response.png',60)
manifest=root/'analysis/current/run-manifest.json'
manifest.write_text(json.dumps({'run_id':'ca-0922','parameters':{'smoothing_window':5},'notebook':str(notebook),'plots':[str(root/'analysis/current/response.png'),str(root/'analysis/current/residuals.png')]},indent=2))
prior=root/'meetings/2026-09-18/notes.md'
prior.write_text('# Prior lab meeting\nDecision: keep smoothing window 5 to preserve transient peaks.\nOpen: check sensitivity to baseline subtraction.\n')
ids={}
for name,path in [('notebook',notebook),('manifest',manifest),('prior',prior),('response',root/'analysis/current/response.png'),('residuals',root/'analysis/current/residuals.png'),('distractor',root/'analysis/archive/response.png')]:
    result=call('mutations','ensure_artifact',path=str(path),artifact_type='document',title='Calcium '+name,status='draft')
    ids[name]=result['node_id']
note=call('mutations','add_note',title='Calcium parameter rationale',content='Keep smoothing window 5 to preserve transient peaks; last meeting left baseline subtraction sensitivity open.',context='Calcium weekly lab meeting 2026-09-18',execution_kind='discuss',used_entities=ids['prior'],execution_description='Synthetic prior meeting decision')
ids['decision']=note['node_id']
(root/'fixture.json').write_text(json.dumps({'ids':ids,'manifest':str(manifest),'notebook':str(notebook),'prior':str(prior)},indent=2))
print(json.dumps({'root':str(root),'ids':ids},indent=2))
