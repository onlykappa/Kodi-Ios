"""Deadline-aware isolated adapter host; never starts playback, downloads or provider dialogs."""
from contextlib import ExitStack, contextmanager
import importlib
import io
import json
import os
from pathlib import Path
import re
import socket
import sys
import threading
import time
import xml.etree.ElementTree as ET
from unittest.mock import patch
import provider_fallback as fallback

# Read-through only: existing provider credentials always take precedence; no token is copied to disk.
ACCOUNT_KEYS = {
    'jacktook': {'alldebrid_token': None, 'alldebrid_enabled': 'enabled'},
    'pov': {'ad.token': None, 'ad.enabled': 'enabled', 'ad.torrent.enabled': 'enabled'},
    'prism': {'alldebrid.apikey': None, 'alldebrid.enabled': 'enabled'},
    'thecrew': {'alldebridtoken': None, 'alldebrid.enabled': 'enabled'},
    'otaku': {'alldebrid.token': None, 'alldebrid.enabled': 'enabled'},
}


class AddonSettings:
    def __init__(self, native, token, keys):
        self.native, self.token, self.keys = native, token, keys

    def __getattr__(self, name):
        return getattr(self.native, name)

    def getSetting(self, key):
        value = self.native.getSetting(key)
        if self.token and self.keys.get(key) == 'enabled' and value == 'false':
            import xml.etree.ElementTree as ET
            try:
                import xbmcvfs
                path = Path(xbmcvfs.translatePath(self.native.getAddonInfo('profile'))) / 'settings.xml'
                saved = ET.parse(path).getroot().find(".//setting[@id='%s']" % key)
                if saved is None:
                    return 'true'
            except FileNotFoundError:
                return 'true'
            except Exception:
                pass
        # Do not enable an account the person explicitly disabled. Unset defaults are distinguished from saved false.
        if value or not self.token or key not in self.keys:
            return value
        return 'true' if self.keys[key] == 'enabled' else self.token

    def getSettingBool(self, key):
        return self.getSetting(key).lower() == 'true'

    def openSettings(self):
        raise RuntimeError('Provider requires configuration')


class Context:
    def __init__(self, provider, folder, deadline, addon, profile, clock=time.monotonic):
        self.provider = provider
        self.addon_id = fallback.ADDONS[provider]
        self.addon_path = addon.getAddonInfo('path')
        self.settings = addon
        self.profile = str(profile)
        self.folder, self.deadline, self.clock = Path(folder), float(deadline), clock
        self.session = None
        self.import_module = importlib.import_module

    def cancelled(self):
        return not self.folder.is_dir() or (self.folder / 'cancel').exists()

    def remaining(self):
        return max(0.0, self.deadline - self.clock())

    def check(self):
        fallback._check(self.cancelled, self.deadline, self.clock)


def module_paths(addon, xbmcaddon):
    """RunScript inherits bootstrap's dependencies, so resolve the selected add-on's Python imports explicitly."""
    paths=[];seen=set()
    def visit(native):
        root=Path(native.getAddonInfo('path')).resolve()
        if root in seen:return
        seen.add(root);manifest=ET.parse(root/'addon.xml').getroot()
        for extension in manifest.findall("extension[@point='xbmc.python.module']"):
            library=extension.get('library') or ''
            target=(root/library).resolve()
            if not target.is_relative_to(root):raise ValueError('Invalid provider module path')
            if target.is_dir() and str(target) not in paths:paths.append(str(target))
        for dependency in manifest.findall('requires/import'):
            ident=dependency.get('addon') or ''
            if not ident or ident.startswith('xbmc.'):continue
            try:visit(xbmcaddon.Addon(ident))
            except Exception:
                if dependency.get('optional')!='true':raise
    visit(addon)
    return paths


class QuietProgress:
    def __init__(self, context): self.context = context
    def create(self, *args, **kwargs): self.context.check()
    def update(self, *args, **kwargs): self.context.check()
    def close(self): pass
    def iscanceled(self): return self.context.cancelled() or self.context.remaining() <= 0
    def isFinished(self): return False


class DiscardOutput(io.TextIOBase):
    def write(self, text): return len(text)


