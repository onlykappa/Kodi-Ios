"""Roadmap 1C.4: TMDb Helper's item details for the titles on screen are fetched before Play is tapped.

Play on a spotlight card or a Continue Watching card used to wait 1-2 s while TMDb Helper fetched the title's details
over the network (owner log e8ab5995: 1.4, 1.9 and 2.1 s). TMDb Helper caches what it fetches, so the service now
asks it to fetch the details of the few titles that are on screen, in the background, one at a time: after each
listing-cache refresh (the hero copies) and for the Continue Watching history. A title is asked at most once every
12 hours, never while a video plays, and never more than WARM_LIMIT titles per pass. The ask is a RunPlugin of
TMDb Helper's own route (info=ios_warm, added by the build's TMDb Helper patch) that builds PlayerDetails with the
arguments Play uses, so Play finds the cached answer."""
import json
import os
import time
import urllib.parse

HELPER = 'plugin://plugin.video.themoviedb.helper/'
MARKER = 'addon_data/service.kodi.ios.bootstrap/details-warm.json'
TTL = 12 * 3600
WARM_LIMIT = 8        # titles per pass
PER_HERO = 3          # first items of each hero copy (the spotlight rotates through these)


def from_item(item):
    """{'tmdb_type', 'tmdb_id'} for a cached TMDb Helper list item (movie or show), else None."""
    if not isinstance(item, dict):
        return None
    info = item.get('info') or {}
    kind = {'movie': 'movie', 'tvshow': 'tv'}.get(info.get('mediatype'))
    ids = item.get('ids') or {}
    tmdb = str(ids.get('tmdb') or (item.get('props') or {}).get('tmdb_id') or '')
    if kind and tmdb.isdigit():
        return {'tmdb_type': kind, 'tmdb_id': tmdb}
    return None


def from_continue(entry):
    """The title a Continue Watching record plays (movie, or the episode with the show's TMDb id)."""
    if not isinstance(entry, dict) or not str(entry.get('tmdb_id') or '').isdigit():
        return None
    if entry.get('kind') == 'movie':
        return {'tmdb_type': 'movie', 'tmdb_id': str(entry['tmdb_id'])}
    out = {'tmdb_type': 'tv', 'tmdb_id': str(entry['tmdb_id'])}
    for part in ('season', 'episode'):
        if str(entry.get(part) or '').isdigit():
            out[part] = str(entry[part])
    return out


def collect(hero_items, continue_entries, limit=WARM_LIMIT):
    """Continue Watching first (most recent first), then the first PER_HERO of each hero copy; no duplicates."""
    found, seen = [], set()
    ordered = [from_continue(e) for e in sorted(continue_entries or [], key=lambda e: -float((e or {}).get('played') or 0))]
    for items in hero_items or []:
        ordered.extend(from_item(i) for i in (items or [])[:PER_HERO])
    for target in ordered:
        if not target:
            continue
        ident = (target['tmdb_type'], target['tmdb_id'], target.get('season', ''), target.get('episode', ''))
        if ident not in seen:
            seen.add(ident)
            found.append(target)
    return found[:limit]


def url(target):
    return HELPER + '?' + urllib.parse.urlencode(dict(target, info='ios_warm'))


def _ident(target):
    return '%s:%s:%s:%s' % (target['tmdb_type'], target['tmdb_id'], target.get('season', ''), target.get('episode', ''))


def run(targets, profile, run_plugin, wait, busy, now=time.time, pause=3.0, log=lambda text: None):
    """Ask TMDb Helper for each target not asked in the last TTL; stops when busy() or wait() says so.
    Returns the number asked."""
    path = os.path.join(profile, MARKER)
    try:
        with open(path, encoding='utf-8') as f:
            asked = json.load(f)
        asked = {k: v for k, v in asked.items() if isinstance(v, (int, float)) and now() - v < TTL} if isinstance(asked, dict) else {}
    except (OSError, ValueError):
        asked = {}
    count = 0
    for target in targets:
        if busy():
            break
        ident = _ident(target)
        if ident in asked:
            continue
        run_plugin(url(target))
        asked[ident] = now()
        count += 1
        if wait(pause):
            break
    if count:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(asked, f)
        except OSError:
            pass
        log('details of %d titles on screen asked for in the background' % count)
    return count
