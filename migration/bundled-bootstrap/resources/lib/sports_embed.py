"""Our own embed resolver for the sports sites we read ourselves (no The Loop, no JetExtractors).

Follows a page's iframes and looks for an HLS playlist in the page: plain addresses, base64 ``atob(...)`` strings and
Dean Edwards "packed" scripts. A candidate is only reported when its playlist really starts with ``#EXTM3U``.
The patterns are written for this project after reading what public embed pages look like; the approach (iframe hops,
m3u8 patterns) is the same one JetExtractors (MIT, (c) 2020 t4ils) uses. The packed-script unpacker is our own code.
"""
import base64
import html as htmllib
import re
from urllib.parse import urljoin, urlsplit

MAX_DEPTH = 4
AD_FRAMES = ('live_chat', 'live-chat', 'getbanner', 'ad.html', 'doubleclick', 'googlesyndication', 'youtube.com', 'facebook.com', 'twitter.com')
M3U8_PATTERNS = (
    r'(?:source|src|file|streamUrl|videoSrc|sourceUrl|playlistUrl|url|stream)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'["\']((?:https?:)?//[^"\'\s<>]+\.m3u8[^"\'\s<>]*)["\']',
    r'((?:https?:)?//[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)',
)


def unpack(source):
    """Undo Dean Edwards' p.a.c.k.e.r: eval(function(p,a,c,k,e,d){...}('payload',base,count,'w|o|r|d|s'.split('|'),0,{}))."""
    found = re.search(r"}\('(.*)',\s*(\d+),\s*(\d+),\s*'(.*?)'\.split\('\|'\)", source, re.S)
    if not found:
        return ''
    payload, base, count, words = found.group(1), int(found.group(2)), int(found.group(3)), found.group(4).split('|')
    payload = payload.replace("\\'", "'").replace('\\\\', '\\')
    digits = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def encode(number):
        text = encode(number // base) if number >= base else ''
        rest = number % base
        return text + (digits[rest] if rest < len(digits) else chr(rest + 29))
    table = {}
    for index in range(count - 1, -1, -1):
        key = encode(index)
        table[key] = words[index] if index < len(words) and words[index] else key
    return re.sub(r'\b\w+\b', lambda word: table.get(word.group(0), word.group(0)), payload)


def clean(url, base):
    if not url:
        return None
    url = htmllib.unescape(url.strip()).replace('\\/', '/').replace('\\u0026', '&').replace('\\u003d', '=')
    if url.startswith('//'):
        url = 'https:' + url
    url = urljoin(base, url)
    return url if urlsplit(url).scheme in ('http', 'https') else None


def find_playlists(page, base):
    """Playlist addresses written in the page, best first."""
    page = re.sub(r'<!--.*?-->', '', page, flags=re.S)
    texts = [page]
    for packed in re.findall(r'(eval\(function\(p,a,c,k,e,[dr]\).+?\)\))\s*(?:;|</script>|$)', page, re.S):
        try:
            texts.append(unpack(packed))
        except Exception:
            pass
    for text in re.findall(r'atob\(\s*["\']([A-Za-z0-9+/=]{16,})["\']\s*\)', page):
        try:
            texts.append(base64.b64decode(text).decode('utf-8', 'ignore'))
        except Exception:
            pass
    found = []
    for text in texts:
        for pattern in M3U8_PATTERNS:
            for match in re.findall(pattern, text, re.I):
                url = clean(match, base)
                path = urlsplit(url).path if url else ''
                if url and '.m3u8' in url.lower() and not path.endswith('/.m3u8') and url not in found:
                    found.append(url)
    return found


def find_frames(page, base):
    page = re.sub(r'<!--.*?-->', '', page, flags=re.S)
    raw = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', page, re.I)
    for text in re.findall(r'atob\(\s*["\']([A-Za-z0-9+/=]{16,})["\']\s*\)', page):
        try:
            decoded = base64.b64decode(text).decode('utf-8', 'ignore')
        except Exception:
            continue
        if decoded.startswith(('http://', 'https://')):
            raw.append(decoded)
    frames = []
    for item in raw:
        url = clean(item, base)
        if url and not any(bad in url.lower() for bad in AD_FRAMES) and url not in frames:
            frames.append(url)
    return frames


def headers_for(page_url):
    parts = urlsplit(page_url)
    return {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1',
            'Referer': page_url, 'Origin': parts.scheme + '://' + parts.netloc}


def resolve(url, referer, get, note=lambda message: None, depth=0, seen=None):
    """(playlist address, headers) for a page or playlist address, or None.

    ``get(url, referer)`` returns (final address, text). Nothing is returned unless the playlist answers with #EXTM3U."""
    seen = set() if seen is None else seen
    if url in seen or depth >= MAX_DEPTH:
        return None
    seen.add(url)
    try:
        final, page = get(url, referer)
    except Exception as error:
        note('embed: %s failed (%s)' % (urlsplit(url).hostname, type(error).__name__))
        return None
    if page.lstrip().startswith('#EXTM3U'):
        return final, headers_for(referer or final)
    for playlist in find_playlists(page, final)[:3]:
        if playlist in seen:
            continue
        seen.add(playlist)
        try:
            address, body = get(playlist, final)
        except Exception as error:
            note('embed: playlist failed (%s)' % type(error).__name__)
            continue
        if body.lstrip().startswith('#EXTM3U'):
            return address, headers_for(final)
    for frame in find_frames(page, final):
        result = resolve(frame, final, get, note, depth + 1, seen)
        if result:
            return result
    return None
