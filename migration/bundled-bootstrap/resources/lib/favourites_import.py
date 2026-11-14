"""Import a list of favourite titles (copied from Notes, or a text file) and keep it as the Favourites list.

Owner-approved mockup boards H-J (docs/design/favourites-import-bell-mockups.html). Pure logic: Kodi, the network and the
screen are in favourites_import_page.py and favourites_match.py.

What a list line gives us is only the NAME. A list like
    1. Naruto //shippuden
    2. bleach  [camera] [tick] [!!]
    4. aot (3) [tick]  RYANNE
    6. Beserk (STARTED)
is read as: rank = the number, titles = the names, watch count = a bare number in brackets, everything else (ticks, emoji,
"(STARTED)", an all-capitals name after the title) is skipped. A key above "1." is skipped. "//" splits one line into several
titles ("dragon ball//Z//super" is Dragon Ball, Dragon Ball Z, Dragon Ball super). If a paste lost its line breaks, numbers
still split it.
"""
import json
import os
import re
import time

FILE = 'imported-favourites.json'
SORTS = (('list', 'List order', 'The order of your imported list'),
         ('year', 'Year', 'Newest first'),
         ('name', 'Name', 'A to Z'),
         ('imported', 'List', 'Grouped by the list it came from'),
         ('added', 'Date added', 'Latest first'))
SORT_KEYS = tuple(s[0] for s in SORTS)
MAX_LINES = 1000

_NUMBERED = re.compile(r'(?:(?<=\s)|^)(\d{1,4})[.)]\s+')
# Emoji, pictographs, dingbats, arrows, variation selectors and the zero-width joiner: markers, never part of a name.
_MARK_RANGES = ((0x203c, 0x2049), (0x2190, 0x21ff), (0x2300, 0x23ff), (0x2460, 0x27bf), (0x2900, 0x297f), (0x2b00, 0x2bff),
                (0x3030, 0x3030), (0x303d, 0x303d), (0x3297, 0x3297), (0x3299, 0x3299), (0xfe00, 0xfe0f), (0x200d, 0x200d),
                (0x20e3, 0x20e3), (0x1f000, 0x1faff), (0xe0000, 0xe007f))
_MARKS = re.compile('[' + ''.join('%s-%s' % (chr(lo), chr(hi)) for lo, hi in _MARK_RANGES) + ']')
_BRACKET = re.compile(r'[(\[{]([^)\]}]*)[)\]}]')
_YEAR = re.compile(r'^(19|20)\d\d$')
_ALLCAPS = re.compile(r'^[A-Z]{4,}$')


def key_of(title):
    """What makes two titles the same title: lower-case letters and digits only."""
    return re.sub(r'[^a-z0-9]+', '', str(title).lower())


def _split_numbered(text):
    """[(rank, text)] for each numbered entry in order; whatever comes before the first number (the key) is dropped."""
    found = list(_NUMBERED.finditer(text))
    out = []
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out.append((int(m.group(1)), text[m.end():end].strip()))
    return out


def _lines(raw):
    text = str(raw or '').replace('\r\n', '\n').replace('\r', '\n').replace('\u2028', '\n')
    lines = [line.strip() for line in text.split('\n')]
    numbered = [line for line in lines if _NUMBERED.match(line)]
    if len(numbered) >= 2 or (len(lines) <= 3 and len(_NUMBERED.findall(text)) >= 2):
        # Numbered list: one entry per number, so a wrapped line or a paste without line breaks still splits right.
        return _split_numbered(' '.join(l for l in lines if l))
    # Plain list: one title per non-empty line, ranked by position.
    return [(i + 1, _NUMBERED.sub('', line, count=1)) for i, line in enumerate(l for l in lines if l)]


