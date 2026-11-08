"""Video controls › Next Episode (owner, build 205: "i want a button at the top to watch next episode").

Kodi's playlist when it holds the next episode (a library show, an add-on that queued the season); otherwise the
next episode of the same show the way the owner starts episodes: TMDb Helper's play, which asks Umbrella (or the
player the owner chose) for a source. Umbrella and TMDb Helper play one episode at a time, with no playlist."""
import json
import urllib.parse

TMDB_PLAY = 'plugin://plugin.video.themoviedb.helper/?'


def plan(item, position, size):
    """('playlist', None) | ('play', url) | (None, why). item: Player.GetItem's item (showtitle, season, episode,
    uniqueid); position/size: the video playlist's."""
    if size and 0 <= position < size - 1:
        return 'playlist', None
    item = item or {}
    show = str(item.get('showtitle') or '').strip()
    try:
        season, episode = int(item.get('season')), int(item.get('episode'))
    except (TypeError, ValueError):
        season = episode = -1
    if not show or season < 0 or episode < 0:
        return None, 'This video is not an episode of a show.'
    query = {'info': 'play', 'tmdb_type': 'tv', 'season': season, 'episode': episode + 1}
    ids = item.get('uniqueid') or {}
    # Umbrella and TMDb Helper tag an episode with its show's TMDb id under 'tvshow.tmdb'; a bare 'tmdb' may be the
    # episode's own id, so the show's title is used instead.
    if str(ids.get('tvshow.tmdb') or '').isdigit():
        query['tmdb_id'] = ids['tvshow.tmdb']
    else:
        query['query'] = show
    return 'play', TMDB_PLAY + urllib.parse.urlencode(query)


def run():
    import xbmc
    import xbmcgui
    rpc = lambda method, params: json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    players = rpc('Player.GetActivePlayers', {}).get('result') or []
    video = [p['playerid'] for p in players if p.get('type') == 'video']
    if not video:
        return
    item = (rpc('Player.GetItem', {'playerid': video[0], 'properties': ['showtitle', 'season', 'episode', 'uniqueid']})
            .get('result') or {}).get('item') or {}
    props = rpc('Player.GetProperties', {'playerid': video[0], 'properties': ['playlistid', 'position']}).get('result') or {}
    size = 0
    if props.get('playlistid', -1) >= 0:
        size = int((rpc('Playlist.GetProperties', {'playlistid': props['playlistid'], 'properties': ['size']}).get('result') or {}).get('size') or 0)
    how, what = plan(item, int(props.get('position', -1)), size)
    if how == 'playlist':
        xbmc.Player().playnext()
    elif how == 'play':
        xbmc.log('Kodi iOS Next Episode: %s S%02dE%02d via TMDb Helper' % (item.get('showtitle'), int(item['season']), int(item['episode']) + 1), xbmc.LOGINFO)
        xbmc.executebuiltin('PlayMedia(%s)' % what)
    else:
        xbmcgui.Dialog().notification('Next Episode', what, xbmcgui.NOTIFICATION_INFO, 3000)


if __name__ == '__main__':
    run()
