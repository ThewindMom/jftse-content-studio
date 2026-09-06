#!/usr/bin/env python3
"""Read pre-query Blender capability data. Never imports sqlite3 or opens the API DB."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

SKILL = Path(__file__).resolve().parents[1]
CATALOG = SKILL/'references/catalog/catalog.json'


def normalize(text):
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text).lower().replace('đ', 'd')
    text = ''.join(char for char in unicodedata.normalize('NFD', text) if unicodedata.category(char) != 'Mn')
    return ' '.join(re.findall(r'\w+', text))


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def find_card(catalog, identifier):
    for card in catalog['routes'] + catalog['pages']:
        if card['id'] == identifier:
            return card
    raise ValueError('Unknown feature/card. Read overview or match first: ' + identifier)


def match(catalog, query, limit=10):
    q = normalize(query)
    words = set(q.split())
    ranked = []
    for route in catalog['routes']:
        aliases = list(route['intent_aliases']) + [route['label_vi'], route['label_en']]
        matched, score = [], 0.0
        for alias in aliases:
            norm = normalize(alias)
            alias_words = set(norm.split())
            if not alias_words:
                continue
            overlap = len(words & alias_words)
            exact_phrase = (' ' + norm + ' ') in (' ' + q + ' ')
            if exact_phrase:
                matched.append(alias)
                score = max(score, 10 + len(alias_words))
            elif overlap >= 2 and overlap == len(alias_words):
                # Reordered words are acceptable; omitted feature words are not.
                # E.g. 'vật thể' alone must not match the alias 'mask vật thể'.
                matched.append(alias)
                score = max(score, overlap / len(alias_words) + overlap / max(1,len(words)))
        if score:
            ranked.append((score, {'id': route['id'], 'label': route['label_en'], 'summary': route['summary'],
                           'matched_aliases': matched, 'choose_when': route['choose_when'], 'status': route['status']}))
    ranked.sort(key=lambda item: (-item[0], item[1]['id']))
    return [item[1] for item in ranked[:limit]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('overview')
    p=sub.add_parser('match'); p.add_argument('request'); p.add_argument('--limit', type=int, default=10)
    p=sub.add_parser('show'); p.add_argument('id')
    p=sub.add_parser('pages'); p.add_argument('domain'); p.add_argument('--offset',type=int,default=0); p.add_argument('--limit',type=int,default=35)
    p=sub.add_parser('symbols'); p.add_argument('query'); p.add_argument('--limit',type=int,default=25)
    p=sub.add_parser('plan'); p.add_argument('--request',required=True); p.add_argument('--feature',action='append',required=True); p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if hasattr(args,'limit') and not 1 <= args.limit <= 1000:
        parser.error('--limit must be 1..1000')
    if hasattr(args,'offset') and args.offset < 0:
        parser.error('--offset must be non-negative')
    catalog=load_catalog()
    if args.command=='overview':
        print((SKILL/'references/catalog/overview.md').read_text())
    elif args.command=='match':
        candidates=match(catalog,args.request,args.limit)
        print(json.dumps({'status':'candidates_require_reading' if candidates else 'insufficient_skill_evidence',
                          'candidates':candidates,'next':'Read chosen feature cards; if ambiguous clarify desired output. Never invent an API or fallback from model memory.'},ensure_ascii=False,indent=2))
    elif args.command=='show':
        print(json.dumps(find_card(catalog,args.id),ensure_ascii=False,indent=2))
    elif args.command=='pages':
        domain=next((d for d in catalog['domains'] if d['id']==args.domain),None)
        if not domain:
            raise ValueError('Unknown domain; read overview')
        cards=[c for c in catalog['pages'] if args.domain in c['domains']]
        selected=cards[args.offset:args.offset+args.limit]
        print(json.dumps({'domain':args.domain,'total':len(cards),'cards':selected,
                          'next_offset':args.offset+len(selected) if args.offset+len(selected)<len(cards) else None},ensure_ascii=False,indent=2))
    elif args.command=='symbols':
        # Discover source identifiers outside SQLite. No semantic expansion.
        query=args.query.casefold()
        data=json.loads((SKILL/'references/catalog/symbols.json').read_text())
        rows=[s for s in data['symbols'] if query in s['name'].casefold()]
        rows.sort(key=lambda s:(s['name'].casefold()!=query,len(s['name']),s['name']))
        print(json.dumps({'matches':rows[:args.limit],'total':len(rows),'meaning':'Identifier discovery only; read the source before claiming behavior.'},ensure_ascii=False,indent=2))
    elif args.command=='plan':
        if args.output.exists():
            raise ValueError('Plan already exists; choose a new path or edit it deliberately')
        cards=[find_card(catalog,identifier) for identifier in dict.fromkeys(args.feature)]
        seeds=sorted({ref for card in cards for ref in card['next_queries']+card.get('api_refs',[])})
        plan={'schema_version':2,'request':args.request,'catalog_sha256':catalog['catalog_sha256'],
              'selected_features':[c['id'] for c in cards], 'seed_refs':seeds,'reads':[],
              'script_sha256':None,'bindings':[],'unresolved':[],
              'evidence_policy':'Blender facts must come from bundled source or recorded runtime inspection. Pretrained Blender knowledge is not admissible.',
              'review_note':'Select source refs and read them with docs.py --plan before implementing. Each Blender-specific statement must have a supporting source; source IDs alone do not prove semantic support.'}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'plan':str(args.output.resolve()),'selected_features':plan['selected_features'],'read_next':seeds},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,KeyError,FileNotFoundError,json.JSONDecodeError) as exc:
        print('Error: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
