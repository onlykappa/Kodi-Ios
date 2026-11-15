"""Import a list into Favourites (mockup boards I-J): pick the list, match every name through TMDb, add what matched, then a
report of duplicates, questions and names that were not found.

Runs from Favourites (Import a List) and as RunScript(service.kodi.ios.bootstrap,favourites_import_page). The screens are the
app's existing ones: the choice sheet (Import source, the report, "did you mean"), Kodi's keyboard and progress dialog.
Reading the list is favourites_import.py; matching is favourites_match.py (both unit-tested)."""
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import favourites_import as fi
import favourites_match as fm

TMDB = 'https://api.themoviedb.org/3'
TITLE = 'Import a List'
CONTINUE_FLAG = 'ios_continue=1'          # ios_continue.CONTINUE_FLAG: play the version picked last time and resume
HELPER = 'plugin://plugin.video.themoviedb.helper/'
CONTINUE_FILE = 'addon_data/plugin.video.kodi.ios.watch/continue.json'
FINISHED = 0.92


def tmdb_search(key):
    """search(query) -> TMDb /search/multi results, made with TMDb Helper's own API key."""
    def search(query):
        url = '%s/search/multi?%s' % (TMDB, urllib.parse.urlencode({'api_key': key, 'query': query, 'include_adult': 'false'}))
        with urllib.request.urlopen(url, timeout=8) as response:
            return json.loads(response.read(2 * 1024 * 1024)).get('results') or []
    return search


def kind_line(c):
    return '%s%s' % ('TV Show' if c['kind'] == 'tv' else 'Movie', ' · %s' % c['year'] if c.get('year') else '')


def pick(xbmcgui, spec):
    """Index of the tapped row, or -1 (Cancel). Falls back to Kodi's select box if the sheet cannot load."""
    try:
        import choice_sheet
        return choice_sheet.choose(spec, xbmcgui=xbmcgui)
    except Exception:
        rows = [xbmcgui.ListItem(label=r['label'], label2=r.get('detail', '')) for r in spec['rows']]
        return xbmcgui.Dialog().select(spec.get('heading') or TITLE, rows)


def last_import_row(data):
    """The Import sheet's "Last import" row (owner, 2026-11-15: the report is a place to check, not a pop-up)."""
    need = fi.need_a_look(data)
    import time
    when = time.strftime('%d %b', time.localtime(float(data.get('time') or 0)))
    detail = '%d added \u00b7 %s' % (int(data.get('added') or 0), when)
    return {'label': 'Last import', 'detail': detail, 'tag': '%d to check' % need if need else '',
            'tag_kind': 'warn' if need else ''}


def read_source(xbmc, xbmcgui, profile=None):
    """(text, list name) from what the person chooses, or ('', ''). "Last import" opens the report page instead."""
    dialog = xbmcgui.Dialog()
    last = fi.load_report(profile) if profile else None
    rows = [{'label': 'Paste a list', 'detail': 'Paste what you copied from Notes'},
            {'label': 'Choose a text file', 'detail': 'A .txt file from the Files app'}]
    if last:
        rows.append(last_import_row(last))
    choice = pick(xbmcgui, {'heading': TITLE, 'sub': 'Copy your list in Notes first, or pick a text file.', 'rows': rows,
                            'foot': 'Only the names are used. Numbers, ticks and side notes are skipped.'})
    if choice == 2 and last:
        open_report(xbmc, xbmcgui, profile)
        return '', '' 
    if choice == 0:
        text = dialog.input('Paste your list', type=xbmcgui.INPUT_ALPHANUM) or ''
        return text, fi.default_list_name()
    if choice == 1:
        chosen = dialog.browse(1, 'Choose a text file', 'files', '.txt|.text|.md', False, False, '')
        if not chosen:
            return '', ''
        try:
            import xbmcvfs
            handle = xbmcvfs.File(chosen)
            try:
                raw = handle.read()
            finally:
                handle.close()
            text = raw if isinstance(raw, str) else bytes(raw).decode('utf-8', 'replace')
        except Exception:
            dialog.ok(TITLE, 'That file could not be read.')
            return '', ''
        name = os.path.splitext(os.path.basename(chosen.rstrip('/\\')))[0]
        return text, name or fi.default_list_name()
    return '', ''


def match_all(xbmc, xbmcgui, entries, key):
    bar = xbmcgui.DialogProgress()
    bar.create(TITLE, 'Looking up titles')

    def progress(n, total, name):
        bar.update(int(100 * (n - 1) / max(total, 1)), '%d of %d · %s' % (n, total, name))

    try:
        return fm.run(entries, tmdb_search(key), progress, cancelled=bar.iscanceled)
    finally:
        bar.close()


