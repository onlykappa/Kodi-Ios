"""The one door the Sports pages use to reach sports data (DEC-057).

Pages call get() and play(); they never talk to an add-on. get() returns a provider with the methods listed in sports_model.py.
Real data only: with no setting, get() is the real provider (ESPN's public scoreboard feed, sports_espn.py); when nothing answers, every call raises
SportsUnavailable and the pages say "Can't load ... right now" (the sample games must never reach a phone as if they were real).
For building and looking at pages in the desktop Kodi rig and in tests, set KODI_IOS_SPORTS=sample (the approved boards' sample
data), =quiet (nothing live: the grey Live Now tile) or =down (every call fails).
"""
import os
import threading
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


def _snapshot_path():
    """Where the last ESPN answer is kept on the phone (None outside Kodi): pages draw it at once after a restart while the new answer loads."""
    try:
        import xbmcvfs
        return os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap'), 'sports-snapshot.json')
    except Exception:
        return None


def real():
    """The phone's provider (owner, 2026-11-20): ESPN for every game, league, time and score; Crew only for the sources of the game whose page is
    open (sports_hybrid.py). KODI_IOS_SPORTS=espn is the same provider without Crew at all."""
    if _real[0] is None:
        import sports_espn
        espn = sports_espn.EspnProvider(snapshot_path=_snapshot_path())
        if os.environ.get('KODI_IOS_SPORTS', '') == 'espn':
            _real[0] = espn
        else:
            import sports_hybrid
            espn.ttl = sports_hybrid.TTL
            _real[0] = sports_hybrid.HybridProvider(espn, crew_sources, more_sources=second_sources, merge=merge_ranked)
    return _real[0]


_scans = [0]
LOOP_SECONDS = 60      # the longest one game's search keeps reading what The Loop's routes list (after The Crew found nothing)
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


REUSE_WALK = 180   # seconds a finished walk of Crew's menus answers a new search for a game it did not list (a game that is not there is not there a minute later)


def walk_reusable(jet, league, now=time.time, window=REUSE_WALK):
    """True when Crew's menus were walked to the end less than `window` seconds ago, for this game's league (or every league): a new search then only reads
    that answer and does not start another walk. Owner, build 646 logs: every search, the prefetch's included, started a full walk (15-70 s of Crew's plugin
    parsing pages while the phone drew the page)."""
    import json
    import sports_jet
    try:
        data = json.loads(jet._home().getProperty(sports_jet.DATA) or 'null')
    except Exception:
        return False
    if not isinstance(data, dict) or not data.get('done'):
        return False
    walked = str(data.get('league') or '')
    return 0 <= now() - float(data.get('at') or 0) < window and walked in ('', str(league or ''))


def _match(game, listings):
    """The sources of the ONE current listing that is this game (sports_match.unique_match), else []. Two different matching listings (a doubleheader) or a game
    ESPN says is over match nothing: the closest one is never guessed. A game record without ESPN's state and start is judged by teams and time only, as before."""
    import source_contract
    import sports_match
    try:
        return sports_match.unique_match(game, listings, strict=False)['sources']
    except source_contract.Outcome:
        return []


def crew_sources(game, sleep=time.sleep, clock=time.monotonic, fresh=False):
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
        sports_crew_patch.mark(home, SEARCH_SECONDS + 30)   # Crew's own menus then see their add-on as the container, and draw no dialog
    except Exception:
        home = None
    try:
        began, asked = clock(), time.time()
        if not fresh and walk_reusable(jet, game.get('league')):   # the walk that just ended did not list it: say so now ("Check now" asks again: fresh)
            try:
                found = _match(game, list(jet.live_games()) + list(jet.upcoming_games()))
                if found:
                    return found
            except sm_unavailable():
                pass
            return []
        for attempt in (0, 1):
            jet.refresh()
            while True:
                try:
                    games = list(jet.live_games()) + list(jet.upcoming_games())
                except sm_unavailable():
                    games = []
                found = _match(game, games)
                if found:
                    return found
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


