"""What each Favourites manager page shows (owner-approved boards K1-K8, docs/design/favourites-manager-mockups.html).

Pure Python: the pages are built from the saved favourites (favourites_import.load), the last import's report
(favourites_import.load_report) and Kodi's own favourites, and returned as
    {'back', 'title', 'sub', 'seg': [labels], 'seg_on': n, 'rows': [row]}
where a row is a dict with 'kind' (header / row / row2 / poster / stats / note / button / link / gap), 'label', 'label2',
'action' (what favourites_manager.py does on a tap) and the properties favourites_manager_page.py draws. Nothing here talks
to Kodi or the network."""
import time

POSTER_URL = 'https://image.tmdb.org/t/p/w342'
ORANGE, GREY, RED, BLUE, GREEN = 'FFFF9F0A', '99EBEBF5', 'FFFF453A', 'FF4FA8FF', 'FF30D158'
WHITE = 'FFFFFFFF'
ONE_LINE = 44            # characters a row's grey line holds on one line (p_foot beside a count); longer ones get ROW2


def poster(path):
    path = str(path or '')
    return (POSTER_URL + path) if path.startswith('/') else path


def kind_word(kind):
    return 'TV Show' if kind == 'tv' else 'Movie' if kind == 'movie' else ''


def grouped(rows):
    """Set 'pos' (only / first / mid / last) on each run of grouped rows (row, row2, poster) for their rounded ends."""
    run = []

    def close():
        for n, r in enumerate(run):
            r['pos'] = 'only' if len(run) == 1 else 'first' if n == 0 else 'last' if n == len(run) - 1 else 'mid'
        del run[:]
    for r in rows:
        if r['kind'] in ('row', 'row2', 'poster'):
            run.append(r)
        else:
            close()
    close()
    return rows


def row(label, line='', action='', **props):
    kind = 'row2' if len(line) > ONE_LINE else 'row'
    return dict({'kind': kind, 'label': label, 'label2': line, 'action': action, 'ltint': WHITE}, **props)


def header(text):
    return {'kind': 'header', 'label': text.upper(), 'action': ''}


def note(text):
    return {'kind': 'note', 'label': text, 'action': ''}


def button(text, action):
    return {'kind': 'button', 'label': text, 'action': action}


def link(text, action, tint=RED):
    return {'kind': 'link', 'label': text, 'action': action, 'ltint': tint}


def gap():
    return {'kind': 'gap', 'label': '', 'action': ''}


def stats(tiles):
    out = {'kind': 'stats', 'label': '', 'action': '', 'tiles': str(len(tiles))}
    for n, (number, name, tint) in enumerate(tiles, 1):
        out.update({'s%dn' % n: str(number), 's%dl' % n: name, 's%dt' % n: tint or WHITE})
    return out


def need_count(report):
    report = report or {}
    return len(report.get('questions') or []) + len(report.get('missing') or [])


def lists(items):
    """[(list name, its titles)] newest import first."""
    by = {}
    for i in items:
        by.setdefault(i.get('list') or 'Imported list', []).append(i)
    return sorted(by.items(), key=lambda kv: -max(float(i.get('added') or 0) for i in kv[1]))


def landing(shown, items, report, own_count, sort_label):
    """K1: Settings › Favourites. shown is what the poster grid holds (favourites_page.read): its counts."""
    report = report or {}
    movies = sum(1 for r in shown if r.get('kind') == 'movie')
    shows = sum(1 for r in shown if r.get('kind') == 'tv')
    need = need_count(report)
    rows = [stats([(len(shown), 'Favourites', WHITE), (movies, 'Movies', WHITE), (shows, 'Shows', WHITE),
                   (need, 'Need a look', ORANGE if need else WHITE)])]
    questions, missing = report.get('questions') or [], report.get('missing') or []
    dups = len(report.get('duplicates') or []) + len([t for t in report.get('already') or [] if t])
    if questions or missing or dups:
        rows.append(header('Needs a look'))
        if questions:
            rows.append(row('Needs your answer', 'Close to more than one title', 'ask', glyph='circle-question.png', tint='33FF9F0A',
                            count=str(len(questions)), count_kind='o', go='1'))
        if missing:
            failed = sum(1 for m in missing if m.get('failed'))
            line = ('%d no match · %d not checked' % (len(missing) - failed, failed)) if failed else 'No title had these names'
            rows.append(row('Not found', line, 'missing', glyph='circle-exclamation.png', tint='33FF453A',
                            count=str(len(missing)), count_kind='o', go='1'))
        if dups:
            rows.append(row('Duplicates', 'Each was added once', 'dups', glyph='equals.png', tint='1FEBEBF5', count=str(dups), go='1'))
    rows.append(header('Your lists'))
    for name, titles in lists(items):
        rows.append(row(name, '%d title%s' % (len(titles), '' if len(titles) == 1 else 's'), 'list:' + name,
                        glyph='list.png', tint='330A84FF', go='1'))
    rows.append(row('Added by hand', '%d from a poster’s menu' % own_count if own_count else 'None yet: hold a poster, Add to favourites',
                    'grid', glyph='star.png', tint='33FF9F0A', go='1'))
    rows.append(header('Manage'))
    rows.append(row('Import a List', 'Paste or share from Notes', 'import', ltint=BLUE, go='1'))
    rows.append(row('Order', 'How the poster grid is sorted', 'sort', value=sort_label, go='1'))
    rows.append(row('Open Favourites', 'The poster grid in the Library', 'grid', go='1'))
    rows.append(gap())
    return {'back': 'Settings', 'title': 'Favourites', 'sub': '', 'rows': grouped(rows)}


