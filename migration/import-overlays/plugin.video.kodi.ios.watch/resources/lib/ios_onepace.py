"""One Pace inside the normal show pages (owner, 2026-11-28): `?action=onepace` lists the arcs as seasons, `&season=N` an arc's episodes, `onepace_play` plays one
(English dub where it exists, else Japanese with English subtitles after a "Japanese only" question), `onepace_download` queues an episode or an arc through the Drive copier.
The data, rows and rules are onepace_show.py / onepace.py in the bootstrap add-on (host-tested); this file only talks to Kodi."""
import urllib.parse

ME = 'plugin://plugin.video.kodi.ios.watch/'
SHOW = 'One Pace'


def _load():
    import xbmcvfs
    from ios_library import boot_path
    boot_path(xbmcvfs)
    import onepace_show
    return onepace_show, xbmcvfs.translatePath('special://profile')


GENRES = ['Animation', 'Action & Adventure']
YEAR = 1999


def art(row, kind):
    """The art dictionary of a row: the site's own pictures (an arc's backdrop, an episode's still), the show-level keys the header reads, nothing where there is none."""
    out = {}
    picture = row.get('thumb') if kind == 'thumb' else row.get('poster')
    fanart = row.get('fanart')
    if picture:
        out['thumb'] = picture
        out['poster'] = row.get('poster') or picture
    if fanart:
        out.update({'fanart': fanart, 'tvshow.fanart': fanart, 'tvshow.poster': row.get('poster') or fanart})
    return out


def url(**params):
    return ME + '?' + urllib.parse.urlencode(dict(action='onepace', **{k: v for k, v in params.items() if v not in (None, '')}))


def play_url(season, episode, prefer='', confirmed=False):
    return ME + '?' + urllib.parse.urlencode({k: v for k, v in dict(action='onepace_play', season=season, episode=episode, prefer=prefer, ok='1' if confirmed else '').items() if v})


def directory(handle, params):
    import xbmcgui
    import xbmcplugin
    show, profile = _load()
    found, error = show.seasons(profile)
    if not found:
        xbmcgui.Dialog().notification(SHOW, 'Cannot reach One Pace right now' + (' (%s)' % error if error else ''), xbmcgui.NOTIFICATION_INFO, 4000)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    season = params.get('season', '')
    rows = []
    if season.isdigit():
        arc = show.find(found, season)
        for r in show.episode_rows(arc) if arc else []:
            li = xbmcgui.ListItem(r['label'])
            tag = li.getVideoInfoTag()
            tag.setMediaType('episode')
            tag.setTitle(r['label'])
            tag.setTvShowTitle(SHOW)
            tag.setSeason(r['season'])
            tag.setEpisode(r['episode'])
            if r['minutes']:
                tag.setDuration(r['minutes'] * 60)
            tag.setPlot(r['plot'])
            li.setProperty('IsPlayable', 'true')
            li.setProperty('onepace', 'true')
            li.setProperty('KodiIOS.SeasonsPath', url())   # the arc row on the episode page (portrait.py library_chips reads it), as for a downloaded show
            li.setArt(art(r, 'thumb'))
            li.setProperty('onepace_japanese_only', 'true' if r['japanese_only'] else '')
            li.setProperty('KodiIOS.EpisodeNote', 'Japanese only' if r['japanese_only'] else 'English dub')   # shown after the length on the show page (portrait.py)
            li.setLabel2(('%dm' % r['minutes'] if r['minutes'] else '') + (' · Japanese only' if r['japanese_only'] else ''))
            rows.append((play_url(r['season'], r['episode']), li, False))
        xbmcplugin.setContent(handle, 'episodes')
    else:
        for r in show.season_rows(found):
            li = xbmcgui.ListItem(r['label'])
            tag = li.getVideoInfoTag()
            tag.setMediaType('season')
            tag.setTitle(r['label'])
            tag.setTvShowTitle(SHOW)
            tag.setSeason(r['season'])
            tag.setPlot(r['plot'])
            tag.setGenres(GENRES)
            tag.setYear(YEAR)
            li.setProperty('onepace', 'true')
            li.setProperty('KodiIOS.ChipShort', show.onepace.chip_name(r['label']))
            li.setProperty('KodiIOS.ChipLabel', r['label'])   # the arc's name on the row and on the Play and Download buttons (portrait.py), not "Season N"
            li.setArt(art(r, 'poster'))
            rows.append((url(season=r['season']), li, True))
        xbmcplugin.setContent(handle, 'seasons')
    xbmcplugin.addDirectoryItems(handle, rows)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def play(handle, params):
    """Resolve one episode. A Japanese-only episode asks first (mockup docs/design/one-pace-japanese-only-mockup.html); cancelling resolves nothing."""
    import xbmc
    import xbmcgui
    import xbmcplugin
    show, profile = _load()
    found, _ = show.seasons(profile)
    target = show.play_target(found, params.get('season', '0'), params.get('episode', '0'), 'japanese' if params.get('prefer') == 'japanese' else 'dub')
    if not target:
        xbmcgui.Dialog().notification(SHOW, 'This episode is not available yet', xbmcgui.NOTIFICATION_INFO, 4000)
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    if target['japanese_only'] and params.get('ok') != '1' and params.get('prefer') != 'japanese' and not show.is_quiet(profile, target['season']):
        # The app's alert card (DialogConfirm, approved mockup): Continue, "don't ask again in this arc" as the third line, Cancel last.
        answer = xbmcgui.Dialog().yesnocustom('This episode is Japanese only', 'It plays in Japanese with English subtitles. Do you want to continue?',
                                              "Continue, don't ask again in this arc", nolabel='Cancel', yeslabel='Continue')
        if answer == 2:
            show.make_quiet(profile, target['season'])
        elif answer != 1:
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
    li = xbmcgui.ListItem(target['title'], path=target['file'])
    tag = li.getVideoInfoTag()
    tag.setMediaType('episode')
    tag.setTitle(target['title'])
    tag.setTvShowTitle(SHOW)
    tag.setSeason(target['season'])
    tag.setEpisode(target['episode'])
    tag.setPlot(target['plot'])
    xbmc.log('Kodi iOS One Pace: playing arc %s episode %s (%s, %s)' % (target['season'], target['episode'], target['audio'], target['resolution']), xbmc.LOGINFO)
    xbmcplugin.setResolvedUrl(handle, True, li)


def download(params):
    import xbmc
    import xbmcgui
    show, profile = _load()
    found, _ = show.seasons(profile)
    import debrid_drive
    queued, failed, japanese = show.download(profile, found, lambda *a: debrid_drive.queue_direct(*a),
                                             params.get('season') or None, params.get('episode') or None,
                                             lambda text: xbmc.log('Kodi iOS ' + text, xbmc.LOGWARNING))
    text = '%d episode%s added to Downloads' % (queued, '' if queued == 1 else 's')
    if japanese:
        text += ' (%d Japanese only)' % japanese
    if failed:
        text += ', %d could not be added' % failed
    xbmcgui.Dialog().notification(SHOW, text, xbmcgui.NOTIFICATION_INFO, 5000)
