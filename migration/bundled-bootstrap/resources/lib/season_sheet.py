"""Build Season (owner, 2026-11-12; docs/design/season-pack-mockups.html boards B, C and D, round 2).

A season download always builds the season from single episodes: no ready-made season packs (owner: "the season builder
should be used at all times ... the only option is Build Season"). The owner picks a quality on a sheet of four cards
(board B); the app looks up every episode at that quality, taking the next quality down for an episode that only exists
lower (board C, the building card); a ready sheet says what was found before anything downloads (board D).

The models below are plain Python (scripts/test_season_sheet.py); the windows are portrait/IOSSeasonQuality.xml and
portrait/IOSSeasonReady.xml (pages.season_quality_sheet / season_ready_sheet) and the card is IOSSearching.xml.
"""
# Board B3 (DEC-041): 4K, 1080p and 720p only (owner: "remove the 480P").
QUALITIES = ('4k', '1080p', '720p')
LABELS = {'4k': '4K', '1440p': '1440p', '1080p': '1080p', '720p': '720p', '480p': '480p', 'sd': 'SD'}
FALLBACK = {'4k': ('1440p', '1080p', '720p'), '1440p': ('1080p', '720p'), '1080p': ('720p',), '720p': ('480p', 'sd'),
            '480p': ('sd',), 'sd': ()}
ROWS = 4          # episode rows on the ready sheet before "N more episodes"
CARD_LINES = 2    # lines on the building card

# Window controls (pages.py draws them with these ids).
CARD_BASE = 9701          # quality cards 9701..9704 (QUALITIES order)
BUILD, CLOSE = 9720, 9721
DOWNLOAD_ALL, READY_CLOSE = 9730, 9731
MORE_ROW = 9732           # the ready sheet's "N more episodes" row: opens the full list (board F)
EP_LIST, EP_ALL, EP_BACK, EP_FILTER = 9740, 9741, 9742, 9745   # board F: list, Download All, back link, filters 9745-9747
CANCEL = 9802             # the card's Cancel (pages.searching_card): stops the work
HIDE = 9803               # the card's Close: hides the card, the work goes on in the background


def size_text(gb):
    if not gb:
        return ''
    return '%.1f GB' % gb if gb >= 1 else '%d MB' % round(gb * 1024)


# DEC-041: the recommended quality is the highest one found unless an episode is over about 3 GB or the season over
# about 40 GB; then the next one down.
EPISODE_LIMIT_GB = 3.0
SEASON_LIMIT_GB = 40.0


def season_size(gb):
    """'15 GB', '8.3 GB', '450 MB' (board B3)."""
    if not gb:
        return ''
    if gb >= 10:
        return '%d GB' % round(gb)
    return size_text(gb)


