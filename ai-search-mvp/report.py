"""One self-contained local inspection report. No network resources or private inputs."""
import json
from pathlib import Path


def build(root: Path):
    data = {}
    for case in ["training", "challenge", "search_only"]:
        folder = root / "runs" / case
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        evaluation = folder / "evaluation.json"
        data[case] = {"result": result, "evaluation": json.loads(evaluation.read_text(encoding="utf-8")) if evaluation.exists() else None}
    semantic=root/'runs/semantic'
    if (semantic/'assessment.json').exists():
        read=lambda p:json.loads(p.read_text(encoding='utf-8'))
        data['semantic']={'result':read(semantic/'result.json'),'evaluation':read(semantic/'assessment.json'),
                          'review':read(semantic/'model/review.json'),'provenance':read(semantic/'model/provenance.json'),
                          'receipt':read(semantic/'model/receipt.json')}
    for case in ['autonomous','followup','attribution','completion','depth','retention','ownership']:
        autonomous=root/'runs'/case
        if (autonomous/'assessment.json').exists():
            read=lambda p:json.loads(p.read_text(encoding='utf-8'))
            data[case]={'result':read(autonomous/'result.json'),'evaluation':read(autonomous/'assessment.json'),
                                'review':read(autonomous/('researcher/review.json' if case in {'completion','depth','retention','ownership'} else 'researcher/response.json')),'provenance':read(autonomous/'provenance.json'),
                                'receipt':read(autonomous/'researcher/receipt.json'),'trace':read(autonomous/'trace.json'),
                                'audit_records':read(autonomous/'audit-records.json')}
            if (autonomous/'attachments.json').exists():data[case]['attachments']=read(autonomous/'attachments.json')
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = (root / "report-template.html").read_text(encoding="utf-8")
    styles = (root / "report-style.css").read_text(encoding="utf-8")
    template = template.replace("__STYLES__", styles)
    output = root.parent / "AI-SEARCH-MVP.html"
    output.write_text(template.replace("__DATA__", payload), encoding="utf-8")
    return str(output)
