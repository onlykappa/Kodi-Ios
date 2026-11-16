"""Sports: The Loop's provider (DEC-055, DEC-057), step 1: find out what its menus really contain.

The Loop's code is not part of this project, and its listings must not be guessed. Until its adapter is written from real data, the
provider below answers "no source" (the pages say "Can't load ... right now") and, once a day at most, lists the add-ons' MENU FOLDERS
through Kodi (Files.GetDirectory; folders only: no item is opened, played or resolved). The tree goes to
special://profile/addon_data/service.kodi.ios.bootstrap/sports-discovery.json and the first lines to kodi.log ("Kodi iOS Sports discovery:"),
bounded in depth, items and time. The owner's log then shows what to parse.

An adapter turns an add-on's items into the records sports_merge.merge() combines; it is added here once the tree is known.
"""
import json
import os
import threading
import time

import sports_model

PLUGINS = ('plugin.video.the-loop', 'plugin.video.loopguide', 'plugin.video.looptv', 'plugin.video.thecrew')
# Where the walk starts when the add-on's front page is not sports: The Crew's sports menu ("Bluehat", owner decision 2026-11-15:
# The Crew and The Loop are the two main sports providers).
START = {'plugin.video.thecrew': 'plugin://plugin.video.thecrew/?action=bluehat'}
DEPTH, NODES, SECONDS, LOG_LINES = 3, 60, 25, 120
SAMPLES = 8                          # playable items recorded per folder (the folder's `items` says how many there are)
EVERY = 12 * 3600                     # seconds between two discoveries
FOLDER = 'special://profile/addon_data/service.kodi.ios.bootstrap/'
OUT = 'sports-discovery.json'
PROPERTIES = ['title', 'plot', 'thumbnail', 'file', 'genre', 'runtime']


def _short(text, n=160):
    text = str(text or '').replace('\n', ' ').strip()
    return text if len(text) <= n else text[:n] + ' [cut]'


def kodi_rpc(xbmc):
    """A function (method, params) -> result over Kodi's JSON-RPC (raises ValueError on an error answer)."""
    def call(method, params=None):
        answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
        if answer.get('error'):
            raise ValueError(str((answer['error'] or {}).get('message') or 'JSON-RPC error'))
        return answer.get('result') or {}
    return call


def walk(rpc, root, clock=time.monotonic, depth=DEPTH, nodes=NODES, seconds=SECONDS, note=None):
    """The menu tree of one add-on as a flat list of {'depth','path','label','folder','plot','items'}; folders are listed and
    descended (breadth first), playable items are only recorded. Stops at `nodes` entries or `seconds`. Raises nothing for a
    folder that fails: the failure is recorded on it."""
    deadline = clock() + seconds
    out, queue = [], [(root, 0, '')]
    while queue and len(out) < nodes and clock() < deadline:
        path, level, label = queue.pop(0)
        began = clock()
        try:
            listing = rpc('Files.GetDirectory', {'directory': path, 'media': 'files', 'properties': PROPERTIES,
                                                'limits': {'start': 0, 'end': nodes}}).get('files') or []
            error = ''
        except Exception as exc:
            listing, error = [], '%s: %s' % (type(exc).__name__, _short(exc, 100))
        if note:   # one line per folder as it answers: a log exported while the walk runs, or after it was cut short, still shows how far it got
            try:
                note('%s%s %d items in %.1f s%s' % ('  ' * level, _short(label or path, 60), len(listing), clock() - began, ' | ' + error if error else ''))
            except Exception:
                pass
        entry = {'depth': level, 'path': _short(path), 'label': _short(label, 80), 'folder': True, 'items': len(listing), 'plot': '', 'error': error}
        out.append(entry)
        shown = 0
        for item in listing:
            folder = item.get('filetype') == 'directory'
            if folder and level + 1 < depth:
                queue.append((item.get('file') or '', level + 1, item.get('label') or item.get('title') or ''))
                continue
            if not folder:
                shown += 1
            if (folder or shown <= SAMPLES) and len(out) < nodes:   # a flood of items must not use up the room folders need
                out.append({'depth': level + 1, 'path': _short(item.get('file')), 'label': _short(item.get('label') or item.get('title'), 80),
                            'folder': folder, 'items': 0, 'plot': _short(item.get('plot'), 80), 'error': ''})
    return out


def discover(rpc, clock=time.monotonic, now=time.time, progress=None, build='', note=None):
    """{'time', 'build', 'plugins': {id: {'nodes': [...]}}} for the Loop add-ons that answer; an add-on that is missing says so.
    progress(result) is called after each add-on, so an early log export already shows the ones that finished."""
    result = {'time': int(now()), 'build': build, 'plugins': {}}
    for plugin in PLUGINS:
        if note:
            note('walking %s' % plugin)
        try:
            result['plugins'][plugin] = {'nodes': walk(rpc, START.get(plugin) or 'plugin://%s/' % plugin, clock=clock,
                                                       note=(lambda line, plugin=plugin: note('%s %s' % (plugin.split('.')[-1], line))) if note else None)}
        except Exception as exc:   # nothing here may stop the page
            result['plugins'][plugin] = {'nodes': [], 'error': '%s: %s' % (type(exc).__name__, _short(exc, 100))}
        if progress:
            try:
                progress(plugin, {'plugins': {plugin: result['plugins'][plugin]}})
            except Exception:
                pass
    return result


