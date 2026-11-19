"""Sports › Edit: which leagues show (owner mockups B1-B2: sports_edit_page.py draws the sheet).

One sheet: every league grouped by sport with a switch each, "Only" on a sport heading, All on / All off, Done. Every change is saved at once
(sports_filter), so closing the sheet any way keeps the choice. `run()` returns True when the choice changed, so the page that opened it draws
itself again. `apply()` is the pure part (the tests drive it without Kodi).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import sports_filter as sf


def apply(off, rows, action, target=None):
    """The new set of leagues that are off after a tap. action: 'flip' (target: a league code), 'only' (a sport), 'all_on', 'all_off'."""
    codes = [r['code'] for r in rows]
    if action == 'flip':
        return sf.toggled(off, target)
    if action == 'only':
        return sf.only_sport([(r.get('sport') or '', r['code'], r.get('name') or r['code']) for r in rows], target)
    if action == 'all_on':
        return sf.all_on()
    if action == 'all_off':
        return sf.all_off(codes)
    return set(off)


def run(args=()):
    import threading
    import time
    import xbmc
    import xbmcgui
    import xbmcvfs
    import sports_edit_page as page
    import sports_logos
    import sports_provider
    profile = xbmcvfs.translatePath('special://profile/')
    try:
        rows = sports_provider.get().all_leagues()
    except Exception as error:
        xbmc.log('Kodi iOS Sports: edit could not list leagues: %s' % type(error).__name__, xbmc.LOGWARNING)
        return False
    before = sf.load(profile)
    state = {'off': set(before), 'logos': {}}

    class Sheet(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.draw()
            def fetch_logos():   # the rows draw first; the real logos arrive a moment later and are kept on the phone
                try:
                    found = sports_logos.paths(profile, [r['code'] for r in rows])
                    if found:
                        state['logos'] = found
                        self.draw()
                except Exception as error:
                    xbmc.log('Kodi iOS Sports: edit logos (%s)' % type(error).__name__, xbmc.LOGINFO)
            threading.Thread(target=fetch_logos, daemon=True).start()

        def draw(self):
            self.items = sf.sheet_items(rows, state['off'], state['logos'], int(time.time()))
            for key, value in sf.sheet_props(self.items).items():
                self.setProperty(key, value)

        def change(self, action, target=None):
            state['off'] = apply(state['off'], rows, action, target)
            sf.save(profile, state['off'])
            self.draw()

        def onClick(self, control):
            if control == page.DONE:
                self.close()
            elif control == page.ALL_ON:
                self.change('all_on')
            elif control == page.ALL_OFF:
                self.change('all_off')
            elif page.ROW0 <= control < page.ROW0 + page.SLOTS:
                n = control - page.ROW0
                if n < len(self.items) and self.items[n]['kind'] == 'row':
                    self.change('flip', self.items[n]['code'])
            elif page.ONLY0 <= control < page.ONLY0 + page.SLOTS:
                n = control - page.ONLY0
                if n < len(self.items) and self.items[n]['kind'] == 'head':
                    self.change('only', self.items[n]['sport'])

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 110):
                self.close()

    try:
        sheet = Sheet(page.WINDOW, HERE, 'Default', '1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'), 'portrait') + '/')
        sheet = Sheet(page.WINDOW, HERE, 'Default', '1080i')
    sheet.doModal()
    del sheet
    return sf.load(profile) != before


if __name__ == '__main__':
    run(sys.argv[1:])
