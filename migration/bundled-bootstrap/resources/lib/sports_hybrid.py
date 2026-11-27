"""The Sports provider on the phone (owner, 2026-11-20): ESPN supplies every list, start time, score, clock and league (UFC, F1, golf and the
rest), and Crew is asked only for the sources of the one game whose page is open. Movies and TV use Crew the same way, for backup sources.

Crew's collector runs as a script (sports_jet_run) and fills a Home property; it is never started by a list any more, so the lists load at once
and nothing overlaps them. A search runs on a thread: request_game returns a token, searching_game says whether it is still looking, and
game_search_failed says whether Crew could not answer (the page then says so in plain words). Sources found for a game stay with it for the
rest of the session; a game with no source found is simply "None yet" (not an error).
"""
import json
import threading
import time
import uuid

import sports_model as sm

FOUND_KEY = 'KodiIOS.SportsFound'   # Home window property: sources found for games, shared by every Kodi script (the prefetch service, each game page)
FOUND_TTL = 30 * 60                  # seconds a found source list is trusted; Crew re-resolves the link when it is played anyway
FOUND_MAX = 12                       # games kept in the shared list


def window_store():
    """(read, write) of the shared found-sources text on the Home window; (None, None) outside Kodi."""
    try:
        import xbmcgui
        home = xbmcgui.Window(10000)
        return (lambda: home.getProperty(FOUND_KEY)), (lambda text: home.setProperty(FOUND_KEY, text))
    except Exception:
        return None, None


TTL = 8   # seconds an ESPN answer is reused: scores and clocks must be live (the pages ask every few seconds while a game is live)


def log(text):
    try:
        import xbmc
        xbmc.log('Kodi iOS Sports: ' + text, xbmc.LOGINFO)
    except ImportError:
        pass


