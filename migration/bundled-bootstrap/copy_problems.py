"""RunScript(service.kodi.ios.bootstrap,copy_problems): Settings › Library › Download problems (ISSUE-198, ISSUE-205).

The owner-approved page (docs/design/download-problems-mockups.html, portrait/IOSDownloadProblems.xml drawn by
copy_problems_page.py): a summary, a filter, the AllDebrid → Google Drive copies that ended grouped by what can be
done (try again · a new source · cancelled), each with its poster, title, a short reason in plain words and one action;
tapping a row opens the choice sheet with the whole reason and every choice. model() is pure so host tests read
every property the page shows."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
import debrid_drive

WHY_FIT = 28     # characters of the grey/coloured reason line (DEC-050: longer ones wrap)
TITLE_FIT = 22   # characters of a row title on one line beside the poster and the action (rig render, build 406)
GROUPS = (('retry', 'Can try again'), ('source', 'Need a new source'), ('prepare', 'Preparing for Kodi and AirPlay'),
          ('cancelled', 'Cancelled by you'))
ACTION = {'retry': 'Retry', 'source': 'Find', 'cancelled': 'Restart', 'prepare': 'Find'}
TINT = {'retry': 'orange', 'source': 'red', 'cancelled': 'grey', 'prepare': 'orange'}   # a video that plays as it is is never red

# (words in the error, the plain reason, the group). The first match wins; the raw error stays in kodi.log.
PLAIN = (('not the quality you picked', 'Not the quality you picked', 'source'),
         ('no peer', 'No one is sharing this source', 'source'),   # AllDebrid: "File not available due to no peer"
         ('cannot read', 'AllDebrid was busy', 'retry'),
         ('too many', 'AllDebrid is full · it waits its turn', 'retry'),
         ('right now', "AllDebrid can't fetch it right now", 'retry'),
         ('download link', "AllDebrid hasn't given the link yet", 'retry'),
         ('blocked this sign-in', 'Sign-in blocked · check your e-mail', 'retry'),
         ('did not accept the key', 'Sign in to AllDebrid again', 'retry'),
         ('sign in to alldebrid', 'Sign in to AllDebrid again', 'retry'),
         ('premium', 'AllDebrid needs a premium subscription', 'retry'),
         ('banned', 'AllDebrid says this account is banned', 'source'),
         ('no video file', 'This source has no video file', 'source'),
         ('no longer has', 'AllDebrid dropped this torrent', 'source'),
         ('could not fetch this file', 'This file is gone from the source', 'source'),
         ('source changed', 'The source changed while copying', 'source'))


PREP_PLAIN = (('tracks mp4 cannot preserve', "DVD subtitles can't be kept"),
              ('without changing hdr', "Its HDR picture can't be copied"),
              ('rpu remapping', "Its Dolby Vision can't be copied"))


def prep_problems(state, caps=None, profile_work=None):
    """Preparation problems as page entries (kind 'prepare'): the same shape as debrid_drive.problems() plus 'id'."""
    import drivelibrary
    import library_files as lf
    import prepare_downloads
    out = []
    for p in prepare_downloads.preparation_problems(state):
        error = p['error']
        low = error.lower()
        reason = next((words for key, words in PREP_PLAIN if key in low), '')
        if not reason:
            reason = ('Stopped · it will try again' if not p['blocked'] else (error.split(': ', 1)[-1].split('; ')[0][:50] or 'Kept as it is'))
        info = drivelibrary.parse(p['name'])
        what_ = 'Episode' if info.get('season') else 'Movie'
        retryable = not prepare_downloads.cannot_prepare(error, caps or {})
        out.append({'kind': 'prepare', 'title': drivelibrary.display_title(p['name']), 'reason': reason, 'error': error, 'id': p['id'],
                    'name': p['name'], 'key': 'prep:' + p['id'], 'job_kind': 'episode' if info.get('season') else 'movie',
                    'sub': ' · '.join(x for x in (what_, lf.size_text(p['size'])) if x), 'blocked': p['blocked'],
                    'retryable': retryable, 'finished': 0, 'hash': '', 'index': -1})
    return out


def plain(problem):
    """(short reason, group) for a debrid_drive.problems() entry."""
    if problem['kind'] == 'prepare':
        return problem['reason'], 'prepare'
    if problem['kind'] == 'cancelled':
        return 'Cancelled', 'cancelled'
    if problem['kind'] == 'network':
        return 'The connection dropped', 'retry'
    text = str(problem.get('error') or problem.get('reason') or '').lower()
    for words, reason, group in PLAIN:
        if words in text:
            return reason, group
    first = str(problem.get('reason') or 'Stopped').split('. ')[0].rstrip('.')
    return (first or 'Stopped'), 'source'   # DEC-050: never cut; a long reason wraps onto a second line


def ago(then, now):
    if not then:
        return ''
    minutes = max(0, int((now - float(then)) // 60))
    if minutes < 60:
        return 'just now' if minutes < 2 else '%d min ago' % minutes
    hours = minutes // 60
    if hours < 24:
        return '%d h ago' % hours
    days = hours // 24
    return 'yesterday' if days == 1 else '%d days ago' % days


def what(problem):
    kind = problem.get('job_kind')
    if kind == 'episode':
        return 'Episode'
    if kind == 'season':
        n = int(problem.get('count') or 0)
        return 'Season · %d episode%s' % (n, '' if n == 1 else 's') if n else 'Season'
    if kind == 'movie':
        return 'Movie'
    return 'Download' if problem.get('title') != 'Unnamed download' else 'No title came with it'


def short_title(problem):
    """ISSUE-257 (owner: "Naruto Shippuuden · S…" was cut off): an episode reads "S1 E5 · Naruto Shippuuden", so what is cut
    is the show's name, which the poster already shows, never the episode."""
    title = str(problem.get('title') or '')
    head, sep, tail = title.rpartition(' \u00b7 ')
    if sep and tail.startswith('S') and ' E' in tail:
        return '%s \u00b7 %s' % (tail, head)
    return title


