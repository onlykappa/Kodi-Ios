"""AllDebrid, for downloads that go straight to Google Drive (owner, build 160: "a movie im downloading goes onto my phone
still … if i do a large movie it wont ever download"; chose "AllDebrid straight to Drive").

AllDebrid fetches the torrent on its own servers (any size; instantly when it already has it) and gives an HTTPS link per
file; debrid_drive.py copies that link into Google Drive a few MB at a time. Nothing is written to the phone.

The key is the one Umbrella keeps (Umbrella › Accounts › AllDebrid: setting `alldebridtoken`), sent as a bearer token.
API: https://docs.alldebrid.com (v4). Pure functions over an injectable `request(method, url, data, headers)`.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.alldebrid.com'
AGENT = 'KodiIOS'
READY, FAILED = 4, 5          # magnet statusCode: 0-3 being fetched, 4 ready, 5 and up an error
VIDEO = ('.mkv', '.mp4', '.m4v', '.avi', '.mov', '.webm', '.ts', '.m2ts', '.mts', '.wmv', '.mpg', '.mpeg')


class Problem(Exception):
    """AllDebrid said no; str() is what to tell the owner."""


class Busy(RuntimeError):
    """AllDebrid could not be reached, or answered with something other than its JSON (a busy or maintenance page, an
    empty reply). Not a "no": debrid_drive tries again later (a RuntimeError, like a network error), and the words
    say what came back, so the log shows it (owner, build 191: Inception failed at once with "an answer this app
    cannot read", and nothing said what the answer was)."""


def describe(raw, code=None):
    """A short, safe description of a reply that is not AllDebrid's JSON."""
    text = (raw or b'').decode('utf-8', 'replace').strip()
    kind = 'an empty reply' if not text else ('a web page' if text.startswith('<') else 'text')
    first = re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', text)).strip()[:80]
    return '%s%s%s' % ('HTTP %d, ' % code if code else '', kind, (': "%s"' % first) if first else '')


ERRORS = {'AUTH_BAD_APIKEY': 'AllDebrid did not accept the key. Sign in to AllDebrid again in Umbrella › Accounts.',
          'AUTH_MISSING_APIKEY': 'Sign in to AllDebrid in Umbrella › Accounts first.',
          'AUTH_BLOCKED': 'AllDebrid blocked this sign-in; open the e-mail AllDebrid sent you to allow it.',
          'AUTH_USER_BANNED': 'AllDebrid says this account is banned.',
          'MUST_BE_PREMIUM': 'AllDebrid needs a premium subscription for this.',
          'MAGNET_TOO_MANY_ACTIVE': 'AllDebrid is already fetching as many torrents as it allows; this one waits.',
          'MAGNET_TOO_MANY': 'AllDebrid is already fetching as many torrents as it allows; this one waits.',
          'MAGNET_INVALID_ID': 'AllDebrid no longer has this torrent.',
          'MAGNET_NO_SERVER': 'AllDebrid cannot fetch this torrent right now.',
          'LINK_DOWN': 'AllDebrid could not fetch this file.'}


def token_from_settings(xml_text):
    """Umbrella's AllDebrid key from its settings.xml text ('' when not signed in)."""
    m = re.search(r'<setting id="alldebridtoken"[^>]*>([^<]*)</setting>', xml_text or '') or \
        re.search(r'<setting id="alldebridtoken" value="([^"]*)"', xml_text or '')
    return (m.group(1).strip() if m else '')


def default_request(method, url, data=None, headers=None, timeout=30):
    body = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    if body is not None:
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


class AllDebrid(object):
    def __init__(self, token, request=default_request):
        if not token:
            raise Problem(ERRORS['AUTH_MISSING_APIKEY'])
        self.token = token
        self.request = request

    def call(self, path, params=None, post=None):
        url = API + path + '?' + urllib.parse.urlencode(dict(params or {}, agent=AGENT), doseq=True)
        code = None
        try:
            raw = self.request('POST' if post is not None else 'GET', url, post, {'Authorization': 'Bearer ' + self.token})
        except urllib.error.HTTPError as error:
            code = error.code
            raw = error.read() if hasattr(error, 'read') else b''
            if not raw:
                raise Busy('AllDebrid did not answer (HTTP %d).' % error.code)
        except (OSError, ValueError) as error:
            raise Busy('AllDebrid could not be reached (%s).' % type(error).__name__)
        try:
            answer = json.loads(raw)
            if not isinstance(answer, dict):
                raise ValueError(answer)
        except ValueError:
            raise Busy('AllDebrid gave an answer this app cannot read (%s %s).' % (describe(raw, code), path))
        if answer.get('status') != 'success':
            error = answer.get('error') or {}
            raise Problem(ERRORS.get(error.get('code'), 'AllDebrid: %s' % (error.get('message') or 'unknown problem')))
        return answer.get('data') or {}

    def add(self, info_hash):
        """Give AllDebrid a torrent by its info-hash. Returns (magnet id, ready now)."""
        data = self.call('/v4/magnet/upload', post={'magnets[]': [info_hash]})
        magnet = (data.get('magnets') or [{}])[0]
        if magnet.get('error'):
            code = magnet['error'].get('code')
            raise Problem(ERRORS.get(code, 'AllDebrid: %s' % magnet['error'].get('message', code)))
        return str(magnet['id']), bool(magnet.get('ready'))

    def status(self, magnet_id):
        """(statusCode, fraction fetched 0..1, AllDebrid's words) for a torrent it is fetching."""
        data = self.call('/v4.1/magnet/status', {'id': magnet_id})
        magnet = data.get('magnets') or {}
        if isinstance(magnet, list):
            magnet = magnet[0] if magnet else {}
        code = int(magnet.get('statusCode', 0))
        size = float(magnet.get('size') or 0)
        done = float(magnet.get('downloaded') or 0)
        return code, (done / size if size else 0.0), str(magnet.get('status') or '')

    def files(self, magnet_id):
        """[(path inside the torrent, size, AllDebrid link)] for every file of a ready torrent."""
        data = self.call('/v4/magnet/files', post={'id[]': [magnet_id]})
        magnet = (data.get('magnets') or [{}])[0]
        out = []

        def walk(nodes, prefix):
            for node in nodes or []:
                name = str(node.get('n') or '')
                if 'e' in node:
                    walk(node['e'], prefix + name + '/')
                elif node.get('l'):
                    out.append((prefix + name, int(node.get('s') or 0), node['l']))
        walk(magnet.get('files'), '')
        return out

    def unlock(self, link):
        """(direct HTTPS URL, file name, size) for one AllDebrid link."""
        data = self.call('/v4/link/unlock', {'link': link})
        if not data.get('link'):
            raise Problem('AllDebrid did not give a download link for this file yet.')
        return data['link'], str(data.get('filename') or ''), int(data.get('filesize') or 0)


def pick(files, kind, season=None, episode=None, episodes=None, offset=None):
    """The video files to copy: the largest for a movie, the matching episode for an episode, every episode for a
    season. Samples and extras are left out."""
    videos = [f for f in files if f[0].lower().endswith(VIDEO) and not re.search(r'(?i)(^|[/._ -])(sample|trailer|extras?)([/._ -]|$)', f[0])]
    if kind == 'movie':
        return sorted(videos, key=lambda f: -f[1])[:1]
    def number(name):
        m = re.search(r'(?i)\bS(\d{1,2})[ ._-]?E(\d{1,3})\b', name) or re.search(r'\b(\d{1,2})x(\d{2,3})\b', name)
        return (int(m.group(1)), int(m.group(2))) if m else None
    if kind == 'episode' and season and episode:
        target = (int(season), int(episode))
        wanted = [f for f in videos if number(f[0].rsplit('/', 1)[-1]) == target]
        base = 0 if target[0] == 1 else offset
        if not wanted and base is not None:
            # Owner builds 317-328 (end-to-end check, scripts/test_download_e2e.py): a complete-series pack names episodes
            # by absolute number ("Naruto Shippuden Episode 006 ….mkv"); nothing matched S01E06 and every episode job
            # copied the pack's largest file (its film) as "S01E01". Season 1's episodes are the first absolute numbers.
            # Later seasons: absolute = the episodes before this season (TMDb, debrid_drive passes offset) + episode.
            wanted = [f for f in videos if not number(f[0].rsplit('/', 1)[-1]) and absolute(f[0]) == base + target[1]
                      and season_folder(f[0]) in (None, target[0])]
        if wanted:
            return sorted(wanted, key=lambda f: -f[1])[:1]
        # A torrent of one video is that episode; with several and none named so, nothing is copied (the job says so)
        # rather than the largest file.
        return videos if len(videos) == 1 else []
    if episodes and season:   # the episodes picked from a season (a pack holds them all)
        wanted = {(int(season), int(n)) for n in episodes}
        found = sorted([f for f in videos if number(f[0].rsplit('/', 1)[-1]) in wanted], key=lambda f: f[0])
        base = 0 if int(season) == 1 else offset
        if not found and base is not None:   # an absolute-numbered pack
            numbers = {base + int(n) for n in episodes}
            found = sorted([f for f in videos if not number(f[0].rsplit('/', 1)[-1]) and absolute(f[0]) in numbers], key=lambda f: f[0])
        return found
    numbered = [f for f in videos if number(f[0].rsplit('/', 1)[-1])]
    if kind == 'season' and str(season or '').isdigit():
        # Owner (build 252: "season 1-3 of naruto shippuden ... somehow its downloading everything", queue over 500): a
        # complete-series pack names episodes by absolute number ("Episode 001 Homecoming.mkv"), nothing matched SxxEyy
        # and every video in the torrent (500 episodes and the films) was queued for each season. A season copies only
        # that season: SxxEyy names first, then a "Season NN" / "S01" folder; never the whole pack.
        s = int(season)
        by_name = [f for f in numbered if number(f[0].rsplit('/', 1)[-1])[0] == s]
        if by_name:
            return sorted(by_name, key=lambda f: f[0])
        by_folder = [f for f in videos if season_folder(f[0]) == s]
        if by_folder:
            return sorted(by_folder, key=lambda f: f[0])
        if numbered:   # the pack is numbered by season, just not this one
            return []
    chosen = sorted(numbered or videos, key=lambda f: f[0])
    if kind == 'season' and len(chosen) > SEASON_MAX:
        raise TooMany(len(chosen))
    return chosen


SEASON_MAX = 60   # more video files than any season: a whole-series pack, never queued blindly


class TooMany(Exception):
    def __init__(self, count):
        Exception.__init__(self, 'This version holds %d videos (a whole series), not one season. Pick a season pack.' % count)
        self.count = count


ABSOLUTE = re.compile(r'(?i)(?:\bepisode[\s._-]*|\bep\.?[\s._-]*|\s[-–][\s._-]*|\bE)(\d{1,4})(?![\dpP])\b')


def absolute(path):
    """The episode number of a name with no season: 'Show Episode 006 Title.mkv', '[Sub] Show - 006 [1080p].mkv',
    'Show E006.mkv' -> 6; None when there is none."""
    base = re.sub(r'\[[^\]]*\]|\([^)]*\)', ' ', str(path).rsplit('/', 1)[-1])
    base = re.sub(r'[._]+', ' ', re.sub(r'\.[A-Za-z0-9]{2,4}$', '', base))
    m = ABSOLUTE.search(base)
    return int(m.group(1)) if m else None


def season_folder(path):
    """The season a file's folders name ('Show (001-500)/Season 01 (001-032)/Episode 001.mkv' -> 1), or None."""
    for part in str(path).split('/')[:-1]:
        m = re.search(r'(?i)\bseason[ ._-]*0*(\d{1,2})\b', part) or re.search(r'(?i)^S0*(\d{1,2})(?:\b|$)', part.strip())
        if m:
            return int(m.group(1))
    return None
