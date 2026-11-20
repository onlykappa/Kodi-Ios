"""The one door the Sports pages use to reach sports data (DEC-057).

Pages call get() and play(); they never talk to an add-on. get() returns a provider with the methods listed in sports_model.py.
Real data only: with no setting, get() is the real provider (ESPN's public scoreboard feed, sports_espn.py); when nothing answers, every call raises
SportsUnavailable and the pages say "Can't load ... right now" (the sample games must never reach a phone as if they were real).
For building and looking at pages in the desktop Kodi rig and in tests, set KODI_IOS_SPORTS=sample (the approved boards' sample
data), =quiet (nothing live: the grey Live Now tile) or =down (every call fails).
"""
import os
import time

import sports_model

_provider = [None]
_real = [None]


def get():
    """The provider with the owner's league filter applied (sports_filter, board B of the Sports redesign)."""
    import sports_filter
    return sports_filter.wrap(_get())


def _get():
    mode = os.environ.get('KODI_IOS_SPORTS', '')
    if mode == 'down':
        return sports_model.Sample(fail=True)
    if mode == 'quiet':
        return sports_model.Sample(offset=sports_model.device_offset(), quiet=True)
    if mode == 'sample':
        if _provider[0] is None:
            _provider[0] = sports_model.Sample(offset=sports_model.device_offset())
        return _provider[0]
    return real()


def real():
    """The phone's provider (owner, 2026-11-20): ESPN for every game, league, time and score; Crew only for the sources of the game whose page is
    open (sports_hybrid.py). KODI_IOS_SPORTS=espn is the same provider without Crew at all."""
    if _real[0] is None:
        import sports_espn
        espn = sports_espn.EspnProvider()
        if os.environ.get('KODI_IOS_SPORTS', '') == 'espn':
            _real[0] = espn
        else:
            import sports_hybrid
            espn.ttl = sports_hybrid.TTL
            _real[0] = sports_hybrid.HybridProvider(espn, crew_sources)
    return _real[0]


_scans = [0]
SEARCH_SECONDS = 150   # the longest one game's source search keeps reading what Crew's collector publishes


def _scan_state(jet):
    """(finished, published_at) of the Crew collector's answer. (True, 0) when it cannot be read (outside Kodi): there is then nothing to wait for."""
    import json
    import sports_jet
    try:
        data = json.loads(jet._home().getProperty(sports_jet.DATA) or 'null')
    except Exception:
        return True, 0
    if not isinstance(data, dict):
        return False, 0
    return bool(data.get('done')), data.get('at', 0)


def crew_sources(game, sleep=time.sleep, clock=time.monotonic):
    """The sources Crew has for this one game (its page asked). Crew's collector runs only now; a list never starts it. Matching is by league,
    start and team names (sports_merge.same_game). The collector publishes as it walks Crew's menus (a minute or two on a phone), so this keeps
    reading what it has published until the game turns up, the collector finishes or SEARCH_SECONDS pass (it used to read once, so a source found
    a minute later was never seen). No match is an empty list, not an error."""
    import sports_jet
    import sports_merge
    jet = sports_jet.JetProvider(remote=True, crew_only=True)
    home = None
    try:
        import sports_crew_patch
        import xbmcgui
        sports_crew_patch.ensure(sports_jet.log)
        home = xbmcgui.Window(10000)
        home.setProperty('KodiIOS.SportsCrewOnlyLeague', str(game.get('league') or ''))   # read only this game's league menu in Crew
        _scans[0] += 1
        home.setProperty(sports_crew_patch.SCAN, '1')   # Crew's own menus then see their add-on as the container (no Crew window)
    except Exception:
        home = None
    try:
        began, asked = clock(), time.time()
        for attempt in (0, 1):
            jet.refresh()
            while True:
                try:
                    games = list(jet.live_games()) + list(jet.upcoming_games())
                except sm_unavailable():
                    games = []
                for other in games:
                    if other.get('sources') and sports_merge.same_game(game, other):
                        return other['sources']
                finished, at = _scan_state(jet)
                if finished or clock() - began > SEARCH_SECONDS:
                    break
                sleep(1)
            if not finished or at >= asked - 1:
                return []     # the collector walked Crew for this request and the game is not there
            # The answer was published before this request began: one more pass starts a fresh walk.
        return []
    finally:
        if home is not None:
            _scans[0] -= 1
            if _scans[0] <= 0:   # another game's search may still be reading
                home.clearProperty('KodiIOS.SportsCrewOnlyLeague')
                home.clearProperty('KodiIOS.SportsCrewScan')


def sm_unavailable():
    return sports_model.SportsUnavailable


def reset():
    """Forget the cached provider (tests)."""
    _provider[0] = None
    _real[0] = None


def play(source, log=lambda message: None, launch=None):
    """Play a source at once (what a tap on a source line does). The sample provider only logs; the real one hands source['play'] to
    Kodi's player."""
    log('sports: play %s from %s (%s, %s)' % (source.get('id'), source.get('addon'), source.get('quality'), source.get('language')))
    if os.environ.get('KODI_IOS_SPORTS', '') in ('', 'jet') and str(source.get('play') or '').startswith('{'):
        import sports_jet
        return sports_jet.play_request(source, log, launch=launch) if launch is not None else sports_jet.play_request(source, log)
    return source.get('play')