def duplicates_text(parsed, already, same):
    lines = []
    for d in list(parsed['duplicates']) + list(same):
        where = ' and '.join(str(n) for n in d['lines'])
        lines.append('%s: lines %s' % (d['title'], where))
    for m in already:
        lines.append('%s: already in Favourites' % m.get('title', m.get('asked', '')))
    return '\n\n'.join(lines) + '\n\nEach was added once, at its first place in the list.'


def report(xbmc, xbmcgui, profile, parsed, result, added, already, list_name):
    """The end-of-import sheet. Returns when the person closes it; answering questions adds titles as they go."""
    dialog = xbmcgui.Dialog()
    questions = list(result['questions'])
    missing = list(result['missing'])
    total_added = len(added)
    while True:
        dup_count = len(parsed['duplicates']) + len(result['duplicates']) + len(already)
        rows, kinds = [], []
        if dup_count:
            rows.append({'label': 'Duplicates', 'detail': 'Tap to see which', 'tag': str(dup_count)})
            kinds.append('dup')
        if questions:
            rows.append({'label': 'Needs your answer', 'detail': 'Misspellings and several matches',
                         'tag': str(len(questions)), 'tag_kind': 'warn'})
            kinds.append('ask')
        if missing:
            rows.append({'label': 'Not found', 'detail': 'Tap to see which', 'tag': str(len(missing)), 'tag_kind': 'warn'})
            kinds.append('missing')
        spec = {'heading': 'Import finished',
                'sub': '%d added to Favourites · %d lines read' % (total_added, parsed['lines']),
                'rows': rows,
                'foot': 'Nothing was removed from your list.' if rows else 'Everything on your list is in Favourites.'}
        choice = pick(xbmcgui, spec)
        if choice < 0 or choice >= len(kinds):
            return total_added
        kind = kinds[choice]
        if kind == 'dup':
            dialog.textviewer('Duplicates', duplicates_text(parsed, already, result['duplicates']))
        elif kind == 'missing':
            names = '\n'.join('Line %s: %s' % (e['line'], e['title']) for e in missing)
            dialog.textviewer('Not found', names + '\n\nCheck the spelling in your list and import it again, or search for them by hand.')
        elif kind == 'ask':
            total_added += answer_questions(xbmcgui, profile, questions, list_name)


def answer_questions(xbmcgui, profile, questions, list_name):
    """One 'did you mean' sheet per question. A pick is added at its place in the list; Cancel skips that name."""
    added = 0
    for q in list(questions):
        entry = q['entry']
        spec = {'heading': '“%s”' % entry['title'], 'sub': 'Line %s. Did you mean one of these?' % entry['line'],
                'rows': [{'label': c['title'], 'detail': kind_line(c)} for c in q['choices']],
                'foot': 'Cancel skips this one.'}
        choice = pick(xbmcgui, spec)
        questions.remove(q)
        if 0 <= choice < len(q['choices']):
            c = q['choices'][choice]
            new, _ = fi.add(profile, [dict(c, rank=entry['rank'], watched=entry.get('watched', 0))], list_name)
            added += len(new)
    return added


def run_import(xbmc, xbmcgui, profile):
    """The whole flow. Returns how many titles were added."""
    dialog = xbmcgui.Dialog()
    import source_match
    key = source_match.tmdb_key()
    if not key:
        dialog.ok(TITLE, 'TMDb Helper is needed to look titles up, and it is not available right now.')
        return 0
    text, list_name = read_source(xbmc, xbmcgui, profile)
    if not text.strip():
        return 0
    parsed = fi.parse(text)
    if not parsed['entries']:
        dialog.ok(TITLE, 'No titles were found in that list.')
        return 0
    result = match_all(xbmc, xbmcgui, parsed['entries'], key)
    added, already = fi.add(profile, result['matched'], list_name)
    failed = [m for m in result['missing'] if m.get('failed')]
    xbmc.log('Kodi iOS favourites import: %d lines, %d added, %d known, %d questions, %d not found, %d could not be looked up' % (
        parsed['lines'], len(added), len(already), len(result['questions']), len(result['missing']) - len(failed), len(failed)),
        xbmc.LOGINFO)
    # ISSUE-323: which names, so a log says whether TMDb had nothing or the lookup failed (titles only, no account data).
    for label, rows in (('not found', [m for m in result['missing'] if not m.get('failed')]), ('lookup failed', failed),
                        ('needs an answer', [q['entry'] for q in result['questions']])):
        if rows:
            xbmc.log('Kodi iOS favourites import %s: %s' % (label, '; '.join(str(r.get('title', ''))[:60] for r in rows[:40])), xbmc.LOGINFO)
    # Owner (2026-11-15): the report is not opened by itself: a short notice, and Import a List › Last import shows it.
    data = fi.save_report(profile, parsed, result, added, already, list_name)
    notify(profile, data)
    return len(added)


