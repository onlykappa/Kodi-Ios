"""Read The Loop's public Kodi listings and retain its exact playback routes."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlsplit

ADDON = 'plugin.video.the-loop'
NAME = 'TheLoopRoute'


def valid_route(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme == 'plugin' and parsed.netloc == ADDON and not parsed.username and not parsed.password
    except (ValueError, TypeError):
        return False


def listing(path):
    if not valid_route(path):
        raise ValueError('invalid Loop route')
    import xbmc
    result = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Files.GetDirectory','params':{'directory':path,'media':'files','properties':['title']}})))
    if result.get('error'):
        raise RuntimeError('Loop listing unavailable')
    return result.get('result', {}).get('files', [])


def label(value):
    return re.sub(r'\[/?(?:COLOR[^\]]*|B|I)\]', '', value or '', flags=re.I).strip()



def prepare_proxy():
    """Patch only recognized readable proxy files; authorization files are untouched."""
    import sports_jet
    folder = sports_jet._folder('script.module.jetextractors')
    if not folder:
        return False
    try:
        import sports_loop_proxy_compat
        return sports_loop_proxy_compat.apply(folder)
    except (OSError, ValueError, KeyError):
        sports_jet.log('jet: local proxy compatibility patch unavailable')
        return False