def read_line(text):
    """(titles, watched, year) for one entry's text; titles is [] when nothing but markers is left."""
    watched, year = 0, ''

    def bracket(m):
        nonlocal watched, year
        inner = m.group(1).strip()
        if inner.isdigit() and len(inner) <= 2:
            watched = int(inner)
        elif _YEAR.match(inner):
            year = inner
        return ' '          # (STARTED), (new) and any other note in brackets

    text = _MARKS.sub(' ', text)
    text = _BRACKET.sub(bracket, text)
    text = re.sub(r'[\u2022\u25cf*_]+|^\s*[-\u2013\u2014]\s+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip(' \t-\u2013\u2014:;,')
    words = text.split(' ')
    # A name written in capitals after the title ("aot RYANNE") is a note to yourself, not part of it.
    if len(words) >= 2 and _ALLCAPS.match(words[-1]) and any(any(c.islower() for c in w) for w in words[:-1]):
        words = words[:-1]
    text = ' '.join(words).strip()
    if not any(c.isalnum() for c in text):
        return [], watched, year
    parts = [p.strip() for p in re.split(r'\s*//+\s*', text) if p.strip()]
    if not parts:
        return [], watched, year
    base, titles = parts[0], [parts[0]]
    first = base.split(' ')[0].lower()
    for part in parts[1:]:
        titles.append(part if part.lower().startswith(first) else '%s %s' % (base, part))
    return titles, watched, year


def parse(raw):
    """Read a pasted list. Returns {'entries': [...], 'duplicates': [...], 'lines': n}.

    entries: [{'rank', 'title', 'watched', 'year', 'line'}] in list order, each title once (first line wins; its rank is
    the position it first appears at). duplicates: [{'title', 'lines': [..]}] for titles that appeared more than once."""
    entries, seen, dup_lines = [], {}, {}
    rows = _lines(raw)[:MAX_LINES]
    for line_no, (number, text) in enumerate(rows, 1):
        titles, watched, year = read_line(text)
        for title in titles:
            k = key_of(title)
            if not k:
                continue
            if k in seen:
                dup_lines.setdefault(k, [seen[k]['line']]).append(number)
                continue
            entry = {'rank': len(entries) + 1, 'title': title, 'watched': watched, 'year': year, 'line': number}
            seen[k] = entry
            entries.append(entry)
    duplicates = [{'title': seen[k]['title'], 'lines': sorted(set(lines))} for k, lines in dup_lines.items()]
    duplicates.sort(key=lambda d: d['lines'][0])
    return {'entries': entries, 'duplicates': duplicates, 'lines': len(rows)}


# --- the saved list -------------------------------------------------------------------------------------------------

def path(profile):
    return os.path.join(profile, 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get('items'), list):
            return data
    except (OSError, ValueError):
        pass
    return {'items': [], 'sort': 'list'}


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, indent=1)
    os.replace(tmp, target)


def item_key(item):
    return '%s:%s' % (item.get('kind', ''), item.get('tmdb', ''))


def add(profile, matched, list_name='', now=None):
    """Add matched titles [{'kind' ('movie'|'tv'), 'tmdb', 'title', 'year', 'poster', 'rank', 'watched'}] to the saved list.
    A title already saved keeps its place and is reported back as a duplicate. Returns (added, already)."""
    now = time.time() if now is None else now
    data = load(profile)
    have = {item_key(i): i for i in data['items']}
    added, already = [], []
    base = max([i.get('rank', 0) for i in data['items']] or [0])
    # A second import continues the numbering, so list order stays the order of the lists as imported.
    for m in sorted(matched, key=lambda m: m.get('rank', 0)):
        k = item_key(m)
        if k in have:
            if m.get('watched') and not have[k].get('watched'):
                have[k]['watched'] = m['watched']
            already.append(m)
            continue
        item = {'kind': m['kind'], 'tmdb': str(m['tmdb']), 'title': m.get('title', ''), 'year': str(m.get('year') or ''),
                'poster': m.get('poster', ''), 'rank': base + len(added) + 1, 'list': list_name, 'added': now,
                'watched': int(m.get('watched') or 0)}
        data['items'].append(item)
        have[item_key(item)] = item
        added.append(item)
    save(profile, data)
    return added, already


def remove(profile, item):
    data = load(profile)
    data['items'] = [i for i in data['items'] if item_key(i) != item_key(item)]
    save(profile, data)


def set_sort(profile, sort_key):
    if sort_key in SORT_KEYS:
        data = load(profile)
        data['sort'] = sort_key
        save(profile, data)


def ordered(items, sort_key='list'):
    """items in the order a sort key asks for. Ties keep list order, so a sort never shuffles equal titles."""
    by_rank = sorted(items, key=lambda i: (i.get('rank', 0), i.get('added', 0)))
    if sort_key == 'year':
        return sorted(by_rank, key=lambda i: str(i.get('year') or '0000'), reverse=True)
    if sort_key == 'name':
        return sorted(by_rank, key=lambda i: re.sub(r'^(the|a|an)\s+', '', str(i.get('title', '')).lower()))
    if sort_key == 'added':
        return sorted(by_rank, key=lambda i: -float(i.get('added') or 0))
    if sort_key == 'imported':
        names = []
        for i in by_rank:
            if i.get('list', '') not in names:
                names.append(i.get('list', ''))
        return sorted(by_rank, key=lambda i: names.index(i.get('list', '')))
    return by_rank


def sort_label(sort_key):
    return dict((k, label) for k, label, _ in SORTS).get(sort_key, 'List order')


def default_list_name(now=None):
    return 'Notes list ' + time.strftime('%d %b', time.localtime(time.time() if now is None else now))
