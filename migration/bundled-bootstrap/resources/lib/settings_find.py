"""Search Settings, pure logic (no Kodi): how a typed query matches a setting, the match in bold, and the
"Section › Category" line under each result. settings_search.py (the page) and settings_search.py (the index) use it.

Matching ignores case and accents. A query matches when every word of it appears in the setting's label or in its
breadcrumb; a match in the label ranks first. Owner-approved mockup: docs/design/settings-pages-mockups.html, board 11."""
import unicodedata

CRUMB = ' › '   # between a section and its category: "Player › Subtitles"
BOLD = ('[B]', '[/B]')
LIMIT = 60


def crumb(*parts):
    """'Player › Subtitles' from the parts that are not empty."""
    return CRUMB.join(str(p).strip() for p in parts if p and str(p).strip())


def fold(text):
    """(folded, owner): the text in lower case without accents, and owner[k] = the index in text of folded character k,
    so a match in the folded text can be shown in the original."""
    chars, owner = [], []
    for i, c in enumerate(str(text or '')):
        for f in unicodedata.normalize('NFKD', c).lower():
            if not unicodedata.combining(f):
                chars.append(f)
                owner.append(i)
    return ''.join(chars), owner


def words(query):
    """The words typed, folded: '  Subtit ' -> ['subtit']."""
    return fold(' '.join(str(query or '').split()))[0].split()


def merge(spans):
    """Overlapping or touching (start, end) spans joined, in order."""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def bold(label, query):
    """The label with [B]..[/B] round each part that matches a word of the query (case and accents ignored)."""
    text = str(label or '')
    folded, owner = fold(text)
    spans = []
    for word in words(query):
        at = folded.find(word)
        while at >= 0:
            spans.append((owner[at], owner[at + len(word) - 1] + 1))
            at = folded.find(word, at + len(word))
    out, pos = '', 0
    for start, end in merge(spans):
        out += text[pos:start] + BOLD[0] + text[start:end] + BOLD[1]
        pos = end
    return out + text[pos:]


def search(entries, query, limit=LIMIT):
    """Entries (label, breadcrumb, action) that match the query: label matches first, each entry once."""
    wanted = words(query)
    if not wanted:
        return []
    first, second, seen = [], [], set()
    for label, where, action in entries:
        name, place = fold(label)[0], fold(where)[0]
        if (name, place) in seen:
            continue
        if all(w in name + ' ' + place for w in wanted):
            seen.add((name, place))
            (first if all(w in name for w in wanted) else second).append((label, where, action))
    return (first + second)[:limit]
