"""ISSUE-342 (owner, after ISSUE-339): a dubbed video whose file has no captions made from the dub (no CC / SDH / dub track)
gets one downloaded and turned on by itself when playback starts, with the SubDL / OpenSubtitles keys saved on the phone.

Plain subtitles of a dual-audio release usually translate the original-language script, not the dub's words. The
playback-start matcher (subtitle_match.run) calls start() once per video when wanted() says so; the search, the timing
check and the file handling are the ones Subtitles › Download and apply uses (subtitle_sources, subtitle_match)."""
import os
import zlib

import subtitle_match as sm

LIMIT = 3            # downloads tried per video (providers have quotas)
FOLDER = 'special://temp/kodiios-subtitles/'


def wanted(video, streams, enabled, keys):
    """True when this video should get a dub caption: dubbed, subtitles on, no track marked as made from the dub, and a
    SubDL or OpenSubtitles key saved (the free fallback rarely marks hearing-impaired versions)."""
    keys = keys or {}
    return bool((video or {}).get('dubbed') and enabled and (keys.get('subdl') or keys.get('opensubtitles'))
                and not any(sm.dub_marked(s) for s in streams or []))


def query(item, video):
    """(title, year, season, episode, tmdb id) to search with: the show and episode for an episode, the title for a film."""
    item = item or {}
    video = video or {}
    show = str(item.get('showtitle') or '').strip()
    season, episode = video.get('season'), video.get('episode')
    if show and season is not None and int(season) >= 0 and episode and int(episode) > 0:
        return show, None, int(season), int(episode), None
    tmdb = (item.get('uniqueid') or {}).get('tmdb')
    return str(item.get('title') or item.get('label') or ''), item.get('year') or None, None, None, tmdb


def best(find, fetch, video):
    """(result, file name, bytes) of the best caption made from the dub, or None. find() -> ranked results."""
    marked = [r for r in find() if sm.dub_marked(r)]
    if not marked:
        return None
    try:
        return sm.choose_download(marked, fetch, video, limit=LIMIT)
    except Exception:
        return None


def start(xbmc, xbmcvfs, item, video, playing, log):
    """Search, download and turn on a dub caption for the video playing now (runs on its own thread)."""
    import subtitle_sources as ss
    import tracks as net   # Subtitles › Download and apply's HTTP (DNS over HTTPS when the site is refused)
    keys = ss.load_keys(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/'))
    lang = video.get('language') or 'en'
    title, year, season, episode = query(item, video)[:4]
    tmdb = query(item, video)[4]
    if not title:
        return False

    def find():
        return ss.find(net.http_get, keys, lang, title, year, season, episode, video.get('filename') or '', tmdb,
                       log=lambda m: log('dub captions ' + m), dubbed=True)

    def fetch(result):
        return ss.fetch(net.http_get, net.http_post, keys, result, season, episode)
    got = best(find, fetch, video)
    if not got:
        log('dub captions: none marked CC / SDH / dub for this video')
        return False
    result, name, data = got
    if xbmc.Player().getPlayingFile() != playing:
        log('dub captions: the video changed before the caption was ready')
        return False
    folder = xbmcvfs.translatePath(FOLDER)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, '%s.%s.dub.%s' % (zlib.crc32(str(result['id']).encode('utf-8')) & 0xffffffff, lang,
                                                 name.rsplit('.', 1)[-1].lower()))
    with open(path, 'wb') as f:
        f.write(data)
    xbmc.Player().setSubtitles(path)
    log('dub captions: turned on a %s caption from %s (%d bytes, match %s)' % (lang, result.get('source'), len(data),
                                                                           result.get('match_score')))
    return True