REPORT_ACTION = 'import_report'    # a Notifications message with this action opens the report page (notifications.py)


def notice_text(data):
    """The Notifications line (owner-approved mockup N, 2026-11-15)."""
    need = fi.need_a_look(data)
    where = ' from %s' % data['list'] if data.get('list') else ''
    return '%d added to Favourites%s%s' % (int(data.get('added') or 0), where, ' \u00b7 %d need a look' % need if need else '')


def notify(profile, data):
    """Owner (2026-11-15): the finished import is a message in Notifications, never a sheet; tapping it opens the report."""
    try:
        import notices
        notices.add(profile, 'general', 'Import finished', notice_text(data), action=REPORT_ACTION)
    except Exception:
        pass


def open_report(xbmc, xbmcgui, profile):
    """The report page (board I3). Its groups act: Duplicates lists them, Needs your answer asks, Not found searches by hand.
    Returns True when View Favourites was tapped."""
    import favourites_report_page as rp
    dialog = xbmcgui.Dialog()

    class Report(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.view = False
            self.show()

        def show(self):
            for key, value in fi.report_properties(fi.load_report(profile)).items():
                self.setProperty(key, value)

        def onClick(self, control):
            data = fi.load_report(profile) or {}
            if control in (rp.BACK, rp.DONE):
                self.close()
            elif control == rp.VIEW:
                self.view = True
                self.close()
            elif control == rp.DUP:
                dialog.textviewer('Duplicates', full_duplicates(data))
            elif control == rp.ASK:
                data['added'] = int(data.get('added') or 0) + answer_saved(xbmcgui, profile, data)
                fi.save_report_data(profile, data)
                self.show()
            elif control == rp.MISS:
                data['added'] = int(data.get('added') or 0) + search_by_hand(xbmcgui, profile, data)
                fi.save_report_data(profile, data)
                self.show()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 110):
                self.close()

    window = Report(rp.WINDOW, HERE, 'Default', '1080i')
    try:
        window.doModal()
        view = getattr(window, 'view', False)
    finally:
        del window
    return view


def full_duplicates(data):
    lines = ['%s: lines %s' % (d['title'], ' and '.join(str(x) for x in d['lines'])) for d in data.get('duplicates') or []]
    lines += ['%s: already in Favourites' % t for t in data.get('already') or [] if t]
    return '\n'.join(lines) + '\n\nEach was added once, at its first place in the list.'


def answer_saved(xbmcgui, profile, data):
    """The report's open questions, one "did you mean" sheet each; an answered or skipped one leaves the report."""
    questions = list(data.get('questions') or [])
    added = answer_questions(xbmcgui, profile, questions, data.get('list') or '')
    data['questions'] = questions
    return added


def search_by_hand(xbmcgui, profile, data):
    """Not found: each name in the keyboard, as written, to search again (owner-approved board I3). A pick is added at its
    place in the list and leaves the report; an empty search keeps the name for later."""
    import source_match
    dialog = xbmcgui.Dialog()
    key = source_match.tmdb_key()
    if not key:
        dialog.ok(TITLE, 'TMDb Helper is needed to look titles up, and it is not available right now.')
        return 0
    search, added, left = tmdb_search(key), 0, []
    for m in list(data.get('missing') or []):
        query = dialog.input('Search for line %s' % m['line'], defaultt=m['title'], type=xbmcgui.INPUT_ALPHANUM)
        if not query:
            left.append(m)
            continue
        try:
            found = [r for r in search(query) if r.get('media_type') in ('tv', 'movie')][:8]
        except Exception:
            found = []
        choices = [c for c in (fm.candidate(r) for r in found) if c]
        if not choices:
            dialog.ok(TITLE, 'Nothing was found for \u201c%s\u201d.' % query)
            left.append(m)
            continue
        choice = pick(xbmcgui, {'heading': '\u201c%s\u201d' % m['title'], 'sub': 'Line %s. Pick the right one.' % m['line'],
                                'rows': [{'label': c['title'], 'detail': kind_line(c)} for c in choices], 'foot': 'Cancel keeps it for later.'})
        if 0 <= choice < len(choices):
            new, _ = fi.add(profile, [dict(choices[choice], rank=m.get('rank') or 0, watched=m.get('watched', 0))], data.get('list') or '')
            added += len(new)
        else:
            left.append(m)
    data['missing'] = left
    return added


