"""Settings > Favourites as a portrait page (owner-approved mockup board 10): the user's favourites as a poster grid. Tapping
one runs what Kodi's own favourite would (ActivateWindow, PlayMedia or RunScript), after this page closes. Edit shows a
remove badge on each favourite that can be removed; removing one asks first and then calls Favourites.AddFavourite with
the same entry, which Kodi toggles off (favourites_rows.py has the reasoning).
The layout is portrait/IOSFavourites.xml, written by portrait.py (settings_page.favourites_page); this fills it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import favourites_rows as fr

BACK = (9, 10, 92, 110)
CELL_BASE = 9700         # favourite n is button 9700+n
EDIT = 9010
DONE = 9011


def rpc(xbmc, method, params=None):
    answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    return answer.get('result')


def read(xbmc):
    favourites = (rpc(xbmc, 'Favourites.GetFavourites', {'properties': fr.READ}) or {}).get('favourites') or []
    return fr.entries(favourites)


def run():
    import xbmc
    import xbmcgui

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.editing = False
            self.rows = read(xbmc)
            self.show()

        def show(self):
            for key, value in fr.properties(self.rows).items():
                self.setProperty(key, value)
            self.setProperty('editing', 'true' if self.editing and self.rows else '')

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
            elif control == EDIT:
                self.editing = True
                self.show()
            elif control == DONE:
                self.editing = False
                self.show()
            elif CELL_BASE < control <= CELL_BASE + len(self.rows):
                entry = self.rows[control - CELL_BASE - 1]
                if self.editing:
                    self.remove(entry)
                else:
                    self.open(entry)

        def open(self, entry):
            self.close()
            xbmc.executebuiltin(entry['action'])

        def remove(self, entry):
            if not entry['removable']:
                return
            if not xbmcgui.Dialog().yesno(entry['title'] or fr.TITLE, 'Remove it from Favourites? You can add it again from any poster.',
                                          nolabel='Cancel', yeslabel='Remove'):
                return
            before = len(self.rows)
            rpc(xbmc, 'Favourites.AddFavourite', entry['remove'])
            self.rows = read(xbmc)
            if len(self.rows) >= before:
                # Kodi toggles a favourite off only when the entry matches; if it did not, say nothing on screen.
                xbmc.log('Kodi iOS favourites_page: removal did not match a favourite', xbmc.LOGWARNING)
            if not self.rows:
                self.editing = False
            self.show()

    page = Page('IOSFavourites.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run()
