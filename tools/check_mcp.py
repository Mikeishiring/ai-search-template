"""No-model stdio handshake and synthetic inventory check; no account connection."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
messages=[
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'local-connection-check','version':'1'}}},
 {'jsonrpc':'2.0','method':'notifications/initialized'},
 {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'source_inventory','arguments':{'case':'training'}}}
]
p=subprocess.run([sys.executable,str(root/'ai-search-mvp/mcp_server.py')],input=''.join(json.dumps(m)+'\n' for m in messages),text=True,capture_output=True,timeout=30)
if p.returncode:raise SystemExit('Server process failed. Check Python version and file access; no source account was contacted.')
replies={r['id']:r for r in map(json.loads,p.stdout.splitlines())}
assert replies[1]['result']['protocolVersion']=='2025-06-18'
assert len(replies[2]['result']['tools'])==6
assert replies[3]['result']['structuredContent']['synthetic'] is True
print(json.dumps({'stdio_handshake':'passed','tools':6,'synthetic_inventory':'passed','model_called':False,'real_sources_connected':False}))
