#!/usr/bin/env python3
"""Rebuild the offline corpus from a local Sphinx HTML tree (requires lxml).

Every regular source file is preserved byte-for-byte in source-html.zip.
HTML is parsed as data; JavaScript, doctrees, pickles and examples are not run.
"""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sqlite3
from urllib.parse import unquote, urlsplit
import zipfile
import zlib

from lxml import html


def local_target(page, href):
    u = urlsplit(href)
    if u.scheme or u.netloc:
        return None
    path = posixpath.normpath(posixpath.join(posixpath.dirname(page), unquote(u.path))) if u.path else page
    if path.startswith('../') or path.startswith('/'):
        return None
    return path, unquote(u.fragment)


class Render:
    """Readable text retaining code, table cells, links, and precise ID ranges."""
    def __init__(self):
        self.parts, self.offset, self.anchors = [], 0, {}

    def emit(self, text):
        self.parts.append(text)
        self.offset += len(text)

    def node(self, el):
        tag = el.tag if isinstance(el.tag, str) else ''
        if tag in {'script', 'style'} or 'headerlink' in el.get('class', '').split():
            return
        ident = el.get('id')
        start = self.offset
        if tag == 'pre':
            self.emit('\n\n```\n' + ''.join(el.itertext()).rstrip('\n') + '\n```\n\n')
        else:
            if re.fullmatch(r'h[1-6]', tag):
                self.emit('\n\n' + '#' * int(tag[1]) + ' ')
            elif tag in {'p', 'div', 'dl', 'dt', 'dd', 'ul', 'ol', 'table', 'section', 'blockquote'}:
                self.emit('\n')
            elif tag == 'li':
                self.emit('\n- ')
            elif tag == 'tr':
                self.emit('\n| ')
            elif tag == 'br':
                self.emit('\n')
            if el.text:
                self.emit(re.sub(r'\s+', ' ', el.text))
            for child in el:
                self.node(child)
                if child.tail:
                    self.emit(re.sub(r'\s+', ' ', child.tail))
            if tag == 'a' and el.get('href') and ''.join(el.itertext()).strip():
                self.emit(' <' + el.get('href') + '>')
            if tag in {'td', 'th'}:
                self.emit(' | ')
            elif tag in {'p', 'div', 'dl', 'dd', 'li', 'table', 'section', 'blockquote', 'dt'} or re.fullmatch(r'h[1-6]', tag):
                self.emit('\n')
        if ident:
            self.anchors[ident] = [start, self.offset]
        # A Sphinx API signature's definition is its following dd sibling.
        if tag == 'dd':
            prev = el.getprevious()
            while prev is not None and prev.tag == 'dt':
                if prev.get('id') in self.anchors:
                    self.anchors[prev.get('id')][1] = self.offset
                prev = prev.getprevious()


