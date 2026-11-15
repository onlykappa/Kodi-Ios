"""Video controls › Next Episode (owner, build 205: "i want a button at the top to watch next episode").

Kodi's playlist when it holds the next episode (a library show, an add-on that queued the season); otherwise the
next episode of the same show the way the owner starts episodes: TMDb Helper's play, which asks Umbrella (or the
player the owner chose) for a source. Umbrella and TMDb Helper play one episode at a time, with no playlist."""
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))

TMDB_PLAY = 'plugin://plugin.video.themoviedb.helper/?'


CONTINUE_STORE = 'special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json'
BUSY = 'KodiIOS.NextEpisode.At'   # ISSUE-331: a second tap while the first is still starting does nothing
BUSY_SECONDS = 10


def current_entry(data, item):
    """ISSUE-331: Continue Watching's entry for the playing episode (the chooser records each episode it starts), when it
    is this show's season/episode: it has the show's TMDb id and the player and version picked."""
    data = data or {}
    entry = (data.get('items') or {}).get(data.get('current')) or {}
    if entry.get('kind') != 'episode' or not str(entry.get('tmdb_id') or '').isdigit():
        return None
    try:
        same = (int(entry.get('season')), int(entry.get('episode'))) == (int(item.get('season')), int(item.get('episode')))
    except (TypeError, ValueError):
        return None
    return dict(entry, key=data.get('current')) if same else None


def aired_seasons(show):
    """ISSUE-341: {season: episodes aired} from TMDb's /tv/{id} answer (specials, season 0, left out). The season that is
    airing counts up to its last aired episode; later seasons count 0, so Next Episode never asks for one not out yet."""
    show = show or {}
    last = show.get('last_episode_to_air') or {}
    try:
        last_season, last_episode = int(last.get('season_number')), int(last.get('episode_number'))
    except (TypeError, ValueError):
        last_season = last_episode = None
    out = {}
    for s in show.get('seasons') or []:
        try:
            number, count = int(s.get('season_number')), int(s.get('episode_count') or 0)
        except (TypeError, ValueError):
            continue
        if number < 1:
            continue
        if last_season is not None:
            if number > last_season:
                count = 0
            elif number == last_season:
                count = min(count, last_episode) if count else last_episode
        out[number] = count
    return out


def next_of(season, episode, seasons=None):
    """(season, episode) to play after this one, or None after the last aired episode. Without the season sizes
    (TMDb not reachable) it is the next episode of the same season, as before."""
    if not seasons or episode < int(seasons.get(season) or 0):
        return season, episode + 1
    for later in sorted(n for n in seasons if n > season):
        if int(seasons[later] or 0) > 0:
            return later, 1
    return None


def plan(item, position, size, current=None, seasons=None):
    """('playlist', None) | ('play', url) | (None, why). item: Player.GetItem's item (type, showtitle, season, episode,
    uniqueid); position/size: the video playlist's; current: current_entry() for the playing episode, or None.
    ISSUE-331 (owner, build 486: Next Episode "seemed to lag out"; "it should only show up for tv shows and it should
    simply select the next episode"): the link carries ios_next=<the playing episode's key>, so the watch menu skips its
    question, plays a downloaded copy when there is one, else uses the same player as this episode and the version page
    picks the one closest to this episode's quality by itself."""
    if size and 0 <= position < size - 1:
        return 'playlist', None
    item = item or {}
    if str(item.get('type') or '') == 'movie':
        return None, 'This video is not an episode of a show.'
    show = str(item.get('showtitle') or '').strip()
    try:
        season, episode = int(item.get('season')), int(item.get('episode'))
    except (TypeError, ValueError):
        season = episode = -1
    if not show or season < 0 or episode < 0:
        return None, 'This video is not an episode of a show.'
    # ISSUE-341 (owner): after a season's last episode, the next season's first (seasons: aired_seasons()).
    following = next_of(season, episode, seasons)
    if following is None:
        return None, 'That was the last episode out so far.'
    query = {'info': 'play', 'tmdb_type': 'tv', 'season': following[0], 'episode': following[1]}
    ids = item.get('uniqueid') or {}
    # Umbrella and TMDb Helper tag an episode with its show's TMDb id under 'tvshow.tmdb'; a bare 'tmdb' may be the
    # episode's own id, so the show's title is used instead.
    if str(ids.get('tvshow.tmdb') or '').isdigit():
        query['tmdb_id'] = ids['tvshow.tmdb']
    elif current:
        query['tmdb_id'] = current['tmdb_id']   # the id Continue Watching saved: no search by name (slower, can miss)
    else:
        query['query'] = show
    if current and current.get('key'):
        query['ios_next'] = current['key']
    return 'play', TMDB_PLAY + urllib.parse.urlencode(query)


