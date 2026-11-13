# -*- coding: utf-8 -*-
# DECK-ELEMENTUM deck_picker v2 (Kodi-iOS: source_match)
"""
Steam Deck link picker for Elementum.

Elementum's background program sends Kodi a list of text entries (one per torrent link)
and Kodi shows them in a big dialog. run() sits in front of that dialog:

  1. reads every entry (quality, seeds, size, tags, providers)
  2. asks which QUALITY you want (only qualities that exist), or "Show all"
  3. shows the best few DIFFERENT links in that quality on a clean page
     ("best" keeps Elementum's own ordering, i.e. your sorting setting)

run() returns the index of the chosen entry in Elementum's ORIGINAL list, -1 if you
cancelled, or None when it should not handle the list (not a torrent list, "Show all"
when every link is verified, or any problem). The caller then shows Elementum's normal
dialog, so nothing can get stuck.

Kodi-iOS (source_match.py): every link is checked against the title being played (title,
year, season/episode). Links of another title ("Fall" 2026 for "Fall" 2022) are never
offered as versions: short lists get this page too, "Show all" lists only verified links
when some were hidden, and a "N hidden (wrong title/year)" row reveals the others.
"""
import os
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


# Kodi-iOS (owner, build 184: "find the same quality in a different source that won't require conversion"): AV1 has to
# be re-encoded on the phone before Kodi and AirPlay can use it (an hour or more); HEVC / H.264 are only repackaged.
# AV1 links go after the others and say so. Library status › a movie › "Find a version without converting" sets
# Window(Home).Property(KodiIOS.AvoidAV1) to "<quality>|<time>": then only other codecs at that quality are offered.
AVOID_PROPERTY = 'KodiIOS.AvoidAV1'
AVOID_FOR = 15 * 60


def slow_to_prepare(item):
    return codec(item) == u'AV1'


def converts_for_tv(item):
    """Roadmap 1B.1 (owner logs, builds 226-229: anime releases in 10-bit H.264 converted for AirPlay at 120-170% of real
    time, so the TV stalls): Apple TV and AirPlay play 8-bit H.264 and HEVC (10-bit included) as they are, but not
    10-bit H.264 (Hi10P), which the phone converts while playing. AV1 has its own badge."""
    b = _blob(_all(item))
    ten = any(w in b for w in (u' 10BIT ', u' 10 BIT ', u' HI10P ', u' HI10 '))
    return ten and codec(item) == u'H.264'


def prep_cost(item):
    """Roadmap F5 (PR #24): among releases of the same quality, the ones that need no work first. (container, picture):
    .mp4 / .m4v / .mov is already AirPlay-ready (0), anything else (.mkv, unknown) needs a re-package (1); H.264 and HEVC
    pictures are copied as they are (0: preparation keeps their packets, build-356 Inception HEVC was copy=True), 10-bit
    H.264 (Hi10P) and AV1 need a real re-encode (2). Cheap name signals only; it only breaks ties after quality, so it
    never ranks below the quality the owner chose."""
    b = _blob(_all(item))
    ready = any(e in b for e in (u' MP4 ', u' M4V ', u' MOV '))
    picture = 2 if (slow_to_prepare(item) or converts_for_tv(item)) else 0
    return (0 if ready else 1, picture)


def avoid_request(now=None, read=None):
    """(quality or '') while a 'without converting' search is wanted, else None."""
    try:
        if read is None:
            import xbmcgui
            read = lambda: xbmcgui.Window(10000).getProperty(AVOID_PROPERTY)
        raw = read() or ''
        quality, _, at = raw.partition('|')
        import time
        now = time.time() if now is None else now
        if not at or now - float(at) > AVOID_FOR:
            return None
        return quality
    except Exception:
        return None


def without_conversion(kept, quality):
    """The links that need no conversion, at `quality` when there are any there; [] when there are none."""
    quick = [i for i in kept if not slow_to_prepare(i)]
    same = [i for i in quick if i['quality'] == quality]
    return same or quick


def is_bad(item):
    """Cam/telesync copies and AI-upscaled / frame-interpolated releases."""
    b = _blob(_all(item))
    for w in (' CAM ', ' HDCAM ', ' TS ', ' HDTS ', ' TELESYNC ', ' SCR ', ' SCREENER ',
              ' RIFE ', ' UPSCALED ', ' UPSCALE ', ' AI UPSCALED '):
        if w in b:
            return True
    return False


# Kodi-iOS: what a phone cannot stream well. The owner's tests played a 72 GB UHD Blu-ray disc file (00030.m2ts, HEVC
# 10-bit at 63 Mbps): it stalled, froze the controls while Kodi waited on it, and could not seek (no index).
HEAVY_GB = 40.0
DISC_WORDS = (' M2TS ', ' BDMV ', ' ISO ', ' BD25 ', ' BD50 ', ' BD66 ', ' BD100 ', ' COMPLETE BLURAY ', ' COMPLETE UHD BLURAY ',
              ' COMPLETE BLU RAY ', ' UHD BD ', ' DISC ')


