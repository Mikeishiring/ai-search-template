"""Create schemas and preregistration before the independent story is generated."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def arr(items):return {'type':'array','items':items}
S={'type':'string'};B={'type':'boolean'};N={'type':['string','null']}
ref=obj({'source':{'type':'string','enum':['chat','docs','repo']},'id':S})
record=obj({'id':S,'source':ref['properties']['source'],'date':S,'author':S,'container':S,'body':S,'parent':N,'links':arr(ref),'title':S,'attachments':arr(S),'link_only':B,'repost_of':N})
source=obj({'id':ref['properties']['source'],'platform':S,'enumeration':B,'inventory':S,'read_only':B})
scope=obj({'question':S,'query':S,'subject':S,'sources':arr(S),'start':S,'end':S,'horizon':S,'timezone':S})
attachment=obj({'id':S,'source':ref['properties']['source'],'title':S,'body':S,'unavailable':B})
theme=obj({'id':S,'name':S,'criterion':S,'anchors':arr(S),'pitfall':S,'importance':{'type':'string','enum':['material','secondary']}})
schema=obj({'corpus':obj({'synthetic':B,'snapshot':S,'sources':arr(source),'records':arr(record),'attachments':arr(attachment)}),'scope':scope,'gold':obj({'label':S,'expected_records':arr(S),'themes':arr(theme),'author_note':S})})
path=ROOT/'model/author.schema.json'
if path.exists():raise SystemExit('Setup already frozen')
path.write_text(json.dumps(schema,indent=2),encoding='utf-8')
files=['model/independent-author.txt','model/autonomous-researcher.txt','model/author.schema.json','model/review.schema.json','autonomous_server.py','independent_experiment.py']
manifest={'synthetic_only':True,'source_call_budget':45,'page_size':3,'author':'Separate isolated Codex invocation; no old corpus, implementation or research prompt supplied','researcher':'Separate fresh Codex invocation with only scope and read-only source tools','assessment':'Source/quotation validation plus manual comparison against author rubric; no automatic semantic grading','stop':'One substantive research attempt, up to 45 source calls or 15 minutes; no hints or retuning after observation','limitations':['Separate AI author, not an independently recruited human author.','Author and researcher use the same provider/default model family; errors may be correlated.'],'freeze':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
(ROOT/'runs/autonomous').mkdir(parents=True,exist_ok=True)
(ROOT/'runs/autonomous/preregistration.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'preregistered':True,'budget':45,'files_frozen':len(files)}))
