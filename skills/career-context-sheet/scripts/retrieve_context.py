"""Find reading leads in a portable career packet; no network, writes or fit scores."""
import argparse
import importlib.util
import json
import re
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    'career_retrieval_renderer', Path(__file__).with_name('render_context.py'))
renderer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(renderer)
LAYERS = ('accounts', 'timeline', 'sources')
FIELDS = {
    'accounts': (*renderer.TEXT_FIELDS, 'decisions', 'limits', 'questions', 'tags', 'capabilities'),
    'timeline': ('period', 'title', 'focus', 'actions', 'tension', 'approach', 'questions'),
    'sources': ('label', 'date', 'content', 'scope'),
}


def text_fields(value, prefix):
    """Preserve field locations; never search transport bytes, IDs or file paths."""
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from text_fields(item, f'{prefix}[{index}]')
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from text_fields(item, f'{prefix}.{key}')


def links(packet, layer, record):
    key = record['id']
    if layer == 'sources':
        return {
            'accountIds': [a['id'] for a in packet['accounts'] if key in a['sourceRefs']],
            'timelineIds': [p['id'] for p in packet.get('timeline', []) if key in p['sourceRefs']],
        }
    return {
        'sourceRefs': record['sourceRefs'],
        'accountIds': record.get('accountIds', []),
        'timelineIds': [p['id'] for p in packet.get('timeline', [])
                        if layer == 'accounts' and key in p['accountIds']],
    }


def snippet(value, match, radius=130):
    start, end = max(0, match.start() - radius), match.end() + radius
    return ('…' if start else '') + value[start:end] + ('…' if end < len(value) else '')


def search(packet, queries, *, layers=LAYERS, limit=8, offset=0):
    queries = list(dict.fromkeys(q.strip() for q in queries))
    if not queries or any(not q or len(q) > 200 for q in queries) or len(queries) > 12:
        raise ValueError('Supply 1–12 nonblank queries, each at most 200 characters.')
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError('Limit must be 1–50 and offset must be nonnegative.')
    if not layers or set(layers) - set(LAYERS):
        raise ValueError('Unknown search layer.')
    patterns = [(query, re.compile(re.escape(query), re.IGNORECASE)) for query in queries]
    result = {'queries': queries, 'method': 'literal case-insensitive OR; packet order; reading leads only',
              'contextSha256': renderer.sections.evidence_fingerprint(packet), 'layers': {}}
    for layer in layers:
        hits = []
        for record in packet.get(layer, []):
            fields = [(field, value) for key in FIELDS[layer]
                      for field, value in text_fields(record.get(key), key)]
            matches = []
            for query, pattern in patterns:
                for field, value in fields:
                    match = pattern.search(value)
                    if match:
                        matches.append({'query': query, 'field': field, 'snippet': snippet(value, match)})
                        break
            if matches:
                hits.append({'id': record['id'], 'label': record.get('title', record.get('label')),
                             'kind': record.get('kind'), 'matches': matches,
                             'links': links(packet, layer, record)})
        page = hits[offset:offset + limit]
        result['layers'][layer] = {'recordsSearched': len(packet.get(layer, [])),
                                  'totalMatches': len(hits), 'offset': offset,
                                  'nextOffset': offset + len(page) if offset + len(page) < len(hits) else None,
                                  'hits': page}
    return result


def read_record(packet, selector):
    layer, separator, key = selector.partition(':')
    if not separator or layer not in LAYERS:
        raise ValueError('Use accounts:ID, timeline:ID or sources:ID.')
    record = next((r for r in packet.get(layer, []) if r['id'] == key), None)
    if record is None:
        raise ValueError('Record not found in this packet.')
    # Work samples stay in the sheet. Avoid dumping embedded image bytes.
    return {'layer': layer, 'record': {k: v for k, v in record.items() if k != 'artifacts'},
            'links': links(packet, layer, record)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Career context JSON or saved HTML')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--query', action='append', help='Literal term or phrase; repeat for alternatives')
    action.add_argument('--read', help='Read a full record by layer:ID')
    parser.add_argument('--layer', action='append', choices=LAYERS)
    parser.add_argument('--limit', type=int, default=8, help='Matches per layer, 1–50')
    parser.add_argument('--offset', type=int, default=0, help='Skip this many matches in each selected layer')
    args = parser.parse_args(argv)
    try:
        packet = renderer.load_packet(args.input)
        renderer.validate(packet)
        result = read_record(packet, args.read) if args.read else search(
            packet, args.query, layers=args.layer or LAYERS, limit=args.limit, offset=args.offset)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'Could not read context: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
