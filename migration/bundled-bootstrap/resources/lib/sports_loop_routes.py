"""Read The Loop's public Kodi listings and retain its exact playback routes."""
import json
import re
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlsplit

ADDON = 'plugin.video.the-loop'
NAME = 'TheLoopRoute'
# Providers observed returning matched games get early background slots.
PRIORITY = ('FawaNews','LiveFeeds','ReedStreams','Embedsport2','EmbedHD API','720pStream','XYZAlt','StreamEastVG','MethStreams')

def source_rank(name):
    name = label(name).removeprefix('Loop ')
    return PRIORITY.index(name) if name in PRIORITY else len(PRIORITY)


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


# Replay/account-input folders must not be opened by a background sports scan.
SKIP_LABELS = ('replay', 'fullfight', 'fullrace', 'fullmatch', 'iptv', 'telegram', 'ondemand', 'wrestling', 'tvgarden', 'nflvideo', 'rugbyvideo', 'sportsvideo', 'collegevideo', 'foxxy', 'cdnlivetv')


def title_pair(text):
    import sports_jet
    text = label(text).split('\n', 1)[0].split('|', 1)[-1].strip()
    text = re.sub(r'\s+---\s+CH\s+\d+.*$', '', text, flags=re.I)
    return sports_jet.teams(text)


def match_game(text, games):
    import sports_merge
    pair = title_pair(text)
    if not pair:
        return None
    matches = [g for g in games if
               (sports_merge.same_team(pair[0], g['away']['name']) and sports_merge.same_team(pair[1], g['home']['name'])) or
               (sports_merge.same_team(pair[1], g['away']['name']) and sports_merge.same_team(pair[0], g['home']['name']))]
    return matches[0] if len(matches) == 1 else None


class LoopSource:
    def __init__(self, title, route, games, read=listing):
        self.name = 'Loop ' + label(title)
        self.route, self.games, self.read = route, games, read

    def get_items(self):
        from sports_independent import Link
        items = []
        seen = set()
        for entry in self.read(self.route)[:512]:
            route = entry.get('file', '')
            if entry.get('filetype') == 'directory' or not valid_route(route) or route in seen:
                continue
            game = match_game(entry.get('title') or entry.get('label') or '', self.games)
            if not game:
                continue
            seen.add(route)
            items.append(SimpleNamespace(title=game['away']['name']+' vs '+game['home']['name'],
                         league=game['league_name'], status='LIVE' if game['state']=='live' else '',
                         starttime=datetime.fromtimestamp(game['start']), links=[Link(route)]))
        return items


def discover(read=listing, schedule=None):
    """Source workers over actual Loop routes; never import JetExtractors as our caller."""
    roots = read('plugin://' + ADDON + '/')
    zones = [entry for entry in roots if 'scraper zone' in label(entry.get('label')).lower() and entry.get('filetype')=='directory']
    if not zones:
        return []
    entries = read(zones[0]['file'])
    if schedule is None:
        import sports_espn
        provider = sports_espn.EspnProvider(fetch=lambda url: sports_espn.fetch_json(url, timeout=3))
        snapshot = provider._load()
        schedule = snapshot['live'] + snapshot['upcoming']
    return [LoopSource(entry.get('label',''), entry['file'], schedule, read) for entry in sorted(entries[:64], key=lambda entry:source_rank(entry.get('label','')))
            if entry.get('filetype')=='directory' and valid_route(entry.get('file','')) and
            not any(word in label(entry.get('label')).lower().replace(' ', '') for word in SKIP_LABELS)]


def warmup_proxy(wait, log, delay=3):
    """Prepare the shared repair for direct addon playback, without opening menus."""
    if wait(delay):
        return False
    try:
        ready = prepare_proxy()
        log('jet: shared proxy ready for native addon playback' if ready else
            'jet: shared proxy not prepared (addon absent or source revision unrecognized)')
        return ready
    except Exception as error:
        log('jet: shared proxy preparation failed (%s)' % type(error).__name__)
        return False
