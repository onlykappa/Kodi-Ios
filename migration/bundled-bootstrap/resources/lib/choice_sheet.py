"""The choice sheet (owner-approved mockup round 3, boards 13-15): a bottom sheet in the Navigation menu's style.

One window for every picker that used Kodi's plain select box ("How would you like to watch", "Pick a quality", a
season's menu and its qualities). The card grows upward from a fixed bottom edge (a vertical grouplist aligned to
its bottom), so it is always as tall as its content; Cancel is its own capsule under it.

spec = {'art': image, 'badge': 'MOVIE · 2014', 'art_title': 'The Maze Runner',
        'heading': 'The Maze Runner', 'sub': 'Pick a quality · 25 versions found',
        'rows': [{'label', 'detail', 'tag', 'tag_kind' ('best'|'warn'|''), 'tint', 'glyph', 'cover' (0-100 or None)}],
        'link': 'Show All 25 Links', 'foot': 'Your choice is remembered ...'}
choose(spec) -> row index, len(rows) for the link row, -1 for Cancel/Back.
Other add-ons (the watch add-on, the version picker) open it through load(); without it they keep Kodi's box.
"""
WINDOW = 'IOSChoiceSheet.xml'
MAX_ROWS = 8
ROW0, LINK, CANCEL, DIM = 9811, 9830, 9840, 9099
TALL0 = 9850        # the same rows when they wrap: one id range per form (title 1-3 lines x detail 1-2 lines), 10 apart
BACK_KEYS = (9, 10, 92, 110)
SIDE = 32           # the sheet's distance from the screen's sides
ROW_H = 176
# Owner (2026-11-14): no text is cut off with "…". A row whose title or detail does not fit on one line wraps: the title on
# up to three lines, the detail on two, the row as tall as its lines (TITLE_LINE per title line, DETAIL_LINE per detail line).
# Characters per line (rig render 2026-11-14, Inter on the 1080-unit canvas): a title beside a tile 30, minus 5 for a chip,
# plus 5 without a tile; a detail beside a tile 42, plus 6 without.
FIT_TITLE, FIT_DETAIL = 30, 42
TITLE_LINE, DETAIL_LINE = 62, 46


def lines(text, per_line):
    """How many lines a text wraps to at word boundaries (at least 1)."""
    count, used = 1, 0
    for word in str(text or '').split():
        need = len(word) + (1 if used else 0)
        if used and used + need > per_line:
            count, used = count + 1, len(word)
        else:
            used += need
    return count


def shape(row):
    """(title lines 1-3, detail lines 1-2) for a row."""
    title_fit = FIT_TITLE - (5 if row.get('tag') else 0) + (0 if row.get('tint') else 5)
    detail_fit = FIT_DETAIL + (0 if row.get('tint') else 6)
    return min(3, lines(row.get('label'), title_fit)), min(2, lines(row.get('detail'), detail_fit)) if row.get('detail') else 0


FORMS = [(t, d) for t in (1, 2, 3) for d in (1, 2)]


def tall_height(title_lines, detail_lines=2):
    return 28 + TITLE_LINE * title_lines + 8 + DETAIL_LINE * detail_lines + 30


def form(row):
    """The wrapped form's number (1-6, FORMS) for a row that does not fit on one line, else ''."""
    t, d = shape(row)
    return str(FORMS.index((t, max(1, d))) + 1) if (t > 1 or d > 1) else ''
ART_H = 420


def properties(spec):
    """Window properties for a spec (pure; tested without Kodi)."""
    rows = list(spec.get('rows') or [])[:MAX_ROWS]
    props = {'art': spec.get('art') or '', 'badge': spec.get('badge') or '', 'art_title': spec.get('art_title') or '',
             'heading': spec.get('heading') or '', 'sub': spec.get('sub') or '', 'link': spec.get('link') or '',
             'foot': spec.get('foot') or '', 'rows': str(len(rows))}
    for n in range(1, MAX_ROWS + 1):
        row = rows[n - 1] if n <= len(rows) else {}
        cover = row.get('cover')
        props.update({'row.%d.label' % n: row.get('label') or '', 'row.%d.detail' % n: row.get('detail') or '',
                      'row.%d.tall' % n: form(row) if n <= len(rows) else '',
                      'row.%d.tag' % n: row.get('tag') or '', 'row.%d.tag_kind' % n: row.get('tag_kind') or '',
                      'row.%d.tint' % n: row.get('tint') or '', 'row.%d.glyph' % n: glyph_path(row.get('glyph')),
                      # the coverage bar in tenths (0-10); '' hides it
                      'row.%d.cover' % n: '' if cover is None else str(max(0, min(10, int(round(float(cover) / 10.0)))))})
    return props