def show_seasons(item, current, timeout=4):
    """The playing show's aired season sizes from TMDb (TMDb Helper's key), or None when its id or TMDb is not there."""
    ids = (item or {}).get('uniqueid') or {}
    show = str(ids.get('tvshow.tmdb') or '') if str(ids.get('tvshow.tmdb') or '').isdigit() else str((current or {}).get('tmdb_id') or '')
    if not show.isdigit():
        return None
    try:
        import source_match
        import urllib.request
        key = source_match.tmdb_key()
        if not key:
            return None
        with urllib.request.urlopen('https://api.themoviedb.org/3/tv/%s?api_key=%s' % (show, key), timeout=timeout) as response:
            return aired_seasons(json.loads(response.read(1024 * 1024)))
    except Exception:
        return None


def wait_stopped(xbmc, limit=6.0, step=0.1):
    """Stop the video and wait until Kodi has no video player (True), at most limit seconds."""
    xbmc.Player().stop()
    waited = 0.0
    monitor = xbmc.Monitor()
    while waited < limit:
        if not xbmc.getCondVisibility('Player.HasVideo') and not xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'):
            monitor.waitForAbort(0.3)   # let the video window and its dialogs finish closing
            return True
        if monitor.waitForAbort(step):
            return False
        waited += step
    return False


def run():
    import xbmc
    import xbmcgui
    rpc = lambda method, params: json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    players = rpc('Player.GetActivePlayers', {}).get('result') or []
    video = [p['playerid'] for p in players if p.get('type') == 'video']
    if not video:
        return
    import time
    home = xbmcgui.Window(10000)
    try:
        if time.time() - float(home.getProperty(BUSY) or 0) < BUSY_SECONDS:
            xbmc.log('Kodi iOS Next Episode: already starting; this tap is ignored', xbmc.LOGINFO)
            return
    except ValueError:
        pass
    item = (rpc('Player.GetItem', {'playerid': video[0], 'properties': ['showtitle', 'season', 'episode', 'uniqueid']})
            .get('result') or {}).get('item') or {}
    props = rpc('Player.GetProperties', {'playerid': video[0], 'properties': ['playlistid', 'position']}).get('result') or {}
    size = 0
    if props.get('playlistid', -1) >= 0:
        size = int((rpc('Playlist.GetProperties', {'playlistid': props['playlistid'], 'properties': ['size']}).get('result') or {}).get('size') or 0)
    current = None
    try:
        import xbmcvfs
        f = xbmcvfs.File(CONTINUE_STORE)
        try:
            current = current_entry(json.loads(f.read() or '{}'), item)
        finally:
            f.close()
    except Exception:
        current = None
    how, what = plan(item, int(props.get('position', -1)), size, current, show_seasons(item, current))
    if how:
        home.setProperty(BUSY, str(time.time()))
    if how == 'playlist':
        xbmc.Player().playnext()
    elif how == 'play':
        target = dict(urllib.parse.parse_qsl(what.split('?', 1)[1]))
        xbmc.log('Kodi iOS Next Episode: %s S%02dE%02d via TMDb Helper' % (item.get('showtitle'), int(target['season']), int(target['episode'])), xbmc.LOGINFO)
        # Roadmap 2.9 (owner log e8ab5995 09:32:47): the source question opened while this video was still closing and
        # was dismissed 0.12 s later ("picked -1", "lib.player - Failure!"). Stop first, start once it has closed.
        try:
            xbmcgui.Dialog().notification('Next Episode', 'S%d, E%d' % (int(target['season']), int(target['episode'])),
                                          xbmcgui.NOTIFICATION_INFO, 2500)
        except (TypeError, ValueError, KeyError):
            pass
        stopped = wait_stopped(xbmc)
        xbmc.log('Kodi iOS Next Episode: current video %s' % ('closed' if stopped else 'still closing after 6 s'), xbmc.LOGINFO)
        xbmc.executebuiltin('PlayMedia(%s)' % what)
    else:
        xbmcgui.Dialog().notification('Next Episode', what, xbmcgui.NOTIFICATION_INFO, 3000)


if __name__ == '__main__':
    run()
