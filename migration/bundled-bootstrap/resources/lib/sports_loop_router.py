"""Rank game choices and let Kodi's native playlist skip failed Loop routes."""
import json
import threading
import time
import uuid
import sports_native_routes as routes
import sports_merge
import sports_stream_health as health_mod

MAX_CHOICES = 32
OWNER = "KodiIOS.SportsNativeOwner"


def native_route(source):
    try:
        value = json.loads(source.get('play') or '')
        address = value['l']['address']
        return address if value.get('e') == routes.route_kind(address) and value.get('e') in ('TheCrewRoute', 'TheLoopRoute') else None
    except (ValueError, KeyError, TypeError):
        return None


def automatic_source(sources):
    ordered = sorted(sources, key=lambda s: (not s.get('addon', '').startswith('Crew '), -sports_merge.quality_rank(s.get('quality')), routes.source_rank(s.get('addon', ''))))
    if not ordered:
        raise ValueError('no sports sources')
    native = [s for s in ordered if native_route(s)]
    result = dict((native or ordered)[0])
    if native:
        result['native_queue'] = [{'play':s['play'], 'addon':s.get('addon', '')} for s in native[:MAX_CHOICES]]
        result['alts'] = [s['play'] for s in ordered if not native_route(s) and s.get('play')]
    else:
        result['alts'] = [s['play'] for s in ordered[1:] if s.get('play')]
    return result


def tapped_source(source, sources):
    """What a tap on one source plays: that source first, then the game's other native sources (best first), so a dead link is never the end.
    The tap is a request, not an order for a stream that is known dead: the queue puts it behind working ones (see Health.order)."""
    if not native_route(source):
        return source
    others = [s for s in sources if s is not source and native_route(s) and s.get('play') != source.get('play')]
    result = dict(source)
    result['native_queue'] = [{'play': s['play'], 'addon': s.get('addon', '')} for s in [source] + others[:MAX_CHOICES - 1]]
    result['native_pinned'] = True   # the first entry is the person's choice; play() keeps it first unless it is known dead
    result['alts'] = list(source.get('alts') or []) + [s['play'] for s in sources if not native_route(s) and s.get('play')]
    return result


