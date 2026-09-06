#!/usr/bin/env python3
"""Evidence-plan checks for the documented Blender workflow.

This validates traceability and stale inputs, not the model's internal knowledge
or whether a cited passage semantically proves an arbitrary Python program.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

from features import find_card, load_catalog


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_plan(path):
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    catalog = load_catalog()
    if plan.get('schema_version') != 2 or plan.get('catalog_sha256') != catalog['catalog_sha256']:
        raise ValueError('Evidence plan is missing or belongs to a different capability catalog')
    ids = plan.get('selected_features', [])
    if not ids or not plan.get('request', '').strip():
        raise ValueError('Plan must select documented features for a concrete request')
    cards = [find_card(catalog, identifier) for identifier in ids]
    seeds = sorted({ref for card in cards for ref in card['next_queries'] + card.get('api_refs', [])})
    if plan.get('seed_refs') != seeds:
        raise ValueError('Plan seed references differ from selected feature data')
    return plan


def write_plan(path, plan):
    Path(path).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def merge_ranges(ranges):
    result = []
    for start, end in sorted(ranges):
        if result and start <= result[-1][1] + 1:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def record_read(path, ref, body, first, last, total, links):
    if not body.strip() or total < 1 or not 1 <= first <= last <= total:
        raise ValueError('No source lines displayed; read the full page or a nonempty anchor before recording evidence')
    plan = read_plan(path)
    receipts = plan.setdefault('reads', [])
    digest = sha256(body.encode('utf-8'))
    existing = next((r for r in receipts if r['ref'] == ref and r['source_text_sha256'] == digest), None)
    if existing is None:
        existing = {'ref': ref, 'source_text_sha256': digest, 'ranges': [], 'total_lines': total, 'links': links}
        receipts.append(existing)
    existing['ranges'] = merge_ranges(existing['ranges'] + [[first, last]])
    existing['complete'] = existing['ranges'] == [[1, total]]
    # Reseal after new reads or changed evidence. No script is implicitly approved.
    plan['script_sha256'] = None
    write_plan(path, plan)


def allowed_page(plan, page):
    targets = {ref.split('#')[0] for ref in plan['seed_refs']}
    for read in plan['reads']:
        targets.add(read['ref'].split('#')[0])
        if read.get('complete'):
            targets.update(read.get('links', []))
    return page in targets


def operation_lines(script):
    """Conservative review list for Blender/imported-object attribute operations.

    Every attribute expression is included except obvious standard-library module
    access. Alias/object types cannot be inferred completely from arbitrary Python;
    use general_python bindings for non-Blender helper lines with a reason.
    """
    tree = ast.parse(script)
    stdlib = set(getattr(sys, 'stdlib_module_names', ()))
    standard_names = set()
    blender_names = {'bpy', 'bmesh', 'mathutils', 'gpu', 'gpu_extras', 'bpy_extras', 'aud', 'blf', 'bl_math', 'imbuf', 'idprop', 'freestyle'}
    imported_blender = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.')[0]
                name = alias.asname or root
                if root in stdlib:
                    standard_names.add(name)
                if root in blender_names:
                    imported_blender.add(name)
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or '').split('.')[0]
            if root in stdlib:
                standard_names.update(alias.asname or alias.name for alias in node.names)
            if root in blender_names:
                imported_blender.update(alias.asname or alias.name for alias in node.names)
    known_blender = imported_blender | blender_names

    def uses_blender(expression):
        return any(isinstance(part, ast.Name) and part.id in known_blender for part in ast.walk(expression))

    # Conservatively propagate ordinary assignments/iteration over known Blender
    # objects. This deliberately over-approximates; arbitrary Python remains a
    # manual semantic review, including types of external function parameters.
    changed = True
    while changed:
        before = set(known_blender)
        for node in ast.walk(tree):
            targets, value = [], None
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                targets, value = [node.target], node.iter
            if value is not None and uses_blender(value):
                for target in targets:
                    if isinstance(target, (ast.Name, ast.Tuple, ast.List)):
                        known_blender.update(part.id for part in ast.walk(target) if isinstance(part, ast.Name))
        changed = before != known_blender
    needed, explicit = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            root = node
            while isinstance(root, (ast.Attribute, ast.Subscript, ast.Call)):
                root = root.func if isinstance(root, ast.Call) else root.value
            if isinstance(root, ast.Name) and root.id in standard_names and root.id not in known_blender:
                continue
            needed.add(node.lineno)
            if isinstance(root, ast.Name) and root.id in known_blender:
                explicit.add(node.lineno)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in known_blender or node.func.id in {'getattr', 'setattr', 'eval', 'exec', '__import__'}:
                needed.add(node.lineno)
                explicit.add(node.lineno)
    return sorted(needed), explicit


def validate(path, script_path, check_digest=True):
    from docs import connect, formatted_lines, resolve
    plan = read_plan(path)
    if plan.get('unresolved'):
        raise ValueError('insufficient_skill_evidence: unresolved facts remain: ' + json.dumps(plan['unresolved'], ensure_ascii=False))
    script_bytes = Path(script_path).read_bytes()
    if check_digest and plan.get('script_sha256') != sha256(script_bytes):
        raise ValueError('Script is unbound or changed since evidence review; bind and seal this exact file')
    needed, explicit = operation_lines(script_bytes.decode('utf-8'))
    covered = set()
    receipts = {item['ref']: item for item in plan.get('reads', []) if item.get('complete')}
    if not receipts:
        raise ValueError('No complete source reads recorded; use docs.py read --plan')
    if not any(ref.split('#')[0] in {s.split('#')[0] for s in plan['seed_refs']} for ref in receipts):
        raise ValueError('No selected feature entry point has been read')
    with connect() as db:
        catalog = load_catalog()
        # Refuse a catalog whose selected descriptions no longer match the API.
        for identifier in plan['selected_features']:
            card = find_card(catalog, identifier)
            facts = card.get('evidence', []) if 'page' not in card else [{'ref': card['page'], 'source_text_sha256': card['source_text_sha256']}]
            for fact in facts:
                page, anchor = resolve(db, fact['ref'])
                body = db.execute('SELECT body FROM pages WHERE path=?', (page,)).fetchone()['body']
                if anchor:
                    bounds = db.execute('SELECT start,end FROM anchors WHERE page=? AND anchor=?', (page, anchor)).fetchone()
                    if bounds is None:
                        raise ValueError('Catalog evidence anchor no longer exists: ' + fact['ref'])
                    body = body[bounds['start']:bounds['end']]
                if sha256(body.encode('utf-8')) != fact['source_text_sha256']:
                    raise ValueError('Selected catalog evidence differs from current source: ' + fact['ref'])
        for ref, item in receipts.items():
            page, anchor = resolve(db, ref)
            body = db.execute('SELECT body FROM pages WHERE path=?', (page,)).fetchone()['body']
            if anchor:
                bounds = db.execute('SELECT start,end FROM anchors WHERE page=? AND anchor=?', (page, anchor)).fetchone()
                if bounds is None:
                    raise ValueError('Evidence anchor no longer exists: ' + ref)
                body = body[bounds['start']:bounds['end']]
            if sha256(body.encode('utf-8')) != item['source_text_sha256']:
                raise ValueError('Source changed since read: ' + ref)
            total = len(formatted_lines(body))
            if not body.strip() or total < 1 or item.get('total_lines') != total or item.get('ranges') != [[1, total]]:
                raise ValueError('Complete evidence needs all nonempty source lines: ' + ref)
        for binding in plan.get('bindings', []):
            lines = binding.get('lines', [])
            if not lines or not all(isinstance(n, int) and n > 0 for n in lines) or not binding.get('reason', '').strip():
                raise ValueError('Bindings need positive line numbers and an explanation')
            if binding.get('basis') == 'general_python':
                if set(lines) & explicit:
                    raise ValueError('Explicit Blender/dynamic operations cannot be labeled general_python')
            elif binding.get('basis') == 'source':
                refs = binding.get('refs', [])
                if not refs or not all(ref in receipts for ref in refs):
                    raise ValueError('Binding cites source that has not been completely read')
            else:
                raise ValueError('Binding basis must be source or general_python; model_memory is rejected')
            covered.update(lines)
    if set(needed) - covered:
        raise ValueError('Operations without evidence bindings at lines: ' + ', '.join(map(str, sorted(set(needed) - covered))))
    return {'ok': True, 'selected_features': plan['selected_features'], 'source_reads': len(receipts),
            'reviewed_operation_lines': needed, 'script_sha256': sha256(script_bytes),
            'scope': 'Traceability, complete recorded reads and unchanged bytes; semantic relevance of each citation and runtime success still require review.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inspect'); p.add_argument('--script', type=Path, required=True)
    for name in ('seal', 'check'):
        p = sub.add_parser(name); p.add_argument('--script', type=Path, required=True); p.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inspect':
        needed, explicit = operation_lines(args.script.read_text())
        lines = args.script.read_text().splitlines()
        print(json.dumps({'review': [{'line': n, 'code': lines[n-1], 'requires_source': n in explicit,
                                     'classification': 'known_blender_or_dynamic' if n in explicit else 'unknown_object_type_review_required'} for n in needed],
                          'note': 'requires_source=false means type is unknown, not permission to classify a Blender operation as general_python.'}, ensure_ascii=False, indent=2))
        return 0
    result = validate(args.plan, args.script, check_digest=args.command == 'check')
    if args.command == 'seal':
        plan = read_plan(args.plan)
        plan['script_sha256'] = result['script_sha256']
        write_plan(args.plan, plan)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, FileNotFoundError, SyntaxError, json.JSONDecodeError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
