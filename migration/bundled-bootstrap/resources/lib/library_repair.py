"""Library file manager L5 (DEC-043 board C3): automatic Repair of an episode that never arrived.

Owner, round 2: "a way for me to repair issues … make it hidden like in a menu"; board C3: "Repair looks this episode
up again in 1080p, takes the best version with seeds and adds it to your downloads. Nothing else changes."
It uses Build Season's automatic pick (season_sources.request, purpose 'queue'): no version question. The quality the
show's other episodes have is tried first, then any quality. library_repair_page.py runs it in its own script, so the
Library pages stay usable while it searches.
"""
import collections

KEYS = {'4k': '4k', '2160p': '4k', 'uhd': '4k', '1440p': '1440p', '1080p': '1080p', '720p': '720p', '480p': '480p', 'sd': 'sd'}


def quality_key(text):
    """'1080p HDR' / '2160p' / '4K' -> season_sources' key ('1080p', '4k'); '' when unknown."""
    for word in str(text or '').lower().replace('·', ' ').split():
        if word in KEYS:
            return KEYS[word]
    return ''


def qualities(rows):
    """What to try, in order: the show's most common quality among its ready episodes, then any (None)."""
    seen = collections.Counter(quality_key(r.get('quality')) for r in rows or () if r.get('id') and quality_key(r.get('quality')))
    first = [seen.most_common(1)[0][0]] if seen else []
    return first + [None]


def repair(request, home, tmdb, title, season, episode, tries, log=lambda text: None):
    """Look the episode up again and queue the best version. Returns ('queued', quality or 'any') or ('none', why)."""
    why = 'No version with seeds was found for it.'
    for quality in tries:
        try:
            result = request(home, tmdb, season, episode, 'queue', quality, title=title)
        except RuntimeError as error:   # another search holds the lane: say so rather than wait
            return 'none', str(error)
        except Exception as error:
            log('Kodi iOS repair: S%02dE%02d %s failed (%s)' % (season, episode, quality or 'any', type(error).__name__))
            why = 'The search did not finish. Try again in a moment.'
            continue
        if result.get('queued'):
            log('Kodi iOS repair: S%02dE%02d queued (%s)' % (season, episode, quality or 'any quality'))
            return 'queued', quality or 'any'
        log('Kodi iOS repair: S%02dE%02d nothing at %s' % (season, episode, quality or 'any quality'))
    return 'none', why


def script_args(tmdb, title, rows, quality):
    """RunScript arguments for library_repair_page: one season's episodes, 'episodes=1;5;9'."""
    clean = lambda text: str(text).replace(',', ' ')
    pairs = sorted({(int(r['season']), int(r['episode'])) for r in rows})
    return ['tmdb=%s' % clean(tmdb), 'title=%s' % clean(title), 'quality=%s' % (quality or ''),
            'episodes=%s' % ';'.join('%d:%d' % pair for pair in pairs)]


def episodes_arg(text):
    """'1:5;1:9' -> [(1, 5), (1, 9)]."""
    out = []
    for part in str(text or '').split(';'):
        season, _, episode = part.partition(':')
        if season.isdigit() and episode.isdigit():
            out.append((int(season), int(episode)))
    return out


def args(text):
    """RunScript arguments 'key=value' -> dict."""
    out = {}
    for item in text:
        key, _, value = str(item).partition('=')
        out[key] = value
    return out
