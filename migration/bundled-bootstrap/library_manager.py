"""Library › TV Shows / Movies: the file manager (DEC-043 board A; portrait/IOSLibraryFiles.xml, library_files_page.py).

Fills the page from what is saved on the phone only (the Drive listing the service keeps fresh, the preparation queue,
AllDebrid copies, AI copies, the artwork cache), so it opens at once with no network wait. The model is library_files;
fill() is pure so host tests can check every property the page reads.
"""
import json
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
    shows, tv_drive = cached(state_dir, 'tv:')
    movies, movie_drive = cached(state_dir, 'movie:')
    episodes = {s['id']: cached(state_dir, 'tv:%s' % s['id'])[0] for s in shows}
    prep, debrid, ups = prepare_downloads.load(profile), debrid_drive.load(profile), upscale_queue.load(profile)
    art = drivelibrary.load_json(os.path.join(state_dir, 'drive-library-art.json'), {})
    poster = lambda kind, e: (drivelibrary.artwork(kind, e.get('title') or '', e.get('year'), None, art, None, cached_only=True) or {}).get('poster', '')
    # ISSUE-197: what was watched to the end (Continue Watching keeps it: Drive file ids and phone paths).
    try:
        with open(os.path.join(str(profile), 'addon_data', 'plugin.video.kodi.ios.watch', 'continue.json'), encoding='utf-8') as f:
            watched = set((json.load(f) or {}).get('watched') or {})
    except (OSError, ValueError, AttributeError):
        watched = set()
    show_rows = lf.show_rows(shows, episodes, prep, debrid, ups, watched)
    for row, show in zip(show_rows, shows):
        row['art'] = poster('tv', show)
    movie_rows = lf.movie_rows(movies, prep, ups, watched)
    for row, movie in zip(movie_rows, movies):
        row['art'] = poster('movie', movie)
    fanart = {s['id']: (drivelibrary.artwork('tv', s.get('title') or '', s.get('year'), None, art, None, cached_only=True) or {}).get('fanart', '')
              for s in shows}
    return {'shows': show_rows, 'movies': movie_rows, 'storage': lf.storage(show_rows, movie_rows, ups),
            'episodes': episodes, 'prep': prep, 'debrid': debrid, 'upscale': ups, 'fanart': fanart, 'watched': watched,
            'driveid': tv_drive or movie_drive,
            'tmdb': {s['id']: (drivelibrary.artwork('tv', s.get('title') or '', s.get('year'), None, art, None, cached_only=True) or {}).get('tmdb_id', '')
                     for s in shows}}


