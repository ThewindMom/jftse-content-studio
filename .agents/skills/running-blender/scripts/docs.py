#!/usr/bin/env python3
"""Search/read the bundled Blender API offline. Python standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import posixpath
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'references/api'


def connect():
    db = sqlite3.connect((ROOT / 'api.sqlite3').as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def resolve(db, target):
    target = unquote(target)
    page, _, anchor = target.partition('#')
    for candidate in (page, page + '.html'):
        if db.execute('SELECT 1 FROM pages WHERE path=?', (candidate,)).fetchone():
            return candidate, anchor
    row = db.execute('SELECT uri FROM symbols WHERE name=? ORDER BY role LIMIT 1', (target,)).fetchone()
    if row:
        return resolve(db, row['uri'])
    raise ValueError(f'Page/symbol not found: {target}. Use search or symbol first.')


def verify():
    manifest = json.loads((ROOT / 'manifest.json').read_text())['files']
    failures = []
    with zipfile.ZipFile(ROOT / 'source-html.zip') as archive:
        if set(archive.namelist()) != {x['path'] for x in manifest}:
            failures.append('Archive file set differs from manifest')
        for entry in manifest:
            data = archive.read(entry['path'])
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                failures.append(entry['path'])
    with connect() as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            failures.append('SQLite integrity check failed')
        expected = json.loads((ROOT / 'coverage.json').read_text())
        if db.execute('SELECT count(*) FROM pages').fetchone()[0] != expected['html_pages']:
            failures.append('HTML page count mismatch')
        if db.execute('SELECT count(*) FROM symbols').fetchone()[0] != expected['inventory_entries']:
            failures.append('Inventory count mismatch')
    print(json.dumps({'ok': not failures, 'verified_source_files': len(manifest), 'failures': failures}, indent=2))
    return bool(failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('search', help='Full-text search with ranked page excerpts')
    p.add_argument('query')
    p.add_argument('--limit', type=int, default=8)
    p.add_argument('--any', action='store_true', help='Match any query term instead of all')
    p.add_argument('--category', help='Filter by category from stats')
    p.add_argument('--plan', type=Path, help='Task evidence plan selected from pre-query catalog')
    p = sub.add_parser('symbol', help='Find exact names, then prefixes, then substrings')
    p.add_argument('query')
    p.add_argument('--limit', type=int, default=20)
    p.add_argument('--plan', type=Path)
    p = sub.add_parser('read', help='Read a page, page#anchor, or exact symbol')
    p.add_argument('target')
    p.add_argument('--start', type=int, default=1, help='First line within the selected page/anchor')
    p.add_argument('--lines', type=int, default=160)
    p.add_argument('--plan', type=Path, help='Record actual displayed source lines in this evidence plan')
    p = sub.add_parser('related', help='Follow local links in a main article')
    p.add_argument('target')
    p.add_argument('--limit', type=int, default=80)
    p.add_argument('--plan', type=Path)
    p = sub.add_parser('source', help='Read an original UTF-8 source member; never executes it')
    p.add_argument('path')
    p.add_argument('--start', type=int, default=1)
    p.add_argument('--lines', type=int, default=120)
    sub.add_parser('stats')
    sub.add_parser('verify', help='Hash every archived source file and check database integrity')
    args = parser.parse_args()
    if hasattr(args, 'limit') and not 1 <= args.limit <= 1000:
        parser.error('--limit must be between 1 and 1000')
    if hasattr(args, 'lines') and (args.lines < 1 or args.start < 1):
        parser.error('--start and --lines must be positive')
    if args.command == 'verify':
        return verify()
    if args.command == 'source':
        with zipfile.ZipFile(ROOT / 'source-html.zip') as archive:
            body = archive.read(args.path).decode('utf-8')
        show_lines(args.path, body, args.start, args.lines)
        return 0
    plan = None
    if getattr(args, 'plan', None):
        from evidence import read_plan
        plan = read_plan(args.plan)
    with connect() as db:
        if args.command == 'stats':
            print(db.execute("SELECT value FROM metadata WHERE key='coverage'").fetchone()[0])
        elif args.command == 'search':
            tokens = re.findall(r'[\w.]+', args.query, flags=re.UNICODE)
            if not tokens:
                raise ValueError('Query needs at least one word')
            query = (' OR ' if args.any else ' AND ').join('"' + x + '"' for x in tokens)
            rows = db.execute('''SELECT pages.path,pages.title,pages.category,
                snippet(search,2,'[',']',' … ',36) AS excerpt,bm25(search,0,8,1) AS rank
                FROM search JOIN pages ON pages.rowid=search.rowid
                WHERE search MATCH ? AND (? IS NULL OR pages.category=?) ORDER BY rank LIMIT ?''',
                (query, args.category, args.category, args.limit)).fetchall()
            for row in rows:
                excerpt = re.sub(r'\s+', ' ', row['excerpt']).strip()
                print(f"{row['path']} | {row['title']} [{row['category']}]\n{excerpt}\n")
            if not rows:
                print('No results. Try fewer English API terms, --any, or symbol.')
        elif args.command == 'symbol':
            escaped = args.query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            rows = db.execute('''SELECT name,role,uri FROM symbols WHERE name LIKE ? ESCAPE '\\'
                ORDER BY CASE WHEN name=? COLLATE NOCASE THEN 0 WHEN name LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END,length(name),name LIMIT ?''',
                ('%' + escaped + '%', args.query, escaped + '%', args.limit)).fetchall()
            for row in rows:
                print(f"{row['name']} [{row['role']}] -> {row['uri']}")
            if not rows:
                print('No symbols found. Try a shorter name or search descriptive terms.')
        elif args.command == 'read':
            page, anchor = resolve(db, args.target)
            if plan:
                from evidence import allowed_page
                if not allowed_page(plan, page):
                    raise ValueError('Page is outside selected features and previously read links. Select an evidence-backed feature/card or follow a documented link first.')
            row = db.execute('SELECT title,body FROM pages WHERE path=?', (page,)).fetchone()
            body = row['body']
            if anchor:
                bounds = db.execute('SELECT start,end FROM anchors WHERE page=? AND anchor=?', (page, anchor)).fetchone()
                if not bounds:
                    raise ValueError(f'Anchor not found: {page}#{anchor}')
                body = body[bounds['start']:bounds['end']]
            label = page + ('#' + anchor if anchor else '')
            total, last = show_lines(label, body, args.start, args.lines)
            if plan:
                from evidence import record_read
                links = set()
                for href in re.findall(r'<([^<>]+)>', body):
                    parsed = urlsplit(href)
                    if not parsed.scheme and not parsed.netloc:
                        linked = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(parsed.path))) if parsed.path else page
                        if db.execute('SELECT 1 FROM pages WHERE path=?', (linked,)).fetchone():
                            links.add(linked)
                record_read(args.plan, label, body, args.start, last, total, sorted(links))
                print('Evidence read recorded in: ' + str(args.plan))
        elif args.command == 'related':
            page, anchor = resolve(db, args.target)
            rows = db.execute('SELECT href,available FROM links WHERE page=? ORDER BY available DESC,href LIMIT ?', (page, args.limit + 1)).fetchall()
            for row in rows[:args.limit]:
                print(('LOCAL ' if row['available'] else 'MISSING ') + row['href'])
            if len(rows) > args.limit:
                print(f'More links available; increase --limit (current {args.limit}).')
    return 0


def formatted_lines(body):
    lines, in_code = [], False
    for line in body.splitlines():
        if line.strip() == '```':
            in_code = not in_code
        if not in_code:
            line = line.rstrip()
            if not line and (not lines or not lines[-1]):
                continue
        lines.append(line)
    return lines


def show_lines(label, body, start, count):
    lines = formatted_lines(body)
    end = min(start + count - 1, len(lines))
    print(f'SOURCE: {label} | lines {start}-{end} of {len(lines)}')
    for number, line in enumerate(lines[start - 1:end], start):
        print(f'{number:5d} {line}')
    if end < len(lines):
        print(f'CONTINUES: --start {end + 1} --lines {count}')
    return len(lines), end


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, sqlite3.Error, UnicodeDecodeError, FileNotFoundError, zipfile.BadZipFile) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(2)
