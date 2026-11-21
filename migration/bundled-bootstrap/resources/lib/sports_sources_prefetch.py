"""Find sources for live games before anyone asks (owner, 2026-11-20: "it should find sources as soon as games are live and have it ready so you
dont have to press check").

A service loop: every `every` seconds, if nothing else is using The Crew (a video is not playing, no game page is searching), take the live
games the owner follows (the provider already applies the league filter) that have no source yet, and search for the soonest-started one the same way a game
page does (provider.request_game). Sources found stay with the game (sports_hybrid.found), so its page opens with them listed; a game with none is
tried again after RETRY seconds while it is live. One search at a time, so Crew's collector is never asked twice.
"""
import time

EVERY = 60          # seconds between looks at the live games
RETRY = 180         # seconds before a live game that had no source is searched again
MAX_SEARCH = 175    # the longest one search is waited for (a game page's own limit is 150)


WARM_AFTER = 8      # seconds after launch before sources are looked for without Sports having been opened (build 646 log 317cd411: the first source came 35 s after launch)
SEEN_FOR = 3 * 3600  # hours after Sports was opened (or after launch, for the warm-up) that sources are kept looked for


def idle_for_search(seen, started, now, on_wifi):
    """False when the search may go ahead. `seen` is when Sports was last opened ('' or 0 when not this session). Owner, build 639 log fd1d028c: on a cold start
    the first game's Play button waited about 30 s for Crew's first scan, because nothing looked for sources until Sports was opened. The look now begins
    WARM_AFTER seconds after launch, on Wi-Fi, so the scan is done (or well on its way) when the owner gets to a game. The service's own checks (a video is
    playing, a game page is searching) still apply on top of this."""
    try:
        seen = float(seen or 0)
    except (TypeError, ValueError):
        seen = 0.0
    if seen:
        return now - seen > SEEN_FOR
    if now - started < WARM_AFTER or now - started > SEEN_FOR:
        return True
    return not on_wifi


class Prefetch:
    def __init__(self, get_provider, busy=lambda: False, log=lambda text: None, clock=time.time, sleep=time.sleep):
        self.get_provider, self.busy, self.log, self.clock, self.sleep = get_provider, busy, log, clock, sleep
        self.attempts = {}   # game id -> when it was last searched

    def tick(self):
        """One look. Returns the game id searched, or None."""
        if self.busy():
            return None
        provider = self.get_provider()
        try:
            games = provider.live_games()
        except Exception as error:
            self.log('prefetch: live games unavailable (%s)' % type(error).__name__)
            return None
        now = self.clock()
        live = {g['id'] for g in games}
        for gone in [gid for gid in self.attempts if gid not in live]:
            del self.attempts[gone]   # it ended: forget it
        for game in sorted(games, key=lambda g: g.get('start') or 0):
            if game.get('sources'):
                continue
            last = self.attempts.get(game['id'])
            if last is not None and now - last < RETRY:
                continue
            self.attempts[game['id']] = now
            self._search(provider, game)
            return game['id']
        return None

    def _search(self, provider, game):
        gid = game['id']
        began = self.clock()
        try:
            token = provider.request_game(gid)
            while provider.searching_game(gid, token) and self.clock() - began < MAX_SEARCH:
                self.sleep(1)
            if provider.searching_game(gid, token):
                provider.cancel_game_search(token)
            found = provider.game(gid)
            count = len((found or {}).get('sources') or [])
            self.log('prefetch: %s %s: %s' % (game.get('league'), gid, ('%d source(s) ready' % count) if count else 'no source yet'))
        except Exception as error:
            self.log('prefetch: %s failed (%s)' % (gid, type(error).__name__))


def watch(get_provider, busy, wait, log=lambda text: None, every=EVERY, first=20, poke=lambda: False):
    """The service loop; `wait(seconds)` returns True when Kodi is quitting. `poke()` is True once when a Sports page has just been opened: the look
    then happens at once instead of at the next minute (owner, build 618: tapping a live game said "Searching for sources" for a minute)."""
    prefetch = Prefetch(get_provider, busy, log)
    waited, limit = 0, first
    while True:
        if wait(1):
            return
        waited += 1
        try:
            poked = bool(poke())
        except Exception:
            poked = False
        if waited < limit and not poked:
            continue
        waited, limit = 0, every
        try:
            prefetch.tick()
        except Exception as error:
            log('prefetch: tick failed (%s)' % type(error).__name__)