class CheckedResponse:
    def __init__(self, response, context, release=lambda response:None): self.response, self.context, self.release = response, context, release
    def __getattr__(self, key): return getattr(self.response, key)
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self):
        self.release(self.response)
        self.response.close()
    def read(self, size=-1):
        self.context.check()
        value = self.response.read(size)
        self.context.check()
        return value


def interrupt_response(response):
    """Closing a buffered reader can wait on its read lock; shut down its socket before closing it."""
    pending=[response];seen=set()
    while pending:
        current=pending.pop()
        if id(current) in seen:continue
        seen.add(id(current))
        if isinstance(current,socket.socket):
            try:current.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        for name in ('raw','_fp','fp','_sock','sock','_connection'):
            try:child=getattr(current,name,None)
            except Exception:continue
            if child is not None and id(child) not in seen:pending.append(child)
    def close():
        try:response.close()
        except Exception:pass
    threading.Thread(target=close,daemon=True).start()


@contextmanager
def guarded(context, xbmc, xbmcgui, xbmcaddon):
    """Provider defaults/settings/HTTP/GUI changes are interpreter-local and always restored."""
    import urllib.request
    with ExitStack() as stack:
        responses=set();response_lock=threading.Lock();stopped=threading.Event()
        def release(response):
            with response_lock:responses.discard(response)
        def track(response):
            with response_lock:responses.add(response)
            try:context.check()
            except Exception:
                release(response);interrupt_response(response);raise
            return response
        def interrupt_all():
            with response_lock:
                current=tuple(responses);responses.clear()
            for response in current:interrupt_response(response)
        def watch():
            while not stopped.wait(.025):
                if context.cancelled() or context.remaining()<=0:
                    interrupt_all();return
        watcher=threading.Thread(target=watch,daemon=True);watcher.start()
        def finish():
            stopped.set();interrupt_all();watcher.join(.1)
        stack.callback(finish)
        original_addon = xbmcaddon.Addon
        try: token = original_addon('plugin.video.umbrella').getSetting('alldebridtoken')
        except Exception: token = ''
        def addon(ident=None, **kwargs):
            ident = ident or kwargs.pop('id', None) or context.addon_id
            native = original_addon(ident, **kwargs)
            return AddonSettings(native, token, ACCOUNT_KEYS.get(context.provider, {})) if ident == context.addon_id else native
        stack.enter_context(patch.object(xbmcaddon, 'Addon', addon))
        context.settings = addon(context.addon_id)
        stack.enter_context(patch.object(xbmc, 'log', lambda *a, **k: None))
        # Upstream debug output may contain signed URLs or account data. Only the parent's coarse status is logged.
        stack.enter_context(patch('sys.stdout', DiscardOutput()))
        stack.enter_context(patch('sys.stderr', DiscardOutput()))
        def builtin(command, *args, **kwargs):
            context.check()
            if str(command).lower().startswith(('dialog.close(', 'setproperty(', 'clearproperty(')):
                return None
            raise RuntimeError('Provider attempted an interactive action')
        stack.enter_context(patch.object(xbmc, 'executebuiltin', builtin))
        for name in ('DialogProgress', 'DialogProgressBG'):
            if hasattr(xbmcgui, name):
                stack.enter_context(patch.object(xbmcgui, name, lambda *a, **k: QuietProgress(context)))
        original_dialog = xbmcgui.Dialog
        class Dialog:
            def __init__(self, *a, **k): pass
            def notification(self, *a, **k): context.check()
            def ok(self, *a, **k): context.check(); return False
            def yesno(self, *a, **k): context.check(); return False
            def select(self, *a, **k): context.check(); return -1
            def input(self, *a, **k): context.check(); return ''
            def __getattr__(self, key):
                raise RuntimeError('Provider requested an unsupported dialog')
        stack.enter_context(patch.object(xbmcgui, 'Dialog', Dialog))
        original_open = urllib.request.OpenerDirector.open
        def open_url(opener, request, data=None, timeout=None, *args, **kwargs):
            context.check()
            budget = context.remaining() if timeout is None else min(float(timeout), context.remaining())
            response = track(original_open(opener, request, data, max(.001,budget), *args, **kwargs))
            return CheckedResponse(response, context, release)
        stack.enter_context(patch.object(urllib.request.OpenerDirector, 'open', open_url))
        try:
            import requests
            original_request = requests.sessions.Session.request
            def request(session, method, url, **kwargs):
                context.check()
                budget = context.remaining()
                limit = kwargs.get('timeout')
                if isinstance(limit, (tuple, list)):
                    budget = min([budget] + [float(v) for v in limit if v is not None])
                elif limit is not None:
                    budget = min(budget, float(limit))
                kwargs['timeout'] = max(.001, budget)
                # Obtain the response at headers. The watchdog can then interrupt a drip-fed body; requests'
                # normal stream=False consumes it before returning and only enforces an inactivity timeout.
                kwargs['stream'] = True
                result = track(original_request(session, method, url, **kwargs))
                original_close=result.close
                def close():
                    release(result);original_close()
                result.close=close
                return result
            stack.enter_context(patch.object(requests.sessions.Session, 'request', request))
            context.session = requests.Session()
            stack.callback(context.session.close)
        except ImportError:
            pass
        yield context