def too_heavy(item):
    """A raw disc copy or a file bigger than HEAVY_GB: listed after the others and labelled on the version page."""
    if item['size'] > HEAVY_GB:
        return True
    b = _blob(_all(item))
    return any(w in b for w in DISC_WORDS)


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


MODE = [u'download']   # u'stream' while Umbrella's sources are shown (umbrella_picker), set by run()


def dv_only(item):
    """Dolby Vision with no HDR10 layer named (profile 5 web releases): plays with wrong colours where DV is missing."""
    b = _blob(_all(item))
    dv = bool(re.search(r' (DOLBY ?VISION|DOVI|DV) ', b))
    return dv and not re.search(r' (HDR10\+?|HDR) ', b)


def live_conversion(item):
    """A stream AirPlay could not send as it is: AV1, 10-bit H.264, Dolby Vision only."""
    return slow_to_prepare(item) or converts_for_tv(item) or dv_only(item)


def pick(items, top_n=TOP_N):
    """items: one quality, already in Elementum's order. Returns up to top_n varied links."""
    items = dedupe(items)
    good = [i for i in items if not is_bad(i) and i['seeds'] > 0]
    # Kodi-iOS: disc copies and huge files after the versions a phone streams well (still offered).
    good = [i for i in good if not too_heavy(i)] + [i for i in good if too_heavy(i)]
    # Kodi-iOS: AV1 after the codecs that need no conversion on the phone (stable: Elementum's order otherwise).
    good = [i for i in good if not slow_to_prepare(i)] + [i for i in good if slow_to_prepare(i)]
    # Kodi-iOS (owner: "only time I'd do live playback is with Umbrella ... if I stream it it should also work without
    # needing conversion"): for a stream, everything AirPlay would have to convert live goes last: 10-bit H.264 (no
    # hardware decoder on Apple devices), Dolby Vision without an HDR10 fallback (wrong colours on TVs without DV).
    # Downloads (Elementum) are prepared once on Drive, so those stay in Elementum's order there.
    if MODE[0] == u'stream':
        good = [i for i in good if not live_conversion(i)] + [i for i in good if live_conversion(i)]
    good_ids = set(id(i) for i in good)
    rest = [i for i in items if id(i) not in good_ids]
    ranked = good + rest                                   # dead / bad copies only if nothing better
    if len(ranked) <= top_n:
        return sorted(ranked, key=lambda it: 1 if it.get('coverage') else 0)   # Kodi-iOS: full seasons first (stable)
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
    return sorted(chosen, key=lambda it: (1 if it.get('coverage') else 0, order[id(it)]))   # Kodi-iOS: full seasons first


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
        cover = it.get('coverage')
        tags = tag_list(it)
        rows.append({'headline': head, 'tags': DOT.join(tags), 'meta': meta_text(it),
                     # All Links page (board 16): up to four tag pills, AV1 flagged; size and seeds to sort by.
                     'pills': tags[:4], 'size': it.get('size') or 0, 'seeds': it.get('seeds') or 0,
                     'badge': cover.upper() if cover else u'FULL SEASON' if cover == u'' else
                     u'MAY STUTTER' if too_heavy(it) else u'AV1 \u00b7 SLOW TO PREPARE' if slow_to_prepare(it)
                     else u'10-BIT \u00b7 SLOW ON AIRPLAY' if converts_for_tv(it) else b.get(n, u''), 'icon': it['icon']})
    return rows


def quality_menu_labels(keys, groups, top_n=TOP_N):
    """Kodi-iOS: just the quality and how many versions it has (e.g. "4K Ultra HD  -  6 versions")."""
    labels = []
    for q in keys:
        uniq = dedupe(groups[q])
        # Owner-approved picker (mockup board 14): the quality, and under it how many versions and the size they start
        # from. choose_quality splits the two at \x1f into the choice's name and its second line.
        smallest = min(uniq, key=lambda it: it['size'])
        # Board 14: HDR when some version of this quality has it.
        blob = u' '.join(_blob(u'%s %s' % (it.get('tags_text', u''), it.get('name', u''))) for it in uniq)
        hdr = u' \u00b7 Dolby Vision' if re.search(r'DOLBY ?VISION| DOVI | DV ', blob) else (u' \u00b7 HDR10' if 'HDR' in blob else u'')
        labels.append(u'[B]%s[/B]\x1f%d version%s%s \u00b7 from %s' % (quality_label(q), len(uniq), u'' if len(uniq) == 1 else u's',
                                                                     hdr, size_text(smallest)))
    return labels


def count_label(shown_n, uniq_n):
    if uniq_n > shown_n:
        return u'Top %d of %d versions' % (shown_n, uniq_n)
    return u'%d version%s' % (shown_n, u'' if shown_n == 1 else u's')