def best_line(choice):
    if not choice:
        return ''
    return 'Best guess: %s · %s%s' % (choice.get('title', ''), kind_word(choice.get('kind')), ' · %s' % choice['year'] if choice.get('year') else '')


def questions_page(report):
    """K2: each name with its best guess and how many titles are close; Answer One by One under them."""
    questions = (report or {}).get('questions') or []
    rows = [note('Each name matched more than one title. Tap one to pick the right title, or skip it.')]
    for n, q in enumerate(questions):
        entry, choices = q['entry'], q.get('choices') or []
        first = choices[0] if choices else {}
        rows.append({'kind': 'poster', 'label': '“%s”' % entry.get('title', ''), 'label2': best_line(first),
                     'em': '%d choices' % len(choices) if len(choices) != 1 else '1 choice', 'rank': str(entry.get('line', '')),
                     'thumb': poster(first.get('poster')), 'poster_box': '1', 'go': '1', 'action': 'ask:%d' % n})
    if questions:
        rows.append(button('Answer One by One', 'ask_all'))
        rows.append(note('Your answers are added to Favourites as you go.'))
    else:
        rows.append(note('Nothing is waiting for an answer.'))
    return {'back': 'Favourites', 'title': 'Needs Your Answer', 'sub': '', 'rows': grouped(rows)}


def missing_page(report, failed):
    """K3: names with no match (Search each, Skip All) or names whose lookup failed (Try Again, Try All Again)."""
    missing = (report or {}).get('missing') or []
    none = [(n, m) for n, m in enumerate(missing) if not m.get('failed')]
    unchecked = [(n, m) for n, m in enumerate(missing) if m.get('failed')]
    shown = unchecked if failed else none
    rows = []
    if failed:
        rows.append(note('The lookup did not answer for these (the connection dropped or TMDb was busy). They have not been checked yet.'))
        if unchecked:
            rows.append(button('Try All %d Again' % len(unchecked), 'retry_all'))
    else:
        rows.append(note('TMDb has nothing close to these names. Search by hand with a different spelling, or skip them.'))
    for n, m in shown:
        rows.append({'kind': 'poster', 'label': ('“%s”' % m.get('title', '')) if not failed else m.get('title', ''),
                     'label2': 'Not checked yet' if failed else 'No title close to this name', 'rank': str(m.get('line', '')),
                     'act': 'Try Again' if failed else 'Search', 'action': ('retry:%d' if failed else 'search:%d') % n})
    if not shown:
        rows.append(note('Nothing here.'))
    elif not failed:
        rows.append(link('Skip All %d' % len(shown), 'skip_all'))
        rows.append(note('Skipping only takes them off this page.'))
    return {'back': 'Favourites', 'title': 'Not Found', 'sub': '', 'seg': ['No match · %d' % len(none), 'Not checked · %d' % len(unchecked)],
            'seg_on': 2 if failed else 1, 'rows': grouped(rows)}


def duplicates_page(report):
    """K4: information only: names on the list twice, and titles that were already favourites."""
    report = report or {}
    rows = [note('The same title was on your list more than once, or was already in Favourites. Each is in Favourites once, at its first place in the list.')]
    dups = report.get('duplicates') or []
    if dups:
        rows.append(header('Twice on the list'))
        for d in dups:
            lines = [str(x) for x in d.get('lines') or []]
            rows.append(row(d.get('title', ''), 'Lines %s · kept at line %s' % (' and '.join(lines), lines[0] if lines else ''), ''))
    already = [t for t in report.get('already') or [] if t]
    if already:
        rows.append(header('Already in Favourites'))
        for t in already:
            rows.append(row(t, 'Was in Favourites before the import', ''))
    rows.append(note('Nothing to do here: this page only explains.'))
    return {'back': 'Favourites', 'title': 'Duplicates', 'sub': '', 'rows': grouped(rows)}


