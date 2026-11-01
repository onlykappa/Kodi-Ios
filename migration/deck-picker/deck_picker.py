# -*- coding: utf-8 -*-
# DECK-ELEMENTUM deck_picker v1
"""
Steam Deck link picker for Elementum.

Elementum's background program sends Kodi a list of text entries (one per torrent link)
and Kodi shows them in a big dialog. run() sits in front of that dialog:

  1. reads every entry (quality, seeds, size, tags, providers)
  2. asks which QUALITY you want (only qualities that exist), or "Show all"
  3. shows the best few DIFFERENT links in that quality on a clean page
     ("best" keeps Elementum's own ordering, i.e. your sorting setting)

run() returns the index of the chosen entry in Elementum's ORIGINAL list, -1 if you
cancelled, or None when it should not handle the list (not a torrent list, a short
list, "Show all", or any problem). The caller then shows Elementum's normal dialog,
so nothing can get stuck.
"""
import re

TOP_N = 5
DOT = u'  \u2022  '

QUALITY_LABELS = {
    '4k': u'4K Ultra HD',
    '1440p': u'1440p QHD',
    '1080p': u'1080p Full HD',
    '720p': u'720p HD',
    '480p': u'480p SD',
    'sd': u'SD',
}
QUALITY_ORDER = ['4k', '1440p', '1080p', '720p', '480p', 'sd']
GOOD_TYPES = (u'Blu-ray Remux', u'Blu-ray', u'WEB-DL', u'WEBRip', u'HDTV')

BB_RE = re.compile(r'\[/?(?:B|I|COLOR[^\]]*|UPPERCASE|LOWERCASE|CAPITALIZE)\]', re.I)
HEAD_RE = re.compile(r'^\s*(\S+)\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)\s*\[\s*([\d.,]+)\s*([A-Za-z]+)\s*\]\s*(.*)$', re.S)
SEP_RE = re.compile(r'[^A-Z0-9+]+')
CHAN_RE = re.compile(r'(?<![0-9])([257])[. ]([01])(?![0-9])')
UNIT_GB = {'KB': 1e-6, 'KIB': 1e-6, 'MB': 1.0 / 1024, 'MIB': 1.0 / 1024, 'GB': 1.0, 'GIB': 1.0,
           'TB': 1024.0, 'TIB': 1024.0}


def _s(value):
    return u'' if value is None else (value if isinstance(value, type(u'')) else str(value))


# ---------------------------------------------------------------------------------
# reading one entry
# ---------------------------------------------------------------------------------
def parse_item(raw, idx):
    """Return a dict for one Elementum entry, or None if it does not look like a torrent link."""
    parts = _s(raw).split('\n')
    plain = BB_RE.sub(u'', parts[0])
    m = HEAD_RE.match(plain)
    if not m:
        return None
    quality, seeds, peers, num, unit, rest = m.groups()
    try:
        size = float(num.replace(',', '')) * UNIT_GB.get(unit.upper(), 0)
    except ValueError:
        return None
    if u' - ' in rest:
        tags_text, prov = rest.rsplit(u' - ', 1)
    else:
        tags_text, prov = rest, u''
    name = (parts[1] if len(parts) > 1 else u'').strip()
    name = re.sub(r'^[-\s]+', u'', name)
    q = quality.lower()
    q = {'2160p': '4k', 'uhd': '4k'}.get(q, q)
    return {
        'idx': idx,
        'quality': q,
        'seeds': int(seeds),
        'peers': int(peers),
        'size': size,
        'tags_text': tags_text.strip(),
        'name': name,
        'providers': [p.strip() for p in prov.split(',') if p.strip()],
        'icon': parts[2] if len(parts) > 2 else u'',
        'multi': len(parts) > 3 and parts[3].strip() == 'multi',
    }


def parse_all(items):
    """List of parsed entries, or None if this is not (mostly) a torrent link list."""
    if not items:
        return None
    parsed = [p for p in (parse_item(it, n) for n, it in enumerate(items)) if p]
    if len(parsed) < 0.8 * len(items):
        return None
    return parsed


# ---------------------------------------------------------------------------------
# words
# ---------------------------------------------------------------------------------
def _blob(text):
    return u' %s ' % SEP_RE.sub(u' ', _s(text).upper()).strip()


