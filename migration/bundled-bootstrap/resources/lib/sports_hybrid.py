"""The Sports provider on the phone (owner, 2026-11-20): ESPN supplies every list, start time, score, clock and league (UFC, F1, golf and the
rest), and Crew is asked only for the sources of the one game whose page is open. Movies and TV use Crew the same way, for backup sources.

Crew's collector runs as a script (sports_jet_run) and fills a Home property; it is never started by a list any more, so the lists load at once
and nothing overlaps them. A search runs on a thread: request_game returns a token, searching_game says whether it is still looking, and
game_search_failed says whether Crew could not answer (the page then says so in plain words). Sources found for a game stay with it for the
rest of the session; a game with no source found is simply "None yet" (not an error).
"""
import threading
import time
import uuid

import sports_model as sm

TTL = 8   # seconds an ESPN answer is reused: scores and clocks must be live (the pages ask every few seconds while a game is live)


def log(text):
    try:
        import xbmc
        xbmc.log('Kodi iOS Sports: ' + text, xbmc.LOGINFO)
    except ImportError:
        pass


class HybridProvider:
    """The contract the pages use (sports_model.py), backed by ESPN for the games and by `crew_sources(game)` for sources."""

    def __init__(self, espn, crew_sources, clock=time.time):
        self.espn, self.crew_sources, self.clock = espn, crew_sources, clock
        self.lock = threading.Lock()
        self.found = {}      # game id -> sources Crew gave for it
        self.searches = {}   # token -> {'game', 'state': 'searching' | 'done' | 'error'}

    # -- games and leagues: ESPN only
    def refresh(self):
        self.espn.refresh()

    def live_games(self, league=None):
        return self._with(self.espn.live_games(league))

    def upcoming_games(self, league=None):
        return self._with(self.espn.upcoming_games(league))

    def leagues(self):
        return self.espn.leagues()

    def overview(self):
        return self.espn.overview()

    def game(self, gid):
        game = self.espn.game(gid)
        return self._with([game])[0] if game else None

    def _with(self, games):
        with self.lock:
            return [dict(g, sources=list(self.found.get(g['id'], []))) for g in games if g]

    # -- sources: Crew, asked for one game at a time
    def request_game(self, game_id):
        game = self.espn.game(game_id)
        if game is None:
            raise sm.SportsUnavailable('this game is no longer listed')
        token = uuid.uuid4().hex
        with self.lock:
            self.searches[token] = {'game': game_id, 'state': 'searching'}

        def work():
            state = 'error'
            try:
                sources = list(self.crew_sources(game) or [])
                with self.lock:
                    if sources:
                        self.found[game_id] = sources
                state = 'done'
            except Exception as error:   # Crew not open, a scan that never answered: the page says so
                log('sources for %s: %s' % (game_id, type(error).__name__))
            with self.lock:
                if token in self.searches:
                    self.searches[token]['state'] = state
        threading.Thread(target=work, daemon=True).start()
        return token

    def searching_game(self, game_id, token):
        with self.lock:
            search = self.searches.get(token)
        return bool(search and search['game'] == game_id and search['state'] == 'searching')

    def game_search_failed(self, token):
        with self.lock:
            search = self.searches.get(token)
        return bool(search and search['state'] == 'error')

    def cancel_game_search(self, token):
        with self.lock:
            self.searches.pop(token, None)