def list_page(name, items, report, view='all'):
    """K5: one imported list in its own order: what happened to each name, filtered All / Added / Need a look."""
    report = report or {}
    mine = sorted([i for i in items if (i.get('list') or 'Imported list') == name], key=lambda i: i.get('rank', 0))
    own_report = report if report.get('list') == name else {}
    asks = list(own_report.get('questions') or [])
    missing = list(own_report.get('missing') or [])
    need = len(asks) + len(missing)
    when = min([float(i.get('added') or 0) for i in mine] or [float(own_report.get('time') or 0)])
    rows = [stats([(own_report.get('lines') or len(mine) + need, 'Names', WHITE), (len(mine), 'Added', GREEN),
                   (need, 'Need a look', ORANGE if need else WHITE)])]
    if when:
        rows.append(note('Imported %s.' % time.strftime('%d %b at %H:%M', time.localtime(when))))
    entries = []
    if view in ('all', 'added'):
        for i in mine:
            entries.append((int(i.get('rank') or 0), {'kind': 'poster', 'label': i.get('title', ''),
                            'label2': '%s%s' % (kind_word(i.get('kind')), ' · %s' % i['year'] if i.get('year') else ''),
                            'rank': str(i.get('rank', '')), 'thumb': poster(i.get('poster')), 'poster_box': '1',
                            'chip': 'Added', 'chip_back': '2E30D158', 'chip_tint': GREEN, 'action': 'open:%s:%s' % (i.get('kind'), i.get('tmdb'))}))
    if view in ('all', 'need'):
        for n, q in enumerate(asks):
            e = q['entry']
            entries.append((int(e.get('rank') or 0), {'kind': 'poster', 'label': '“%s”' % e.get('title', ''),
                            'label2': '%d titles close to this name' % len(q.get('choices') or []), 'rank': str(e.get('line', '')),
                            'chip': 'Answer', 'chip_back': '2EFF9F0A', 'chip_tint': ORANGE, 'action': 'ask:%d' % n}))
        for n, m in enumerate(missing):
            entries.append((int(m.get('rank') or 0), {'kind': 'poster', 'label': '“%s”' % m.get('title', ''),
                            'label2': 'Not checked yet' if m.get('failed') else 'No title close to this name', 'rank': str(m.get('line', '')),
                            'chip': 'Not found', 'chip_back': '2EFF453A', 'chip_tint': RED,
                            'action': ('retry:%d' if m.get('failed') else 'search:%d') % n}))
    rows += [r for _, r in sorted(entries, key=lambda e: e[0])]
    if not entries:
        rows.append(note('Nothing to show here.'))
    if mine:
        rows.append(link('Remove This List', 'remove_list'))
        rows.append(note('Takes this list’s %d title%s out of Favourites. Favourites added by hand stay.' % (len(mine), '' if len(mine) == 1 else 's')))
    return {'back': 'Favourites', 'title': name, 'sub': '', 'seg': ['All', 'Added', 'Need a look'],
            'seg_on': {'all': 1, 'added': 2, 'need': 3}.get(view, 1), 'rows': grouped(rows)}


def kind_line(c, details=None):
    """Under a poster in the picker (owner: the name and the year, not just the art): Anime / TV Show / Movie · year ·
    seasons or episodes when TMDb's details say."""
    d = details or {}
    genres = {g.get('id') for g in d.get('genres') or []} | set(c.get('genre_ids') or [])
    japanese = 'JP' in (d.get('origin_country') or c.get('origin_country') or []) or (d.get('original_language') or c.get('original_language')) == 'ja'
    word = 'Anime' if 16 in genres and japanese else kind_word(c.get('kind'))
    parts = [word, str(c.get('year') or '')]
    if c.get('kind') == 'tv':
        seasons, episodes = int(d.get('number_of_seasons') or 0), int(d.get('number_of_episodes') or 0)
        if seasons > 1:
            parts.append('%d seasons' % seasons)
        elif seasons == 1 and episodes:
            parts.append('%d episodes' % episodes)
    return ' · '.join(p for p in parts if p)


def picker(name, line, choices, details=None, search='', mode='ask'):
    """K7 (mode 'ask') and K8 (mode 'search'): the posters to choose from, the most likely one marked."""
    details = details or {}
    cells = []
    for n, c in enumerate(choices):
        key = '%s:%s' % (c.get('kind'), c.get('tmdb'))
        cells.append({'label': c.get('title', ''), 'label2': kind_line(c, details.get(key)), 'poster': poster(c.get('poster')),
                      'best': ('Most likely' if mode == 'ask' else 'Best match') if n == 0 else ''})
    sub = ('Line %s · Which one did you mean? Tap its poster.' % line) if mode == 'ask' else \
          ('Line %s · No title had this name. Change the spelling to search again.' % line if not choices or search == name else
           'Line %s · Tap the right poster, or change the search.' % line)
    if mode == 'search' and not choices:
        sub = 'Line %s · Nothing was found for “%s”. Change the spelling to search again.' % (line, search or name)
    return {'back': 'Needs Your Answer' if mode == 'ask' else 'Not Found', 'title': '“%s”' % name, 'sub': sub,
            'search': '1' if mode == 'search' else '', 'query': search or name,
            'other': 'Search Another Name' if mode == 'ask' else '', 'cells': cells}