def fill(data, tab='tv', sort='recent', search='', slots=30, view='list'):
    """{property: value} for the page: title, storage card, sort label, rows (title, sub, art, chips, pos), empty."""
    props = {'tab': tab, 'title': 'TV Shows' if tab == 'tv' else 'Movies', 'search': search, 'view': view,
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
        for key in ('title', 'sub', 'art', 'badge', 'badgec'):
            props['mov.%d.%s' % (n, key)] = ''
    if view == 'grid':
        # L7 (board E): posters in a three-column grid, the size under each title; the badge only says the state.
        # Owner (build 356): TV Shows too: the episode count and size under the show, its first chip as the badge.
        for n, r in enumerate(rows):
            k = 'mov.%d.' % n
            props[k + 'title'], props[k + 'art'] = r['title'], r.get('art', '')
            if tab == 'tv':
                props[k + 'sub'] = ' · '.join(x for x in ('%d ep' % r['episodes'], lf.size_text(r['size'])) if x)
                first = (r.get('chips') or [('', '')])[0]
                props[k + 'badge'], props[k + 'badgec'] = first[0], first[1] if first[0] else ''
                continue
            props[k + 'sub'] = ' · '.join(x for x in (lf.size_text(r['size']), r.get('quality') or '') if x)
            props[k + 'badge'] = r['badge']
            props[k + 'badgec'] = {'Ready': 'green', 'Converting': 'orange', 'Problem': 'red', 'Copying': 'blue'}.get(
                r['badge'], 'orange' if str(r['badge']).endswith('%') else 'purple')
        props['empty'] = '' if rows else ('Nothing matches “%s”.' % search if search else
                                          'No downloaded %s yet. Downloads appear here once they are on Google Drive.' % ('shows' if tab == 'tv' else 'movies'))
        return props, rows
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


VIEW_FILE = 'library-view.json'


def _views(state_dir):
    import json
    try:
        with open(os.path.join(state_dir, VIEW_FILE), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_view(state_dir, tab='movie'):
    """The view the owner chose last for a side ('movie' or 'tv'): 'list' (the default, owner's choice) or 'grid'."""
    view = _views(state_dir).get('movies' if tab == 'movie' else 'tv')
    return view if view in ('list', 'grid') else 'list'


def save_view(state_dir, view, tab='movie'):
    import json
    data = _views(state_dir)
    data['movies' if tab == 'movie' else 'tv'] = view
    try:
        os.makedirs(state_dir, exist_ok=True)
        with open(os.path.join(state_dir, VIEW_FILE), 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except OSError:
        pass


def fill_show(data, show, season=None, slots=60, seasons_max=8):
    """Board B: {property: value} for one show and the season shown (default: its first), and the episode rows."""
    rows = lf.episode_rows(show, data.get('episodes', {}).get(show['id']) or [], data.get('prep'), data.get('debrid'),
                           data.get('upscale'), data.get('watched') or ())
    seasons = sorted({r['season'] for r in rows}) or [0]
    season = season if season in seasons else seasons[0]
    shown = [r for r in rows if r['season'] == season]
    ready = sum(1 for r in rows if r['state'] in (lf.READY, lf.UNKNOWN))
    props = {'title': show['title'], 'fanart': (data.get('fanart') or {}).get(show['id'], ''),
             'sub': ' \u00b7 '.join(x for x in (str(show.get('year') or ''), 'Google Drive \u203a TV Shows') if x),
             'n.episodes': str(len(rows)), 'n.episodes.label': 'episodes',
             'n.size': lf.size_text(sum(r['size'] for r in rows)) or '0 MB', 'n.size.label': 'on Drive',
             'n.ready': str(ready), 'n.ready.label': 'ready for TV',
             'season.on': str(seasons.index(season))}
    for n in range(seasons_max):
        props['season.%d' % n] = ('Season %d' % seasons[n] if seasons[n] else 'Specials') if n < len(seasons) else ''
        props['season.%d.tint' % n] = 'FF0A84FF' if n < len(seasons) and seasons[n] == season else 'FF2C2C2E'
    for n in range(slots):
        for key in ('title', 'line', 'state', 'bar', 'repair', 'pos'):
            props['ep.%d.%s' % (n, key)] = ''
    shown = shown[:slots]
    for n, r in enumerate(shown):
        k = 'ep.%d.' % n
        props[k + 'title'] = '%d \u00b7 %s' % (r['episode'], r['name'] or 'Episode %d' % r['episode'])
        props[k + 'line'] = r['line']
        props[k + 'state'] = r['state']
        props[k + 'bar'] = 'true' if r['state'] in (lf.CONVERTING, lf.COPYING) and r.get('progress') is not None else ''
        props[k + 'repair'] = 'true' if r['repair'] else ''
        props[k + 'pos'] = POS(n, len(shown))
    props['empty'] = '' if shown else 'No episodes of this show on Google Drive yet.'
    return props, shown, seasons


def fill_item(row, show=None, kind='episode'):
    """Board C: {property: value} for one episode (row from fill_show) or movie (row from movie_rows), and its actions:
    ('play'|'repair'|'retry', 'tv'|'choose'|'', 'delete')."""
    s = row['state']
    probe = row.get('probe') or {}
    title = ('%d \u00b7 %s' % (row['episode'], row.get('name') or 'Episode %d' % row['episode'])) if kind == 'episode' else row.get('title') or ''
    sub = (' \u00b7 '.join(x for x in ((show or {}).get('title'), 'Season %d' % row['season'] if row.get('season') else '') if x)
           if kind == 'episode' else ' \u00b7 '.join(x for x in ('Movie', str(row.get('year') or '')) if x))
    props = {'title': title, 'sub': sub}
    steps = []
    if s == lf.COPYING:
        steps.append(('run', 'Copying to Google Drive', 'From AllDebrid' + (' \u00b7 %d %%' % row['progress'] if row.get('progress') is not None else '')))
    elif s == lf.PROBLEM and not row.get('id'):
        steps.append(('bad', 'Not added', 'Its lookup came back without a version that could be added.'))
    else:
        steps.append(('ok', 'On Google Drive', ' \u00b7 '.join(x for x in (lf.size_text(row.get('size') or 0), row.get('quality') or '') if x)))
    if s == lf.PROBLEM and row.get('id'):
        steps.append(('bad', 'Not ready for Kodi and AirPlay', (row.get('problem') or 'Preparation stopped')[:90]))
    elif s == lf.CONVERTING:
        steps.append(('run', 'Converting for TV', 'Made ready for Kodi and AirPlay in the background'))
    elif s in (lf.READY, lf.UNKNOWN):
        steps.append(('ok', 'Ready for Kodi and AirPlay', 'Plays at once, seeks without waiting'))
    else:
        steps.append(('off', 'Ready for Kodi and AirPlay', 'After it is on Google Drive'))
    if row.get('ai'):
        steps.append(('ok', 'AI Upscale \u00b7 %s' % (row.get('ai_label') or '4K UHD'),
                      ' \u00b7 '.join(x for x in (lf.size_text(row.get('ai_size') or 0), 'the TV gets this copy') if x)))
    else:
        steps.append(('off', 'AI Upscale', 'Off \u00b7 Settings \u203a AI Upscale'))
    tracks = probe.get('subtitle_tracks')
    steps.append(('ok' if tracks else 'off', 'Subtitles', '%d in the file' % tracks if tracks else 'None in the file \u00b7 search while it plays'))
    for n in range(4):
        st = steps[n] if n < len(steps) else ('', '', '')
        props['step.%d.state' % n], props['step.%d.title' % n], props['step.%d.detail' % n] = st
        props['step.%d.pct' % n] = str(row['progress']) if st[0] == 'run' and row.get('progress') is not None else ''
    picture = ' \u00b7 '.join(x for x in ('%s\u00d7%s' % (probe['width'], probe['height']) if probe.get('width') else '',
                                          str(probe.get('codec') or '').upper()) if x)
    facts = [('Picture', picture or '\u2014'), ('Sound', '%s track%s' % (probe['audio_tracks'], '' if probe['audio_tracks'] == 1 else 's')
              if probe.get('audio_tracks') else '\u2014'),
             ('Size', lf.size_text(row.get('size') or 0) or '\u2014'), ('File', (row.get('file') or '\u2014')[:60])]
    for n, (k, v) in enumerate(facts):
        props['fact.%d.k' % n], props['fact.%d.v' % n] = k, v
    if s == lf.PROBLEM:
        primary = 'repair' if not row.get('id') else 'retry'
        props.update(primary='Repair', secondary='Choose a Version' if not row.get('id') else '',
                     delete='Remove from Library\u2026' if not row.get('id') else 'Delete %s\u2026' % ('Episode' if kind == 'episode' else 'Movie'))
        actions = (primary, 'choose' if not row.get('id') else '', 'delete' if row.get('id') else '')
    elif s == lf.COPYING:
        props.update(primary='Close', secondary='', delete='')
        actions = ('close', '', '')
    else:
        props.update(primary='Play', secondary='Play on TV', delete='Delete %s\u2026' % ('Episode' if kind == 'episode' else 'Movie'))
        actions = ('play', 'tv', 'delete')
    return props, actions


def repair_words(rows, why):
    """P6: what Repair says when trying again can't help: what stops it, that it still plays, and what to do."""
    many = len(rows) > 1
    return ('%s can\'t be made ready for AirPlay yet: %s.\n%s still play%s in Kodi as %s.\nFind Another Version (the show\'s '
            '\u2022\u2022\u2022 \u203a Pick Better Versions) gets one that needs nothing.') % (
        '%d videos' % len(rows) if many else 'This video', why, 'They' if many else 'It', '' if many else 's', 'they are' if many else 'it is')


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
            self.state_dir = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')
            self.view = load_view(self.state_dir, self.tab)
            try:
                self.data = model(profile)
            except Exception as error:
                xbmc.log('Kodi iOS library files: could not read saved state (%s)' % type(error).__name__, xbmc.LOGWARNING)
                self.data = {'shows': [], 'movies': [], 'storage': lf.storage([], [])}
            self.draw()

        def draw(self):
            props, self.rows = fill(self.data, self.tab, self.sort, self.search, page.SLOTS, self.view)
            for key, value in props.items():
                self.setProperty(key, str(value))
            try:
                self.getControl(page.STORE_BAR).setPercent(float(props['store.pct']))
            except Exception:
                pass

        def onClick(self, control):
            if control == page.TAB_SHOWS:
                self.tab = 'tv';self.view = load_view(self.state_dir, self.tab)
            elif control == page.TAB_MOVIES:
                self.tab = 'movie';self.view = load_view(self.state_dir, self.tab)
            elif control in (page.VIEW, page.VIEW + 1):
                self.view = 'list' if self.view == 'grid' else 'grid'
                save_view(self.state_dir, self.view, self.tab)
                self.setFocusId(page.VIEW + (1 if self.view == 'grid' else 0))
            elif control == page.STORE:
                if open_freeup(self.data):
                    self.data = model(profile)
            elif control == page.SEARCH:
                self.search = xbmcgui.Dialog().input('Search downloads', self.search) or ''
            elif control == page.SORT:
                pick = xbmcgui.Dialog().select('Sort by', [label for _, label in SORTS])
                if pick >= 0:
                    self.sort = SORTS[pick][0]
            elif page.MOVIE <= control < page.MOVIE + page.SLOTS and control - page.MOVIE < len(self.rows) and self.view == 'grid':
                row = self.rows[control - page.MOVIE]
                if self.tab == 'tv':
                    show = Show(show_page.WINDOW, HERE, 'Default', '1080i')
                    show.data, show.show = self.data, row
                    show.doModal()
                    del show
                elif open_item(self.data, row, None, 'movie'):
                    self.close()
                return
            elif page.ROW <= control < page.ROW + page.SLOTS and control - page.ROW < len(self.rows):
                row = self.rows[control - page.ROW]
                if self.tab == 'tv':
                    show = Show(show_page.WINDOW, HERE, 'Default', '1080i')
                    show.data, show.show = self.data, row
                    show.doModal()
                    del show
                elif open_item(self.data, row, None, 'movie'):
                    self.close()
                return
            else:
                return
            self.draw()

    import library_show_page as show_page
    import library_item_page as item_page
    import urllib.parse

    def repair_rows(rows, data, show, episodes=None):
        """L5 (board C3): Build Season's automatic pick, no question; the show's own quality first, then any. One
        script repairs the episodes one after another (the search lane takes one at a time)."""
        import library_repair
        tmdb = (data.get('tmdb') or {}).get((show or {}).get('id'), '')
        if not tmdb or not rows:
            return False
        xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_repair_page,%s)' % ','.join(
            library_repair.script_args(tmdb, (show or {}).get('title', ''), rows, library_repair.qualities(episodes or rows)[0])))
        return True

    def act(action, row, data, show=None, kind='episode', episodes=None):
        """Board C's actions. Returns True when the pages should close (playback started)."""
        import drivelibrary
        if action == 'play' or action == 'tv':
            url = drivelibrary.play_url(data.get('driveid'), row['id'])
            xbmc.executebuiltin('Dialog.Close(all,true)')
            player = xbmc.Player()
            player.play(url)
            if action == 'tv':
                monitor = xbmc.Monitor()
                for _ in range(60):   # Play on TV works on the video that is playing
                    if player.isPlayingVideo() or monitor.waitForAbort(0.5):
                        break
                xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,cast)')
            return True
        if action == 'retry':
            import prepare_downloads
            # ISSUE-226 / P6: a video the converter can't keep the tracks of is not tried again for nothing; say why.
            why = prepare_downloads.cannot_prepare(row.get('problem'), prepare_downloads.capabilities(profile))
            if why:
                if xbmcgui.Dialog().yesno('Can\'t be prepared yet', repair_words([row], why), nolabel='OK', yeslabel='Find Another Version'):
                    act('choose', row, data, show, kind, episodes)
                return False
            prepare_downloads.request(profile, 'retry', row.get('job_id') or row['id'])
            xbmcgui.Dialog().notification('Repair', 'Preparing it again', xbmcgui.NOTIFICATION_INFO, 3000)
            return False
        if action in ('repair', 'choose'):
            tmdb = (data.get('tmdb') or {}).get((show or {}).get('id'), '')
            if not tmdb:
                xbmcgui.Dialog().ok('Repair', 'This show has no TMDb match yet, so its episodes cannot be looked up again.')
                return False
            if action == 'repair':
                repair_rows([row], data, show, episodes)
                return False
            # Choose a Version: the episode's download step, which searches it again and lets the owner pick.
            args = ['kind=episode', 'tmdb=%s' % tmdb, 'tvshow.tmdb_id=%s' % tmdb, 'season=%d' % row['season'],
                    'episode=%d' % row['episode'], 'title=%s' % (show or {}).get('title', '')]
            xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,download,%s)' % ','.join(a.replace(',', ' ') for a in args))
            return False
        if action == 'delete':
            query = urllib.parse.urlencode({'action': 'library_remove', 'kind': 'movie' if kind == 'movie' else 'tv',
                                            'name': row.get('title') if kind == 'movie' else '%s S%02dE%02d' % ((show or {}).get('title', ''), row['season'], row['episode']),
                                            'drive': row['id']})
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.kodi.ios.watch/?%s)' % query, True)
            return False
        return action == 'close'

    class Item(xbmcgui.WindowXMLDialog):
        """Board C: one episode or movie."""
        def onInit(self):
            props, self.actions = fill_item(self.row, self.show, self.kind)
            for key, value in props.items():
                self.setProperty(key, str(value))
            for n in range(item_page.STEPS):
                if props.get('step.%d.pct' % n):
                    try:
                        self.getControl(item_page.STEP_BAR + n).setPercent(float(props['step.%d.pct' % n]))
                    except Exception:
                        pass

        def onClick(self, control):
            index = {item_page.PRIMARY: 0, item_page.SECONDARY: 1, item_page.DELETE: 2}.get(control)
            if control == item_page.CLOSE:
                self.close()
                return
            if index is None or not self.actions[index]:
                return
            self.close()
            self.playing = act(self.actions[index], self.row, self.data, self.show, self.kind, self.episodes)

    def open_item(data, row, show=None, kind='episode', episodes=None):
        sheet = Item(item_page.WINDOW, HERE, 'Default', '1080i')
        sheet.data, sheet.row, sheet.show, sheet.kind, sheet.playing, sheet.episodes = data, row, show, kind, False, episodes
        sheet.doModal()
        playing = sheet.playing
        del sheet
        return playing

    import library_select_page as select_page

    class Select(xbmcgui.WindowXMLDialog):
        """Board D: tick several, see the space, delete to Drive's Trash after one alert."""
        def onInit(self):
            self.draw()

        def draw(self):
            import library_delete as ld
            count, size = ld.totals(self.items, self.picked)
            props = {'title': '%d selected' % count if count else self.heading,
                     'all.label': 'Select None' if self.items and count == len(self.items) else 'Select All',
                     'watched.label': 'Watched (%d)' % len(self.watched) if self.watched else '',
                     'delete.label': ld.bar_label(count, size)}
            shown = self.items[:select_page.SLOTS]
            for n in range(select_page.SLOTS):
                it = shown[n] if n < len(shown) else {}
                props['it.%d.title' % n] = it.get('title', '')
                props['it.%d.line' % n] = it.get('line', '')
                props['it.%d.on' % n] = 'true' if it and it['id'] in self.picked else ''
                props['it.%d.pos' % n] = POS(n, len(shown)) if it else ''
            for key, value in props.items():
                self.setProperty(key, str(value))

        def onAction(self, action):
            # The phone sends a long press on a row as action 10 too (build 347): only a real Back closes the sheet.
            if action.getId() in (9, 10, 92, 110) and not (action.getId() == 10 and select_page.ROW <= self.getFocusId() < select_page.ROW + select_page.SLOTS):
                self.close()

        def onClick(self, control):
            import library_delete as ld
            if control == select_page.DONE:
                self.close()
                return
            if control == select_page.ALL:
                self.picked = set() if len(self.picked) == len(self.items) else {i['id'] for i in self.items}
            elif control == select_page.WATCHED:
                self.picked = set(self.watched)
            elif select_page.ROW <= control < select_page.ROW + select_page.SLOTS and control - select_page.ROW < len(self.items):
                ident = self.items[control - select_page.ROW]['id']
                self.picked ^= {ident}
            elif control == select_page.DELETE and self.picked:
                if self.delete():
                    self.close()
                    return
            self.draw()

        def delete(self):
            import library_delete as ld
            import drivelibrary
            count, _ = ld.totals(self.items, self.picked)
            heading, text, yes = ld.alert(count, self.noun)
            dialog = xbmcgui.Dialog()
            if not dialog.yesno(heading, text, nolabel='Cancel', yeslabel=yes):
                return False
            extra = ld.ai_bytes(self.items, self.picked)
            with_ai = bool(extra) and dialog.yesno('AI Upscale copies', 'Also delete their AI copies (%s)?' % lf.size_text(extra),
                                                   nolabel='Keep Them', yeslabel='Delete Them')
            drive, _ = drivelibrary.client()
            if not drive:
                dialog.ok('Delete', 'Sign in to Google Drive first (Settings › Google Drive).')
                return False
            import upscale_queue
            ups = upscale_queue.load(profile)
            state_dir = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')
            removed, failed = ld.delete(self.items, self.picked, with_ai, lambda i: drivelibrary.trash(drive, i), state_dir, ups,
                                        log=lambda t: xbmc.log(t, xbmc.LOGWARNING))
            upscale_queue.save(profile, ups)
            self.removed = removed
            if failed:
                dialog.ok('Could not delete everything', '%d could not be moved to the Trash: %s. Try again in a moment.' % (
                    len(failed), ', '.join(failed[:3])))
            else:
                dialog.notification('Deleted', '%d moved to Google Drive\'s Trash' % len(removed), xbmcgui.NOTIFICATION_INFO, 3000)
            return True

    def open_select(items, heading, noun='episode', picked=(), watched=()):
        """Board D (and Free Up Space's Review): returns the ids deleted."""
        try:
            sheet = Select(select_page.WINDOW, HERE, 'Default', '1080i')
        except RuntimeError:
            import xbmcvfs as _v
            _v.listdir(os.path.join(_v.translatePath('special://skin/'), 'portrait') + '/')
            sheet = Select(select_page.WINDOW, HERE, 'Default', '1080i')
        sheet.items, sheet.heading, sheet.noun = items, heading, noun
        sheet.picked, sheet.watched, sheet.removed = set(picked), set(watched), []
        sheet.doModal()
        removed = sheet.removed
        del sheet
        return removed

    import library_freeup_page as freeup_page

    class FreeUp(xbmcgui.WindowXMLDialog):
        """Board F: suggestions, biggest first; Review opens board D already ticked."""
        def onInit(self):
            self.draw()

        def draw(self):
            import library_delete as ld
            self.groups = ld.free_up_groups(self.data['shows'], self.data.get('episodes', {}), self.data['movies'], self.data.get('upscale'),
                                            self.data.get('watched') or ())
            store = self.data['storage']
            props = {'store.line': '%s on Google Drive' % (lf.size_text(store['total']) or '0 MB'),
                     'store.sub': ' · '.join(x for x in ('Shows %s' % (lf.size_text(store['shows']) or '0 MB'),
                                                         'Movies %s' % (lf.size_text(store['movies']) or '0 MB'),
                                                         'AI copies %s' % lf.size_text(store['ai']) if store['ai'] else '') if x),
                     'empty': '' if self.groups else 'Nothing to suggest right now.'}
            for n in range(freeup_page.SLOTS):
                g = self.groups[n] if n < len(self.groups) else {}
                props['g.%d.title' % n] = g.get('title', '')
                props['g.%d.sub' % n] = g.get('sub', '')
                props['g.%d.pos' % n] = POS(n, len(self.groups)) if g else ''
            for key, value in props.items():
                self.setProperty(key, str(value))

        def onAction(self, action):
            # The phone sends a long press on a row as action 10 too (build 347): only a real Back closes the sheet.
            if action.getId() in (9, 10, 92, 110) and not (action.getId() == 10 and freeup_page.ROW <= self.getFocusId() < freeup_page.ROW + freeup_page.SLOTS):
                self.close()

        def onClick(self, control):
            if control == freeup_page.BACK:
                self.close()
            elif freeup_page.ROW <= control < freeup_page.ROW + freeup_page.SLOTS and control - freeup_page.ROW < len(self.groups):
                g = self.groups[control - freeup_page.ROW]
                if open_select(g['items'], g['title'], g['noun'], picked=[i['id'] for i in g['items']]):
                    self.changed = True
                    self.data = model(profile)
                    self.draw()

    def open_freeup(data):
        """Board F. Returns True when something was deleted (the caller reloads)."""
        try:
            sheet = FreeUp(freeup_page.WINDOW, HERE, 'Default', '1080i')
        except RuntimeError:
            import xbmcvfs as _v
            _v.listdir(os.path.join(_v.translatePath('special://skin/'), 'portrait') + '/')
            sheet = FreeUp(freeup_page.WINDOW, HERE, 'Default', '1080i')
        sheet.data, sheet.changed = data, False
        sheet.doModal()
        changed = sheet.changed
        del sheet
        return changed

    def more_entries(rows, repick=0):
        """Board B round 2's ••• menu: Find Missing Episodes always; Repair All Problems only when there is one; Pick
        Better Versions when episodes wait with a version not started yet (owner, build 328)."""
        problems = [r for r in rows if r.get('repair')]
        return ([('find', 'Find Missing Episodes')] + ([('repair_all', 'Repair All Problems (%d)' % len(problems))] if problems else []) +
                ([('repick', 'Pick Better Versions (%d)' % repick)] if repick else []))

    class Show(xbmcgui.WindowXML):
        """Board B: one show. Season chips switch the episodes; Repair and ••• come with L5, the episode sheet with L4."""
        def onInit(self):
            self.season = None
            self.draw()

        def draw(self):
            props, self.episodes, self.seasons = fill_show(self.data, self.show, self.season, show_page.SLOTS, show_page.SEASONS)
            for key, value in props.items():
                self.setProperty(key, str(value))
            for n, r in enumerate(self.episodes):
                if r.get('progress') is not None:
                    try:
                        self.getControl(show_page.BAR + n).setPercent(float(r['progress']))
                    except Exception:
                        pass

        def more(self):
            import debrid_drive
            tmdb_id = (self.data.get('tmdb') or {}).get(self.show['id'], '')
            hashes, waiting = debrid_drive.repick_plan(debrid_drive.load(profile), self.show['title'], tmdb_id)
            entries = more_entries(self.episodes, len(waiting))
            pick = xbmcgui.Dialog().contextmenu([label for _, label in entries])
            if pick < 0:
                return
            what = entries[pick][0]
            tmdb = (self.data.get('tmdb') or {}).get(self.show['id'], '')
            if what == 'find':
                if not tmdb:
                    xbmcgui.Dialog().ok('Find Missing Episodes', 'This show has no TMDb match yet, so its season cannot be looked up.')
                    return
                # Build Season looks the season up and adds only what is not on Drive or queued already.
                season = self.season if self.season is not None else (self.seasons[0] if self.seasons else 1)
                xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,download,kind=season,tmdb=%s,tvshow.tmdb_id=%s,season=%d,title=%s)' % (
                    tmdb, tmdb, season or 1, self.show['title'].replace(',', ' ')))
            elif what == 'repick':
                if not tmdb:
                    xbmcgui.Dialog().ok('Pick Better Versions', 'This show has no TMDb match yet, so its episodes cannot be looked up again.')
                    return
                if not xbmcgui.Dialog().yesno('Pick Better Versions', '%d waiting episodes are looked up again and the best version '
                                              'for your quality and a sensible size is queued instead. Episodes already copying '
                                              'are not touched.' % len(waiting), nolabel='Cancel', yeslabel='Pick Again'):
                    return
                import library_repair
                rows = [{'season': s_, 'episode': e_} for s_, e_ in waiting]
                xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_repair_page,%s)' % ','.join(
                    library_repair.script_args(tmdb, self.show['title'], rows, library_repair.qualities(self.episodes)[0]) +
                    ['cancel=%s' % ';'.join(hashes)]))
            elif what == 'repair_all':
                problems = [r for r in self.episodes if r.get('repair')]
                import prepare_downloads
                caps = prepare_downloads.capabilities(profile)
                stuck = [r for r in problems if r.get('id') and prepare_downloads.cannot_prepare(r.get('problem'), caps)]
                for row in [r for r in problems if r.get('id') and r not in stuck]:   # a preparation problem: prepared again
                    act('retry', row, self.data, self.show)
                if stuck:   # one message for all of them, not one per episode (ISSUE-226 / P6)
                    xbmcgui.Dialog().ok('Can\'t be prepared yet', repair_words(stuck, prepare_downloads.cannot_prepare(stuck[0].get('problem'), caps)))
                repair_rows([r for r in problems if not r.get('id')], self.data, self.show, self.episodes)

        def onClick(self, control):
            if control == show_page.BACK:
                # Build 347: the round back button had no action, so it took a swipe to leave a show.
                self.close()
            elif show_page.SEASON <= control < show_page.SEASON + show_page.SEASONS and control - show_page.SEASON < len(self.seasons):
                self.season = self.seasons[control - show_page.SEASON]
                self.draw()
            elif show_page.EP <= control < show_page.EP + show_page.SLOTS and control - show_page.EP < len(self.episodes):
                if open_item(self.data, self.episodes[control - show_page.EP], self.show, episodes=self.episodes):
                    self.close()
            elif control == show_page.SELECT:
                # Board D: every episode of the show on Drive, ticked one by one (or Select All / Watched).
                import library_delete as ld
                rows = lf.episode_rows(self.show, self.data.get('episodes', {}).get(self.show['id']) or [], self.data.get('prep'),
                                       self.data.get('debrid'), self.data.get('upscale'), self.data.get('watched') or ())
                items = ld.items_from_rows(rows, self.data.get('upscale'),
                                           title=lambda r: ' · '.join(x for x in ('S%d E%d' % (r['season'], r['episode']),
                                                                                    r['name'] if r['name'] and r['name'].casefold() != self.show['title'].casefold() else '') if x))
                if not items:
                    xbmcgui.Dialog().notification('Select', 'Nothing of this show is on Google Drive yet', xbmcgui.NOTIFICATION_INFO, 3000)
                    return
                if open_select(items, self.show['title'], 'episode', watched=[i['id'] for i in items if 'watched' in i['line']]):
                    self.data = model(profile)
                    self.draw()
            elif control == show_page.MORE:
                self.more()
            elif show_page.REPAIR <= control < show_page.REPAIR + show_page.SLOTS and control - show_page.REPAIR < len(self.episodes):
                row = self.episodes[control - show_page.REPAIR]
                act('repair' if not row.get('id') else 'retry', row, self.data, self.show, episodes=self.episodes)

    if 'freeup' in sys.argv[1:]:
        # Settings › AI Upscale › AI copies on Google Drive (DEC-044 board A2): straight to Free Up Space.
        open_freeup(model(profile))
        return
    if 'check' in sys.argv[1:]:
        # Settings › Library › Check Drive for problems: what older builds left, ticked, behind board D's alert.
        import library_delete as ld
        import drivelibrary
        state_dir = os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap')
        found = ld.drive_problems(drivelibrary.load_json(os.path.join(state_dir, 'drive-library.json'), {}))
        if not found:
            xbmcgui.Dialog().ok('Check Drive for problems', 'Nothing to fix: no films saved as episodes, no episode twice, no empty '
                                'download folders. (This reads the Library\'s last look at Drive; Refresh Library first for the latest.)')
            return
        open_select(found, 'Problems on Drive', 'file', picked=[i['id'] for i in found])
        return
    window = Files(page.WINDOW, HERE, 'Default', '1080i')
    window.doModal()
    del window


if __name__ == '__main__':
    run()