def tall(row):
    """True when a row's title or detail would not fit on one line (it then wraps, never "…")."""
    title, detail = shape(row)
    return title > 1 or detail > 1


def result(control, rows, link):
    """The answer for a tapped control: a row index, len(rows) for the link, -1 otherwise."""
    if ROW0 <= control < ROW0 + min(rows, MAX_ROWS):
        return control - ROW0
    for k in range(len(FORMS)):
        if TALL0 + 10 * k <= control < TALL0 + 10 * k + min(rows, MAX_ROWS):
            return control - TALL0 - 10 * k
    if control == LINK and link:
        return rows
    return -1


def glyph_path(name):
    """A row tile's glyph: an icon name ('trash.png') becomes the skin's icon path (rig render, 2026-11-14: the tiles
    drew as bare coloured squares because the image control was given the bare name)."""
    name = str(name or '')
    return name if not name or '://' in name or name.startswith(('/', '$')) else 'special://skin/extras/icons/' + name


def choose(spec, xbmcgui=None, xbmc=None, path=None):
    import os
    if xbmcgui is None:
        import xbmcgui
    if xbmc is None:
        import xbmc
    props = properties(spec)
    rows, link = int(props['rows']), bool(props['link'])

    class Sheet(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.answer = -1
            for key, value in props.items():
                self.setProperty(key, value)
            try:
                first = TALL0 + 10 * (int(props['row.1.tall']) - 1) if props.get('row.1.tall') else ROW0   # FORMS index
                self.setFocusId(first if rows else (LINK if link else CANCEL))
            except Exception:
                pass

        def onClick(self, control):
            self.answer = result(control, rows, link)
            self.close()

        def onAction(self, action):
            if action.getId() in BACK_KEYS:
                self.answer = -1
                self.close()

    sheet = Sheet(WINDOW, path or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                  'Default', '1080i')
    try:
        sheet.doModal()
        return getattr(sheet, 'answer', -1)
    finally:
        del sheet


def load():
    """This module from another add-on (None when the bootstrap add-on or its sheet is not there)."""
    try:
        import importlib.util
        import os
        import xbmcaddon
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


def window(p):
    """portrait/IOSChoiceSheet.xml (p: the portrait module)."""
    W = p.WIDTH - 2 * SIDE
    P = lambda k: '$INFO[Window().Property(%s)]' % k
    has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k
    is_ = lambda k, v: 'String.IsEqual(Window().Property(%s),%s)' % (k, v)
    card = p.SURFACE2
    slab = lambda h, extra='': p.image(0, 0, W, h, p.MEDIA + 'white.png', card, extra)

    def block(h, inner, visible=''):
        vis = '<visible>%s</visible>' % visible if visible else ''
        return '<control type="group"><width>%d</width><height>%d</height>%s%s%s</control>' % (W, h, vis, slab(h), inner)

    cap = lambda name: ('<control type="image"><width>%d</width><height>48</height>'
                        '<texture border="44,0,44,0" colordiffuse="%s">%s%s</texture></control>') % (W, card, p.MEDIA, name)
    # The title's art with its kind and name over it (board 13).
    art = block(ART_H + 20,
                p.image(34, 0, W - 68, ART_H, P('art'), p.WHITE, '', '>scale', p.MEDIA + 'card_mask.png', background=True) +
                p.image(34, ART_H - 200, W - 68, 200, p.MEDIA + 'hero_fade.png', 'B3000000', '', '', p.MEDIA + 'card_mask.png') +
                p.label(74, ART_H - 120, W - 148, 100, P('art_title'), 'p_h2', p.WHITE, 'left', '<scroll>false</scroll>') +
                # The badge on a dark capsule that fits its text (a disabled auto-width button), right-aligned.
                '<control type="grouplist"><left>34</left><top>24</top><width>%d</width><height>60</height><orientation>horizontal</orientation>'
                '<align>right</align><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>' % (W - 68 - 24, has('badge')) +
                '<control type="button"><width min="80" max="420">auto</width><height>56</height><label>[B]%s[/B]</label><font>p_cap</font>'
                '<textoffsetx>22</textoffsetx><align>center</align><aligny>center</aligny><enable>false</enable><disabledcolor>%s</disabledcolor>'
                '<texturenofocus border="28" colordiffuse="99000000">%spill_56.png</texturenofocus>'
                '<texturefocus border="28" colordiffuse="99000000">%spill_56.png</texturefocus></control></control>' % (P('badge'), p.WHITE, p.MEDIA, p.MEDIA),
                has('art'))
    heading = block(84, p.label(48, 8, W - 96, 76, '[B]%s[/B]' % P('heading'), 'p_h3', p.WHITE, 'center', '<scroll>false</scroll>'), has('heading'))
    sub = block(108, p.label(56, 0, W - 112, 100, P('sub'), 'p_foot', p.GREY, 'center',
                             '<aligny>top</aligny><wrapmultiline>true</wrapmultiline>'), has('sub'))

    def tag_button(n):
        kinds = (('best', p.GREEN, '3330D158'), ('warn', 'FFFF9F0A', '33FF9F0A'), ('', p.GREY, '24EBEBF5'))
        out = ''
        for kind, text, fill in kinds:
            cond = is_('row.%d.tag_kind' % n, kind) if kind else '!%s + !%s' % (is_('row.%d.tag_kind' % n, 'best'), is_('row.%d.tag_kind' % n, 'warn'))
            out += ('<control type="button"><width min="60" max="320">auto</width><height>48</height><top>8</top>'
                    '<label>[B]%s[/B]</label><font>p_cap</font><textoffsetx>16</textoffsetx><align>center</align><aligny>center</aligny>'
                    '<disabledcolor>%s</disabledcolor><textcolor>%s</textcolor><enable>false</enable>'
                    '<texturenofocus border="24" colordiffuse="%s">%spill_56.png</texturenofocus>'
                    '<texturefocus border="24" colordiffuse="%s">%spill_56.png</texturefocus>'
                    '<visible>%s + %s</visible></control>') % (P('row.%d.tag' % n), text, text, fill, p.MEDIA, fill, p.MEDIA,
                                                              has('row.%d.tag' % n), cond)
        return out

    def row(n):
        k = 'row.%d.' % n
        tile = has(k + 'tint')
        tx_tile, tx_plain = 172, 48
        text_w = W - 48 - 80
        sep = p.image(48, 0, W - 48, 2, p.MEDIA + 'white.png', p.SEP, '<visible>!String.IsEqual(Window().Property(rows),0) + %s</visible>' % ('true' if n > 1 else 'false'))
        tiles = ('<control type="image"><left>48</left><top>%d</top><width>96</width><height>96</height>'
                 '<texture border="26" colordiffuse="%s">%stile100.png</texture><visible>%s</visible></control>'
                 % ((ROW_H - 96) // 2, P(k + 'tint'), p.MEDIA, tile) +
                 p.icon(72, (ROW_H - 48) // 2, 48, P(k + 'glyph'), p.WHITE, '<visible>%s</visible>' % tile))

        def text(x, visible):
            w = text_w - (x - 48)
            title = ('<control type="grouplist"><left>%d</left><top>28</top><width>%d</width><height>64</height><orientation>horizontal</orientation>'
                     '<itemgap>14</itemgap><usecontrolcoords>true</usecontrolcoords>' % (x, w) +
                     '<control type="label"><width max="%d">auto</width><height>64</height><font>p_h3</font><textcolor>%s</textcolor>'
                     '<aligny>center</aligny><label>%s</label><scroll>false</scroll></control>' % (w - 140, p.WHITE, P(k + 'label')) +
                     tag_button(n) + '</control>')
            detail = p.label(x, 96, w, 50, P(k + 'detail'), 'p_foot', p.GREY, 'left', '<scroll>false</scroll>')
            bar = ''
            bar_w = w - 20
            bar += p.image(x, 150, bar_w, 10, p.MEDIA + 'white.png', 'FF3A3A3C', '<visible>%s</visible>' % has(k + 'cover'))
            for t in range(1, 11):
                color = p.GREEN if t == 10 else p.ACCENT
                bar += p.image(x, 150, bar_w * t // 10, 10, p.MEDIA + 'white.png', color,
                               '<visible>%s</visible>' % is_(k + 'cover', t))
            return '<control type="group"><visible>%s</visible>%s%s%s</control>' % (visible, title, detail, bar)

        def tall_text(x, visible, lines_, dlines):
            # The title on `lines_` lines (the chip on its right), then the detail on up to two: wrapped, never "…".
            w = text_w - (x - 48)
            th = TITLE_LINE * lines_
            chip = ('<control type="grouplist"><left>%d</left><top>28</top><width>%d</width><height>64</height><orientation>horizontal</orientation>'
                    '<align>right</align><usecontrolcoords>true</usecontrolcoords>' % (x, w) + tag_button(n) + '</control>')
            wrap = '<aligny>top</aligny><wrapmultiline>true</wrapmultiline>'
            title = p.label(x, 28, w - 150, th, P(k + 'label'), 'p_h3', p.WHITE, 'left', wrap)
            title_wide = p.label(x, 28, w, th, P(k + 'label'), 'p_h3', p.WHITE, 'left', wrap)
            detail = p.label(x, 28 + th + 8, w, DETAIL_LINE * dlines, P(k + 'detail'), 'p_foot', p.GREY, 'left', wrap)
            return ('<control type="group"><visible>%s</visible>%s<control type="group"><visible>%s</visible>%s</control>'
                    '<control type="group"><visible>!%s</visible>%s</control>%s</control>') % (
                visible, chip, has(k + 'tag'), title, has(k + 'tag'), title_wide, detail)

        def button(h, index):
            # Remote/keyboard only (touch taps the row): up/down to the neighbouring rows' same form.
            base = TALL0 + 10 * index
            up = str(base + n - 2) if n > 1 else str(base)
            down = str(base + n) if n < MAX_ROWS else str(LINK)
            return ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
                    '<texturefocus /><texturenofocus /><onup>%s</onup><ondown>%s</ondown></control>'
                    % (base + n - 1, W, h, up, down))

        def tiles_at(h):
            return ('<control type="image"><left>48</left><top>%d</top><width>96</width><height>96</height>'
                    '<texture border="26" colordiffuse="%s">%stile100.png</texture><visible>%s</visible></control>'
                    % ((h - 96) // 2, P(k + 'tint'), p.MEDIA, tile) +
                    p.icon(72, (h - 48) // 2, 48, P(k + 'glyph'), p.WHITE, '<visible>%s</visible>' % tile))

        talls = ''
        for index, (lines_, dlines) in enumerate(FORMS):
            h = tall_height(lines_, dlines)
            talls += block(h, sep + button(h, index) + tiles_at(h) + tall_text(tx_tile, tile, lines_, dlines) +
                           tall_text(tx_plain, '!' + tile, lines_, dlines) + p.icon(W - 72, (h - 34) // 2, 34, 'chevron-right.png', p.GREY),
                           has(k + 'label') + ' + ' + is_(k + 'tall', index + 1))
        inner = (sep + '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
                 '<texturefocus /><texturenofocus /><onup>%s</onup><ondown>%s</ondown></control>'
                 % (ROW0 + n - 1, W, ROW_H, ROW0 + n - 2 if n > 1 else ROW0, ROW0 + n if n < MAX_ROWS else LINK) +
                 tiles + text(tx_tile, tile) + text(tx_plain, '!' + tile) +
                 p.icon(W - 72, (ROW_H - 34) // 2, 34, 'chevron-right.png', p.GREY))
        return block(ROW_H, inner, has(k + 'label') + ' + ' + '!' + has(k + 'tall')) + talls

    link = block(132, p.image(0, 0, W, 2, p.MEDIA + 'white.png', p.SEP) +
                 '<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>132</height>'
                 '<label>[B]%s[/B]</label><font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
                 '<align>center</align><aligny>center</aligny><texturefocus /><texturenofocus /></control>'
                 % (LINK, W, P('link'), p.ACCENT, p.ACCENT), has('link'))
    foot = block(150, p.label(56, 18, W - 112, 120, P('foot'), 'p_cap', p.GREY, 'center',
                              '<aligny>top</aligny><wrapmultiline>true</wrapmultiline>'), has('foot'))
    top_pad = block(20, '', '!' + has('art'))
    bottom = 60
    cancel_h = 128
    sheet_h = p.HEIGHT - bottom - cancel_h - 22
    stack = ('<control type="grouplist" id="9800"><left>%d</left><top>0</top><width>%d</width><height>%d</height>'
             '<orientation>vertical</orientation><align>right</align><itemgap>0</itemgap><usecontrolcoords>false</usecontrolcoords>'
             % (SIDE, W, sheet_h) +
             cap('cap_top.png') + top_pad + art + heading + sub + ''.join(row(n) for n in range(1, MAX_ROWS + 1)) +
             link + foot + cap('cap_bottom.png') + '</control>')
    cancel = ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
              '<label>[B]Cancel[/B]</label><font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
              '<align>center</align><aligny>center</aligny>'
              '<texturefocus border="64" colordiffuse="%s">%spill_128.png</texturefocus>'
              '<texturenofocus border="64" colordiffuse="%s">%spill_128.png</texturenofocus><onup>%d</onup></control>'
              % (CANCEL, SIDE, p.HEIGHT - bottom - cancel_h, W, cancel_h, p.WHITE, p.WHITE, card, p.MEDIA, card, p.MEDIA, ROW0))
    body = ('<controls><control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
            '<texturefocus colordiffuse="99000000">%swhite.png</texturefocus><texturenofocus colordiffuse="99000000">%swhite.png</texturenofocus>'
            '<onclick>Close</onclick></control>' % (DIM, p.WIDTH, p.HEIGHT, p.MEDIA, p.MEDIA) + stack + cancel + '</controls>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol>'
            '<animation effect="slide" start="0,300" end="0,0" time="260" tween="cubic" easing="out">WindowOpen</animation>'
            '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>'
            '<animation effect="fade" start="100" end="0" time="140">WindowClose</animation>%s</window>\n') % (p.MARKER, ROW0, body)