def inventory(raw):
    header = raw.split(b'\n', 4)
    if len(header) != 5 or b'inventory version 2' not in header[0]:
        raise ValueError('Expected Sphinx inventory version 2')
    rows = []
    for line in zlib.decompress(header[4]).decode('utf-8').splitlines():
        name, role, priority, uri, display = line.split(' ', 4)
        if uri.endswith('$'):
            uri = uri[:-1] + name
        rows.append((name, role, uri, display))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'references/api')
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    if source == out or source in out.parents:
        parser.error('Output must be outside the source tree')
    if not (source / 'index.html').is_file():
        parser.error('Source must contain index.html')
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in source.rglob('*')):
        parser.error('Source symlinks are not supported; supply a regular extracted tree')
    names = {p.relative_to(source).as_posix() for p in files}
    html_names = {p for p in names if p.endswith('.html')}
    records = []
    print(f'Archiving and hashing {len(files)} files...', flush=True)
    with zipfile.ZipFile(out / 'source-html.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            rel = path.relative_to(source).as_posix()
            data = path.read_bytes()
            item = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data, compresslevel=9)
            records.append({'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    db_path = out / 'api.sqlite3'
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript('''
        CREATE TABLE pages(path TEXT PRIMARY KEY, title TEXT, body TEXT, category TEXT);
        CREATE TABLE anchors(page TEXT, anchor TEXT, start INTEGER, end INTEGER, PRIMARY KEY(page,anchor));
        CREATE TABLE links(page TEXT, href TEXT, target TEXT, anchor TEXT, available INTEGER, PRIMARY KEY(page,href));
        CREATE TABLE symbols(name TEXT, role TEXT, uri TEXT, display TEXT);
        CREATE INDEX symbols_name ON symbols(name COLLATE NOCASE);
        CREATE VIRTUAL TABLE search USING fts5(path UNINDEXED,title,body,content='pages',content_rowid='rowid');
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
    ''')
    queue, seen, reachable = deque(['index.html']), set(), set()
    missing = {}
    external = set()
    empty = []
    category_counts = Counter()
    while queue or html_names - seen:
        if not queue:
            queue.append(sorted(html_names - seen)[0])
        page = queue.popleft()
        if page in seen:
            continue
        seen.add(page)
        tree = html.fromstring((source / page).read_bytes())
        # Crawl the whole HTML, including navigation, starting from index.html.
        for href in set(tree.xpath('//@href | //@src')):
            target = local_target(page, href)
            if target:
                dest, anchor = target
                if dest in html_names and dest not in seen:
                    queue.append(dest)
                    if page == 'index.html' or page in reachable:
                        reachable.add(dest)
                if dest not in names:
                    missing.setdefault(dest, set()).add(page)
            else:
                external.add(href)
        articles = tree.xpath('//article[@role="main"]')
        if not articles:
            raise ValueError(f'No main article: {page}')
        article = articles[0]
        render = Render()
        render.node(article)
        body = ''.join(render.parts)
        if not body.strip():
            empty.append(page)
        heading = article.xpath('.//h1')
        title = ''.join(heading[0].itertext()).replace('¶', '').strip() if heading else ''.join(tree.xpath('//title/text()'))
        if page.startswith('bpy.types.'):
            category = 'bpy.types'
        elif page.startswith('bpy.ops.'):
            category = 'bpy.ops'
        elif page.startswith('bpy_types_enum_items/'):
            category = 'enum-items'
        elif page.startswith('info_'):
            category = 'guides'
        elif page.startswith('genindex') or page in {'index.html', 'py-modindex.html', 'search.html'}:
            category = 'indices'
        else:
            category = 'modules'
        category_counts[category] += 1
        con.execute('INSERT INTO pages VALUES(?,?,?,?)', (page, title, body, category))
        con.executemany('INSERT INTO anchors VALUES(?,?,?,?)', [(page, key, *bounds) for key, bounds in render.anchors.items()])
        for href in set(article.xpath('.//@href | .//@src')):
            target = local_target(page, href)
            if target:
                dest, anchor = target
                con.execute('INSERT INTO links VALUES(?,?,?,?,?)', (page, href, dest, anchor, int(dest in names)))
        if len(seen) % 250 == 0:
            print(f'Indexed {len(seen)}/{len(html_names)} HTML pages', flush=True)
    inventory_raw = (source / 'objects.inv').read_bytes()
    inventory_header = [line.decode('utf-8') for line in inventory_raw.split(b'\n', 4)[:4]]
    symbols = inventory(inventory_raw)
    con.executemany('INSERT INTO symbols VALUES(?,?,?,?)', symbols)
    con.execute("INSERT INTO search(search) VALUES('rebuild')")
    con.commit()
    bad_symbols = []
    for name, role, uri, display in symbols:
        target = local_target('index.html', uri)
        if target:
            dest, anchor = target
            if dest not in names or (anchor and dest in html_names and not con.execute('SELECT 1 FROM anchors WHERE page=? AND anchor=?', (dest, anchor)).fetchone()):
                bad_symbols.append({'name': name, 'role': role, 'uri': uri})
    overview = con.execute("SELECT body FROM pages WHERE path='index.html'").fetchone()[0]
    version_match = re.search(r'Blender ([\d.]+) Python API Documentation', overview)
    version = version_match.group(1) if version_match else 'unknown'
    report = {
        'schema_version': 1,
        'documentation_version': version,
        'inventory_header': inventory_header,
        'source_label': source.name,
        'source_index': 'index.html',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source_files': len(files),
        'source_bytes': sum(x['bytes'] for x in records),
        'html_pages': len(html_names),
        'indexed_pages': len(seen),
        'reachable_html_from_index': len(reachable | {'index.html'}),
        'orphan_html_pages': sorted(html_names - reachable - {'index.html'}),
        'empty_main_articles': empty,
        'categories': dict(sorted(category_counts.items())),
        'inventory_entries': len(symbols),
        'inventory_roles': dict(sorted(Counter(x[1] for x in symbols).items())),
        'indexed_anchors': con.execute('SELECT count(*) FROM anchors').fetchone()[0],
        'extracted_characters': con.execute('SELECT sum(length(body)) FROM pages').fetchone()[0],
        'unresolved_inventory_targets': bad_symbols,
        'missing_local_targets': [{'target': k, 'referring_pages': len(v), 'examples': sorted(v)[:3]} for k, v in sorted(missing.items())],
        'external_link_count': len(external),
        'scope': 'All files in the supplied offline Python API snapshot. External websites are not recursively downloaded. Presence in docs does not prove background-mode or runtime support.',
    }
    con.execute('INSERT INTO metadata VALUES(?,?)', ('coverage', json.dumps(report, ensure_ascii=False)))
    con.commit()
    con.execute('VACUUM')
    con.close()
    (out / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'files': records}, ensure_ascii=False, indent=2) + '\n')
    (out / 'coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (out / 'external-links.txt').write_text('\n'.join(sorted(external)) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in {'unresolved_inventory_targets', 'missing_local_targets'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
