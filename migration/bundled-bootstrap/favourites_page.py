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
import favourites_import as fi

BACK = (9, 10, 92, 110)
CELL_BASE = 9700         # favourite n is button 9700+n
EDIT = 9010
DONE = 9011
IMPORT, SORT, IMPORT_EMPTY = 9030, 9031, 9032     # Import a List, the sort sheet, the empty state's button


def rpc(xbmc, method, params=None):
    answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    return answer.get('result')


def profile_path(xbmcvfs):
    return xbmcvfs.translatePath('special://profile/')


def read(xbmc, xbmcvfs=None):
    """The imported list (in the saved sort order) first, then Kodi's own favourites; and the sort key."""
    favourites = (rpc(xbmc, 'Favourites.GetFavourites', {'properties': fr.READ}) or {}).get('favourites') or []
    own = fr.entries(favourites)
    if xbmcvfs is None:
        return own, 'list'
    data = fi.load(profile_path(xbmcvfs))
    sort = data.get('sort') if data.get('sort') in fi.SORT_KEYS else 'list'
    imported = [fr.imported_entry(i) for i in fi.ordered(data['items'], sort)]
    return (imported + own)[:fr.MAX], sort


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.editing = False
            self.filter = 'all'
            self.all, self.sort = read(xbmc, xbmcvfs)
            self.show()

        def show(self):
            # DEC-045 board F2: All / Movies / Shows (the segmented control, ids 9020+); the grid shows the filter's.
            self.rows = fr.shown(self.all, self.filter)
            props = fr.properties(self.rows, ranked=self.sort == 'list')
            props['sortlabel'] = 'Sort: %s' % fi.sort_label(self.sort)
            props['count'] = str(len(self.all))
            props['chips'] = 'true' if self.all else ''
            props['filter'] = self.filter
            props['none'] = ('No %s in your favourites' % ('movies' if self.filter == 'movie' else 'shows')) if self.all and not self.rows else ''
            for key, value in props.items():
                self.setProperty(key, value)
            self.setProperty('editing', 'true' if self.editing and self.rows else '')

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
            elif control in (IMPORT, IMPORT_EMPTY):
                self.import_list()
            elif control == SORT:
                self.choose_sort()
            elif control == EDIT:
                self.editing = True
                self.show()
            elif control == DONE:
                self.editing = False
                self.show()
            elif 9020 <= control < 9020 + len(fr.FILTERS):
                self.filter = fr.FILTERS[control - 9020][0]
                self.show()
            elif CELL_BASE < control <= CELL_BASE + len(self.rows):
                entry = self.rows[control - CELL_BASE - 1]
                if self.editing:
                    self.remove(entry)
                else:
                    self.open(entry)

        def open(self, entry):
            if entry.get('imported') and entry['imported'].get('kind') == 'movie':
                # A movie stopped part-way asks Continue or Start Over on top of this page; the sheet closes it only when it plays.
                import favourites_import_page as page
                page.open_item(xbmc, xbmcgui, xbmcvfs, entry)
                return
            self.close()
            xbmc.executebuiltin(entry['action'])

        def import_list(self):
            import favourites_import_page as page
            page.run_import(xbmc, xbmcgui, profile_path(xbmcvfs))
            self.all, self.sort = read(xbmc, xbmcvfs)
            self.show()

        def choose_sort(self):
            import favourites_import_page as page
            rows = [{'label': label, 'detail': detail, 'tag': 'Chosen' if key == self.sort else '', 'tag_kind': 'best' if key == self.sort else ''}
                    for key, label, detail in fi.SORTS]
            choice = page.pick(xbmcgui, {'heading': 'Sort Favourites', 'rows': rows})
            if 0 <= choice < len(fi.SORTS):
                fi.set_sort(profile_path(xbmcvfs), fi.SORTS[choice][0])
                self.all, self.sort = read(xbmc, xbmcvfs)
                self.show()

        def remove(self, entry):
            if not entry['removable']:
                return
            if not xbmcgui.Dialog().yesno(entry['title'] or fr.TITLE, 'Remove it from Favourites? You can add it again from any poster.',
                                          nolabel='Cancel', yeslabel='Remove'):
                return
            before = len(self.rows)
            if entry.get('imported'):
                fi.remove(profile_path(xbmcvfs), entry['imported'])
            else:
                rpc(xbmc, 'Favourites.AddFavourite', entry['remove'])
            self.all, self.sort = read(xbmc, xbmcvfs)
            self.rows = fr.shown(self.all, self.filter)
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
