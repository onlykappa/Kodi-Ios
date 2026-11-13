"""F4 (PR #24 roadmap): what the owner will most likely watch next, so it is prepared first and gets the line first.

"Next to watch" is read from Continue Watching (plugin.video.kodi.ios.watch's continue.json, no network): for every
episode started there, that episode and the AHEAD episodes after it in the same season. Matching is by the library's own
keys (prepare_downloads.line_key: show, season, episode), so 'Naruto - 006', 'Naruto.S01E06' and 'Naruto Episode 006'
are the same episode.
"""
import json
import os

AHEAD = 3


def keys(data, ahead=AHEAD):
    """{(show key, season, episode)} for the started episodes and the next `ahead` of each."""
    import debrid_drive
    out = set()
    for entry in ((data or {}).get('items') or {}).values():
        if not isinstance(entry, dict) or entry.get('kind') != 'episode':
            continue
        try:
            season, episode = int(entry.get('season') or 0), int(entry.get('episode') or 0)
        except (TypeError, ValueError):
            continue
        show = debrid_drive.show_match(entry.get('tvshowtitle'))   # 'Shippūden', 'Shippuden', 'Shippuuden': one show
        if not show or not episode:
            continue
        for n in range(episode, episode + ahead + 1):
            out.add((show, season or 1, n))
    return out


def matches(wanted, name):
    import debrid_drive
    import drivelibrary
    import prepare_downloads
    _, season, episode = prepare_downloads.line_key(name)[:3]
    if not episode:
        return False
    found = drivelibrary.parse(name)
    title = found.get('title') or ''
    if not found.get('episode'):   # 'Naruto Shippuden - 006': the title is what stands before the number
        import re
        title = re.split(r'\s+-\s+\d|\bE(?:pisode)?\s*\d', re.sub(r'\[[^\]]*\]', '', re.sub(r'[._]+', ' ', str(name))), flags=re.I)[0]
    return (debrid_drive.show_match(title), season, episode) in wanted


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'plugin.video.kodi.ios.watch', 'continue.json')


def cached(profile):
    """name -> bool, re-reading Continue Watching only when its file changed."""
    seen = {'stamp': None, 'keys': set()}

    def wanted(name):
        try:
            stamp = os.path.getmtime(path(profile))
        except OSError:
            return False
        if stamp != seen['stamp']:
            try:
                with open(path(profile), encoding='utf-8') as f:
                    seen['keys'] = keys(json.load(f))
            except (OSError, ValueError):
                seen['keys'] = set()
            seen['stamp'] = stamp
        try:
            return matches(seen['keys'], name)
        except Exception:
            return False
    return wanted
