"""Settings > Favourites as a portrait page (owner-approved mockup board 10): the user's favourites as a poster grid. Tapping
one runs what Kodi's own favourite would (ActivateWindow, PlayMedia or RunScript), after this page closes. Edit shows a
remove badge on each favourite that can be removed; removing one asks first and then calls Favourites.AddFavourite with
the same entry, which Kodi toggles off (favourites_rows.py has the reasoning).
The layout is portrait/IOSFavourites.xml, written by portrait.py (settings_page.favourites_page); this fills it."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import favourites_rows as fr
import favourites_import as fi

BACK = (9, 10, 92, 110)
LONG = (101, 117)        # right click, context menu: a long press (the phone sends it as 10 too, then 117)
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
    """Kodi's own (hand-added) favourites first, newest first, then the imported list in the saved sort order; and the sort key."""
    favourites = (rpc(xbmc, 'Favourites.GetFavourites', {'properties': fr.READ}) or {}).get('favourites') or []
    own = fr.entries(favourites)
    if xbmcvfs is None:
        return own[:fr.MAX], 'list'
    data = fi.load(profile_path(xbmcvfs))
    sort = data.get('sort') if data.get('sort') in fi.SORT_KEYS else 'list'
    imported = [fr.imported_entry(i) for i in fi.ordered(data['items'], sort)]
    return fr.merged(own, imported), sort


def menu_options(entry):
    """ISSUE-322: a held favourite's choices, as (choice-sheet row, builtin or 'remove'): Download, View details, and
    Remove from Favourites last (owner). Never "Add to favourites": it is one already."""
    tmdb = str((entry.get('imported') or {}).get('tmdb') or entry.get('tmdb') or '')
    kind = entry.get('kind') or ''
    title = entry.get('title') or ''
    year = str(entry.get('year') or (entry.get('imported') or {}).get('year') or '')
    out = []
    if tmdb.isdigit() and kind in ('movie', 'tv'):
        script = 'RunScript(service.kodi.ios.bootstrap,download,kind=%s,tmdb=%s%s%s)' % (
            'movie' if kind == 'movie' else 'tvshow', tmdb, ',title=%s' % arg(title) if arg(title) else '', ',year=%s' % year if year.isdigit() else '')
        out.append(({'label': 'Download', 'detail': 'Save it to your library' if kind == 'movie' else 'Choose a season to save',
                     'glyph': 'circle-down.png', 'tint': 'FF0A84FF'}, script))
        out.append(({'label': 'View Details', 'detail': 'Plot, cast and more' + ('' if kind == 'movie' else ', and its seasons'),
                     'glyph': 'circle-info.png', 'tint': 'FF8E8E93'},
                    'RunScript(plugin.video.themoviedb.helper,add_tmdb=%s,tmdb_type=%s,call_auto=1190)' % (tmdb, kind)))
    if entry.get('removable'):
        out.append(({'label': 'Remove from Favourites', 'detail': 'You can add it again from any poster',
                     'glyph': 'trash.png', 'tint': 'FFFF453A'}, 'remove'))
    return out


def arg(text):
    """A title as one RunScript argument: Kodi splits arguments at commas and strips quotes and brackets."""
    import re
    return re.sub(r'\s+', ' ', re.sub(r'[,()"\\]', ' ', str(text or ''))).strip()


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
            code = action.getId()
            # ISSUE-322 (owner, build 486): holding a poster closed Favourites (iOS sends a long press as Back, 10, then
            # 117) and Kodi's own menu opened over Home with "Add to favourites". On a poster a long press opens this
            # page's menu and never means Back; the second action of the same press does nothing.
            if code in LONG or code == 10:
                entry = self.focused_entry()
                if entry is not None:
                    if time.time() - getattr(self, 'menu_done', 0) >= 1.5:
                        self.entry_menu(entry)
                    self.menu_done = time.time()
                    return
            if code in BACK:
                self.close()

        def focused_entry(self):
            n = self.getFocusId() - CELL_BASE
            return self.rows[n - 1] if 0 < n <= len(getattr(self, 'rows', [])) else None

        def entry_menu(self, entry):
            import favourites_import_page as page
            options = menu_options(entry)
            if not options:
                return
            choice = page.pick(xbmcgui, {'heading': entry['title'] or fr.TITLE, 'rows': [o[0] for o in options]})
            if not 0 <= choice < len(options):
                return
            action = options[choice][1]
            if action == 'remove':
                self.remove(entry, ask=False)
            else:
                xbmc.executebuiltin(action)

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

        def remove(self, entry, ask=True):
            if not entry['removable']:
                return
            if ask and not xbmcgui.Dialog().yesno(entry['title'] or fr.TITLE, 'Remove it from Favourites? You can add it again from any poster.',
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