def _all(item):
    return u'%s %s' % (item['name'], item['tags_text'])


def source_type(item):
    for text in (item['name'], item['tags_text']):          # the name is more specific than Elementum's tag
        b = _blob(text)
        if ' REMUX ' in b or ' BDREMUX ' in b:
            return u'Blu-ray Remux'
        if ' BLURAY ' in b or ' BLU RAY ' in b or ' BDRIP ' in b or ' BRRIP ' in b:
            return u'Blu-ray'
        if ' WEBRIP ' in b or ' WEB RIP ' in b:
            return u'WEBRip'
        if ' WEB DL ' in b or ' WEBDL ' in b:
            return u'WEB-DL'
        if ' HDTV ' in b:
            return u'HDTV'
        if ' DVDRIP ' in b or ' DVD ' in b:
            return u'DVD'
        if ' WEB ' in b:
            return u'WEB'
    return u''


def codec(item):
    b = _blob(_all(item))
    if ' AV1 ' in b:
        return u'AV1'
    if ' HEVC ' in b or ' H265 ' in b or ' X265 ' in b or ' H 265 ' in b:
        return u'H.265'
    if ' AVC ' in b or ' H264 ' in b or ' X264 ' in b or ' H 264 ' in b:
        return u'H.264'
    return u''


def is_bad(item):
    """Cam/telesync copies and AI-upscaled / frame-interpolated releases."""
    b = _blob(_all(item))
    for w in (' CAM ', ' HDCAM ', ' TS ', ' HDTS ', ' TELESYNC ', ' SCR ', ' SCREENER ',
              ' RIFE ', ' UPSCALED ', ' UPSCALE ', ' AI UPSCALED '):
        if w in b:
            return True
    return False


def tag_list(item):
    b = _blob(_all(item))
    raw = _s(_all(item)).upper()
    out = []

    def has(*words):
        return any((u' %s ' % w) in b for w in words)

    if has('DOLBY VISION', 'DV', 'DOVI'):
        out.append(u'Dolby Vision')
    if has('HDR10+', 'HDR10PLUS'):
        out.append(u'HDR10+')
    elif has('HDR10'):
        out.append(u'HDR10')
    elif has('HDR'):
        out.append(u'HDR')
    c = codec(item)
    if c:
        out.append(c)
    if has('10BIT'):
        out.append(u'10-bit')
    if has('ATMOS'):
        out.append(u'Atmos')
    elif has('DTS X'):
        out.append(u'DTS:X')
    elif has('TRUEHD', 'DOLBY TRUEHD'):
        out.append(u'TrueHD')
    elif has('DTS HD MA'):
        out.append(u'DTS-HD MA')
    elif has('DD+', 'DDP', 'DDP5', 'DDP7', 'EAC3'):
        out.append(u'DD+')
    elif has('DTS HD'):
        out.append(u'DTS-HD')
    elif has('DTS'):
        out.append(u'DTS')
    elif has('AC3', 'DOLBYDIGITAL'):
        out.append(u'Dolby Digital')
    elif has('AAC'):
        out.append(u'AAC')
    ch = CHAN_RE.search(raw)
    if ch and ch.group(1) + '.' + ch.group(2) in ('5.1', '7.1', '2.0'):
        out.append({'5.1': u'5.1', '7.1': u'7.1', '2.0': u'Stereo'}[ch.group(1) + '.' + ch.group(2)])
    if has('MULTI', 'DUAL'):
        out.append(u'Multi-audio')
    if is_bad(item):
        out.append(u'Low-quality copy' if (' CAM ' in b or ' HDCAM ' in b or ' TS ' in b or ' HDTS ' in b
                                           or ' TELESYNC ' in b or ' SCR ' in b) else u'AI upscaled')
    return out[:6]


def quality_label(q):
    return QUALITY_LABELS.get(q, _s(q).upper() if q else u'SD')


def size_text(item):
    return (u'%.2f GB' % item['size']) if item['size'] >= 1 else (u'%d MB' % round(item['size'] * 1024))


def meta_text(item):
    parts = [size_text(item), u'%d seeds' % item['seeds'] if item['seeds'] != 1 else u'1 seed']
    if item['providers']:
        parts.append(u', '.join(item['providers']))
    return DOT.join(parts)