def loop_sources(game, sleep=time.sleep, clock=time.monotonic, make=None, progress=None):
    """The sources The Loop's routes list for this one game: the second place to look when The Crew has none (owner, 2026-11-26: the Crew's one site had no feed for a live game
    while The Loop's many sites did). The Loop must be installed from its repository (Kodi records where it came from, and The Loop refuses to run without that). Its routes
    are read through Kodi's own directory listing (nothing of its code is imported or bypassed), only this game's league and teams are matched, and the same strict one-listing
    rule as Crew applies. No match, no Loop, or an error is an empty list."""
    import sports_jet
    jet = None
    quiet = threading.Event()
    try:
        if not sports_jet._folder('plugin.video.the-loop'):
            sports_jet.log('sports: Loop search skipped (The Loop is not installed or is switched off)')
            return []
        sports_jet.log('sports: Loop search started')
        jet = make() if make else sports_jet.JetProvider(loop_only=True, loop_schedule=[game], wait=2)
        began, first, shown = clock(), None, 0
        quiet = _quiet_progress_boxes()
        sports_jet.log('sports: Loop search for %s' % game.get('id'))
        while True:
            try:
                games = list(jet.live_games()) + list(jet.upcoming_games())
            except sm_unavailable():
                games = []
            found = _match(game, games)
            if found and (progress is not None) and len(found) > shown:
                shown = len(found)
                try:
                    progress(found)   # the page gets each site's sources as they come in, not only when the search ends
                except Exception:
                    pass
            if found and first is None:
                first = clock()
            if found and (clock() - first >= LOOP_MORE or not jet_busy(jet)):
                return found   # the sites that answered within LOOP_MORE seconds of the first one are in the list too
            if clock() - began > LOOP_SECONDS or not jet_busy(jet):
                return found or []
            sleep(1)
    except Exception as error:
        sports_jet.log('sports: Loop search ended (%s)' % type(error).__name__)
        return []
    finally:
        try:
            jet.stop()   # whatever the answer, the rest of The Loop's routes are not walked in the background
        except Exception:
            pass
        try:
            quiet.set()
        except Exception:
            pass


OWN_SECONDS = 25   # our own scrapers answer in a few seconds; a site that has not answered by then is left out of this search


def own_extractors():
    """The sites we read ourselves (no The Loop, no JetExtractors, so no boxes and nothing to install): their lists are plain web requests."""
    import sports_fawa
    import sports_independent
    import sports_livefeeds
    import sports_p720
    return [sports_independent.StreamsCenter(), sports_fawa.FawaNews(), sports_livefeeds.LiveFeeds(), sports_p720.P720Stream()]


def own_sources(game, sleep=time.sleep, clock=time.monotonic, make=None, progress=None):
    """The sources our own scrapers have for this one game. Quiet (no dialogs), so unlike The Loop it may run ahead of time (prefetch) as Crew's does."""
    import sports_jet
    jet = None
    try:
        jet = make() if make else sports_jet.JetProvider(loader=lambda: (own_extractors(), 'independent'), wait=2)
        began, shown = clock(), 0
        while True:
            try:
                games = list(jet.live_games()) + list(jet.upcoming_games())
            except sm_unavailable():
                games = []
            found = _match(game, games)
            if found and progress is not None and len(found) > shown:
                shown = len(found)
                try:
                    progress(found)
                except Exception:
                    pass
            if not jet_busy(jet) or clock() - began > OWN_SECONDS:
                if found:
                    sports_jet.log('sports: own sources for %s: %d' % (game.get('id'), len(found)))
                return found or []
            sleep(.5)
    except Exception as error:
        sports_jet.log('sports: own search ended (%s)' % type(error).__name__)
        return []
    finally:
        try:
            jet.stop()
        except Exception:
            pass


def second_sources(game, sleep=time.sleep, clock=time.monotonic, progress=None, own=None, loop=None, claim=None):
    """Everything beyond Crew: our own scrapers (quiet, so they also run ahead of time) and, only while the game page is open, The Loop's routes (which draw boxes).
    Both run at once and each site's sources reach the page as they arrive; own sources are listed before The Loop's twins."""
    own = own or own_sources
    loop = loop or loop_sources
    claim = claim if claim is not None else claim_loop
    lock = threading.Lock()
    parts = {'own': [], 'loop': []}

    def push(key):
        def put(found):
            with lock:
                parts[key] = list(found)
                merged = merge_sources(parts['own'], parts['loop'])
            if progress is not None:
                progress(merged)
        return put
    result = {}

    def run_own():
        try:
            result['own'] = own(game, progress=push('own'))
        except Exception:
            result['own'] = []
    worker = threading.Thread(target=run_own, daemon=True)
    worker.start()
    try:
        asked = bool(claim(game.get('id')))
    except Exception:
        asked = True
    result['loop'] = []
    if asked:
        try:
            result['loop'] = loop(game, progress=push('loop'))
        except Exception:
            result['loop'] = []
    worker.join(OWN_SECONDS + 5)
    return merge_sources(result.get('own', []), result.get('loop', []))


def _quiet_progress_boxes(close=None, every=0.08):
    """The Loop draws its own progress box ("JetExtractor: EmbedHD API, Fetched 0 items" with Cancel) for every route it reads, over the Sports page (build 774 screenshot). While a
    Loop search runs, Kodi's progress boxes are closed as soon as they appear. Returns an Event: set it to stop. Closing is not cancelling: the route's script goes on."""
    done = threading.Event()
    if close is None:
        def close():
            import xbmc
            xbmc.executebuiltin('Dialog.Close(progressdialog,true)')
            xbmc.executebuiltin('Dialog.Close(extendedprogressdialog,true)')

    def work():
        while not done.wait(every):
            try:
                close()
            except Exception:
                return
    threading.Thread(target=work, daemon=True).start()
    return done


