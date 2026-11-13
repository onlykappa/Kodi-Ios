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
    shows, tv_drive = cached(state_dir, 'tv:')
    movies, movie_drive = cached(state_dir, 'movie:')
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
    fanart = {s['id']: (drivelibrary.artwork('tv', s.get('title') or '', s.get('year'), None, art, None, cached_only=True) or {}).get('fanart', '')
              for s in shows}
    return {'shows': show_rows, 'movies': movie_rows, 'storage': lf.storage(show_rows, movie_rows, ups),
            'episodes': episodes, 'prep': prep, 'debrid': debrid, 'upscale': ups, 'fanart': fanart,
            'driveid': tv_drive or movie_drive,
            'tmdb': {s['id']: (drivelibrary.artwork('tv', s.get('title') or '', s.get('year'), None, art, None, cached_only=True) or {}).get('tmdb_id', '')
                     for s in shows}}


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


def fill_show(data, show, season=None, slots=60, seasons_max=8):
    """Board B: {property: value} for one show and the season shown (default: its first), and the episode rows."""
    rows = lf.episode_rows(show, data.get('episodes', {}).get(show['id']) or [], data.get('prep'), data.get('debrid'),
                           data.get('upscale'))
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

    def more_entries(rows):
        """Board B round 2's ••• menu: Find Missing Episodes always; Repair All Problems only when there is one."""
        problems = [r for r in rows if r.get('repair')]
        return [('find', 'Find Missing Episodes')] + ([('repair_all', 'Repair All Problems (%d)' % len(problems))] if problems else [])

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
            entries = more_entries(self.episodes)
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
            elif what == 'repair_all':
                problems = [r for r in self.episodes if r.get('repair')]
                for row in [r for r in problems if r.get('id')]:   # a preparation problem: prepared again
                    act('retry', row, self.data, self.show)
                repair_rows([r for r in problems if not r.get('id')], self.data, self.show, self.episodes)

        def onClick(self, control):
            if show_page.SEASON <= control < show_page.SEASON + show_page.SEASONS and control - show_page.SEASON < len(self.seasons):
                self.season = self.seasons[control - show_page.SEASON]
                self.draw()
            elif show_page.EP <= control < show_page.EP + show_page.SLOTS and control - show_page.EP < len(self.episodes):
                if open_item(self.data, self.episodes[control - show_page.EP], self.show, episodes=self.episodes):
                    self.close()
            elif control == show_page.MORE:
                self.more()
            elif show_page.REPAIR <= control < show_page.REPAIR + show_page.SLOTS and control - show_page.REPAIR < len(self.episodes):
                row = self.episodes[control - show_page.REPAIR]
                act('repair' if not row.get('id') else 'retry', row, self.data, self.show, episodes=self.episodes)

    window = Files(page.WINDOW, HERE, 'Default', '1080i')
    window.doModal()
    del window


if __name__ == '__main__':
    run()