# ---------------------------------------------------------------------------------
# on-screen pieces (only these touch Kodi; tests replace them)
# ---------------------------------------------------------------------------------
def _sheet():
    """The bootstrap add-on's choice sheet (owner-approved mockup board 14), or None (Kodi's box is used)."""
    try:
        import importlib.util
        from kodi_six import xbmcaddon
        here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
        source = os.path.join(here, 'resources', 'lib', 'choice_sheet.py')
        if not os.path.isfile(source):
            return None
        spec = importlib.util.spec_from_file_location('kodi_ios_choice_sheet', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.HOME = here
        return module
    except Exception:
        return None


def quality_sheet(labels, title=u'', total=0):
    """The sheet for the quality menu: the title and how many versions, each quality with its line, the best one
    tagged, and Show All as a blue row (the last label)."""
    rows = []
    for n, text in enumerate(labels[:-1]):
        name, _, detail = text.partition(u'\x1f')
        rows.append({'label': re.sub(r'\[/?B\]', u'', name), 'detail': detail,
                     'tag': u'BEST' if n == 0 else u'', 'tag_kind': u'best' if n == 0 else u''})
    return {'heading': title, 'sub': u'Pick a quality \u00b7 %d versions found' % total if total else u'Pick a quality',
            'rows': rows, 'link': labels[-1].replace(u'Show all', u'Show All').replace(u' links', u' Links')}


def choose_quality(labels, title=u'', total=0):
    sheet = _sheet()
    if sheet is not None:
        try:
            return sheet.choose(quality_sheet(labels, title, total), path=getattr(sheet, 'HOME', None))
        except Exception:
            pass
    from kodi_six import xbmcgui
    items = []
    for text in labels:
        name, _, detail = text.partition(u'\x1f')
        items.append(xbmcgui.ListItem(label=name, label2=detail))
    return xbmcgui.Dialog().select(u'Pick a quality', items)


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
            self.mode = kwargs.get('mode', u'')
            self.sort = 0
            self.retval = -1

        def onInit(self):
            self.setProperty('deck.subject', self.subject)
            self.setProperty('deck.quality_label', self.quality)
            self.setProperty('deck.count_label', self.count_text)
            self.setProperty('deck.poster', self.poster)
            for key in ('fanart', 'title', 'meta', 'plot'):
                self.setProperty('deck.' + key, self.details.get(key, u''))
            self.getControl(32501).setLabel(u'Choose a version')
            self.setProperty('deck.mode', self.mode)
            self.fill()

        def list_id(self):
            return 32504 if self.mode == u'all' else 32503

        def fill(self):
            self.setProperty('deck.sort', SORTS[self.sort][1])
            try:
                listControl = self.getControl(self.list_id())
            except RuntimeError:   # an older page without the All Links list
                self.mode = u''
                listControl = self.getControl(32503)
            listControl.reset()
            order = sort_order(self.rows, SORTS[self.sort][0]) if self.mode == u'all' else range(len(self.rows))
            # Board 09 "nothing found": All Links with no version says so, with Try Again (back to the qualities).
            self.setProperty('deck.empty', u'' if self.rows or self.mode != u'all' else
                             u'Nothing playable came back for this title. Try again, or pick another quality.')
            for n in order:
                r = self.rows[n]
                item = xbmcgui.ListItem(r['headline'], r['meta'])
                item.setProperty('index', str(n))
                item.setProperty('headline', r['headline'])
                item.setProperty('tags', r['tags'])
                item.setProperty('meta', r['meta'])
                item.setProperty('badge', r['badge'])
                for k, tag in enumerate(r.get('pills') or [], 1):
                    item.setProperty('tag%d' % k, tag)
                    item.setProperty('tag%d.kind' % k, u'av1' if u'AV1' in tag.upper() else u'')
                listControl.addItem(item)
            self.setFocusId(self.list_id())

        def onClick(self, controlId):
            if controlId == 32500:
                self.close()
            elif controlId == 32512:   # Try Again on the nothing-found state
                self.close()
            elif controlId == 32510:
                self.sort = (self.sort + 1) % len(SORTS)
                self.fill()
            elif controlId in (32503, 32504):
                self.retval = int(self.getControl(controlId).getSelectedItem().getProperty('index'))
                self.close()

        def onAction(self, action):
            if action.getId() in [ACTION_PARENT_DIR, KEY_NAV_BACK, ACTION_PREVIOUS_MENU]:
                self.close()

    _WINDOW_CLASS.append(DeckSelect)
    return DeckSelect


SORTS = ((u'best', u'Best First'), (u'small', u'Smallest'), (u'seeds', u'Most Seeds'))


def sort_order(rows, how):
    """Positions of rows for a sort (board 16's menu); rows without a size (the hidden-links row) stay last."""
    real = [n for n, r in enumerate(rows) if r.get('size')]
    rest = [n for n, r in enumerate(rows) if not r.get('size')]
    if how == u'small':
        real.sort(key=lambda n: rows[n]['size'])
    elif how == u'seeds':
        real.sort(key=lambda n: -rows[n].get('seeds', 0))
    return real + rest


def choose_source(title, rows, quality, count_text, mode=u''):
    from elementum.addon import ADDON_PATH
    details = _details_for(title)
    window = _window_class()("DeckSourceSelect.xml", ADDON_PATH, "Default", rows=rows, subject=title,
                             quality=quality, count_text=count_text, poster=details['poster'], details=details, mode=mode)
    window.doModal()
    retval = window.retval
    del window
    return retval


# ---------------------------------------------------------------------------------
# the whole flow
# ---------------------------------------------------------------------------------
SHOW_ALL_ROW = {'headline': u'Show all links', 'tags': u"Elementum's full, unfiltered list", 'meta': u'', 'badge': u'',
                'icon': u''}


# ---------------------------------------------------------------------------------
# Kodi-iOS: Continue Watching plays the version picked last time
# ---------------------------------------------------------------------------------
CONTINUE_STORE = 'special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json'
RESUME_PROPERTY = 'KodiIOS.Resume.Source'   # set by the watch menu (ios_watch_dialog.py) for a Continue Watching play
RESUME_FRESH = 300


def resume_wanted(home=None, now=None):
    """The version the watch menu asked for, once, if it was asked for in the last few minutes."""
    import json
    import time
    try:
        if home is None:
            from kodi_six import xbmcgui
            home = xbmcgui.Window(10000)
        raw = home.getProperty(RESUME_PROPERTY)
        if not raw:
            return None
        home.clearProperty(RESUME_PROPERTY)
        wanted = json.loads(raw)
        if (now if now is not None else time.time()) - float(wanted.get('time', 0)) > RESUME_FRESH:
            return None
        return wanted
    except Exception:
        return None


def find_same(parsed, wanted):
    """The entry with the same release name (and quality, if several share the name), or None."""
    name = _s((wanted or {}).get('name')).strip().lower()
    if not name:
        return None
    same = [p for p in parsed if p['name'].strip().lower() == name]
    if not same:
        return None
    return ([p for p in same if p['quality'] == wanted.get('quality')] or same)[0]


# ---------------------------------------------------------------------------------
# Kodi-iOS (owner, build 205: "cant it automatically pick sources based off my first quality pick? ... find
# compatible sources for each episode of that show automatically"): the version picked for a season download is
# kept as a profile (SEASON_PICK); download.py then asks for each other episode with AUTO_PICK and this page picks
# the closest version itself, without showing (AUTO_RESULT says what it took).
# ---------------------------------------------------------------------------------
SEASON_PICK = 'KodiIOS.SeasonPick'
AUTO_PICK = 'KodiIOS.AutoPick'
AUTO_RESULT = 'KodiIOS.AutoPick.Result'
_CONTEXT = {'exp': None}
HDR_TAGS = (u'Dolby Vision', u'HDR10+', u'HDR10', u'HDR')


def profile(item):
    """What made the first pick: quality, HDR kind, codec, source type, size (GB) and how much of the season it held."""
    tags = tag_list(item)
    return {'quality': item['quality'], 'hdr': next((t for t in tags if t in HDR_TAGS), u''), 'codec': codec(item),
            'source': source_type(item), 'size': round(item['size'], 2), 'coverage': item.get('coverage')}


def _home():
    from kodi_six import xbmcgui
    return xbmcgui.Window(10000)


def _note_pick(item, home=None):
    exp = _CONTEXT.get('exp') or {}
    if exp.get('kind') == 'movie' or exp.get('season') is None:   # a season or one of its episodes
        return
    try:
        import json
        import time
        (home or _home()).setProperty(SEASON_PICK, json.dumps(dict(profile(item), time=time.time(),
            show_tmdb=exp.get('tmdb'),season=exp.get('season'),episode=exp.get('episode'),selection_name=item.get('name'))))
    except Exception:
        pass


# Build Season looks up three episodes at once (owner, 2026-11-12: "fix the speed for shows"; one at a time took
# 5.5 s an episode): each lookup has its own lane, AUTO_PICK + lane and AUTO_RESULT + lane (episode_watch.LANES).
LANES = ('', '.1', '.2')


def auto_request(home=None, now=None, exp=None):
    """download.py's request to pick by itself ({'profile', 'until', '_lane'}), or None. With exp, the request whose
    target is this episode (any lane); without, the first live one."""
    import json
    import time
    now = now if now is not None else time.time()
    first = None
    live = 0
    for lane in LANES:
        try:
            raw = (home or _home()).getProperty(AUTO_PICK + lane)
            wanted = json.loads(raw) if raw else None
        except Exception:
            wanted = None
        if not wanted or float(wanted.get('until', 0)) < now:
            continue
        wanted['_lane'] = lane
        live += 1
        if exp is None or automatic_matches(wanted, exp):
            return wanted
        first = first or wanted
    # ISSUE-178 (owner log 77b35834): with Build Season's three lanes live, a page whose episode matches none of them
    # used to answer into the first lane, so another episode's lookup got this page's links (or "not found").
    # With more than one lane live it now answers nobody; that lane's own page answers it.
    if exp is not None and live > 1:
        return {'_unmatched': True}
    return first


def _auto_result(auto, value):
    import json
    if not auto or auto.get('_unmatched'):
        return
    _home().setProperty(AUTO_RESULT + (auto.get('_lane') or ''), json.dumps(value))


def _log_unmatched(title):
    try:
        import xbmc
        xbmc.log('Kodi iOS cloud: version page "%s" matches no running Build Season lookup; left to its own lane' % title, xbmc.LOGINFO)
    except Exception:
        pass


def automatic_matches(wanted,exp):
    target=wanted.get('target')
    if not target:return True  # existing rest-of-season requests
    return all(str(exp.get(k) or '')==str(target.get(k) or '') for k in ('tmdb','season','episode'))


WHOLE_SERIES = re.compile(r'(?i)complete[ ._-]*series|collection[ ._-]*of[ ._-]*\d{3}|'
                          r'[(\[ ._-]0*1[ ._]*-[ ._]*\d{3}[)\] ._-]|\ball[ ._-]*\d{3}[ ._-]*episodes')   # source_match.WHOLE_SERIES


def mark_multi(kept, exp, sm=None):
    """ISSUE-178: for one episode's page, marks the links that hold more than that episode (a season pack, an episode
    range, a box set), by name when the matcher can tell, else by size (over 3x the median at its quality), so a
    one-episode file comes first in Build Season's sizes and automatic picks. The pack is still used when alone."""
    season_exp = dict(exp, episode=None)
    by_quality = {}
    for p in kept:
        by_quality.setdefault(p['quality'], []).append(p['size'])
    for p in kept:
        multi = False
        if sm is not None and hasattr(sm, 'coverage'):
            try:
                cover = sm.coverage(p['name'], season_exp)
                multi = cover in (u'', u'Whole series') or (cover or u'').startswith(u'Episodes ')
            except Exception:
                multi = False
        sizes = sorted(by_quality.get(p['quality']) or [])
        if not multi and len(sizes) >= 3:
            median = sizes[len(sizes) // 2]
            multi = median > 0 and p['size'] > 3 * median
        p['multi'] = multi
    return kept


# Owner log b2f10d1f (build 327: "things just move slow slow"): Build Season took 4-6 GB files for 23-minute episodes
# (1440x1080 10-bit H.264), each 4 h through the phone at ~0.3 MB/s and then converted for AirPlay. Owner (build 328):
# "pick the genuine best options based off size and the quality i pick not just the smallest but just overall best".
# At the quality picked, the automatic pick weighs, in this order: no conversion; a size that fits the quality for the
# episode's length (a sensible bitrate: not a bloated remux, not a starved encode); the source (Blu-ray, WEB-DL, ...);
# enough seeds; then, among equals, the larger file (more picture for the same kind of release).
EPISODE_GB = {u'4k': 10.0, u'1440p': 5.0, u'1080p': 3.0, u'720p': 1.5, u'480p': 0.8, u'sd': 0.8}
# Video bitrate that looks right for each quality, Mbit/s (low, high); HEVC needs about 60 % of H.264's.
BITRATE = {u'4k': (10.0, 40.0), u'1440p': (5.0, 16.0), u'1080p': (2.5, 10.0), u'720p': (1.2, 5.0),
           u'480p': (0.6, 2.5), u'sd': (0.6, 2.5)}
SOURCE_RANK = {u'Blu-ray': 0, u'WEB-DL': 1, u'WEB': 2, u'WEBRip': 2, u'Blu-ray Remux': 3, u'HDTV': 4, u'DVD': 5, u'': 3}


def oversized_episode(item):
    """An episode file far bigger than its quality needs (remux, 10-bit encodes): it copies for hours."""
    limit = EPISODE_GB.get(_s(item.get('quality')).lower(), 3.0)
    return not item.get('multi') and float(item.get('size') or 0) > limit


def size_fit(item, minutes=0):
    """0 when the file's bitrate suits its quality for the episode's length (TMDb runtime), 1 when it is a little
    outside, 2 when far (a remux, a starved encode). Without a runtime, the episode-size limits stand in."""
    size = float(item.get('size') or 0)
    if item.get('multi') or size <= 0:
        return 1
    quality = _s(item.get('quality')).lower()
    if not minutes:
        return 2 if oversized_episode(item) else 0
    low, high = BITRATE.get(quality, (2.5, 10.0))
    if codec(item) == u'H.265':
        low, high = low * 0.6, high * 0.6
    mbps = size * 8192.0 / (minutes * 60.0)
    if low <= mbps <= high:
        return 0
    return 1 if low / 1.5 <= mbps <= high * 1.5 else 2


def size_step(item):
    """The size in steps of about 25 %: a few MB more never beat more seeds; a clearly larger file of the same kind
    (more picture) does."""
    import math
    size = float(item.get('size') or 0)
    return int(round(math.log(size, 1.25))) if size > 0 else -99


def seed_bucket(item):
    """0: plenty (20+), 1: some (5-19), 2: few. Within a bucket the size and source decide, not a few more seeds."""
    seeds = int(item.get('seeds') or 0)
    return 0 if seeds >= 20 else 1 if seeds >= 5 else 2


def auto_choose(kept, want):
    """The version closest to the first pick: its quality (else the nearest lower, then higher), its HDR kind and
    codec, never AV1 when avoidable, seeds, then the size nearest the first pick's. None when nothing has seeds."""
    if want.get('strict_quality'):
        kept = [p for p in kept if p['quality'] == want.get('quality') and not is_bad(p)]
    if not kept:
        return None
    order = {q: n for n, q in enumerate(QUALITY_ORDER)}
    target = order.get(want.get('quality'), 2)
    size = float(want.get('size') or 0)
    minutes = int(want.get('runtime') or 0)
    if want.get('coverage') == u'' and size:
        size = 0.0                                      # a pack's size says nothing about one episode's

    def score(it):
        q = order.get(it['quality'], 9)
        distance = (q - target) * 2 if q >= target else (target - q) * 2 + 1      # lower quality before higher
        tags = tag_list(it)
        hdr = next((t for t in tags if t in HDR_TAGS), u'')
        # Owner log 15e6cbc4: one episode of a season build was taken from a 500-episode "Complete Series" pack (the
        # most seeds); whole-series packs come last, used only when nothing else has the episode.
        return (is_bad(it), it['seeds'] <= 0, bool(WHOLE_SERIES.search(_s(it.get('name')))), bool(it.get('multi')), distance,
                hdr != want.get('hdr', u''), codec(it) != want.get('codec', u''),
                slow_to_prepare(it), converts_for_tv(it), too_heavy(it), prep_cost(it), size_fit(it, minutes), seed_bucket(it),
                SOURCE_RANK.get(source_type(it), 3), abs(it['size'] - size) if size else -size_step(it), -it['seeds'])
    best = min(dedupe(kept), key=score)
    return None if best['seeds'] <= 0 else best


def remember(item, title, path=None, now=None):
    """Save the version picked for the title the watch menu has just started, for Continue Watching."""
    _note_pick(item)
    import json
    import os
    import time
    try:
        if path is None:
            import xbmcvfs
            path = xbmcvfs.translatePath(CONTINUE_STORE)
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        entry = data.get('items', {}).get(data.get('current'))
        now = now if now is not None else time.time()
        if not entry or now - float(entry.get('played', 0)) > 900:
            return False
        names = [_s(n).lower() for n in (entry.get('tvshowtitle'), entry.get('title')) if n]
        if names and not any(n in _s(title).lower() for n in names):
            return False
        entry['version'] = {'name': item['name'], 'quality': item['quality'], 'size': round(item['size'], 2)}
        temp = path + '.tmp'
        with open(temp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=1)
        os.replace(temp, path)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------------
# Kodi-iOS: only links of the title being played (source_match.py)
# ---------------------------------------------------------------------------------
_MATCHER = []


def _matcher():
    """source_match.py: beside this file (Elementum's site-packages/elementum, the bootstrap add-on's lib) or on
    sys.path; in the repository it sits in migration/bundled-bootstrap/resources/lib."""
    if _MATCHER:
        return _MATCHER[0]
    found = None
    try:
        import source_match as found
    except Exception:
        try:
            from elementum import source_match as found
        except Exception:
            here = os.path.dirname(os.path.abspath(__file__))
            for path in (os.path.join(here, 'source_match.py'),
                         os.path.join(here, '..', 'bundled-bootstrap', 'resources', 'lib', 'source_match.py')):
                if os.path.isfile(path):
                    try:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location('deck_source_match', path)
                        found = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(found)
                        break
                    except Exception:
                        found = None
    _MATCHER.append(found)
    return found


def identity(title, sm=None):
    """What the links must be: the identity Burst checked for this search (Home window), else the title and year the
    watch menu left for this page, completed from TMDb. None when it cannot be known."""
    sm = sm or _matcher()
    if sm is None:
        return None
    exp = sm.published(title) or sm.from_details(title)
    if exp and not exp.get('enriched'):
        exp = sm.enrich(exp)
    return exp


def hidden_row(hidden, sm):
    return {'headline': u'%d hidden (wrong title/year)' % len(hidden), 'tags': sm.reasons_text(hidden) if sm else u'',
            'meta': u'Not this title: tap to see them', 'badge': u'', 'icon': u''}


def hidden_rows(hidden):
    rows = build_rows([it for it, _ in hidden])
    for row, (it, reason) in zip(rows, hidden):
        row['badge'] = reason.upper()[:24]
        row['tags'] = it['name'][:110]                     # the release name, to judge it
    return rows


def show_hidden(title, hidden):
    """The links that are not this title, with the reason, when asked for."""
    sel = choose_source(title, hidden_rows(hidden), u'Hidden: not this title?', u'%d hidden' % len(hidden))
    if sel is None or sel < 0 or sel >= len(hidden):
        return -1
    return hidden[sel][0]['idx']


def show_list(title, entries, hidden, sm, quality_text, count_text, mode=u''):
    """Our page for a list of verified links (every one of them), plus the hidden row."""
    rows = build_rows(entries) + ([hidden_row(hidden, sm)] if hidden else [])
    sel = choose_source(title, rows, quality_text, count_text, mode)
    if sel is None or sel < 0:
        return -1
    if sel < len(entries):
        remember(entries[sel], title)
        return entries[sel]['idx']
    return show_hidden(title, hidden)


def show_all(title, items, parsed, kept, hidden, sm):
    """"Show all": Elementum's own list when every link in it is verified, else every verified link here."""
    if not hidden and len(parsed) == len(items):
        return None
    return show_list(title, kept, hidden, sm, u'All verified links', u'%d version%s' % (len(kept), u'' if len(kept) == 1 else u's'), u'all')


def run(title, items, top_n=TOP_N, expect=None, mode=u'download'):
    MODE[0] = mode
    parsed = parse_all(items)
    if parsed is None:
        auto=auto_request()
        if auto and auto.get('_unmatched'):
            return -1
        if auto and auto.get('target'):
            sm=_matcher();exp=expect if expect is not None else identity(title,sm)
            auto=auto_request(exp=exp) if exp else auto
            if auto.get('_unmatched'):
                _log_unmatched(title)
                return -1
            if auto.get('purpose') in ('scan','packs') and (not exp or not automatic_matches(auto,exp)):
                _auto_result(auto,{'request_id':auto['request_id'],'error':'identity_mismatch'})
                return -1
            if exp and automatic_matches(auto,exp):
                if auto.get('purpose') in ('scan','packs'):
                    _auto_result(auto,{'request_id':auto['request_id'],
                        'qualities':[],'packs':False,'error':'unsupported_source_list' if items else ''})
                return -1
        return None
    sm = _matcher()
    exp = expect if expect is not None else identity(title, sm)
    _CONTEXT['exp'] = exp
    # Owner (build 309): "this menu also shows up as its downloading ... ensure its removed for downloading seasons".
    # While Build Season looks up episodes, a version page whose episode is not known never asks: that lookup gets
    # nothing (and is looked up again), the owner is not shown a menu.
    if not exp:
        pending = auto_request()
        if pending and pending.get('target'):
            _log_unmatched(title)
            return -1
    active=auto_request(exp=exp) if exp else auto_request()
    if active and active.get('_unmatched'):
        _log_unmatched(title)
        return -1
    if active and active.get('purpose') in ('scan','packs','survey') and (not exp or not automatic_matches(active,exp)):
        _auto_result(active,{'request_id':active['request_id'],'error':'identity_unavailable'})
        return -1
    if sm is not None and exp:
        kept, hidden = sm.split(parsed, exp, name=lambda p: p['name'], result=lambda p: None)
        sm.report('Choose a version', exp, kept, hidden, name=lambda p: p['name'])
        # Kodi-iOS (owner, build 205: "i pressed full season" and got episode 1 alone): for a season download, full
        # seasons first and every row says which it is.
        if hasattr(sm, 'coverage'):
            for p in kept:
                p['coverage'] = sm.coverage(p['name'], exp)
            if any(p['coverage'] is not None for p in kept):
                kept = [p for p in kept if p['coverage'] == u''] + [p for p in kept if p['coverage'] != u'']
    else:
        kept, hidden = parsed, []
        if sm is not None:
            sm.log(u'Choose a version: %d links for "%s" not checked (the title being played is not known)' % (len(parsed), title))
    # Kodi-iOS: the rest of a season, picked here without asking (download.py's AUTO_PICK).
    try:
        import episode_watch
        if exp and episode_watch.canceled(_home(),exp):return -1
    except (ImportError,AttributeError):pass
    auto = auto_request(exp=exp) if exp else auto_request()
    if auto and auto.get('_unmatched'):
        _log_unmatched(title)
        return -1
    if exp and exp.get('episode'):
        mark_multi(kept, exp, sm)
    if auto and exp and automatic_matches(auto, exp) and auto.get('purpose') in ('scan', 'packs', 'survey'):
        import json
        usable = [p for p in kept if p['seeds'] > 0 and not is_bad(p)] if sm is not None and exp.get('titles') else []
        if auto['purpose'] in ('packs', 'survey'):
            usable = [p for p in usable if p.get('coverage') == u'']
        # Kodi-iOS season sheet (season-pack-mockups board B): a pack request for one quality shows only that quality.
        only = (auto.get('profile') or {}).get('quality')
        if auto['purpose'] == 'packs' and only:
            usable = [p for p in usable if p['quality'] == only]
        result = {'request_id': auto['request_id'],
                  'qualities': [q for q in QUALITY_ORDER if any(p['quality'] == q for p in usable)],
                  'packs': bool(usable) if auto['purpose'] in ('packs', 'survey') else False}
        if auto['purpose'] == 'scan':
            # Build Season (board D): the best-seeded copy's size per quality, for the ready sheet's sizes.
            sizes, details = {}, {}
            # ISSUE-178: a one-episode file before a season pack or box set holding it (owner log 77b35834: episode 5
            # read "4.1 GB" from a pack with more seeds), then the most seeds.
            for p in sorted(usable, key=lambda p: (bool(p.get('multi')), -p['seeds'])):
                sizes.setdefault(p['quality'], p['size'])
                # Board F: what the version is (video, audio, seeds), shown per episode in the full list.
                details.setdefault(p['quality'], u' \u00b7 '.join([t for t in tag_list(p) if t not in ('4K', '1080p', '720p')][:4] +
                                                          ['%d seeds' % p['seeds']]))
            result['sizes'] = sizes
            result['details'] = details
        if auto['purpose'] == 'survey':
            # The season sheet's cards: per quality, how many genuine full-season packs and the best one's size/seeds.
            by = {}
            for p in usable:
                best = by.get(p['quality'])
                if best is None or p['seeds'] > best['seeds']:
                    by[p['quality']] = {'count': (best or {}).get('count', 0), 'size_gb': p['size'], 'seeds': p['seeds']}
                by[p['quality']]['count'] = by[p['quality']].get('count', 0) + 1
            result['packs_by_quality'] = by
        _auto_result(auto, result)
        if auto['purpose'] in ('scan', 'survey') or not usable:
            return -1
        # A Full season request offers genuine packs only. Cancel never queues a partial episode.
        return show_list(title, usable, [], sm, u'Full season packs', count_label(len(usable), len(usable)))
    if auto is not None and exp and exp.get('episode') and automatic_matches(auto,exp):
        failed=set(auto.get('excluded_names') or [])
        best = auto_choose([p for p in kept if p['name'] not in failed], auto.get('profile') or {})
        try:
            import json
            _auto_result(auto, {'episode': exp.get('episode'), 'found': bool(best),
                                'quality': best['quality'] if best else u'', 'name': best['name'] if best else u'',
                                'request_id':auto.get('request_id')})
        except Exception:
            pass
        if sm is not None:
            sm.log(u'Choose a version (automatic): %s: %s' % (exp.get('label') or title, best['name'] if best else u'nothing with seeds'))
        return best['idx'] if best else -1
    # Library status › "Find a version without converting": only links that need no conversion, at the same quality.
    wanted = avoid_request()
    if wanted is not None:
        quick = without_conversion(kept, wanted)
        if quick:
            shown = pick(quick, top_n)
            rows = build_rows(shown)
            for row in rows:
                row['badge'] = u'NO CONVERSION NEEDED'
            sel = choose_source(title, rows, quality_label(shown[0]['quality']), count_label(len(shown), len(dedupe(quick))))
            if sel is None or sel < 0 or sel >= len(shown):
                return -1
            return shown[sel]['idx']
    # Continue Watching: the same version as last time, without asking, when it is still in the list.
    same = find_same(kept, resume_wanted())
    if same is not None:
        return same['idx']
    if not kept:
        if exp and exp.get('revealed'):                     # already asked to see them (Burst)
            return show_hidden(title, hidden)
        sel = choose_source(title, [hidden_row(hidden, sm)], u'No version of this title', u'All %d links hidden' % len(hidden))
        if sel is None or sel < 0:
            return -1
        return show_hidden(title, hidden)
    if len(kept) <= top_n:
        return show_list(title, kept, hidden, sm, quality_label(kept[0]['quality']) if len(group_by_quality(kept)[0]) == 1
                         else u'All versions', count_label(len(kept), len(kept)))
    keys, groups = group_by_quality(kept)
    labels = quality_menu_labels(keys, groups, top_n)
    while True:
        if len(keys) == 1:
            qi = 0
        else:
            choice = choose_quality(labels + [u'Show all %d links' % len(kept)], title, len(kept))
            if choice is None or choice < 0:
                return -1
            if choice >= len(keys):
                return show_all(title, items, parsed, kept, hidden, sm)
            qi = choice
        q = keys[qi]
        shown = pick(groups[q], top_n)
        rows = build_rows(shown) + [SHOW_ALL_ROW] + ([hidden_row(hidden, sm)] if hidden else [])
        sel = choose_source(title, rows, quality_label(q), count_label(len(shown), len(dedupe(groups[q]))))
        if sel is None or sel < 0:
            if len(keys) == 1:
                return -1
            continue
        if sel == len(shown):
            return show_all(title, items, parsed, kept, hidden, sm)
        if sel > len(shown):
            return show_hidden(title, hidden)
        remember(shown[sel], title)
        return shown[sel]['idx']