def run(folder, profile, xbmc=None, xbmcgui=None, xbmcaddon=None):
    if xbmc is None:
        import xbmc, xbmcgui, xbmcaddon
    folder = Path(folder)
    request_file = folder / 'request.json'
    if request_file.is_symlink() or request_file.stat().st_size > fallback.MAX_JOB_BYTES:
        raise ValueError('Invalid provider request')
    payload = json.loads(request_file.read_text())
    provider, operation = payload.get('provider'), payload.get('operation')
    if provider not in fallback.PROVIDERS or operation not in ('search', 'resolve'):
        raise ValueError('Unknown provider operation')
    native = xbmcaddon.Addon(fallback.ADDONS[provider])
    context = Context(provider, folder, payload['deadline'], native, profile)
    context.check()
    # Defaults to this provider, not the bootstrap service. Separate RunScript invocations avoid lib/resources collisions.
    imports=module_paths(native,xbmcaddon)
    paths = [context.addon_path] + imports
    if provider == 'pov': paths += [os.path.join(context.addon_path, 'lib'), os.path.join(context.addon_path, 'resources/lib')]
    # Existing Kodi dependency paths may be present behind unrelated add-ons; move this graph to the front.
    for path in reversed(list(dict.fromkeys(paths))):
        while path in sys.path: sys.path.remove(path)
        sys.path.insert(0, path)
    # Upstream modules parse plugin argv even during headless source collection.
    original_argv = sys.argv
    sys.argv = ['plugin://' + context.addon_id, '1', '']
    for name in tuple(sys.modules):
        if name in ('resources', 'lib', 'modules', 'pov') or name.startswith(('resources.', 'lib.', 'modules.', 'pov.')):
            sys.modules.pop(name, None)
    status, value = 'offline', None
    try:
        with guarded(context, xbmc, xbmcgui, xbmcaddon):
            adapter = importlib.import_module('provider_adapters.' + provider)
            context.check()
            request = payload.get('request') or {}
            value = adapter.search(request, context) if operation == 'search' else adapter.resolve(payload.get('candidate') or {}, context)
            context.check()
            if operation == 'search':
                value = [c for c in list(value or [])[:fallback.MAX_CANDIDATES] if isinstance(c, dict)]
            status = 'ok'
    except fallback.Canceled:
        status = 'canceled'
    except TimeoutError:
        status = 'timeout'
    except Exception:
        status = 'offline'
    sys.argv = original_argv
    if folder.is_dir() and not context.cancelled() and context.remaining() > 0:
        fallback.write_private(folder / 'result.json', {'status': status, 'value': value if status == 'ok' else None})


def main(args):
    if len(args) != 1 or not re.fullmatch('[0-9a-f]{32}', args[0]):
        return
    import xbmc, xbmcgui, xbmcaddon, xbmcvfs
    profile = xbmcvfs.translatePath('special://profile/')
    root = Path(profile) / 'addon_data/service.kodi.ios.bootstrap/provider-fallback-jobs'
    folder = root / args[0]
    if root.is_symlink() or folder.is_symlink() or not folder.is_dir():
        return
    try:
        run(folder, profile, xbmc, xbmcgui, xbmcaddon)
    except Exception:
        # No traceback with native resolver data/URLs. Parent owns timeout/fallback diagnostics.
        pass