def show_of(problem):
    """The show an episode problem belongs to ('' for a movie)."""
    title = str(problem.get('title') or '')
    head, sep, tail = title.rpartition(' \u00b7 ')
    return head if sep and tail.startswith('S') and ' E' in tail else ''


def model(found, filter_='all', now=None, slots=40, poster=lambda problem: ''):
    """({property: value}, [slot entries]) for the page. A slot entry is {'head': text} or the problem it shows."""
    now = time.time() if now is None else now
    groups = {key: [] for key, _ in GROUPS}
    for p in found:
        reason, group = plain(p)
        groups[group].append(dict(p, why=reason, group=group))
    props = {'filter': filter_, 'sum.any': 'true' if found else '', 'empty': '' if found else 'true',
             'sum.retry': str(len(groups['retry'])), 'sum.source': str(len(groups['source'])),
             'sum.prepare': str(len(groups['prepare'])), 'sum.cancelled': str(len(groups['cancelled'])), 'retry.label': '', 'clear.label': '', 'foot': '', 'more': '', 'none': ''}
    entries = []
    shown = [key for key, _ in GROUPS if filter_ in ('all', key)]
    for key, title in GROUPS:
        if key not in shown or not groups[key]:
            continue
        entries.append({'head': ('%s · %d' % (title, len(groups[key]))).upper(), 'headclear': 'Clear' if key == 'cancelled' else ''})
        entries += [dict(p, pos='') for p in groups[key]]
    over = max(0, len(entries) - slots)
    entries = entries[:slots]
    if over:
        props['more'] = 'And %d more · use the filter to see them' % over
    # Rounded ends: a row is first / last / only within its group (section headers break the groups).
    for n, e in enumerate(entries):
        if 'head' in e:
            continue
        before = n > 0 and 'head' not in entries[n - 1]
        after = n + 1 < len(entries) and 'head' not in entries[n + 1]
        e['pos'] = 'mid' if before and after else 'last' if before else 'first' if after else 'only'
    for n in range(slots):
        k = 'row.%d.' % n
        e = entries[n] if n < len(entries) else {}
        props[k + 'head'] = e.get('head', '')
        props[k + 'headclear'] = e.get('headclear', '')
        if 'head' in e or not e:
            for key in ('title', 'sub', 'why', 'whyc', 'act', 'pos', 'poster', 'two'):
                props[k + key] = ''
            continue
        when = ago(e.get('finished'), now)
        props[k + 'title'] = short_title(e)
        # DEC-050: a title longer than one line wraps onto two (the row grows), never "…".
        props[k + 'two'] = ''   # set below once the reason is known
        props[k + 'sub'] = e.get('sub') or what(e)
        props[k + 'why'] = ('Cancelled %s' % when) if e['group'] == 'cancelled' and when else e['why']
        props[k + 'whyc'] = TINT[e['group']]
        import choice_sheet
        lines = min(3, choice_sheet.lines(props[k + 'title'], TITLE_FIT))
        long_why = choice_sheet.lines(props[k + 'why'], WHY_FIT) > 1
        props[k + 'two'] = str(max(2, lines)) if lines > 1 or long_why else ''   # the title's lines in the taller row
        props[k + 'act'] = ('Retry' if e.get('retryable') else 'Find') if e['group'] == 'prepare' else ACTION[e['group']]
        props[k + 'pos'] = e['pos']
        props[k + 'poster'] = poster(e)
    if groups['retry'] and filter_ in ('all', 'retry'):
        props['retry.label'] = 'Retry %d' % len(groups['retry'])
    again = [p for p in groups['prepare'] if p.get('retryable')]
    if again and filter_ == 'prepare':
        props['retry.label'] = 'Try Again %d' % len(again)
    if groups['prepare'] and filter_ == 'prepare':
        props['foot'] = ('These are on Google Drive and play in Kodi. Preparing only makes them fast to open and ready for AirPlay.')
    if groups['cancelled'] and filter_ == 'cancelled':
        props['foot'] = ('Cancelled copies stay listed so you can restart them. Clearing removes them from this list only; '
                         'nothing on Google Drive changes.')
        props['clear.label'] = 'Clear Cancelled (%d)' % len(groups['cancelled'])
    if found and not any('title' in e for e in entries):
        props['none'] = 'Nothing here.'
    return props, entries


