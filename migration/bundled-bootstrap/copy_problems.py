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

GROUPS = (('retry', 'Can try again'), ('source', 'Need a new source'), ('cancelled', 'Cancelled by you'))
ACTION = {'retry': 'Retry', 'source': 'Find', 'cancelled': 'Restart'}
TINT = {'retry': 'orange', 'source': 'red', 'cancelled': 'grey'}

# (words in the error, the plain reason, the group). The first match wins; the raw error stays in kodi.log.
PLAIN = (('cannot read', 'AllDebrid was busy', 'retry'),
         ('too many', 'AllDebrid is full · it waits its turn', 'retry'),
         ('right now', "AllDebrid can't fetch it right now", 'retry'),
         ('download link', "AllDebrid hasn't given the link yet", 'retry'),
         ('blocked this sign-in', 'AllDebrid blocked the sign-in · check your e-mail', 'retry'),
         ('did not accept the key', 'Sign in to AllDebrid again', 'retry'),
         ('sign in to alldebrid', 'Sign in to AllDebrid again', 'retry'),
         ('premium', 'AllDebrid needs a premium subscription', 'retry'),
         ('banned', 'AllDebrid says this account is banned', 'source'),
         ('no video file', 'This source has no video file', 'source'),
         ('no longer has', 'AllDebrid dropped this torrent', 'source'),
         ('could not fetch this file', 'This file is gone from the source', 'source'),
         ('source changed', 'The source changed while copying', 'source'))


def plain(problem):
    """(short reason, group) for a debrid_drive.problems() entry."""
    if problem['kind'] == 'cancelled':
        return 'Cancelled', 'cancelled'
    if problem['kind'] == 'network':
        return 'The connection dropped', 'retry'
    text = str(problem.get('error') or problem.get('reason') or '').lower()
    for words, reason, group in PLAIN:
        if words in text:
            return reason, group
    first = str(problem.get('reason') or 'Stopped').split('. ')[0].rstrip('.')
    return (first[:60] or 'Stopped'), 'source'


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


def model(found, filter_='all', now=None, slots=40, poster=lambda problem: ''):
    """({property: value}, [slot entries]) for the page. A slot entry is {'head': text} or the problem it shows."""
    now = time.time() if now is None else now
    groups = {key: [] for key, _ in GROUPS}
    for p in found:
        reason, group = plain(p)
        groups[group].append(dict(p, why=reason, group=group))
    props = {'filter': filter_, 'sum.any': 'true' if found else '', 'empty': '' if found else 'true',
             'sum.retry': str(len(groups['retry'])), 'sum.source': str(len(groups['source'])),
             'sum.cancelled': str(len(groups['cancelled'])), 'retry.label': '', 'clear.label': '', 'foot': '', 'more': '', 'none': ''}
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
            for key in ('title', 'sub', 'why', 'whyc', 'act', 'pos', 'poster'):
                props[k + key] = ''
            continue
        when = ago(e.get('finished'), now)
        props[k + 'title'] = e['title']
        props[k + 'sub'] = what(e)
        props[k + 'why'] = ('Cancelled %s' % when) if e['group'] == 'cancelled' and when else e['why']
        props[k + 'whyc'] = TINT[e['group']]
        props[k + 'act'] = ACTION[e['group']]
        props[k + 'pos'] = e['pos']
        props[k + 'poster'] = poster(e)
    if groups['retry'] and filter_ in ('all', 'retry'):
        props['retry.label'] = 'Retry %d' % len(groups['retry'])
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
    if group != 'cancelled':
        rows.append({'label': 'Find Another Source'});actions.append('find')
    rows.append({'label': 'Restart' if group == 'cancelled' else 'Try This Source Again'});actions.append('retry')
    rows.append({'label': 'Remove From List', 'tint': 'FFFF453A'});actions.append('remove')
    full = str(problem.get('error') or problem.get('reason') or '')
    detail = problem['why'] if group == 'cancelled' else ('%s. %s' % (problem['why'], full) if full and full.lower() not in problem['why'].lower() else problem['why'])
    return {'heading': problem['title'], 'sub': detail[:220], 'rows': rows}, actions


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
            self.filter = 'all'
            self.draw()

        def draw(self):
            self.found = debrid_drive.problems(debrid_drive.load(profile))
            props, self.entries = model(self.found, self.filter, poster=poster)
            for key, value in props.items():
                self.setProperty(key, str(value))

        def note(self, text):
            xbmcgui.Dialog().notification('Download problems', text, xbmcgui.NOTIFICATION_INFO, 3000)

        def act(self, action, problem):
            if action == 'retry':
                if problem['group'] == 'cancelled':   # the cancel request would stop it again
                    import transfer_control
                    transfer_control.clear_cancelled(profile, problem.get('hash') or '')
                n = debrid_drive.retry_failed(profile, ('network', 'source', 'cancelled'), only={problem['key']})
                self.note('Back in line' if n else 'Already on Google Drive')
            elif action == 'remove':
                debrid_drive.clear_failed(profile, only={problem['key']})
            elif action == 'find':
                xbmc.executebuiltin('ActivateWindow(Videos,%s,return)' % search_path(problem))
                return

        def onClick(self, control):
            if control == page.BACK:
                self.close();return
            if page.FILTER0 <= control < page.FILTER0 + len(page.FILTERS):
                self.filter = page.FILTERS[control - page.FILTER0][0]
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
            elif page.ACT <= control < page.ACT + page.SLOTS:
                e = self.entries[control - page.ACT] if control - page.ACT < len(self.entries) else {}
                if 'title' not in e:
                    return
                self.act({'retry': 'retry', 'source': 'find', 'cancelled': 'retry'}[e['group']], e)
            elif page.ROW <= control < page.ROW + page.SLOTS:
                e = self.entries[control - page.ROW] if control - page.ROW < len(self.entries) else {}
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