def check_numbers(numbers):
    """The three episodes the quick check looks up first: start, middle, end (board B3·1)."""
    numbers = sorted(numbers)
    if len(numbers) <= 3:
        return numbers
    return sorted({numbers[0], numbers[len(numbers) // 2], numbers[-1]})


def survey(found):
    """{episode: scan answer} -> {quality: [size of one episode, ...]} for the sheet's three rows. A copy found only
    below 720p counts for 720p (Build Season takes it a quality down)."""
    out = {}
    for answer in found.values():
        sizes = answer.get('sizes') or {}
        got = list(answer.get('qualities') or [])
        for q in QUALITIES:
            have = q if q in got else (best_for(got, q) if q == '720p' else None)
            if have:
                out.setdefault(q, []).append(float(sizes.get(have) or 0))
    return out


def each_size(sizes):
    sizes = [s for s in sizes or [] if s]
    return sum(sizes) / len(sizes) if sizes else 0.0


def recommend(found, episodes):
    """The quality picked for the owner (DEC-041), or None when the check found nothing."""
    have = [q for q in QUALITIES if q in found]
    for q in have:
        each = each_size(found[q])
        if each <= EPISODE_LIMIT_GB and each * episodes <= SEASON_LIMIT_GB:
            return q
    return have[-1] if have else None


def checking_props(title, season, episodes, checked, done, states):
    """Board B3·1: the check card while three episodes are looked up. states: {quality: 'found'|'none'|''}."""
    props = {'season.title': 'Season %s' % season, 'season.sub': '%s · %d episode%s' % (title, episodes, '' if episodes == 1 else 's'),
             'checking': 'true', 'check.title': 'Checking which qualities exist\u2026',
             'check.sub': 'Looking at episode%s %s' % ('' if len(checked) == 1 else 's', _and(checked)),
             'check.pct': str(int(100 * done / max(1, len(checked)))),
             'how': 'Takes a few seconds. Only qualities that exist can be chosen.', 'button': 'Build Season', 'button.off': 'true'}
    for n, q in enumerate(QUALITIES, 1):
        props['check.q.%d' % n] = '%s \u00b7 %s' % (LABELS[q], {'found': 'found', 'none': 'not found'}.get(states.get(q), '\u2026'))
    return props


def _and(numbers):
    numbers = ['%d' % n for n in numbers]
    return numbers[0] if len(numbers) == 1 else ', '.join(numbers[:-1]) + ' and ' + numbers[-1]


def quality_props(title, season, episodes, found=None, chosen=None):
    """Board B3: three rows (4K, 1080p, 720p) with the season's size and an episode's, a quality no copy exists in
    greyed, one RECOMMENDED; the sentence and the button for the chosen one. found=None: the check did not answer, so
    every row can be chosen and none has a size."""
    unchecked = found is None
    found = found or {}
    rec = None if unchecked else recommend(found, episodes)
    chosen = chosen or rec or '1080p'
    props = {'season.title': 'Season %s' % season, 'season.sub': '%s · %d episode%s' % (title, episodes, '' if episodes == 1 else 's'),
             'checking': ''}
    for n, q in enumerate(QUALITIES, 1):
        each = each_size(found.get(q))
        ok = unchecked or q in found
        props['q.%d.label' % n] = LABELS[q]
        props['q.%d.rec' % n] = 'RECOMMENDED' if q == rec else ''
        props['q.%d.on' % n] = 'true' if q == chosen and ok else ''
        props['q.%d.off' % n] = '' if ok else 'true'
        if unchecked:
            props['q.%d.size' % n], props['q.%d.each' % n] = 'Not checked', 'Sizes show once it is found'
        elif not ok:
            props['q.%d.size' % n], props['q.%d.each' % n] = 'Not found', 'No copy exists'
        elif each:
            props['q.%d.size' % n], props['q.%d.each' % n] = '%s season' % season_size(each * episodes), '%s each' % size_text(each)
        else:
            props['q.%d.size' % n], props['q.%d.each' % n] = 'Found', 'Size not known'
    label = LABELS[chosen]
    total = season_size(each_size(found.get(chosen)) * episodes)
    higher = [q for q in QUALITIES[:QUALITIES.index(rec)]] if rec else []
    missing = [q for q in higher if q not in found]
    if unchecked:
        how = ('The quick check did not answer, so every quality can be chosen. An episode only found lower comes a '
               'quality down, marked.')
    elif not found:
        how = 'No copy of these episodes was found in 4K, 1080p or 720p. Try again later.'
    elif chosen != rec:
        how = ('Finds the best copy of each of the %d episodes in %s and downloads them in order. One only out lower '
               'comes a quality down, marked.' % (episodes, label))
    elif not higher:
        how = '[B]%s is small for this show[/B], so it is picked for you. Any episode only found lower comes a quality down, marked.' % label
    elif missing and len(missing) == len(higher):
        how = 'No %s copy exists, so %s greyed and cannot be chosen. [B]%s[/B] is the best there is.' % (
            ' or '.join(LABELS[q] for q in missing), 'it is' if len(missing) == 1 else 'they are', label)
    else:
        big = next(q for q in higher if q in found)
        how = '[B]%s is very large[/B] here (%s), so %s is recommended. %s can still be chosen.' % (
            LABELS[big], season_size(each_size(found[big]) * episodes) or 'over 40 GB', label, LABELS[big])
    props['how'] = how
    props['chosen'] = chosen
    props['button'] = 'Build %s Season%s' % (label, ' \u00b7 ' + total if total else '')
    props['button.off'] = 'true' if not unchecked and not found else ''
    return props


def best_for(qualities, wanted):
    """The quality an episode is taken in: the wanted one, else the next one down that exists, else None."""
    if wanted in qualities:
        return wanted
    return next((q for q in FALLBACK.get(wanted, ()) if q in qualities), None)


def card_props(kicker, title, lines, pct):
    """The building card (board C) / searching card (board A): kicker, title, up to five lines (text, count,
    state: ok | wait | none) and the bar."""
    props = {'IOSSearch.Kicker': kicker, 'IOSSearch.Title': title, 'IOSSearch.Pct': str(int(max(0, min(100, pct)))),
             'IOSSearch.Lines': str(len(lines))}
    for n in range(1, 6):
        text, count, state = lines[n - 1] if n <= len(lines) else ('', '', '')
        props['IOSSearch.Line.%d.Text' % n] = text
        props['IOSSearch.Line.%d.Count' % n] = count
        props['IOSSearch.Line.%d.State' % n] = state
    return props


def building_props(season, quality, title, done, total, found, looking):
    lines = [('Episodes found', '%d of %d' % (found, total), 'ok' if found else 'none')]
    if looking:
        lines.append(('Looking for episode %d' % looking, '', 'wait'))
    return card_props('Building Season %s · %s' % (season, LABELS[quality]), title, lines, 100.0 * done / max(1, total))


def queueing_props(season, quality, title, done, total):
    return card_props('Season %s · %s' % (season, LABELS[quality]), title,
                      [('Adding episodes', '%d of %d' % (done, total), 'wait' if done < total else 'ok')],
                      100.0 * done / max(1, total))


def full_rows(wanted, picks, names, details=None):
    """Board F (owner, 2026-11-12: "if i press 28 more episodes it should show the list, and tell me any details and
    stuff like 720p only"): every episode in order, found or not: number, name, size, an orange tag when it was only
    found lower, the version's details (quality, video, audio, seeds), and 'Left out' for one found nowhere."""
    details = details or {}
    rows = []
    for n in sorted(picks):
        q, size = picks[n]
        lower = bool(q) and q != wanted
        if q:
            line = (LABELS.get(q, q) + (' only' if lower else '') + (' \u00b7 ' + details[n] if details.get(n) else ''))
        else:
            line = 'Not found in any quality yet'
        rows.append({'no': str(n), 'name': names.get(n) or 'Episode %d' % n, 'size': size_text(size) if q else '',
                     'low': LABELS.get(q, '') if lower else '', 'detail': line, 'gone': '' if q else 'true',
                     'kind': 'gone' if not q else ('lower' if lower else 'ok')})
    return rows


def ready_model(title, season, wanted, picks, names, details=None):
    """Board D. picks: {episode: (quality or None, size_gb)}; names: {episode: title}. Episodes not found are left out
    of the download and said so; lower ones are marked."""
    got = sorted(n for n, (q, _) in picks.items() if q)
    missing = sorted(n for n, (q, _) in picks.items() if not q)
    lower = [n for n in got if picks[n][0] != wanted]
    total = sum(picks[n][1] or 0 for n in got)
    shown = (lower + [n for n in got if n not in lower])[:ROWS]
    rows = [{'no': str(n), 'name': names.get(n) or 'Episode %d' % n, 'size': size_text(picks[n][1]),
             'low': LABELS.get(picks[n][0], '') if n in lower else ''} for n in sorted(shown)]
    more = len(got) - len(rows)
    if missing and lower:
        warn, ok = '%d only in a lower quality; %d not found, left out.' % (len(lower), len(missing)), False
    elif missing:
        warn, ok = '%d episode%s not found in any quality, left out.' % (len(missing), '' if len(missing) == 1 else 's'), False
    elif lower:
        warn, ok = '%d episode%s only found in a lower quality.' % (len(lower), '' if len(lower) == 1 else 's'), False
    else:
        warn, ok = 'Every episode found in %s.' % LABELS[wanted], True
    return {'title': 'Season %s is ready' % season, 'sub': '%s · Build Season' % title,
            'count': str(len(got)), 'quality': LABELS[wanted], 'total': size_text(total) or '—',
            'rows': rows, 'more': ('%d more episode%s' % (more, '' if more == 1 else 's')) if more > 0 else '',
            'warn': warn + ' Everything goes to Google Drive in episode order.', 'ok': ok,
            'button': ('Download All %d · %s' % (len(got), size_text(total))) if total else 'Download All %d' % len(got),
            'episodes': got, 'all': full_rows(wanted, picks, names, details),
            'counts': {'all': len(picks), 'lower': len(lower), 'gone': len(missing)}}


def ready_props(model):
    props = {k: model[k] for k in ('title', 'sub', 'count', 'quality', 'total', 'more', 'warn', 'button')}
    props['ok'] = 'true' if model['ok'] else ''
    for n in range(1, ROWS + 1):
        r = model['rows'][n - 1] if n <= len(model['rows']) else {}
        for k in ('no', 'name', 'size', 'low'):
            props['row.%d.%s' % (n, k)] = r.get(k, '')
    return props


# --- windows (Kodi only) ---------------------------------------------------------------------------------------------
def _here():
    import os
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pick_quality(xbmcgui, title, season, episodes, check=None, wait=None):
    """Board B3: the quality to build in, or None. check(show, stopped) looks up a few episodes while the sheet shows
    the check card (B3·1): show(done, states) updates it, stopped() is true once the sheet was closed; it returns
    {episode: scan answer}, or None when no lookup answered. wait(seconds) is Kodi's wait (taps reach the sheet only
    while this script waits in Kodi); it returns True when Kodi is quitting."""
    state = {'q': None, 'answer': None, 'closed': False, 'found': {}, 'ready': check is None, 'props': {}}
    if check is None:
        state['found'] = None

    def pick_props():
        return quality_props(title, season, episodes, state['found'], state['q'])

    class Sheet(xbmcgui.WindowXMLDialog):
        def apply(self, props):
            state['props'] = props
            for k, v in props.items():
                try:
                    self.setProperty(k, v)
                except Exception:
                    pass

        def onInit(self):
            self.apply(state['props'] or pick_props())
            try:
                self.setFocusId(BUILD if state['ready'] else CLOSE)
            except Exception:
                pass

        def onClick(self, control):
            if control == CLOSE:
                self.close()
            elif not state['ready']:
                return
            elif CARD_BASE <= control < CARD_BASE + len(QUALITIES):
                q = QUALITIES[control - CARD_BASE]
                if state['found'] is not None and q not in state['found']:
                    return                                    # greyed: no copy exists
                state['q'] = q
                self.apply(pick_props())
            elif control == BUILD and not state['props'].get('button.off'):
                state['answer'] = state['q'] or state['props'].get('chosen')
                self.close()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
                self.close()

        def close(self):
            state['closed'] = True
            xbmcgui.WindowXMLDialog.close(self)

    sheet = Sheet('IOSSeasonQuality.xml', _here(), 'Default', '1080i')
    try:
        if check is None:
            state['props'] = pick_props()
            sheet.doModal()
            return state['answer']
        import threading
        checked = []
        state['props'] = checking_props(title, season, episodes, getattr(check, 'numbers', ()) or (), 0, {})
        threading.Thread(target=sheet.doModal, daemon=True).start()

        def show(done, states):
            sheet.apply(checking_props(title, season, episodes, getattr(check, 'numbers', ()) or (), done, states))
        found = check(show, lambda: state['closed'])
        if state['closed']:
            return None
        state['found'] = survey(found) if found is not None else None
        state['ready'] = True
        props = pick_props()
        state['q'] = next((q for n, q in enumerate(QUALITIES, 1) if props.get('q.%d.on' % n)), None)
        sheet.apply(props)
        try:
            sheet.setFocusId(BUILD)
        except Exception:
            pass
        while not state['closed']:
            if wait is not None and wait(0.1):
                sheet.close()
                break
            if wait is None:
                import time
                time.sleep(0.1)
        return state['answer']
    finally:
        del sheet


FILTERS = (('all', 'All'), ('lower', 'Lower'), ('gone', 'Not found'))


def filter_rows(rows, key):
    return [r for r in rows if key == 'all' or r['kind'] == key]


def episodes_props(model, key):
    """Window properties for board F: the season, the counts on the three filter buttons, the button."""
    c = model.get('counts') or {}
    props = {'title': 'All %d episodes' % c.get('all', 0), 'back': '\u2039 ' + model['title'].replace(' is ready', ''),
             'sub': model['sub'].split(' \u00b7 ')[0] + ' \u00b7 %s \u00b7 %s' % (model['quality'], model['total']),
             'button': model['button'], 'filter': key}
    for k, label in FILTERS:
        props['f.' + k] = '%s %d' % (label, c.get(k, 0)) if k != 'all' else '%s %d' % (label, c.get('all', 0))
    lower, gone = c.get('lower', 0), c.get('gone', 0)
    props['note'] = ' '.join(t for t in (
        ('%d only exist%s in a lower quality and come in it.' % (lower, 's' if lower == 1 else '')) if lower else '',
        ('%d %s left out; looked for again later.' % (gone, 'is' if gone == 1 else 'are')) if gone else '') if t)
    return props


def show_episodes(xbmcgui, model):
    """Board F: every episode. True when Download All was tapped here, False to go back to the ready sheet."""
    state = {'go': False, 'key': 'all'}

    class Page(xbmcgui.WindowXMLDialog):
        def fill(self):
            for k, v in episodes_props(model, state['key']).items():
                self.setProperty(k, v)
            lst = self.getControl(EP_LIST)
            lst.reset()
            items = []
            for r in filter_rows(model.get('all') or [], state['key']):
                li = xbmcgui.ListItem(r['name'])
                for k in ('no', 'size', 'low', 'detail', 'gone'):
                    li.setProperty(k, r[k])
                items.append(li)
            lst.addItems(items)

        def onInit(self):
            self.fill()
            try:
                self.setFocusId(EP_LIST)
            except Exception:
                pass

        def onClick(self, control):
            if control == EP_ALL:
                state['go'] = True
                self.close()
            elif control == EP_BACK:
                self.close()
            elif EP_FILTER <= control < EP_FILTER + len(FILTERS):
                state['key'] = FILTERS[control - EP_FILTER][0]
                self.fill()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
                self.close()

    page = Page('IOSSeasonEpisodes.xml', _here(), 'Default', '1080i')
    try:
        page.doModal()
        return state['go']
    finally:
        del page


def confirm_ready(xbmcgui, model):
    """Board D: True when Download All was tapped (here or on the full list, board F)."""
    state = {'go': False}

    class Sheet(xbmcgui.WindowXMLDialog):
        def onInit(self):
            for k, v in ready_props(model).items():
                self.setProperty(k, v)
            try:
                self.setFocusId(DOWNLOAD_ALL)
            except Exception:
                pass

        def onClick(self, control):
            if control == MORE_ROW:
                if show_episodes(xbmcgui, model):
                    state['go'] = True
                    self.close()
                return
            state['go'] = control == DOWNLOAD_ALL
            if control in (DOWNLOAD_ALL, READY_CLOSE):
                self.close()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
                self.close()

    sheet = Sheet('IOSSeasonReady.xml', _here(), 'Default', '1080i')
    try:
        sheet.doModal()
        return state['go']
    finally:
        del sheet


class Card(object):
    """The building card (board C) over the page while the episodes are looked up. Cancel sets `canceled`."""
    def __init__(self, xbmcgui):
        import threading
        self.gui, self.canceled, self.window, self.hidden = xbmcgui, False, None, False
        home = xbmcgui.Window(10000)
        owner = self

        class Window(xbmcgui.WindowXMLDialog):
            def onClick(self, control):
                if control == CANCEL:
                    owner.canceled = True
                    self.close()
                elif control == HIDE:
                    owner.hide()

            def onAction(self, action):
                if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
                    owner.canceled = True
                    self.close()
        self.home = home
        try:
            self.window = Window('IOSSearching.xml', _here(), 'Default', '1080i')
            threading.Thread(target=self.window.doModal, daemon=True).start()
        except Exception:
            self.window = None

    def hide(self):
        """Close: the card goes, the season goes on (owner: play around while it works); the ready sheet or the
        'added to your downloads' message still comes at the end."""
        self.hidden = True
        if self.window is not None:
            try:
                self.window.close()
            except Exception:
                pass
        try:
            self.gui.Dialog().notification(self.home.getProperty('IOSSearch.Kicker') or 'Season', 'Working in the background',
                                           self.gui.NOTIFICATION_INFO, 3000, False)
        except Exception:
            pass

    def show(self, props):
        for k, v in props.items():
            self.home.setProperty(k, v)

    def close(self):
        if self.window is not None:
            try:
                self.window.close()
            except Exception:
                pass
        for k in list(card_props('', '', [], 0)):
            self.home.clearProperty(k)