def sheet(problem):
    """The choice sheet for a row (board C1): the whole reason and every choice. Returns (spec, actions)."""
    group = problem['group']
    rows, actions = [], []
    if group == 'prepare':
        # Board E2: nothing is deleted, so nothing is red.
        rows = [{'label': 'Find Another Version'}, {'label': 'Try Again'}, {'label': 'Keep as It Is'}, DONT_SHOW]
        why = ("It has DVD picture subtitles or a second video track an MP4 can't keep, so it isn't made ready for AirPlay. "
               if 'cannot preserve' in str(problem.get('error') or '') else '%s. ' % problem['why'])
        return {'heading': problem['title'], 'sub': (why + 'Nothing was lost: it is on Google Drive and still plays in Kodi.')[:220],
                'rows': rows}, ['find', 'retry', 'keep', 'ignore']
    if group != 'cancelled':
        rows.append({'label': 'Find Another Source'});actions.append('find')
    rows.append({'label': 'Restart' if group == 'cancelled' else 'Try This Source Again'});actions.append('retry')
    rows.append(DONT_SHOW);actions.append('ignore')
    rows.append({'label': 'Remove From List', 'tint': 'FFFF453A', 'glyph': 'trash.png'});actions.append('remove')
    if show_of(problem):   # ISSUE-257: once a season is done, its leftovers go in one tap
        rows.append({'label': 'Clear All for This Show', 'detail': show_of(problem), 'tint': 'FFFF453A', 'glyph': 'trash.png'});actions.append('clear_show')
    return {'heading': problem['title'], 'sub': detail_text(problem)[:220], 'rows': rows}, actions


# Owner (2026-11-14): "one more option that clears it for good and only will show up if there is a different issue"
# (problem_ignore). A grey tile with the eye-slash glyph; the grey line says when it comes back.
DONT_SHOW = {'label': "Don't Show Again", 'detail': 'Back only if something else goes wrong', 'tint': 'FF636366',
             'glyph': 'eye-slash.png'}