class HybridProvider:
    """The contract the pages use (sports_model.py), backed by ESPN for the games and by `crew_sources(game)` for sources."""

    def __init__(self, espn, crew_sources, clock=time.time, store=None, more_sources=None, merge=None, claim=None):
        self.espn, self.crew_sources, self.clock = espn, crew_sources, clock
        self.more_sources, self.merge, self.claim = more_sources, merge, claim   # a second place to look (The Loop), how to merge and rank two lists, and a cross-script "someone is already asking" check
        self.topped = {}     # game id -> when this script last asked the second place
        self.read, self.write = store if store is not None else window_store()
        self.shared_at = {}   # game id -> when the shared list that gave its sources was published
        self.lock = threading.Lock()
        self.found = {}      # game id -> sources Crew gave for it
        self.searches = {}   # token -> {'game', 'state': 'searching' | 'done' | 'error'}

    # -- games and leagues: ESPN only
    def refresh(self, block=False):
        code = getattr(getattr(self.espn.refresh, '__func__', self.espn.refresh), '__code__', None)
        if code is not None and 'block' in code.co_varnames[:code.co_argcount]:
            self.espn.refresh(block=block)
        else:   # a provider without the block argument (tests, the sample)
            self.espn.refresh()

    def has_answer(self):
        return bool(getattr(self.espn, 'has_answer', lambda: False)())

    def remembered(self):
        return bool(getattr(self.espn, 'remembered', lambda: False)())

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

    def _adopt(self):
        """Sources another script found (the service's prefetch finds them before anyone opens the page) join this one's. Owner, build 618: a live game's
        page said "Searching for sources" for a minute although the prefetch had found them; each Kodi script has its own provider and saw nothing."""
        if not self.read:
            return
        try:
            shared = json.loads(self.read() or '{}')
        except (ValueError, TypeError):
            return
        now = self.clock()
        for gid, entry in (shared if isinstance(shared, dict) else {}).items():
            try:
                if now - float(entry.get('at') or 0) <= FOUND_TTL and entry.get('sources') and gid not in self.found:
                    self.found[gid] = list(entry['sources'])
            except (AttributeError, TypeError, ValueError):
                continue

    def _publish(self, game_id, sources):
        """Leave a game's sources where every Kodi script can read them (newest FOUND_MAX games)."""
        if not self.write:
            return
        try:
            try:
                shared = json.loads(self.read() or '{}') if self.read else {}
            except (ValueError, TypeError):
                shared = {}
            shared = shared if isinstance(shared, dict) else {}
            now = self.clock()
            shared[game_id] = {'at': now, 'sources': sources}
            keep = sorted(shared, key=lambda g: -float((shared[g] or {}).get('at') or 0))[:FOUND_MAX]
            self.write(json.dumps({g: shared[g] for g in keep if now - float((shared[g] or {}).get('at') or 0) <= FOUND_TTL}, separators=(',', ':')))
        except Exception:
            pass

    def _with(self, games):
        with self.lock:
            self._adopt()
            return [dict(g, sources=list(self.found.get(g['id'], []))) for g in games if g]

    # -- sources: Crew, asked for one game at a time
    def request_game(self, game_id, fresh=False):
        game = self.espn.game(game_id)
        if game is None:
            raise sm.SportsUnavailable('this game is no longer listed')
        token = uuid.uuid4().hex
        with self.lock:
            self._adopt()
            known = bool(self.found.get(game_id))
            self.searches[token] = {'game': game_id, 'state': 'done' if known else 'searching'}   # sources already found for it: nothing to look for
        if known:
            self._top_up(game_id, game)   # Crew's sources are on the page already; The Loop's join them when they arrive
            return token

        def work():
            state = 'error'
            try:
                sources = list((self.crew_sources(game, fresh=True) if fresh else self.crew_sources(game)) or [])
                if self.more_sources and not sources and self._ask_more(game_id, fresh):
                    sources = self._more(game, [])   # nothing from Crew: the page keeps saying "searching" while The Loop is asked
                with self.lock:
                    if sources:
                        self.found[game_id] = sources
                if sources:
                    self._publish(game_id, sources)
                    self._top_up(game_id, game)
                state = 'done'
            except Exception as error:   # Crew not open, a scan that never answered: the page says so
                log('sources for %s: %s' % (game_id, type(error).__name__))
            with self.lock:
                if token in self.searches:
                    self.searches[token]['state'] = state
        threading.Thread(target=work, daemon=True).start()
        return token

    # -- the second place to look (The Loop): its sources are merged into the game's list whenever they arrive
    def _ask_more(self, game_id, fresh=False):
        """True when this script should ask The Loop about the game now: not asked in the last 90 s here, and no other script is asking (claim)."""
        if not self.more_sources:
            return False
        now = self.clock()
        with self.lock:
            if not fresh and now - self.topped.get(game_id, -1e9) < 90:
                return False
            self.topped[game_id] = now
        try:
            return bool(self.claim(game_id)) if self.claim else True
        except Exception:
            return True

    def _more(self, game, have, progress=None):
        try:
            try:
                extra = list(self.more_sources(game, progress=progress) or []) if progress else list(self.more_sources(game) or [])
            except TypeError:   # a second source without the progress argument (tests)
                extra = list(self.more_sources(game) or [])
        except Exception as error:
            log('second source for %s: %s' % (game.get('id'), type(error).__name__))
            extra = []
        merged = self.merge(have, extra) if self.merge else list(have) + extra
        log('sources for %s: %d from the first place, %d from the second, %d in all' % (game.get('id'), len(have), len(extra), len(merged)))
        return merged

    def _top_up(self, game_id, game):
        if not self._ask_more(game_id):
            return

        def grow(extra):
            """The second place has sources for the game now (more may follow): they join the list at once."""
            with self.lock:
                have = list(self.found.get(game_id, []))
                merged = self.merge(have, list(extra)) if self.merge else have + list(extra)
                if len(merged) <= len(have):
                    return
                self.found[game_id] = merged
            self._publish(game_id, merged)

        def work():
            with self.lock:
                have = list(self.found.get(game_id, []))
            merged = self._more(game, have, progress=grow)
            with self.lock:
                if len(merged) > len(self.found.get(game_id, [])):
                    self.found[game_id] = merged
                else:
                    merged = None
            if merged is not None:
                self._publish(game_id, merged)
        threading.Thread(target=work, daemon=True).start()

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
