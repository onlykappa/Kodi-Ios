"""The anticipated-episodes bell on a show page (mockup board G, docs/design/favourites-import-bell-mockups.html).

The bell shows only for a show with an episode still to come. Tapping it opens a sheet with two switches kept per show in
episode_watch's registry: Alert me (a notification when an episode comes out) and Add to downloads automatically.
This module is the pure part: reading TMDb's show record, the wording, and the switches. bell_service() watches the open
show page and sets the window properties the skin's bell reads; anticipated_bell.py is the sheet.
"""
import datetime
import json
import time
import urllib.parse
import urllib.request

import episode_watch as watch

TMDB = 'https://api.themoviedb.org/3'
TTL = 6 * 3600
PROP_TMDB = 'KodiIOS.Bell.Tmdb'      # the show the bell below is for
PROP_NEXT = 'KodiIOS.Bell.Next'      # "Next: Season 5 · Episode 1 · Fri 21 Nov"
PROP_ON = 'KodiIOS.Bell.On'          # 'true' when either switch is on (the bell is filled)


def _day(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def upcoming(details, today=None):
    """{'season', 'episode', 'date'} for the next episode still to come, or None (then there is no bell).

    TMDb's next_episode_to_air first; otherwise a season announced with a future date counts as its episode 1."""
    today = today or datetime.date.today()
    if not isinstance(details, dict):
        return None
    nxt = details.get('next_episode_to_air')
    if isinstance(nxt, dict):
        day = _day(nxt.get('air_date'))
        if day and day >= today and isinstance(nxt.get('season_number'), int) and nxt.get('season_number') >= 1:
            return {'season': nxt['season_number'], 'episode': int(nxt.get('episode_number') or 1), 'date': day.isoformat()}
    future = []
    for row in details.get('seasons') or []:
        day = _day(row.get('air_date'))
        if day and day >= today and isinstance(row.get('season_number'), int) and row['season_number'] >= 1:
            future.append((day, row['season_number']))
    if future:
        day, number = min(future)
        return {'season': number, 'episode': 1, 'date': day.isoformat()}
    return None


def label(info):
    """'Next: Season 5 · Episode 1 · Fri 21 Nov'."""
    day = _day(info.get('date'))
    when = ' · %s' % day.strftime('%a %d %b').replace(' 0', ' ') if day else ''
    return 'Next: Season %s · Episode %s%s' % (info['season'], info['episode'], when)


def switches(profile, tmdb):
    alert, auto = watch.option(profile, tmdb, 'alert'), watch.option(profile, tmdb, 'auto')
    return {'alert': alert, 'auto': auto, 'on': alert or auto}


def rows(state):
    """Rows for the choice sheet: tap a row to flip its switch."""
    def row(label_, detail, on):
        return {'label': label_, 'detail': detail, 'tag': 'On' if on else 'Off', 'tag_kind': 'best' if on else ''}
    return [row('Alert me', 'A notification when a new episode comes out', state['alert']),
            row('Add to downloads automatically', 'Searches and downloads each one when it airs', state['auto'])]


def flip(profile, tmdb, title, which, info, preference=None, now=None):
    """Flip one switch ('alert' or 'auto') for a show whose next episode is `info`. Returns the new switches."""
    now_on = not watch.option(profile, tmdb, which)
    watch.set_option(profile, tmdb, title, which, now_on, floor=(info['season'], info['episode']),
                     preference=preference if which == 'auto' else None, now=now)
    return switches(profile, tmdb)


def alert_text(show, episode):
    """(title, text) of the notification for an episode that came out."""
    name = (episode.get('name') or '').strip()
    where = 'Season %s · Episode %s' % (episode.get('season_number'), episode.get('episode_number'))
    return show.get('title') or 'New episode', '%s%s is out now.' % (where, ' (%s)' % name if name and not name.lower().startswith('episode ') else '')


class Lookup:
    """TMDb show records for the bell, kept for six hours so opening a show page again costs nothing."""

    def __init__(self, key, clock=time.time, fetch=None):
        self.key, self.clock, self.cache = key, clock, {}
        self.fetch = fetch or self._fetch

    def _fetch(self, tmdb):
        url = '%s/tv/%s?%s' % (TMDB, tmdb, urllib.parse.urlencode({'api_key': self.key}))
        with urllib.request.urlopen(url, timeout=8) as response:
            return json.loads(response.read(2 * 1024 * 1024))

    def upcoming(self, tmdb, today=None):
        tmdb = str(tmdb)
        hit = self.cache.get(tmdb)
        if hit and self.clock() - hit[0] < TTL:
            return hit[1]
        info = upcoming(self.fetch(tmdb), today)
        self.cache[tmdb] = (self.clock(), info)
        return info


def bell_service(monitor, profile, window, getinfo, key_source, log=lambda *a, **k: None):
    """Keep the bell's window properties right for the show page that is open. `getinfo(label)` reads Kodi infolabels.
    A failed lookup only hides the bell: nothing else depends on it."""
    lookup = None
    shown = None
    while not monitor.waitForAbort(1.0):
        tmdb = (getinfo('Container(50).ListItem.Property(tvshow.tmdb_id)') or '').strip()
        if getinfo('Container.Content') != 'seasons':
            tmdb = ''
        if tmdb == shown:
            continue
        shown = tmdb
        info = None
        if tmdb.isdigit():
            try:
                if lookup is None:
                    key = key_source()
                    lookup = Lookup(key) if key else None
                info = lookup.upcoming(tmdb) if lookup else None
            except Exception as error:
                log('bell_lookup_failed', error=type(error).__name__)
        if info:
            window.setProperty(PROP_NEXT, label(info))
            window.setProperty(PROP_ON, 'true' if switches(profile, tmdb)['on'] else '')
            window.setProperty(PROP_TMDB, tmdb)
        else:
            for name in (PROP_TMDB, PROP_NEXT, PROP_ON):
                window.clearProperty(name)
