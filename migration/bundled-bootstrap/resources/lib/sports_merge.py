"""Sports: several add-ons' answers become one list of games (DEC-055).

An add-on adapter (sports_loop.py for The Loop, later others) turns what its add-on lists into *records*, one per stream:

    record  {'addon', 'league', 'league_name', 'sport', 'state' ('live' | 'upcoming'), 'start' (epoch),
             'away': {'code', 'name', 'score'}, 'home': {...}, 'joiner', 'clock', 'left',
             'quality' ('1080p' or ''), 'language' ('English' or ''), 'play' (what the play path is given)}

merge() returns games of the contract in sports_model.py:
  1. a game several add-ons list is ONE game (same league, same two teams, starts within 45 minutes of each other);
  2. the SAME stream (same picture size and language) from several add-ons is ONE source, on the line of the add-on that ranks first,
     with the others named in `also`;
  3. different choices (another size or language) stay as separate sources, the best one first;
  4. the clearest picture is tagged `best`; a second source worth recommending is tagged `good`; the rest carry no tag.
"""
import hashlib
import re
import unicodedata

QUALITY_RANK = {'2160p': 4, '4k': 4, '1440p': 3, '1080p': 3, '720p': 2, '576p': 1, '480p': 1, '360p': 0, '240p': 0}
GOOD_FROM = 2          # a second source is recommended from 720p up
SAME_GAME_WITHIN = 45 * 60
NOISE = {'fc', 'cf', 'afc', 'sc', 'ac', 'the', 'club', 'de', 'of'}


def quality_rank(quality):
    """3 for 1080p ... 0 for unknown or low; a number such as '1080' or '1080p' both work."""
    q = str(quality or '').strip().lower()
    if q in QUALITY_RANK:
        return QUALITY_RANK[q]
    m = re.match(r'(\d{3,4})', q)
    return QUALITY_RANK.get(m.group(1) + 'p', 0) if m else 0


def tokens(name):
    """Lower-case words of a team name without accents, punctuation or noise words ('FC', 'the')."""
    text = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode().lower().replace('&', ' and ')
    return [t for t in re.findall(r'[a-z0-9]+', text) if t not in NOISE]


def same_team(a, b):
    """'Man City' = 'Manchester City'; 'Brighton & Hove Albion' = 'Brighton and Hove Albion FC'; 'Chelsea' != 'Chelsea Women'."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(short) == len(long_):
        pairs = list(zip(sorted(short), sorted(long_)))
    else:
        return False   # different numbers of words are different teams (Chelsea / Chelsea Women)
    return all(x == y or (len(x) >= 3 and y.startswith(x)) or (len(y) >= 3 and x.startswith(y)) for x, y in pairs)


def same_game(a, b):
    if (a.get('league') or '') != (b.get('league') or ''):
        return False
    if abs((a.get('start') or 0) - (b.get('start') or 0)) > SAME_GAME_WITHIN:
        return False
    return same_team(a['away'].get('name'), b['away'].get('name')) and same_team(a['home'].get('name'), b['home'].get('name'))


def game_id(record):
    key = '%s|%s|%s' % (record.get('league'), '-'.join(tokens(record['away'].get('name'))), '-'.join(tokens(record['home'].get('name'))))
    return '%s-%s' % ((record.get('league') or 'x').lower(), hashlib.sha1(key.encode()).hexdigest()[:8])


def source_id(record):
    return '%s|%s|%s' % (record.get('addon'), record.get('quality') or '', record.get('language') or '')


def _rank(addon_order, addon):
    return addon_order.index(addon) if addon in addon_order else len(addon_order)


def _sources(records, addon_order, language):
    """One source per (picture size, language); best first; tags."""
    groups = {}
    for r in records:
        groups.setdefault(((r.get('quality') or '').lower(), (r.get('language') or '').lower()), []).append(r)
    out = []
    for (quality, lang), members in groups.items():
        members.sort(key=lambda r: _rank(addon_order, r.get('addon')))
        first = members[0]
        also = []
        for m in members[1:]:
            if m.get('addon') != first.get('addon') and m.get('addon') not in also:
                also.append(m.get('addon'))
        out.append({'id': source_id(first), 'addon': first.get('addon'), 'quality': first.get('quality') or '', 'language': first.get('language') or '',
                    'tag': '', 'also': also, 'play': first.get('play') or ''})
    want = (language or '').lower()
    out.sort(key=lambda s: (-quality_rank(s['quality']), 0 if (not want or s['language'].lower() in ('', want)) else 1,
                            _rank(addon_order, s['addon']), s['language']))
    if out:
        out[0]['tag'] = 'best'
    if len(out) > 1 and quality_rank(out[1]['quality']) >= GOOD_FROM:
        out[1]['tag'] = 'good'
    return out


def merge(records, addon_order=(), language='English'):
    """The games of the contract from the records of every add-on; `addon_order` ranks the add-ons for ties (first wins)."""
    games = []   # [(first record, [records])]
    for r in sorted(records, key=lambda r: (r.get('start') or 0, _rank(addon_order, r.get('addon')))):
        for first, members in games:
            if same_game(first, r):
                members.append(r)
                break
        else:
            games.append((r, [r]))
    out = []
    for first, members in games:
        lead = min(members, key=lambda r: _rank(addon_order, r.get('addon')))   # the add-on that ranks first supplies score and clock
        scored = next((m for m in sorted(members, key=lambda r: _rank(addon_order, r.get('addon'))) if m['away'].get('score') is not None), lead)
        states = {m.get('state') for m in members}
        away, home = dict(lead['away']), dict(lead['home'])
        away.setdefault('crest', '')
        home.setdefault('crest', '')
        if 'live' in states and scored['away'].get('score') is not None:
            away['score'], home['score'] = scored['away'].get('score'), scored['home'].get('score')
        left = next((m.get('left') for m in members if m.get('left') is not None), None)
        out.append({'id': game_id(lead), 'league': lead.get('league'), 'league_name': lead.get('league_name') or lead.get('league'),
                    'sport': lead.get('sport') or '', 'state': 'live' if 'live' in states else lead.get('state') or 'upcoming',
                    'away': away, 'home': home, 'joiner': lead.get('joiner') or 'vs', 'start': min(m.get('start') or 0 for m in members),
                    'clock': next((m.get('clock') for m in members if m.get('clock')), ''), 'left': left,
                    'sources': _sources([m for m in members if m.get('play')], addon_order, language)})
    return out
