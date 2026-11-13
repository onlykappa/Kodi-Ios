"""Video controls › Picture (wand): AI Upscale and Saturation for this video, this show or every video.

RunScript(service.kodi.ios.bootstrap,picture_page) opens 1080i/IOSPictureMenu.xml (picture_osd.py) over the video.
The rules are picture_menu.py (host-tested); settings live in picture-settings.json (picture.py). AI Upscale changes
which file plays next time (the upscaled copy on Google Drive, ios_library.upscaled_path); on AirPlay the menu shows
the copy's state and can ask for one (board E). Saturation is remembered here; it changes the picture once the Kodi
build carries the saturation shader (V2, kodi-21.3-portrait.patch).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import picture  # noqa: E402
import picture_menu as pm  # noqa: E402
import picture_osd as osd  # noqa: E402

BACK = (9, 10, 92, 110)


def playing_media(xbmc, home):
    """The download playing (ios_library left it on Window(home)), else what Kodi says about the video (a stream)."""
    try:
        media = json.loads(home.getProperty(pm.MEDIA_PROPERTY) or '{}')
    except ValueError:
        media = {}
    show = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
    title = xbmc.getInfoLabel('VideoPlayer.Title')
    known = str(media.get('show') or '').casefold()
    # The saved download is this video only when its show (or, for a movie, its title) is what Kodi plays now; a stream
    # opened after a download must not inherit the download's Drive file.
    if media and known and ((show and known == show.casefold()) or (not show and title and known == title.casefold())):
        return media
    return {'type': 'tv' if show else 'movie', 'show': show or title, 'title': title, 'drive_id': ''}


def video_size(xbmc):
    def number(label):
        try:
            return int(float(xbmc.getInfoLabel(label) or 0))
        except ValueError:
            return 0
    return number('Player.Process(videowidth)'), number('Player.Process(videoheight)')


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    import upscale_queue as uq
    import airplay
    profile = xbmcvfs.translatePath('special://profile/')
    home = xbmcgui.Window(10000)
    media = playing_media(xbmc, home)
    width, height = video_size(xbmc)
    on_tv = bool(airplay.busy(home, __import__('time').time())) if hasattr(airplay, 'busy') else False

    class Menu(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.page = ''
            self.draw()

        def model(self):
            data = uq.load(profile)
            ai = (data.get('engine') or {}).get('upscales', True)
            return pm.model(media, width, height, picture.load(profile), data, airplay=on_tv, ai_available=ai)

        def draw(self):
            self.m = self.model()
            for key, value in pm.props(self.m).items():
                self.setProperty(key, value)
            self.setProperty('page', self.page)
            try:
                self.getControl(9531).setPercent(float(self.getProperty('tv.pct') or 0))
                self.getControl(9543).setPercent(float(self.getProperty('satpct') or 0))
            except Exception:
                pass
            if self.page == 'apply':
                lst = self.getControl(osd.LIST)
                lst.reset()
                self.rows = pm.apply_rows(self.m, media)
                for key, label, on in self.rows:
                    item = xbmcgui.ListItem(label)
                    item.setProperty('on', 'true' if on else '')
                    lst.addItem(item)

        def save(self, settings):
            picture.save(profile, settings)
            # V2 (Kodi r32): the saturation changes the picture at once; older Kodi builds ignore the unknown built-in.
            xbmc.executebuiltin(picture.builtin(picture.resolve(settings, media)[1]['saturation']))
            self.draw()

        def onAction(self, action):
            if action.getId() in BACK:
                if self.page:
                    self.page = ''
                    self.draw()
                    self.setFocusId(osd.SCOPE)
                else:
                    self.close()

        def onClick(self, control):
            settings = picture.load(profile)
            if control == osd.CLOSE:
                self.close()
            elif control == osd.SCOPE:
                self.page = 'apply'
                self.draw()
                self.setFocusId(osd.LIST)
            elif control == osd.BACK_LINK:
                self.page = ''
                self.draw()
                self.setFocusId(osd.SCOPE)
            elif control == osd.LIST:
                n = self.getControl(osd.LIST).getSelectedPosition()
                if 0 <= n < len(self.rows):
                    self.save(pm.apply_to(settings, media, self.rows[n][0]))
            elif control == osd.RESET:
                self.save(pm.apply_to(settings, media, 'reset'))
            elif control in (osd.SAT_MINUS, osd.SAT_PLUS):
                self.save(pm.nudge_saturation(settings, media, -1 if control == osd.SAT_MINUS else 1))
            elif control == osd.PREPARE:
                label = (self.m.get('airplay') or {}).get('label', '')
                uq.save(profile, pm.prepare_copy(uq.load(profile), media, width, height, label))
                xbmcgui.Dialog().notification('AI Upscale', 'The %s copy is made in the background' % label, xbmcgui.NOTIFICATION_INFO, 3000)
                self.draw()
            elif osd.STOP_BASE <= control < osd.STOP_BASE + 60:
                n, k = divmod(control - osd.STOP_BASE, 10)
                if n == len(self.m['stops']):
                    self.save(pm.choose_stop(settings, media, width, height, k))
                    xbmc.log('Kodi iOS picture: AI Upscale %s (%s)' % (self.m['stops'][k] if k < len(self.m['stops']) else '?',
                                                                       pm.write_scope(self.m['scope'])), xbmc.LOGINFO)

    menu = Menu(osd.MENU, HERE, 'Default', '1080i')
    menu.doModal()
    del menu


if __name__ == '__main__':
    run()