def detail_text(problem):
    """The sheet's grey line: the plain reason, then the full one when it says more. Owner screenshot (build 384): "Not the
    quality you picked. Not the quality you picked: 640x480, you chose 1080p" said the same words twice."""
    why = str(problem.get('why') or '')
    if problem['group'] == 'cancelled':
        return why
    full = str(problem.get('error') or problem.get('reason') or '').strip().rstrip('.')
    if not full or full.lower() in why.lower():
        return why
    if full.lower().startswith(why.lower().rstrip('.')):
        return full[:1].upper() + full[1:]
    return '%s. %s' % (why, full)


def auto_find(profile, problem):
    """ISSUE-263 (owner: "have it select highest quality available then I can upscale later"): Find on an episode of a
    known show runs the automatic Repair search instead of a manual one: the show's chosen quality first, and the best
    version with seeds when that quality does not exist (dead torrents left out). RunScript arguments, or None for a movie
    or a download with no show (the manual search then)."""
    tmdb = str(problem.get('show_tmdb') or '')
    season, episode = str(problem.get('season') or ''), str(problem.get('episode') or '')
    if problem.get('job_kind') != 'episode' or not (tmdb and season.isdigit() and episode.isdigit()):
        return None
    import library_repair
    quality = library_repair.chosen(profile, tmdb, [])
    show = str(problem.get('title') or '').split(' · S')[0]
    return library_repair.script_args(tmdb, show, [{'season': season, 'episode': episode}], quality)


