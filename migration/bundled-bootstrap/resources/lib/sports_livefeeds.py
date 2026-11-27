"""LiveFeeds (cdnsport.ru and topsurge.st match lists), read by us. Port of the JetExtractors LiveFeeds scraper (MIT,
(c) 2020 t4ils) with our own fetching and embed resolver; nothing here imports The Loop or JetExtractors."""
import json
import time
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import urlsplit

CDN = 'https://cdnsport.ru/data.json'
TOP = 'https://topsurge.st/api_proxy.php'
NAME = 'IndependentLiveFeeds'
TTL = 60.0
TRIES = 6


def norm(text):
    return ' '.join((text or '').lower().split())


def parse(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


class LiveFeeds:
    name = NAME

    def __init__(self, get=None, clock=time.time):
        from sports_independent import fetch
        self.get, self.clock = get or fetch, clock
        self.cache = (0.0, None, None)

    def feeds(self):
        stamp, cdn, top = self.cache
        if cdn is not None or top is not None:
            if self.clock() - stamp < TTL:
                return cdn or {}, top or {}
        cdn = top = None
        for url, referer in ((CDN, 'https://cdnsport.ru/'), (TOP, 'https://topsurge.st/')):
            try:
                data = parse(self.get(url, referer)[1])
            except Exception:
                data = None
            if url == CDN:
                cdn = data
            else:
                top = data
        if cdn is None and top is None:
            raise RuntimeError('LiveFeeds has no feed')
        self.cache = (self.clock(), cdn, top)
        return cdn or {}, top or {}

    def get_items(self):
        from sports_independent import Link
        cdn, top = self.feeds()
        items, seen = [], []
        for source, key, host in ((cdn, 'id', 'https://cdnsport.ru/#'), (top, 'slug', 'https://topsurge.st/#')):
            for match in source.get('matches') or []:
                if not isinstance(match, dict) or not match.get(key):
                    continue
                one, two = (match.get('team1') or '').strip(), (match.get('team2') or '').strip()
                title = one + ' vs ' + two if two else one
                if not title:
                    continue
                status = (match.get('status') or '').strip().lower()
                start = None
                stamp = match.get('datetime_utc')
                if stamp:
                    try:
                        start = datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone().replace(tzinfo=None)
                    except ValueError:
                        pass
                elif match.get('startTimestamp'):
                    try:
                        start = datetime.fromtimestamp(int(match['startTimestamp']) / 1000)
                    except (ValueError, OSError):
                        pass
                # One game once (both feeds list it), but the sessions of a race weekend share a name and differ by time.
                at = int(start.timestamp()) if start else None
                if any(t == norm(title) and (a is None or at is None or abs(a - at) < 1800) for t, a in seen):
                    continue
                seen.append((norm(title), at))
                items.append(SimpleNamespace(title=title, links=[Link(host + str(match[key]))], starttime=start,
                                             status='LIVE' if status == 'live' else status.capitalize(), league=match.get('league') or ''))
        return items

    def candidates(self, address):
        """Embed page addresses listed for the game (both feeds)."""
        cdn, top = self.feeds()
        fragment = urlsplit(address).fragment
        mine = None
        for source, key in ((cdn, 'id'), (top, 'slug')):
            for match in source.get('matches') or []:
                if isinstance(match, dict) and str(match.get(key)) == fragment:
                    mine = match
        if mine is None:
            return []
        wanted = {norm((mine.get('team1') or '') + ' vs ' + (mine.get('team2') or '')), norm(mine.get('team1'))}
        wanted.add(norm((mine.get('team2') or '') + ' vs ' + (mine.get('team1') or '')))
        found = []
        for source in (cdn, top):
            for match in source.get('matches') or []:
                if not isinstance(match, dict):
                    continue
                if norm(match.get('matchstr')) not in wanted and not (match is mine):
                    continue
                for channel in match.get('channels') or []:
                    for url in (channel.get('links') or []) if isinstance(channel, dict) else []:
                        if isinstance(url, str) and url.startswith('http') and url not in found:
                            found.append(url)
        return found


def resolve(address, note=lambda message: None, feed=None, get=None):
    import sports_embed
    from sports_independent import fetch
    feed = feed or LiveFeeds()
    get = get or fetch
    pages = feed.candidates(address)
    note('livefeeds: %d embed pages' % len(pages))
    for page in pages[:TRIES]:
        result = sports_embed.resolve(page, 'https://cdnsport.ru/', get, note)
        if result:
            note('livefeeds: verified HLS playlist')
            return result
    raise RuntimeError('no verified HLS stream available')
