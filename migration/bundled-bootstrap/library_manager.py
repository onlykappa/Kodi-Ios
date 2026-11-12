"""Library › TV Shows / Movies: the file manager (DEC-043 board A; portrait/IOSLibraryFiles.xml, library_files_page.py).

Fills the page from what is saved on the phone only (the Drive listing the service keeps fresh, the preparation queue,
AllDebrid copies, AI copies, the artwork cache), so it opens at once with no network wait. The model is library_files;
fill() is pure so host tests can check every property the page reads.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import library_files as lf  # noqa: E402

SORTS = (('recent', 'Recent'), ('name', 'Name'), ('size', 'Size'))
POS = lambda n, total: 'only' if total == 1 else 'first' if n == 0 else 'last' if n == total - 1 else 'mid'


def cached(state_dir, slot):
    """A saved Drive listing (drivelibrary.listing's cache), never the network: (entries, driveid)."""
    import drivelibrary
    hit = drivelibrary.load_json(os.path.join(state_dir, 'drive-library.json'), {}).get(slot) or {}
    return hit.get('entries') or [], hit.get('driveid')


def model(profile):
    """Everything board A needs, from saved state."""
    import drivelibrary
    import prepare_downloads
    import debrid_drive
    import upscale_queue
    state_dir = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')
    shows, _ = cached(state_dir, 'tv:')
    movies, _ = cached(state_dir, 'movie:')
    episodes = {s['id']: cached(state_dir, 'tv:%s' % s['id'])[0] for s in shows}
    prep, debrid, ups = prepare_downloads.load(profile), debrid_drive.load(profile), upscale_queue.load(profile)
    art = drivelibrary.load_json(os.path.join(state_dir, 'drive-library-art.json'), {})
    poster = lambda kind, e: (drivelibrary.artwork(kind, e.get('title') or '', e.get('year'), None, art, None, cached_only=True) or {}).get('poster', '')
    show_rows = lf.show_rows(shows, episodes, prep, debrid, ups)
    for row, show in zip(show_rows, shows):
        row['art'] = poster('tv', show)
    movie_rows = lf.movie_rows(movies, prep, ups)
    for row, movie in zip(movie_rows, movies):
        row['art'] = poster('movie', movie)
    return {'shows': show_rows, 'movies': movie_rows, 'storage': lf.storage(show_rows, movie_rows, ups)}


def fill(data, tab='tv', sort='recent', search='', slots=30):
    """{property: value} for the page: title, storage card, sort label, rows (title, sub, art, chips, pos), empty."""
    props = {'tab': tab, 'title': 'TV Shows' if tab == 'tv' else 'Movies', 'search': search,
             'sort.label': dict(SORTS)[sort]}
    store = data['storage']
    props['store.line'] = '%s on Google Drive' % (lf.size_text(store['total']) or '0 MB')
    legend = ['Shows %s' % (lf.size_text(store['shows']) or '0 MB'), 'Movies %s' % (lf.size_text(store['movies']) or '0 MB')]
    if store['ai']:
        legend.append('AI copies %s' % lf.size_text(store['ai']))
    props['store.legend'] = ' · '.join(legend)
    props['store.pct'] = int(100 * store['shows'] / store['total']) if store['total'] else 0
    if tab == 'tv':
        rows = lf.sort_shows(lf.search(data['shows'], search), sort)
    else:
        rows = lf.search(data['movies'], search)
        rows = sorted(rows, key=lambda r: -r['size']) if sort == 'size' else sorted(rows, key=lambda r: str(r['title']).casefold()) if sort == 'name' else rows
    rows = rows[:slots]
    for n in range(slots):
        for key in ('title', 'sub', 'art', 'pos') + tuple('chip%d' % c for c in range(3)) + tuple('chip%dc' % c for c in range(3)):
            props['row.%d.%s' % (n, key)] = ''
    for n, r in enumerate(rows):
        k = 'row.%d.' % n
        props[k + 'title'] = r['title']
        props[k + 'art'] = r.get('art', '')
        props[k + 'pos'] = POS(n, len(rows))
        if tab == 'tv':
            seasons = r['seasons']
            what = ('Season %d' % seasons[0]) if len(seasons) == 1 else ('Seasons %d–%d' % (seasons[0], seasons[-1]) if seasons else '')
            props[k + 'sub'] = ' · '.join(x for x in (what, '%d episode%s' % (r['episodes'], '' if r['episodes'] == 1 else 's'),
                                                         lf.size_text(r['size'])) if x)
            chips = r['chips']
        else:
            props[k + 'sub'] = ' · '.join(x for x in (str(r['year'] or ''), lf.size_text(r['size']), r.get('quality') or '') if x)
            tone = {'Ready': 'green', 'Converting': 'orange', 'Problem': 'red', 'Copying': 'blue'}.get(r['badge'], 'purple')
            chips = [(r['badge'], tone)]
        for c, (label, tone) in enumerate(chips[:3]):
            props[k + 'chip%d' % c], props[k + 'chip%dc' % c] = label, tone
    props['empty'] = '' if rows else ('Nothing matches “%s”.' % search if search else
                                      'No downloaded %s yet. Downloads appear here once they are on Google Drive.' % ('shows' if tab == 'tv' else 'movies'))
    return props, rows


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    import library_files_page as page
    profile = xbmcvfs.translatePath('special://profile/')

    class Files(xbmcgui.WindowXML):
        def onInit(self):
            self.tab = 'movie' if 'movie' in sys.argv[1:] else 'tv'
            self.sort, self.search, self.rows = 'recent', '', []
            try:
                self.data = model(profile)
            except Exception as error:
                xbmc.log('Kodi iOS library files: could not read saved state (%s)' % type(error).__name__, xbmc.LOGWARNING)
                self.data = {'shows': [], 'movies': [], 'storage': lf.storage([], [])}
            self.draw()

        def draw(self):
            props, self.rows = fill(self.data, self.tab, self.sort, self.search, page.SLOTS)
            for key, value in props.items():
                self.setProperty(key, str(value))
            try:
                self.getControl(page.STORE_BAR).setPercent(float(props['store.pct']))
            except Exception:
                pass

        def onClick(self, control):
            if control == page.TAB_SHOWS:
                self.tab = 'tv'
            elif control == page.TAB_MOVIES:
                self.tab = 'movie'
            elif control == page.SEARCH:
                self.search = xbmcgui.Dialog().input('Search downloads', self.search) or ''
            elif control == page.SORT:
                pick = xbmcgui.Dialog().select('Sort by', [label for _, label in SORTS])
                if pick >= 0:
                    self.sort = SORTS[pick][0]
            elif page.ROW <= control < page.ROW + page.SLOTS and control - page.ROW < len(self.rows):
                row = self.rows[control - page.ROW]
                kind = 'tv' if self.tab == 'tv' else 'movie'
                # Board B (one show) and C (one movie) are the next roadmap steps (L3, L4); until then the existing
                # Library listing for the show opens.
                xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=%s,return)' % kind)
                return
            else:
                return
            self.draw()

    window = Files(page.WINDOW, HERE, 'Default', '1080i')
    window.doModal()
    del window


if __name__ == '__main__':
    run()