def search_path(problem):
    """Find Another Source: the title's TMDb search, movies or shows (the Search page's own results)."""
    import searchbar
    title = str(problem.get('title') or '').split(' · S')[0]
    return searchbar.results_path(title, 'tv' if problem.get('job_kind') in ('episode', 'season') else 'movie')


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    import copy_problems_page as page
    import transfer_artwork
    import drivelibrary
    import choice_sheet
    profile = xbmcvfs.translatePath('special://profile/')
    here = os.path.dirname(os.path.abspath(__file__))
    cache = drivelibrary.load_json(transfer_artwork.cache_path(profile), {})

    def poster(problem):
        try:
            return transfer_artwork.describe(problem.get('name') or problem.get('title', ''), cache)['poster']
        except Exception:
            return ''

    class Page(xbmcgui.WindowXML):
        def onInit(self):
            self.filter = 'prepare' if 'prepare' in sys.argv[1:] else 'all'   # Library status › Review opens the Prepare filter
            self.draw()

        def draw(self):
            import prepare_downloads
            self.caps = prepare_downloads.capabilities(profile)
            # What the owner asked for shows at once (the service applies it at its next pass).
            queue = prepare_downloads.apply_to(prepare_downloads.load(profile), prepare_downloads.pending_requests(profile), time.time())
            import problem_ignore
            self.found = problem_ignore.visible(profile, debrid_drive.problems(debrid_drive.load(profile)) + prep_problems(queue, self.caps))
            props, self.entries = model(self.found, self.filter, poster=poster)
            for key, value in props.items():
                self.setProperty(key, str(value))

        def note(self, text):
            xbmcgui.Dialog().notification('Download problems', text, xbmcgui.NOTIFICATION_INFO, 3000)

        def act_prepare(self, action, problem):
            import prepare_downloads
            if action == 'retry':
                why = prepare_downloads.cannot_prepare(problem.get('error'), self.caps)
                if why:   # P6: not tried again for nothing
                    if xbmcgui.Dialog().yesno('Can\'t be prepared yet', "This video can't be made ready for AirPlay yet: %s.\nIt still plays in Kodi as it is." % why,
                                              nolabel='OK', yeslabel='Find Another Version'):
                        self.act('find', problem)
                    return
                prepare_downloads.request(profile, 'retry', problem['id'])
                self.note('Preparing it again')
            elif action == 'keep':
                prepare_downloads.request(profile, 'keep', problem['id'])
                self.note('Kept as it is')
            elif action == 'find':
                xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % search_path(problem))

        def act(self, action, problem):
            if action == 'ignore':
                import problem_ignore
                problem_ignore.ignore(profile, problem)
                self.note("Hidden · it comes back only if something else goes wrong")
                return
            if problem.get('kind') == 'prepare':
                return self.act_prepare(action, problem)
            if action == 'retry':
                if problem['group'] == 'cancelled':   # the cancel request would stop it again
                    import transfer_control
                    transfer_control.clear_cancelled(profile, problem.get('hash') or '')
                n = debrid_drive.retry_failed(profile, ('network', 'source', 'cancelled'), only={problem['key']})
                self.note('Back in line' if n else 'Already on Google Drive')
            elif action == 'remove':
                debrid_drive.clear_failed(profile, only={problem['key']})
            elif action == 'clear_show':
                show = show_of(problem)
                keys = {p['key'] for p in self.found if p.get('kind') != 'prepare' and show_of(p) == show}
                if xbmcgui.Dialog().yesno('Clear all for %s?' % show, '%d leave this list. Nothing on Google Drive changes.' % len(keys),
                                          nolabel='Cancel', yeslabel='Clear All'):
                    debrid_drive.clear_failed(profile, only=keys)
            elif action == 'find':
                args = auto_find(profile, problem)
                if args:
                    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_repair_page,%s)' % ','.join(args))
                    self.note('Looking for the best version with seeds')
                    return
                xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % search_path(problem))
                return

        def onClick(self, control):
            if control == page.BACK:
                self.close();return
            if page.FILTER0 <= control < page.FILTER0 + len(page.FILTERS):
                self.filter = page.FILTERS[control - page.FILTER0][0]
            elif control == page.RETRY and self.filter == 'prepare':
                import prepare_downloads
                again = [p for p in self.found if p.get('kind') == 'prepare' and p.get('retryable')]
                for p in again:
                    prepare_downloads.request(profile, 'retry', p['id'])
                self.note('%d back in line' % len(again))
            elif control == page.RETRY:
                keys = {e['key'] for e in self.entries if e.get('group') == 'retry'}
                if self.filter == 'all':   # every one that can try again, not only those with a slot
                    keys = {p['key'] for p in self.found if plain(p)[1] == 'retry'}
                self.note('%d back in line' % debrid_drive.retry_failed(profile, ('network', 'source'), only=keys))
            elif control == page.CLEAR or page.HEAD_CLEAR <= control < page.HEAD_CLEAR + page.SLOTS:
                n = sum(1 for p in self.found if p['kind'] == 'cancelled')
                if not xbmcgui.Dialog().yesno('Clear %d cancelled downloads?' % n,
                                              'They leave this list. Videos already on Google Drive stay, and AllDebrid keeps its copy.',
                                              nolabel='Cancel', yeslabel='Clear'):
                    return
                debrid_drive.clear_failed(profile, ('cancelled',))
            elif page.ACT <= control < page.ACT + page.SLOTS or page.ACT2 <= control < page.ACT2 + 50 + page.SLOTS:
                n = (control - page.ACT) if control < page.ACT2 else (control - page.ACT2) % 50
                e = self.entries[n] if n < len(self.entries) else {}
                if 'title' not in e:
                    return
                self.act({'retry': 'retry', 'source': 'find', 'cancelled': 'retry',
                          'prepare': 'retry' if e.get('retryable') else 'find'}[e['group']], e)
            elif page.ROW <= control < page.ROW + page.SLOTS or page.ROW2 <= control < page.ROW2 + 50 + page.SLOTS:
                n = (control - page.ROW) if control < page.ROW2 else (control - page.ROW2) % 50
                e = self.entries[n] if n < len(self.entries) else {}
                if 'title' not in e:
                    return
                spec, actions = sheet(e)
                pick = choice_sheet.choose(spec, xbmcgui=xbmcgui, xbmc=xbmc, path=here)
                if not 0 <= pick < len(actions):
                    return
                if actions[pick] == 'remove' and not xbmcgui.Dialog().yesno(
                        'Remove %s?' % e['title'], 'It leaves this list. Nothing on Google Drive changes.', nolabel='Cancel', yeslabel='Remove'):
                    return
                self.act(actions[pick], e)
            else:
                return
            self.draw()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 110):
                self.close()

    window = Page(page.WINDOW, here, 'Default', '1080i')
    try:
        window.doModal()
    finally:
        del window


if __name__ == '__main__':
    run()
