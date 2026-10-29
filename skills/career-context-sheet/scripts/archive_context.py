"""Keep selected career context in one local SQLite database. No network calls."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile

_spec = importlib.util.spec_from_file_location('context_renderer', Path(__file__).with_name('render_context.py'))
renderer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(renderer)
APPLICATION_ID = 1128481073
DDL = '''
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE revisions (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL, packet TEXT NOT NULL, html BLOB NOT NULL);
CREATE TABLE accounts (revision TEXT REFERENCES revisions(id), id TEXT, title TEXT, period TEXT, content TEXT,
                       PRIMARY KEY(revision,id));
CREATE TABLE sources (revision TEXT REFERENCES revisions(id), id TEXT, label TEXT, kind TEXT, content TEXT,
                      scope TEXT, locator TEXT, PRIMARY KEY(revision,id));
CREATE TABLE account_sources (revision TEXT, account_id TEXT, source_id TEXT,
    FOREIGN KEY(revision,account_id) REFERENCES accounts(revision,id),
    FOREIGN KEY(revision,source_id) REFERENCES sources(revision,id), PRIMARY KEY(revision,account_id,source_id));
CREATE TABLE artifacts (revision TEXT, account_id TEXT, id TEXT, title TEXT, caption TEXT, media_type TEXT,
                        sha256 TEXT, bytes BLOB, PRIMARY KEY(revision,id),
                        FOREIGN KEY(revision,account_id) REFERENCES accounts(revision,id));
CREATE TABLE collection (revision TEXT REFERENCES revisions(id), ordinal INTEGER, platform TEXT,
    location TEXT, access TEXT, status TEXT, scope TEXT, next_step TEXT, PRIMARY KEY(revision,ordinal));
'''


def connect(path, *, readonly=False):
    path = Path(path).expanduser().absolute()
    if path.is_symlink():
        raise ValueError('Database must not be a symbolic link')
    if not path.is_file():
        raise ValueError('No career database at this path')
    db = sqlite3.connect(path.resolve().as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        if db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID or db.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise ValueError('Not a supported career-context database')
    except (sqlite3.Error, ValueError):
        db.close()
        raise
    return db


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.career-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build(source, workspace, *, update=False, allow_view_removal=False):
    source, workspace = Path(source).resolve(), Path(workspace).expanduser().absolute()
    if workspace.is_symlink() or workspace.resolve().is_relative_to(renderer.SKILL.resolve()):
        raise ValueError('Use a private workspace outside the installed skill')
    workspace.mkdir(parents=True, exist_ok=True)
    database, sheet = workspace / 'career.sqlite', workspace / 'CAREER-CONTEXT.html'
    if database.is_symlink() or sheet.is_symlink():
        raise ValueError('Workspace outputs must not be symbolic links')
    existing = database.exists()
    if existing and not update:
        raise ValueError('Archive exists; use --update to retain a new revision')
    if not existing and sheet.exists():
        raise ValueError('An untracked sheet exists here; use a new workspace')
    # Validate and render everything before opening a write transaction.
    with tempfile.TemporaryDirectory(dir=workspace, prefix='.render-') as folder:
        staged = Path(folder) / 'sheet.html'
        renderer.render(source, staged)
        raw = staged.read_bytes()
        packet = renderer.load_packet(staged)
    revision = hashlib.sha256(raw).hexdigest()
    clean = json.loads(json.dumps(packet))
    images = []
    for account in clean['accounts']:
        for artifact in account.get('artifacts', []):
            mime, data = renderer.image_data(artifact, source.parent)
            artifact.pop('_dataUrl', None)
            images.append((revision, account['id'], artifact['id'], artifact['title'], artifact['caption'],
                           mime, artifact['sha256'], data))
    previous = None
    if existing:
        db = connect(database)
    else:
        # Exclusive creation prevents replacing an unrelated or concurrent database.
        with database.open('xb'):
            pass
        db = None
        try:
            db = sqlite3.connect(database)
            db.execute('PRAGMA foreign_keys=ON')
            db.executescript(DDL)
            db.execute(f'PRAGMA application_id={APPLICATION_ID}')
            db.execute('PRAGMA user_version=1')
            db.commit()
        except Exception:
            if db is not None:
                db.close()
            database.unlink(missing_ok=True)
            raise
    replaced = False
    try:
        db.execute('BEGIN IMMEDIATE')
        meta = dict(db.execute('SELECT key,value FROM metadata'))
        if meta.get('person') and meta['person'] != packet['person']['name']:
            raise ValueError('This archive belongs to a different person; use a separate workspace')
        if sheet.exists():
            previous = sheet.read_bytes()
            if hashlib.sha256(previous).hexdigest() != meta.get('current'):
                raise ValueError('The saved sheet has local changes; use it as input in a new workspace to preserve both versions')
            if not allow_view_removal:
                renderer.preserve_views(renderer.parse_packet(previous.decode('utf-8'), is_html=True), packet)
        new_revision = not db.execute('SELECT 1 FROM revisions WHERE id=?', (revision,)).fetchone()
        if new_revision:
            db.execute('INSERT INTO revisions VALUES (?,?,?,?)',
                       (revision, packet['updatedAt'], json.dumps(clean, ensure_ascii=True), raw))
            for account in clean['accounts']:
                db.execute('INSERT INTO accounts VALUES (?,?,?,?,?)',
                           (revision, account['id'], account['title'], account['period'], json.dumps(account, ensure_ascii=False)))
            for source_item in clean['sources']:
                db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
                           (revision, source_item['id'], source_item['label'], source_item['kind'], source_item['content'],
                            source_item['scope'], source_item.get('locator', '')))
            db.executemany('INSERT INTO account_sources VALUES (?,?,?)',
                           [(revision, a['id'], ref) for a in clean['accounts'] for ref in a['sourceRefs']])
            db.executemany('INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?)', images)
            db.executemany('INSERT INTO collection VALUES (?,?,?,?,?,?,?,?)',
                           [(revision, i, *[item[k] for k in ['platform', 'location', 'access', 'status', 'scope', 'nextStep']])
                            for i, item in enumerate(clean.get('collection', []))])
        db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)',
                       [('current', revision), ('person', packet['person']['name'])])
        atomic_write(sheet, raw)
        replaced = True
        db.commit()
    except Exception:
        db.rollback()
        if replaced:
            if previous is None:
                sheet.unlink(missing_ok=True)
            else:
                atomic_write(sheet, previous)
        raise
    finally:
        db.close()
    return {'path': str(sheet), 'database': str(database), 'revision': revision, 'newRevision': new_revision,
            'accounts': len(clean['accounts']), 'sources': len(clean['sources']), 'artifacts': len(images)}


def search(database, query):
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError('Supply a search phrase of 1–500 characters')
    db = connect(database, readonly=True)
    try:
        current = db.execute("SELECT value FROM metadata WHERE key='current'").fetchone()
        if not current:
            raise ValueError('Archive has no saved revision; run build --update to recover')
        pattern = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        rows = db.execute('''SELECT 'account',id,title,content FROM accounts
            WHERE revision=? AND (title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')
            UNION ALL SELECT 'source',id,label,content FROM sources
            WHERE revision=? AND (label LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\') LIMIT 50''',
                          (current[0], pattern, pattern, current[0], pattern, pattern)).fetchall()
        return [{'kind': kind, 'id': key, 'title': title, 'content': content} for kind, key, title, content in rows]
    finally:
        db.close()


def export(database, output, revision=None):
    output = Path(output).expanduser().absolute()
    if output.suffix.lower() not in {'.html', '.htm'} or output.exists() or output.is_symlink():
        raise ValueError('Choose a new HTML output path')
    db = connect(database, readonly=True)
    try:
        if revision is None:
            current = db.execute("SELECT value FROM metadata WHERE key='current'").fetchone()
            revision = current[0] if current else None
        row = db.execute('SELECT html FROM revisions WHERE id=?', (revision,)).fetchone()
        if not row or hashlib.sha256(row[0]).hexdigest() != revision:
            raise ValueError('Missing or damaged archive revision')
        # Never execute the saved HTML. Verify its structured payload and images.
        packet = renderer.parse_packet(row[0].decode('utf-8'), is_html=True)
        renderer.validate(packet)
        for account in packet['accounts']:
            for artifact in account.get('artifacts', []):
                renderer.image_data(artifact, output.parent)
        with output.open('xb') as stream:
            stream.write(row[0])
        return {'path': str(output), 'revision': revision}
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('build', help='Create a database and the portable HTML from selected context')
    create.add_argument('input', type=Path)
    create.add_argument('workspace', type=Path)
    create.add_argument('--update', action='store_true')
    create.add_argument('--allow-remove-views', action='store_true')
    find = commands.add_parser('search', help='Search current accounts and selected source text locally')
    find.add_argument('database', type=Path)
    find.add_argument('query')
    save = commands.add_parser('export', help='Recover the current or a historical portable sheet')
    save.add_argument('database', type=Path)
    save.add_argument('output', type=Path)
    save.add_argument('--revision')
    args = parser.parse_args(argv)
    try:
        if args.command == 'build':
            result = build(args.input, args.workspace, update=args.update, allow_view_removal=args.allow_remove_views)
        elif args.command == 'search':
            result = search(args.database, args.query)
        else:
            result = export(args.database, args.output, args.revision)
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as error:
        parser.exit(2, f'Could not use the career archive: {error}\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
