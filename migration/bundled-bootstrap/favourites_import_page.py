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


def read_source(xbmc, xbmcgui):
    """(text, list name) from what the person chooses, or ('', '')."""
    dialog = xbmcgui.Dialog()
    choice = pick(xbmcgui, {'heading': TITLE, 'sub': 'Copy your list in Notes first, or pick a text file.',
                            'rows': [{'label': 'Paste a list', 'detail': 'Paste what you copied from Notes'},
                                     {'label': 'Choose a text file', 'detail': 'A .txt file from the Files app'}],
                            'foot': 'Only the names are used. Numbers, ticks and side notes are skipped.'})
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
    text, list_name = read_source(xbmc, xbmcgui)
    if not text.strip():
        return 0
    parsed = fi.parse(text)
    if not parsed['entries']:
        dialog.ok(TITLE, 'No titles were found in that list.')
        return 0
    result = match_all(xbmc, xbmcgui, parsed['entries'], key)
    added, already = fi.add(profile, result['matched'], list_name)
    xbmc.log('Kodi iOS favourites import: %d lines, %d added, %d known, %d questions, %d not found' % (
        parsed['lines'], len(added), len(already), len(result['questions']), len(result['missing'])), xbmc.LOGINFO)
    return report(xbmc, xbmcgui, profile, parsed, result, added, already, list_name)


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
    xbmc.executebuiltin(entry['action'])


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    run_import(xbmc, xbmcgui, xbmcvfs.translatePath('special://profile/'))


if __name__ == '__main__':
    run()
