"""Rank game choices and let Kodi's native playlist skip failed Loop routes."""
import json
import time
import uuid
import sports_loop_routes as routes
import sports_merge

MAX_CHOICES = 32
OWNER = "KodiIOS.SportsNativeOwner"


def native_route(source):
    try:
        value = json.loads(source.get('play') or '')
        address = value['l']['address']
        return address if value.get('e') == routes.NAME and routes.valid_route(address) else None
    except (ValueError, KeyError, TypeError):
        return None


def automatic_source(sources):
    ordered = sorted(sources, key=lambda s: (-sports_merge.quality_rank(s.get('quality')), routes.source_rank(s.get('addon', ''))))
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


def play(queue, logger, backend=None, clock=time.monotonic, timeout=90, owner=None, keep_owner_on_failure=False):
    if backend is None:
        import xbmc as backend
    choices, seen = [], set()
    for source in queue[:MAX_CHOICES]:
        address = native_route(source)
        if address and address not in seen:
            seen.add(address)
            choices.append((address, source.get('addon') or 'Sports'))
    if not choices:
        raise ValueError('no native Loop routes')
    routes.prepare_proxy()

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
    def owns_queue():
        return home is None or home.getProperty(OWNER) == owner
    # Drain the previous attempt's Stop before registering this observer.
    backend.Player().stop()
    backend.sleep(100)
    playlist = backend.PlayList(backend.PLAYLIST_VIDEO)
    playlist.clear()
    for address, name in choices:
        item = xbmcgui.ListItem(label=name)
        item.setProperty('IsPlayable', 'true')
        playlist.add(address, item)
    player = Observer()
    monitor = backend.Monitor()
    logger('sports: opening native Loop queue (%d choices)' % len(choices))
    began, previous, failed_through = clock(), clock(), -1
    current_index = 0
    try:
        player.play(playlist)
        while not monitor.abortRequested():
            backend.sleep(200)  # permits native Player callbacks on the script thread
            if not owns_queue():
                raise InterruptedError('a newer play request replaced this queue')
            now = clock()
            # A person choosing a nested link is not a slow or failed server.
            if backend.getCondVisibility('Window.IsActive(selectdialog)'):
                began += now - previous
            previous = now
            if not player.ready and now - began >= timeout:
                raise RuntimeError('native sports opening timed out')
            position = playlist.getposition()
            if (player.failed or (player.stopped and player.started)) and not player.ready:
                current = max(current_index, 0, position)
                for n in range(failed_through + 1, current + 1):
                    logger('jet: a source failed (native media open failed, choice %d)' % (n + 1))
                    failed_through = n
                # Only a recorded VideoPlayer error closes its own media-error
                # dialog; authorization/refusal dialogs do not trigger this hook.
                backend.executebuiltin('Dialog.Close(okdialog)')
                backend.sleep(100)
                if current + 1 >= len(choices):
                    raise RuntimeError('native queue exhausted')
                player.failed = player.stopped = player.started = False
                current_index = current + 1
                if playlist.size() != len(choices):
                    playlist.clear()
                    for address, name in choices:
                        item = xbmcgui.ListItem(label=name)
                        item.setProperty('IsPlayable','true')
                        playlist.add(address,item)
                player.play(playlist, startpos=current_index)
                continue
            if position < 0 and not player.isPlayingVideo():
                if backend.getCondVisibility('Window.IsActive(okdialog)'):
                    raise RuntimeError('no native source opened')
                if now - began > 1 and not backend.getCondVisibility('Window.IsActive(progressdialog)') and not backend.getCondVisibility('Window.IsActive(selectdialog)'):
                    for n in range(failed_through + 1, len(choices)):
                        logger('jet: a source failed (native open failed, choice %d)' % (n + 1))
                    raise RuntimeError('native queue exhausted')
            for n in range(failed_through + 1, max(0, position)):
                logger('jet: a source failed (native open failed, choice %d)' % (n + 1))
                failed_through = n
            if player.ready and player.isPlayingVideo():
                logger('sports: playing (native Loop queue)')
                return True
            if now - began >= timeout:
                raise RuntimeError('native sports opening timed out')
        raise InterruptedError('Kodi shutting down')
    finally:
        # This must not play another provider when the successful game ends.
        if owns_queue():
            playlist.clear()
            if not player.ready: player.stop()
            if home is not None and (player.ready or not keep_owner_on_failure): home.clearProperty(OWNER)