# --- opening a favourite ---------------------------------------------------------------------------------------------

def hms(seconds):
    seconds = int(seconds)
    return '%d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60) if seconds >= 3600 else '%d:%02d' % (seconds // 60, seconds % 60)


def movie_progress(xbmcvfs, tmdb):
    """(position, total) of a movie the owner stopped part-way (Continue Watching's own file), or None."""
    try:
        path = xbmcvfs.translatePath('special://profile/' + CONTINUE_FILE)
        with open(path, encoding='utf-8') as handle:
            entry = (json.load(handle).get('items') or {}).get('movie:%s::' % tmdb)
    except (OSError, ValueError, AttributeError):
        return None
    if not entry:
        return None
    position, total = float(entry.get('position') or 0), float(entry.get('total') or 0)
    if position < 30 or (total and position >= FINISHED * total):
        return None
    return position, total


def show_progress(xbmcvfs, tmdb):
    """(season, episode, position, total) of the episode of this show the owner stopped part-way most recently, or None."""
    try:
        path = xbmcvfs.translatePath('special://profile/' + CONTINUE_FILE)
        with open(path, encoding='utf-8') as handle:
            items = (json.load(handle).get('items') or {}).values()
    except (OSError, ValueError, AttributeError):
        return None
    best = None
    for entry in items:
        if entry.get('kind') != 'episode' or str(entry.get('tmdb_id')) != str(tmdb):
            continue
        position, total = float(entry.get('position') or 0), float(entry.get('total') or 0)
        if position < 30 or (total and position >= FINISHED * total):
            continue
        if best is None or float(entry.get('played') or 0) > best[0]:
            best = (float(entry.get('played') or 0), str(entry.get('season') or ''), str(entry.get('episode') or ''), position, total)
    return best[1:] if best else None


def mark_show(xbmc, xbmcvfs, tmdb):
    """ISSUE-312: the show page marks the in-progress episode "Continue · 11:20 left" (portrait.episode_item reads these Home
    properties; they are cleared when the show has none)."""
    found = show_progress(xbmcvfs, tmdb)
    values = {'Tmdb': '', 'Season': '', 'Episode': '', 'Left': ''}
    if found:
        season, episode, position, total = found
        values = {'Tmdb': str(tmdb), 'Season': season, 'Episode': episode,
                  'Left': 'Continue \u00b7 %s left' % hms(total - position) if total > position else 'Continue'}
    for name, value in values.items():
        xbmc.executebuiltin('SetProperty(KodiIOS.ShowContinue%s,"%s",home)' % (name, value))


def open_item(xbmc, xbmcgui, xbmcvfs, entry):
    """Tap on an imported favourite. A show opens its page (its episodes carry Continue); a movie stopped part-way asks
    Continue Watching or Start Over; any other title goes to the app's "How would you like to watch" chooser."""
    item = entry['imported']
    if item.get('kind') == 'movie':
        progress = movie_progress(xbmcvfs, item.get('tmdb'))
        if progress:
            position, total = progress
            spec = {'heading': item.get('title', ''), 'sub': 'Stopped at %s%s' % (hms(position), ' of %s' % hms(total) if total else ''),
                    'rows': [{'label': 'Continue Watching', 'detail': 'From %s' % hms(position)},
                             {'label': 'Start Over', 'detail': 'Choose how to watch'}]}
            choice = pick(xbmcgui, spec)
            if choice < 0:
                return
            base = '%s?info=play&tmdb_type=movie&tmdb_id=%s' % (HELPER, item['tmdb'])
            xbmc.executebuiltin('PlayMedia(%s)' % ('"%s&%s"' % (base, CONTINUE_FLAG) if choice == 0 else '"%s"' % base))
            return
    if item.get('kind') != 'movie':
        mark_show(xbmc, xbmcvfs, item.get('tmdb'))
    xbmc.executebuiltin(entry['action'])


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    profile = xbmcvfs.translatePath('special://profile/')
    if 'report' in sys.argv[1:]:        # from the Notifications message (mockup N) or anywhere else
        if open_report(xbmc, xbmcgui, profile):
            xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,favourites_page)')
        return
    run_import(xbmc, xbmcgui, profile)


if __name__ == '__main__':
    run()
