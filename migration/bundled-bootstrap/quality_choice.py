"""RunScript(service.kodi.ios.bootstrap,quality_choice,tmdb=..,season=..): DEC-049 boards B and C.

Board B, the choice sheet: "Season N isn't in real 1080p" with Use the Best, Choose Another Version (board C, the season's
versions with the real picture size a copy found), Keep Looking, Always Use the Best for This Show, and Cancel. The answer
is kept (resources/lib/quality_choice.py); the season's held episodes are then looked up again by Repair, whose automatic
pick now takes the best version (or the chosen one) and copies it without refusing it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))


def args(argv):
    out = {}
    for item in argv:
        k, _, v = str(item).partition('=')
        out[k] = v
    return out


def run(argv):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import choice_sheet
    import debrid_drive
    import library_repair
    import quality_choice
    a = args(argv[1:])
    tmdb, season = a.get('tmdb', ''), int(a.get('season') or 0)
    profile = xbmcvfs.translatePath('special://profile/')
    record = quality_choice.load(profile)['seasons'].get(quality_choice.key(tmdb, season)) or {}
    if not tmdb or not season or not record.get('quality'):
        xbmcgui.Dialog().notification('Quality', 'Nothing waits for a choice here', xbmcgui.NOTIFICATION_INFO, 3000)
        return
    while True:
        spec, actions = quality_choice.sheet(record, season)
        pick = choice_sheet.choose(spec, xbmcgui=xbmcgui, xbmc=xbmc, path=HERE)
        if not 0 <= pick < len(actions):
            return
        what, name = actions[pick], ''
        if what == 'versions':
            vspec, names = quality_choice.versions_sheet(record, season)
            if not names:
                xbmcgui.Dialog().ok('Choose Another Version', 'No other version was found for this season. Repair can look again later.')
                continue
            chosen = choice_sheet.choose(vspec, xbmcgui=xbmcgui, xbmc=xbmc, path=HERE)
            if not 0 <= chosen < len(names):
                continue        # back to board B
            what, name = 'chosen', names[chosen]
        break
    held = quality_choice.answer(profile, tmdb, season, what, name)
    title = record.get('title') or ''
    if what == 'looking':
        xbmcgui.Dialog().notification('Season %d' % season, 'Asks again tomorrow · nothing downloads', xbmcgui.NOTIFICATION_INFO, 4000)
        return
    # The answer lets this season's fallbacks through: the copy is not refused for its quality (ISSUE-258).
    debrid_drive.remember_fallback(profile, tmdb, season, record.get('quality'))
    if held:
        rows = [{'season': season, 'episode': n} for n in held]
        xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_repair_page,%s)' % ','.join(
            library_repair.script_args(tmdb, title, rows, record.get('quality'))))
    else:
        xbmcgui.Dialog().notification('Season %d' % season, 'Later episodes use it', xbmcgui.NOTIFICATION_INFO, 4000)


if __name__ == '__main__':
    run(sys.argv)