def play(queue, logger, backend=None, clock=time.monotonic, timeout=90, owner=None, keep_owner_on_failure=False, auto_pick=True, pinned=False,
         health=None, info=None):
    if backend is None:
        import xbmc as backend
    if health is None:
        health = health_mod.open_health()
    if info is None:
        info = getattr(backend, 'getInfoLabel', None)
    choices, seen = [], set()
    for source in queue[:MAX_CHOICES]:
        address = native_route(source)
        if address and address not in seen:
            seen.add(address)
            choices.append((address, source.get('addon') or 'Sports', source))
    if not choices:
        raise ValueError('no native addon routes')
    # What the phone has learned: sources that worked lately and looked sharp first, one that died minutes ago last. The person's own pick leads
    # unless it is known dead (an automatic Play has no pick: everything is ranked).
    before = [choice[1] for choice in choices]
    choices = health.order(choices, key=lambda choice: choice[1], quality=lambda choice: sports_merge.quality_rank(choice[2].get('quality')),
                           first=choices[0] if pinned else None)
    if [choice[1] for choice in choices] != before:
        logger('sports: source order from what worked before: %s' % ', '.join('%s (%.1f)' % (c[1], health.score(c[1])) for c in choices[:4]))
    routes.prepare_proxy([choice[0] for choice in choices])

    class Observer(backend.Player):
        ready = False
        started = False
        stopped = False
        failed = False
        def onPlayBackStarted(self):
            self.started = True
            self.stopped = self.failed = False
        def onAVStarted(self): self.ready = True
        def onPlayBackStopped(self):
            self.stopped = True
            logger('sports: native Stop event (%s)' % ('current media' if self.started else 'before current media'))
        def onPlayBackError(self):
            self.failed = True
            logger('sports: native media opening error')

    import xbmcgui
    try:
        home = xbmcgui.Window(10000)
    except AttributeError:
        home = None  # minimal host-test backend
    if home is not None:
        if owner is not None and home.getProperty(OWNER) != owner:
            raise InterruptedError('a newer play request replaced this queue')
        owner = owner or uuid.uuid4().hex
        home.setProperty(OWNER, owner)
        try:
            import sports_crew_patch
            sports_crew_patch.ensure(logger)
            sports_crew_patch.mark(home, timeout + 60)   # Crew's resolver then draws no "Finding Your Event" box
        except Exception:
            pass
    def owns_queue():
        return home is None or home.getProperty(OWNER) == owner
    # Drain the previous attempt's Stop before registering this observer.
    backend.Player().stop()
    backend.sleep(100)
    playlist = backend.PlayList(backend.PLAYLIST_VIDEO)
    playlist.clear()
    def stage(index):
        # Crew clears its resolver cache on a league menu. Preparing every
        # candidate up front would invalidate earlier candidates again.
        if not owns_queue():
            raise InterruptedError('a newer play request replaced this queue')
        try:
            address = routes.prepare_source(choices[index][2])
        except (ValueError, RuntimeError) as error:
            logger('sports: native source preparation ended (%s)' % type(error).__name__)
            raise InterruptedError('native source preparation incomplete') from error
        if not owns_queue():
            raise InterruptedError('a newer play request replaced this queue')
        item = xbmcgui.ListItem(label=choices[index][1])
        item.setProperty('IsPlayable', 'true')
        playlist.add(address, item)
    player = Observer()
    monitor = backend.Monitor()
    logger('sports: opening native addon queue (%d choices)' % len(choices))
    began, previous, failed_through = clock(), clock(), -1
    check = health_mod.Watch()
    current_index = 0
    choice_began = clock()   # when the current choice was handed to Kodi (the person answering Crew's chooser does not count)
    pick = {'seen': None, 'picked': False}   # when a Crew chooser appeared, and whether it has been answered
    pick_lock = threading.Lock()

    def chooser_up(now):
        """True while Crew's link chooser is on screen. Owner, 2026-11-20: no Crew UI. The chooser is answered with its first (best) entry, once
        per appearance, after a moment for the list to build: Kodi's own select action, nothing of Crew's code is called."""
        with pick_lock:
            if backend.getCondVisibility('Window.IsActive(selectdialog)'):
                if auto_pick:
                    if pick['seen'] is None:
                        pick['seen'] = now
                    elif not pick['picked'] and now - pick['seen'] >= .4:
                        backend.executebuiltin('Action(Select)')
                        logger('sports: picked the first link in Crew\'s chooser')
                        pick['picked'] = True
                return True
            pick['seen'], pick['picked'] = None, False
            return False
    def advance(why):
        """Stop what is on, then open the next choice (raises when none is left)."""
        nonlocal current_index, check, choice_began, failed_through
        if current_index + 1 >= len(choices):
            raise RuntimeError('native queue exhausted')
        failed_through = current_index
        logger('jet: a source failed (%s, choice %d)' % (why, current_index + 1))
        player.stop()
        backend.sleep(300)   # let Kodi report this Stop before the observer's flags are cleared for the next choice
        backend.executebuiltin('Dialog.Close(okdialog)')
        player.failed = player.stopped = player.started = player.ready = False
        current_index += 1
        playlist.clear()
        stage(current_index)
        check, choice_began = health_mod.Watch(), clock()
        player.play(playlist, startpos=0)

    try:
        stage(0)
        # Build 611 (phone log): player.play() does not return until Crew has resolved the link, and Crew's chooser appears during that wait, so
        # nothing answered it (the owner had to tap). A watcher answers it while play() is blocked; the loop below shares its state.
        watching = threading.Event()
        def watch():
            while not watching.is_set():
                try:
                    chooser_up(clock())
                except Exception:
                    pass
                time.sleep(.2)
        threading.Thread(target=watch, daemon=True).start()
        try:
            player.play(playlist)
        finally:
            watching.set()
        previous = clock()
        while not monitor.abortRequested():
            backend.sleep(200)  # permits native Player callbacks on the script thread
            if not owns_queue():
                raise InterruptedError('a newer play request replaced this queue')
            now = clock()
            # A person choosing a nested link is not a slow or failed server.
            if chooser_up(now):
                began += now - previous
                choice_began += now - previous
            previous = now
            if not player.ready and now - began >= timeout:
                raise InterruptedError('native sports opening timed out')
            position = playlist.getposition()
            # Kodi also reports a user's stop during opening as a pre-AV
            # Stop. Never infer failure from that ambiguous callback.
            if player.stopped and not player.failed:
                logger('sports: native opening stopped; queue cancelled')
                raise InterruptedError('native opening stopped')
            if player.failed and not player.ready:
                current = current_index
                for n in range(failed_through + 1, current + 1):
                    logger('jet: a source failed (native media open failed, choice %d)' % (n + 1))
                    health.fail(choices[n][1], 'would not open')
                    failed_through = n
                # Only a recorded VideoPlayer error closes its own media-error
                # dialog; authorization/refusal dialogs do not trigger this hook.
                backend.executebuiltin('Dialog.Close(okdialog)')
                backend.sleep(100)
                if current + 1 >= len(choices):
                    raise RuntimeError('native queue exhausted')
                player.failed = player.stopped = player.started = False
                current_index = current + 1
                playlist.clear()
                stage(current_index)
                check, choice_began = health_mod.Watch(), clock()
                player.play(playlist, startpos=0)
                continue
            if position < 0 and not player.isPlayingVideo():
                if backend.getCondVisibility('Window.IsActive(okdialog)'):
                    raise InterruptedError('native opening ended with a dialog')
                # Crew often plays its resolved stream itself (the playlist then no longer holds our item, position -1) while the stream is
                # still opening. Build 611 (Crew's progress box now silent) stopped that playback 0.2 s after Crew opened it, because the
                # progress box used to be what kept this check from firing. Media that Kodi has begun to open or play is not an ended opening.
                taking_over = player.started or backend.getCondVisibility('Player.HasMedia')
                if now - began > 1 and not taking_over and not backend.getCondVisibility('Window.IsActive(progressdialog)') and not backend.getCondVisibility('Window.IsActive(selectdialog)'):
                    logger('sports: native opening ended without a confirmed error; queue cancelled')
                    raise InterruptedError('native opening ended')
            if player.ready and player.isPlayingVideo():
                try:
                    position_seconds = player.getTime()
                except (RuntimeError, AttributeError, ValueError):
                    position_seconds = None
                stats = health_mod.read_stats(info) if info else {}
                verdict = check.feed(now, position_seconds, stats)
                if verdict == 'good':
                    health.ok(choices[current_index][1], check.stats)
                    logger('sports: playing (native addon queue)')
                    logger('sports: stream check: %s is playing (%s)' % (choices[current_index][1], health_mod.describe(check.stats)))
                    return True
                if verdict == 'bad':
                    logger('sports: stream check: %s is not usable (%s)' % (choices[current_index][1], check.reason))
                    health.fail(choices[current_index][1], check.reason)
                    advance('stream check')
                    continue
            elif len(choices) > current_index + 1 and not player.ready and now - choice_began >= health_mod.FIRST_PICTURE:
                # One source that never shows a picture must not hold the other four for the whole timeout.
                logger('sports: stream check: %s showed no picture in %d s' % (choices[current_index][1], health_mod.FIRST_PICTURE))
                health.fail(choices[current_index][1], 'no picture')
                advance('no picture')
                continue
            if now - began >= timeout + (health_mod.OBSERVE + health_mod.STALL if player.ready else 0):   # a picture that has begun gets its checking time
                # A stop can remain queued while Kodi is blocked opening media.
                # Do not launch an alternate after an ambiguous timeout.
                raise InterruptedError('native sports opening timed out')
        raise InterruptedError('Kodi shutting down')
    finally:
        # This must not play another provider when the successful game ends.
        if owns_queue():
            playlist.clear()
            if not player.ready: player.stop()
            if home is not None and (player.ready or not keep_owner_on_failure): home.clearProperty(OWNER)