# ---------------------------------------------------------------------------------
# choosing
# ---------------------------------------------------------------------------------
def dedupe(items):
    """Same release from several providers: keep the best-ranked one, remember all provider names."""
    kept, seen = [], {}
    for it in items:
        sig = (source_type(it), codec(it), round(it['size'], 1))
        if sig in seen:
            rep = seen[sig]
            for p in it['providers']:
                if p not in rep['providers']:
                    rep['providers'].append(p)
            continue
        it = dict(it, providers=list(it['providers']))
        seen[sig] = it
        kept.append(it)
    return kept


def pick(items, top_n=TOP_N):
    """items: one quality, already in Elementum's order. Returns up to top_n varied links."""
    items = dedupe(items)
    good = [i for i in items if not is_bad(i) and i['seeds'] > 0]
    good_ids = set(id(i) for i in good)
    rest = [i for i in items if id(i) not in good_ids]
    ranked = good + rest                                   # dead / bad copies only if nothing better
    if len(ranked) <= top_n:
        return ranked
    chosen, seen = [], set()
    for it in ranked:
        key = (source_type(it), codec(it))
        if key not in seen:
            seen.add(key)
            chosen.append(it)
            if len(chosen) == top_n:
                break
    for it in ranked:
        if len(chosen) >= top_n:
            break
        if not any(it is c for c in chosen):
            chosen.append(it)
    order = {id(it): n for n, it in enumerate(ranked)}
    return sorted(chosen, key=lambda it: order[id(it)])


def group_by_quality(parsed):
    groups = {}
    for it in parsed:
        groups.setdefault(it['quality'], []).append(it)
    keys = sorted(groups, key=lambda q: (QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 99, q))
    return keys, groups


def badges(shown):
    out = {}
    if not shown:
        return out
    out[0] = u'BEST MATCH'
    if len(shown) > 1:
        top_seeds = max(range(len(shown)), key=lambda n: (shown[n]['seeds'], -n))
        if top_seeds != 0 and shown[top_seeds]['seeds'] > shown[0]['seeds']:
            out[top_seeds] = u'MOST SEEDS'
        small = min(range(len(shown)), key=lambda n: (shown[n]['size'], n))
        if small != 0 and small not in out and shown[small]['size'] < shown[0]['size']:
            out[small] = u'SMALLEST'
    return out


def build_rows(shown, total_label=u''):
    b = badges(shown)
    rows = []
    for n, it in enumerate(shown):
        head = quality_label(it['quality'])
        st = source_type(it)
        if st:
            head = head + DOT + st
        rows.append({'headline': head, 'tags': DOT.join(tag_list(it)), 'meta': meta_text(it),
                     'badge': b.get(n, u''), 'icon': it['icon']})
    return rows


def quality_menu_labels(keys, groups, top_n=TOP_N):
    labels = []
    for q in keys:
        uniq = dedupe(groups[q])
        top = pick(groups[q], top_n)[0]
        labels.append(u'[B]%s[/B]     %d version%s     (top pick: %s, %d seeds)' % (
            quality_label(q), len(uniq), u'' if len(uniq) == 1 else u's', size_text(top), top['seeds']))
    return labels


def count_label(shown_n, uniq_n):
    if uniq_n > shown_n:
        return u'Top %d of %d versions' % (shown_n, uniq_n)
    return u'%d version%s' % (shown_n, u'' if shown_n == 1 else u's')


# ---------------------------------------------------------------------------------
# on-screen pieces (only these touch Kodi; tests replace them)
# ---------------------------------------------------------------------------------
def choose_quality(labels):
    from kodi_six import xbmcgui
    return xbmcgui.Dialog().select(u'Pick a quality', labels)


def _poster_for(title):
    """TMDb Helper's poster for the item on the Home screen, only if it is clearly the same title."""
    try:
        from kodi_six import xbmc
        label = xbmc.getInfoLabel('Window(Home).Property(TMDbHelper.ListItem.base_label)')
        poster = xbmc.getInfoLabel('Window(Home).Property(TMDbHelper.ListItem.base_poster)')
        if label and poster and label.strip().lower() in _s(title).lower():
            return poster
    except Exception:
        pass
    return u''