def build_id(here=os.path.dirname(os.path.abspath(__file__))):
    """The installed build's commit (bootstrap/build.json), or '' when unknown."""
    try:
        return str(json.load(open(os.path.join(here, '..', '..', 'build.json'), encoding='utf-8')).get('commit') or '')
    except (OSError, ValueError, AttributeError):
        return ''


def log_lines(result):
    """The first LOG_LINES lines of the tree for kodi.log, one folder or item per line."""
    lines = []
    for plugin, data in result['plugins'].items():
        if data.get('error'):
            lines.append('%s: %s' % (plugin, data['error']))
        for n in data['nodes']:
            lines.append('%s %s%s | %s | %s%s%s' % (plugin.split('.')[-1], '  ' * n['depth'], 'folder' if n['folder'] else 'item', n['label'], n['path'],
                                                  ' | %d items' % n['items'] if n['folder'] else '', ' | ' + n['error'] if n['error'] else ''))
    return lines[:LOG_LINES]


ASK = 'KodiIOS.SportsDiscover'   # Home window property: the Sports page sets it; the service runs the walk
RETRY = 10 * 60   # an earlier discovery that listed no add-on at all (they were not installed yet) is tried again after this


def due(path, now, exists=os.path.exists, mtime=os.path.getmtime, wait=EVERY):
    """True when no discovery has been written in the last `wait` seconds."""
    try:
        return not exists(path) or now - mtime(path) >= wait
    except OSError:
        return True


def wait_for(path, read=None, build=''):
    """EVERY when the last discovery listed at least one add-on, else RETRY: build 544's first run found the add-ons missing (build 538
    had saved an empty answer) and so skipped the walk for twelve hours, which hid the Loop add-ons that had since been installed."""
    try:
        if read:
            data = read(path)
        else:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        if build and data.get('build') != build:
            return 0   # a different build than the one that made the answer: look again once (the add-ons or the walk may have changed)
        return EVERY if any(d.get('nodes') for d in (data.get('plugins') or {}).values()) else RETRY
    except (OSError, ValueError, AttributeError):
        return RETRY


def discover_once(xbmc, xbmcvfs, log, now=time.time):
    """Run a discovery unless one ran lately; write the tree and log it. Blocks for up to about 75 seconds: call it on its own thread."""
    folder = xbmcvfs.translatePath(FOLDER)
    path = os.path.join(folder, OUT)
    if not due(path, now(), wait=wait_for(path, build=build_id())):
        return None
    def each(plugin, part):   # logged as each add-on finishes: a log exported early still has the first ones
        for line in log_lines(part):
            log('discovery: ' + line)
    log('discovery: started')
    result = discover(kodi_rpc(xbmc), now=now, progress=each, build=build_id(), note=lambda line: log('discovery: ' + line))
    os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    log('discovery: written to %s (%d add-ons listed)' % (OUT, sum(1 for d in result['plugins'].values() if d['nodes'])))
    return result


class LoopProvider:
    """The Loop as a provider. There is no adapter yet, so every call says "no source" and, once per process, starts the discovery."""

    def __init__(self, starter=None):
        self.started = False
        self.starter = starter or self._start

    def _start(self):
        """Ask the service to run the discovery. Owner log 70f32729: it used to run on a thread of the page's own script, which Kodi ends
        when the page closes, so a walk that takes a minute or more never finished (nothing was logged). The service lives as long as the app."""
        try:
            import xbmcgui
        except ImportError:   # not inside Kodi (tests, tools): nothing to list
            return
        try:
            xbmcgui.Window(10000).setProperty(ASK, '1')
        except Exception:
            pass

    def _none(self):
        if not self.started:
            self.started = True
            self.starter()
        raise sports_model.SportsUnavailable('no adapter for The Loop yet')

    def refresh(self):
        self._none()

    def overview(self):
        self._none()

    def live_games(self, league=None):
        self._none()

    def upcoming_games(self, league=None):
        self._none()

    def leagues(self):
        self._none()

    def game(self, gid):
        self._none()


def serve(xbmc, xbmcvfs, xbmcgui, wait, log, first_delay=45, every=5):
    """The service's loop: a walk first_delay seconds after startup (the Loop add-ons need the app up), then whenever the Sports page asks. discover_once itself
    skips a walk that is not due (twelve hours after a good one, ten minutes after an empty one, and again for each new build)."""
    window = xbmcgui.Window(10000)
    if wait(first_delay):
        return
    asked = True
    while True:
        if asked:
            window.clearProperty(ASK)
            try:
                discover_once(xbmc, xbmcvfs, log)
            except Exception as exc:   # a walk must never stop the service
                log('discovery: skipped (%s)' % type(exc).__name__)
        if wait(every):
            return
        asked = window.getProperty(ASK) == '1'
