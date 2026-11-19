"""Which leagues Sports shows (owner-approved board B, docs/design/sports-redesign-mockups.html).

One choice for the hub, Upcoming and Leagues, kept in sports-leagues.json in the add-on's data folder as the list of leagues
turned OFF. Nothing off (the default) shows every league, including ones the schedule has not listed before; a new league
appears switched on. Pure apart from the JSON file, so it is host-tested.
"""
import json
import os

FILE = 'sports-leagues.json'


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    """The set of league codes turned off."""
    try:
        with open(path(profile), encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return set()
    off = data.get('off') if isinstance(data, dict) else None
    return {str(c) for c in off} if isinstance(off, list) else set()


def save(profile, off):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump({'off': sorted(off)}, handle)
    os.replace(tmp, target)


def games(items, off):
    """The games of the leagues that are on."""
    return [g for g in items if g.get('league') not in off]


def leagues(items, off):
    """The league rows (Leagues page) of the leagues that are on."""
    return [l for l in items if (l.get('code') or l.get('league')) not in off]


def known(items):
    """[(sport, code, name)] of every league seen in games or league rows, in first-seen order."""
    out, seen = [], set()
    for it in items:
        code = it.get('code') or it.get('league')
        if code and code not in seen:
            seen.add(code)
            out.append((it.get('sport') or '', code, it.get('league_name') or it.get('name') or code))
    return out


def toggled(off, code):
    return (set(off) - {code}) if code in off else (set(off) | {code})


def all_on(_known=None):
    return set()


def all_off(known_codes):
    return set(known_codes)


def only_sport(known_rows, sport):
    """Turn the sport's leagues on and every other league off."""
    return {code for s, code, _ in known_rows if s != sport}


def only_codes(known_codes, wanted):
    return {c for c in known_codes if c not in set(wanted)}


def active(off, known_codes):
    """True while at least one known league is off (the Edit button shows a count then)."""
    return bool(set(off) & set(known_codes))


def count_on(off, known_codes):
    return len([c for c in known_codes if c not in off])


def summary(off, known_rows):
    """'Showing NFL and NBA', 'Showing 4 leagues', 'No leagues selected', or '' when nothing is filtered."""
    codes = [c for _, c, _ in known_rows]
    if not active(off, codes):
        return ''
    on = [c for c in codes if c not in off]
    if not on:
        return 'No leagues selected'
    if len(on) <= 2:
        return 'Showing ' + ' and '.join(on)
    return 'Showing %d leagues' % len(on)


# --- the provider every Sports page reads --------------------------------------------------------------------------------
def profile_dir():
    """Kodi's profile folder (the add-on's data lives under it), or KODI_IOS_SPORTS_PROFILE for tests and the rig."""
    forced = os.environ.get('KODI_IOS_SPORTS_PROFILE')
    if forced:
        return forced
    try:
        import xbmcvfs
        return xbmcvfs.translatePath('special://profile/')
    except Exception:
        return ''


class FilteredProvider:
    """The provider with the owner's league choice applied to every list and every count, so the hub, Upcoming and Leagues
    always agree. Anything else (game, refresh, sources, play) is the real provider's own."""

    def __init__(self, base, off=None, clock=None):
        self._base = base
        self._off = off or (lambda: load(profile_dir()) if profile_dir() else set())
        self._clock = clock

    def __getattr__(self, name):
        return getattr(self._base, name)

    def off(self):
        return set(self._off())

    def live_games(self, league=None):
        return games(self._base.live_games(league), self.off())

    def upcoming_games(self, league=None):
        return games(self._base.upcoming_games(league), self.off())

    def leagues(self):
        return leagues(self._base.leagues(), self.off())

    def all_leagues(self):
        """Every league the schedule lists, filtered or not, for the Edit sheet."""
        rows = list(self._base.leagues())
        seen = {(r.get('code')) for r in rows}
        for g in list(self._base.live_games()) + list(self._base.upcoming_games()):   # a league with games but no row
            if g.get('league') not in seen:
                seen.add(g.get('league'))
                rows.append({'code': g.get('league'), 'name': g.get('league_name') or g.get('league'), 'sport': g.get('sport') or '',
                             'live': 0, 'next': None})
        return rows

    def overview(self):
        import time
        import sports_model as sm
        base = self._base.overview()
        off = self.off()
        if not off:
            return base
        now = int(self._clock() if self._clock else time.time())
        offset = sm.device_offset(now)
        live = self.live_games()
        coming = [g['start'] for g in self.upcoming_games() if g['start'] >= now]
        today = [s for s in coming if sm.day_label(s, now, offset) == 'Today']
        out = dict(base)
        out.update({'live': len(live), 'live_sports': sorted({g['sport'] for g in live}),
                    'next': min(coming) if coming else None, 'more_today': max(0, len(today) - 1),
                    'leagues': len(self.leagues())})
        return out


_WRAPPERS = {}


def wrap(provider):
    """One wrapper per provider, so asking twice gives the same object."""
    if isinstance(provider, FilteredProvider):
        return provider
    kept = _WRAPPERS.get(id(provider))
    if kept is None or kept[0] is not provider:
        kept = _WRAPPERS[id(provider)] = (provider, FilteredProvider(provider))
    return kept[1]


def unwrap(provider):
    """The real provider behind a wrapper (tests that check which provider the pages get)."""
    return getattr(provider, '_base', provider)