def jet_busy(jet):
    """True while The Loop's source workers are still answering."""
    running = getattr(jet, 'running', None)
    return running is not None and not running.is_set()


LOOP_MORE = 15    # seconds The Loop's other sites get after the first one has a stream for the game (build 772 log: first site 27 s after the search began, 37 more still working)
LOOP_AFTER = 6    # seconds The Crew may take before The Loop starts looking too (it starts at once when The Crew answers, empty or not)
LOOP_GRACE = 12   # seconds the slower of the two gets once the first has sources, so a game shows both places' sources, not only the quicker one's


def merge_sources(*lists):
    """Every source once (same play request), in the order given: The Crew's first, then The Loop's. Ranking is the page's (sports_model.order_sources) and the Auto button's."""
    seen, out = set(), []
    for found in lists:
        for source in found or []:
            key = source.get('play') or source.get('id')
            if key in seen:
                continue
            seen.add(key)
            out.append(source)
    return out


def rank_sources(sources, health=None):
    """The best first: what played well before (this phone's own memory per source: a recent success and its sharpness and bitrate count, a recent failure with no success since counts against),
    then the add-on's own quality, then the order given (The Crew's before The Loop's). The first source that has worked before is tagged 'best' and the next two 'good', so the page's
    "Best" and "Also good" rows show them; sources never tried keep whatever tag they had."""
    import sports_merge
    import sports_stream_health
    try:
        health = health or sports_stream_health.open_health()
    except Exception:
        return list(sources)
    key = lambda s: s.get('addon') or s.get('id') or ''
    try:
        score = lambda s: health.score(key(s), sports_merge.quality_rank(s.get('quality')))
        ranked = sorted(sources, key=lambda s: -score(s))
        out, shown = [], 0
        for source in ranked:
            known = (health.data.get(key(source)) or {}).get('ok_at') and not health.dead(key(source))
            if known and shown < 3:
                source = dict(source, tag='best' if shown == 0 else 'good')
                shown += 1
            out.append(source)
        return out
    except Exception:
        return list(sources)   # a memory file that cannot be read never hides a source


def all_sources(game, fresh=False, after=None, crew=None, loop=None, grace=None, health=None, **kwargs):
    """The sources of both places for one game (owner, 2026-11-26: "show me the best sources", Loop's options too): The Crew's and The Loop's, merged. The Loop starts as soon as The
    Crew has answered, or after `after` seconds of Crew silence (a dry Crew can keep reading its menus for minutes); once one place has sources the other gets `grace` more seconds,
    then the page gets what there is. Neither having any is an empty list."""
    import threading
    crew = crew or (lambda: crew_sources(game, fresh=fresh, **kwargs))
    loop = loop or (lambda: loop_sources(game))
    after = LOOP_AFTER if after is None else after
    grace = LOOP_GRACE if grace is None else grace
    answers, lock, changed, crew_done = {}, threading.Lock(), threading.Event(), threading.Event()

    def run(name, work):
        try:
            found = list(work() or [])
        except Exception:
            found = []
        with lock:
            answers[name] = found
        if name == 'crew':
            crew_done.set()
        changed.set()
    threading.Thread(target=run, args=('crew', crew), daemon=True).start()
    crew_done.wait(after)
    threading.Thread(target=run, args=('loop', loop), daemon=True).start()
    first_found = None
    while True:
        changed.wait(1)
        changed.clear()
        with lock:
            done = set(answers)
            have = any(answers.get(n) for n in answers)
            merged = merge_sources(answers.get('crew'), answers.get('loop'))
        if done == {'crew', 'loop'}:
            return rank_sources(merged, health)
        if have:
            first_found = first_found if first_found is not None else time.monotonic()
            if time.monotonic() - first_found >= grace:
                return rank_sources(merged, health)


def merge_ranked(have, extra):
    """Two lists of sources as one, each source once, ranked by what played well before (rank_sources)."""
    return rank_sources(merge_sources(have, extra))


def claim_loop(game_id, now=time.time, ttl=90):
    """Whether this Kodi script may ask The Loop about a game now. Only while a Sports game page is open (`sports_game.OPEN` holds a time in the future): The Loop draws its own
    progress boxes ("JetExtractor: Backdoor1, Fetched 0 items") while its routes are read, and from the prefetch or a reminder they landed on whatever was on screen, for example
    a movie page (build 773 log). And only one script at a time: the Home window holds when it was last asked."""
    try:
        import xbmcgui
    except ImportError:
        return True   # outside Kodi (tests)
    try:
        home = xbmcgui.Window(10000)
        if float(home.getProperty('KodiIOS.SportsGameOpen') or 0) <= now():
            return False
        key = 'KodiIOS.SportsLoopAsked.' + str(game_id)
        if now() - float(home.getProperty(key) or 0) < ttl:
            return False
        home.setProperty(key, str(now()))
        return True
    except Exception:
        return False


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