def _details_for(title):
    """DECK-POSTER v1: poster, background, title, year/runtime and plot that the Sources
    chooser left on the Home window. Used only when it is clearly this title and recent."""
    out = {'poster': u'', 'fanart': u'', 'title': u'', 'meta': u'', 'plot': u''}
    try:
        import time
        from kodi_six import xbmcgui
        home = xbmcgui.Window(10000)
        name = _s(home.getProperty('Deck.Picker.Title')).strip().lower()
        stamp = float(home.getProperty('Deck.Picker.Time') or 0)
        if name and name in _s(title).lower() and 0 <= time.time() - stamp < 1800:
            for key in out:
                out[key] = _s(home.getProperty('Deck.Picker.' + key.capitalize()))
    except Exception:
        pass
    if not out['poster']:
        out['poster'] = _poster_for(title)
    return out


_WINDOW_CLASS = []


def _window_class():
    if _WINDOW_CLASS:
        return _WINDOW_CLASS[0]
    from kodi_six import xbmcgui
    from elementum.dialog import ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU

    class DeckSelect(xbmcgui.WindowXMLDialog):
        def __init__(self, *args, **kwargs):
            xbmcgui.WindowXML.__init__(self)
            self.rows = kwargs['rows']
            self.subject = kwargs.get('subject', u'')
            self.quality = kwargs.get('quality', u'')
            self.count_text = kwargs.get('count_text', u'')
            self.poster = kwargs.get('poster', u'')
            self.details = kwargs.get('details') or {}
            self.retval = -1

        def onInit(self):
            self.setProperty('deck.subject', self.subject)
            self.setProperty('deck.quality_label', self.quality)
            self.setProperty('deck.count_label', self.count_text)
            self.setProperty('deck.poster', self.poster)
            for key in ('fanart', 'title', 'meta', 'plot'):
                self.setProperty('deck.' + key, self.details.get(key, u''))
            self.getControl(32501).setLabel(u'Choose a version')
            listControl = self.getControl(32503)
            for n, r in enumerate(self.rows):
                item = xbmcgui.ListItem(r['headline'], r['meta'])
                item.setProperty('index', str(n))
                item.setProperty('headline', r['headline'])
                item.setProperty('tags', r['tags'])
                item.setProperty('meta', r['meta'])
                item.setProperty('badge', r['badge'])
                listControl.addItem(item)
            self.setFocusId(32503)

        def onClick(self, controlId):
            if controlId == 32500:
                self.close()
            elif controlId == 32503:
                self.retval = int(self.getControl(32503).getSelectedItem().getProperty('index'))
                self.close()

        def onAction(self, action):
            if action.getId() in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU]:
                self.close()

    _WINDOW_CLASS.append(DeckSelect)
    return DeckSelect


def choose_source(title, rows, quality, count_text):
    from elementum.addon import ADDON_PATH
    details = _details_for(title)
    window = _window_class()("DeckSourceSelect.xml", ADDON_PATH, "Default", rows=rows, subject=title,
                             quality=quality, count_text=count_text, poster=details['poster'], details=details)
    window.doModal()
    retval = window.retval
    del window
    return retval


# ---------------------------------------------------------------------------------
# the whole flow
# ---------------------------------------------------------------------------------
SHOW_ALL_ROW = {'headline': u'Show all links', 'tags': u"Elementum's full, unfiltered list", 'meta': u'', 'badge': u'',
                'icon': u''}


def run(title, items, top_n=TOP_N):
    parsed = parse_all(items)
    if parsed is None or len(parsed) <= top_n:
        return None
    keys, groups = group_by_quality(parsed)
    labels = quality_menu_labels(keys, groups, top_n)
    while True:
        if len(keys) == 1:
            qi = 0
        else:
            choice = choose_quality(labels + [u'Show all %d links' % len(items)])
            if choice is None or choice < 0:
                return -1
            if choice >= len(keys):
                return None
            qi = choice
        q = keys[qi]
        shown = pick(groups[q], top_n)
        rows = build_rows(shown) + [SHOW_ALL_ROW]
        sel = choose_source(title, rows, quality_label(q), count_label(len(shown), len(dedupe(groups[q]))))
        if sel is None or sel < 0:
            if len(keys) == 1:
                return -1
            continue
        if sel >= len(shown):
            return None
        return shown[sel]['idx']
