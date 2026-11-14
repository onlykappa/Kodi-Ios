"""Match imported names to TMDb titles (the id TMDb Helper uses). Pure logic: `search` is injected (favourites_import_page.py
passes a TMDb /search/multi call made with TMDb Helper's own API key, as the episode checks do).

A name is one of three things, and the report says which:
  match    exactly one good title. It is added.
  question several plausible titles, or a misspelling that is close to something ("one peice"). The person picks one.
  missing  nothing plausible. The person can search by hand or skip.
"""
import difflib
import re

SURE = 0.92          # a title this close to the name, and clearly the best, is taken without asking
PLAUSIBLE = 0.55     # below this a result is not offered at all
MAX_CHOICES = 4


def norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()


def _name(result):
    return result.get('title') or result.get('name') or ''


def _year(result):
    return str(result.get('release_date') or result.get('first_air_date') or '')[:4]


def candidate(result):
    """The fields the app keeps for a TMDb result, or None when it is not a movie or a show."""
    kind = result.get('media_type') or ''
    if kind not in ('movie', 'tv') or not result.get('id'):
        return None
    return {'kind': kind, 'tmdb': str(result['id']), 'title': _name(result), 'year': _year(result),
            'poster': result.get('poster_path') or '', 'popularity': float(result.get('popularity') or 0)}


def score(query, result):
    """0..1, how close the result's titles are to the name asked for."""
    q = norm(query)
    best = 0.0
    for title in (_name(result), result.get('original_title') or result.get('original_name') or ''):
        t = norm(title)
        if not t:
            continue
        if t == q:
            return 1.0
        # An abbreviation of the title's words: "aot" is Attack on Titan, "mha" My Hero Academia.
        words = t.split()
        if len(q) >= 3 and ' ' not in q and len(words) >= 3 and q == ''.join(w[0] for w in words):
            best = max(best, 0.93)
            continue
        ratio = difflib.SequenceMatcher(None, q, t).ratio()
        # "heavenly delusion" asked for, "Heavenly Delusion" found with a subtitle: a whole-word prefix is close too.
        if t.startswith(q + ' ') or q.startswith(t + ' '):
            ratio = max(ratio, 0.9)
        best = max(best, ratio)
    return best


def _rank(query, results, year=''):
    scored = []
    for result in results or []:
        c = candidate(result)
        if not c:
            continue
        s = score(query, result)
        if s < PLAUSIBLE:
            continue
        if year and c['year'] == year:
            s = min(1.0, s + 0.05)
        c['score'] = round(s, 3)
        scored.append(c)
    # A TV show before a film of the same name only when popularity says so; otherwise the more popular title first.
    scored.sort(key=lambda c: (-c['score'], -c['popularity']))
    return scored


def resolve(name, search, year=''):
    """('match', candidate) | ('question', [candidates]) | ('missing', None) for one name."""
    queries = [name]
    words = name.split()
    if len(words) >= 3:
        queries.append(' '.join(words[:-1]))      # a stray trailing word ("heavenly delusion ng")
    ranked, found = [], []
    for query in queries:
        results = search(query)
        found = found or results
        ranked = _rank(query, results, year)
        if ranked and ranked[0]['score'] >= SURE:
            break
    if not ranked:
        # TMDb found titles for it, but none looks like the name (an alternative or foreign title): ask, never guess.
        guesses = [c for c in (candidate(r) for r in found[:MAX_CHOICES]) if c]
        for c in guesses:
            c['score'] = 0.5
        return ('question', guesses) if guesses else ('missing', None)
    top = ranked[0]
    close = [c for c in ranked if c['score'] >= top['score'] - 0.02]
    if top['score'] >= SURE:
        exact = [c for c in close if c['score'] >= 1.0] or close[:1]
        # One title with that name, or several where one is far more popular (remakes, Film: Red and the show).
        if len(exact) == 1 or exact[0]['popularity'] >= 3 * max(exact[1]['popularity'], 1):
            return 'match', exact[0]
    return 'question', ranked[:MAX_CHOICES]


def run(entries, search, progress=None, cancelled=lambda: False):
    """Resolve parse()'s entries. Returns {'matched': [...], 'questions': [...], 'missing': [...], 'duplicates': [...]}.

    Two names that resolve to the same TMDb id ("heavenly delusion" and "heavenly delusion ng") are a duplicate, added once."""
    matched, questions, missing, same = [], [], [], []
    seen = {}
    for n, entry in enumerate(entries, 1):
        if cancelled():
            break
        if progress:
            progress(n, len(entries), entry['title'])
        try:
            status, found = resolve(entry['title'], search, entry.get('year', ''))
        except Exception:
            status, found = 'missing', None
        if status == 'match':
            key = (found['kind'], found['tmdb'])
            row = dict(found, rank=entry['rank'], watched=entry.get('watched', 0), line=entry['line'], asked=entry['title'])
            if key in seen:
                same.append({'title': found['title'], 'lines': sorted({seen[key]['line'], entry['line']})})
                continue
            seen[key] = row
            matched.append(row)
        elif status == 'question':
            questions.append({'entry': entry, 'choices': found})
        else:
            missing.append(entry)
    return {'matched': matched, 'questions': questions, 'missing': missing, 'duplicates': same}
