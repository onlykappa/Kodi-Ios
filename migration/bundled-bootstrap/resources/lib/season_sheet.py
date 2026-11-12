"""Build Season (owner, 2026-11-12; docs/design/season-pack-mockups.html boards B, C and D, round 2).

A season download always builds the season from single episodes: no ready-made season packs (owner: "the season builder
should be used at all times ... the only option is Build Season"). The owner picks a quality on a sheet of four cards
(board B); the app looks up every episode at that quality, taking the next quality down for an episode that only exists
lower (board C, the building card); a ready sheet says what was found before anything downloads (board D).

The models below are plain Python (scripts/test_season_sheet.py); the windows are portrait/IOSSeasonQuality.xml and
portrait/IOSSeasonReady.xml (pages.season_quality_sheet / season_ready_sheet) and the card is IOSSearching.xml.
"""
QUALITIES = ('4k', '1080p', '720p', '480p')
LABELS = {'4k': '4K', '1440p': '1440p', '1080p': '1080p', '720p': '720p', '480p': '480p', 'sd': 'SD'}
NOTES = {'4k': 'Sharpest · big files', '1080p': 'Best for most', '720p': 'Smaller files', '480p': 'Smallest files'}
FALLBACK = {'4k': ('1440p', '1080p', '720p'), '1440p': ('1080p', '720p'), '1080p': ('720p',), '720p': ('480p', 'sd'),
            '480p': ('sd',), 'sd': ()}
DEFAULT = '1080p'
ROWS = 4          # episode rows on the ready sheet before "N more episodes"
CARD_LINES = 2    # lines on the building card

# Window controls (pages.py draws them with these ids).
CARD_BASE = 9701          # quality cards 9701..9704 (QUALITIES order)
BUILD, CLOSE = 9720, 9721
DOWNLOAD_ALL, READY_CLOSE = 9730, 9731
CANCEL = 9802             # the card's one Cancel (pages.searching_card)


def size_text(gb):
    if not gb:
        return ''
    return '%.1f GB' % gb if gb >= 1 else '%d MB' % round(gb * 1024)


def quality_props(title, season, episodes, chosen=DEFAULT):
    """Window properties for board B: the four cards, the sentence and the button for the chosen quality."""
    props = {'season.title': 'Season %s' % season, 'season.sub': '%s · %d episode%s' % (title, episodes, '' if episodes == 1 else 's')}
    for n, q in enumerate(QUALITIES, 1):
        props['q.%d.label' % n] = LABELS[q]
        props['q.%d.note' % n] = NOTES[q]
        props['q.%d.on' % n] = 'true' if q == chosen else ''
    # Rig (2026-11-12): four lines were cut off above the button; the mockup's sentence is three lines.
    props['how'] = ('Finds the best copy of each of the %d episodes in %s and downloads them in order. '
                    'One only out lower comes a quality down, marked.' % (episodes, LABELS[chosen]))
    props['button'] = 'Build %s Season' % LABELS[chosen]
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
                      [('Adding to your downloads', '%d of %d' % (done, total), 'wait' if done < total else 'ok')],
                      100.0 * done / max(1, total))


def ready_model(title, season, wanted, picks, names):
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
            'episodes': got}


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


def pick_quality(xbmcgui, title, season, episodes):
    """Board B: the quality to build in, or None."""
    state = {'q': DEFAULT, 'answer': None}

    class Sheet(xbmcgui.WindowXMLDialog):
        def show_choice(self):
            for k, v in quality_props(title, season, episodes, state['q']).items():
                self.setProperty(k, v)

        def onInit(self):
            self.show_choice()
            try:
                self.setFocusId(BUILD)
            except Exception:
                pass

        def onClick(self, control):
            if CARD_BASE <= control < CARD_BASE + len(QUALITIES):
                state['q'] = QUALITIES[control - CARD_BASE]
                self.show_choice()
            elif control == BUILD:
                state['answer'] = state['q']
                self.close()
            elif control == CLOSE:
                self.close()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
                self.close()

    sheet = Sheet('IOSSeasonQuality.xml', _here(), 'Default', '1080i')
    try:
        sheet.doModal()
        return state['answer']
    finally:
        del sheet


def confirm_ready(xbmcgui, model):
    """Board D: True when Download All was tapped."""
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
        self.gui, self.canceled, self.window = xbmcgui, False, None
        home = xbmcgui.Window(10000)
        owner = self

        class Window(xbmcgui.WindowXMLDialog):
            def onClick(self, control):
                if control == CANCEL:
                    owner.canceled = True
                    self.close()

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
