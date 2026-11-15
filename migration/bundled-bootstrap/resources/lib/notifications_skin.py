"""Board 5 (build 194: laid out from docs/design/build-193-measurements.md): a segmented filter, the running cards (the same
card as Library status, compact), the 'Up next' line with its Library status link, and the earlier messages in one
grouped card with tinted tiles."""
import status_ui as u

BARS = 9470          # running-card bars: prepare 9470, upload 9471, downloads 9472.. (set by notifications.py)
COPIES = 6           # owner (build 356): the pill said 3 running, this page showed one copy; one card per copy lane
COPY_IDS = 9441      # the 2nd..6th copy cards: 9441-9445, their bars BARS + 6.. (9476-9480)


def cards():
    """[(property prefix, card id, bar id)] in page order: preparing, every copy, then torrent downloads."""
    out = [('prepare.', 9433, BARS), ('up.', 9432, BARS + 1)]
    out += [('up.%d.' % k, COPY_IDS + k - 2, BARS + 4 + k) for k in range(2, COPIES + 1)]
    out += [('dl.%d.' % k, 9435 + k, BARS + 1 + k) for k in range(1, 5)]
    return out
LINK_W = 290   # room for the accent 'Library status' after the Up next line
TOP = 380            # C1: the list starts right under the smaller filter


def segmented(p, filters, prop='filter', y=308, base=9101):
    """iOS segmented control: a SURFACE track (10 pt radius, 2 pt inset), the chosen segment #48484A (8 pt radius),
    13 pt semibold labels, white when chosen, grey otherwise."""
    S, w = p.SIDE, p.WIDTH - 2 * p.SIDE
    out = p.image(S, y, w, 97, p.MEDIA + 'r27.png', p.SURFACE, border=27)
    sw = (w - 10) // len(filters)
    for i, (key, title) in enumerate(filters):
        x = S + 5 + i * sw
        on = 'String.IsEqual(Window().Property(%s),%s)' % (prop, key)
        out += p.image(x, y + 5, sw, 86, p.MEDIA + 'r21.png', 'FF48484A', '<visible>%s</visible>' % on, border=21)
        out += ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>118</height><label></label>'
                '<texturefocus /><texturenofocus /></control>') % (base + i, x, y - 10, sw, )
        out += '<control type="group"><visible>%s</visible>%s</control>' % (on, u.text(p, x, y + 5, sw, 86, title, 'p_foot_b', p.WHITE, 'center'))
        out += '<control type="group"><visible>%s</visible>%s</control>' % (u.neg(on), u.text(p, x, y + 5, sw, 86, title, 'p_foot_b', p.GREY, 'center'))
    return out


# C1 (owner, 2026-11-14: "a lot of grey open space, can be cleaner"; build442-mockups.html, approved): rows sized to
# their content, 30 pt tiles, the text right under the title, Fix as a text action, repeats folded into one row.
RUN_H = 172                    # 64 pt: a 44 pt poster and 9 pt above and below
TILE, PAD = 81, 24             # 30 pt tiles, 9 pt row padding
TEXT_X = 140                   # from the card's left edge: tile 32 + 81 + 27
TITLE_LINE, TEXT_LINE = 52, 46
TIME_W = 190
END_H = 43                     # the last 16 pt of every row (rounded at the card's bottom)
TITLE_CHARS, TITLE_CHARS_CHIP, TEXT_CHARS = 27, 23, 47   # characters a line surely holds (p_pill 40 / p_foot 35); lines()


def lines(text, per_line, most):
    """How many lines `text` needs at `per_line` characters, word-wrapped (whole words never split), at most `most`.
    Conservative on purpose: a row one line too tall is fine, a line too few would hide text (DEC-050)."""
    words, count, used = str(text or '').split(), 1, 0
    if not words:
        return 0
    for word in words:
        need = len(word) + (1 if used else 0)
        if used and used + need > per_line:
            count, used = count + 1, len(word)
        else:
            used += need
    return min(count, most)


_NARROW, _MID, _WIDE = set("iljI.,:;!|'\u00b7 "), set('frt()-/"'), set('mwMW')


def text_width(text, size, bold=False):
    """About how wide Inter draws `text` at `size` (skin units), from per-character widths a little above Inter's
    own: narrow 0.3 em, f r t ( ) 0.38, digits 0.6, lower case 0.56, capitals 0.7, m w 0.88."""
    em = 0.0
    for ch in str(text or ''):
        em += (0.3 if ch in _NARROW else 0.38 if ch in _MID else 0.9 if ch in _WIDE else 0.6 if ch.isdigit()
               else 0.7 if ch.isupper() else 0.56)
    return em * size * (1.06 if bold else 1.0)


def lines_in(text, size, width, most, bold=False):
    """Lines `text` takes in a box `width` units wide (whole words wrap), at most `most`; 0 for no text."""
    words = str(text or '').split()
    if not words:
        return 0
    count, line = 1, ''
    for word in words:
        trial = (line + ' ' + word) if line else word
        if line and text_width(trial, size, bold) > width:
            count, line = count + 1, word
        else:
            line = trial
    return min(count, most)


def compact(p, key, ident, bar):
    """C1's running row: a 30 x 44 pt poster, the title, the model's line, a progress ring. One grouped card
    (key+'pos', set by notifications.py)."""
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    b = u.row_back(p, key, w, RUN_H) + u.tap(p, ident, S, 0, w, RUN_H)
    b += p.image(S + 32, 27, 81, 118, M + 'white.png', u.SURF2, diffuse=M + 'poster16.png')
    b += p.image(S + 32, 27, 81, 118, P(key + 'poster'), p.WHITE, '', '>scale', M + 'poster16.png', background=True)
    b += p.textbox(S + TEXT_X, 22, w - TEXT_X - 130, TITLE_LINE, P(key + 'title'), 'p_foot_b', p.WHITE)
    b += p.textbox(S + TEXT_X, 22 + TITLE_LINE, w - TEXT_X - 130, 2 * 42, P(key + 'line'), 'p_cap', p.GREY)
    b += p.image(S + w - 32 - 70, (RUN_H - 70) // 2, 70, 70, M + 'ring_20.png', u.TRACK)
    b += p.image(S + w - 32 - 70, (RUN_H - 70) // 2, 70, 70, M + P(key + 'ring'), P(key + 'tint'))
    # The page script still fills the old bar (Control.setPercent); C1 shows the ring instead.
    b += '<control type="group"><visible>false</visible>%s</control>' % u.id_bar(p, bar, S, 0, 10, 4, u.BLUE)
    return u.group(p, RUN_H, b, u.has(key + 'title'))


def message(p, n):
    """C1's message row, stacked from parts the grouplist lays out one under the other, so the row is as tall as its
    title (1 or 2 lines, key+'tl'), text (1 to 3 lines, key+'ll') and Fix action need. Nothing is cut (DEC-050)."""
    S, W, w, M, P = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    key = 'msg.%d.' % n
    on = u.has(key + 'title')
    eq = lambda k, v: 'String.IsEqual(Window().Property(%s%s),%s)' % (key, k, v)
    first = '%s | %s' % (eq('pos', 'first'), eq('pos', 'only'))
    last = '%s | %s' % (eq('pos', 'last'), eq('pos', 'only'))
    plain = lambda h: p.image(S, 0, w, h, M + 'white.png', p.SURFACE)
    out = ''

    def tile_again(head_h, cond):
        """The tile once more, drawn from the next part (a one-line title's header is shorter than the tile, and the next
        part's background is drawn after it)."""
        top = PAD - head_h
        return ('<control type="group"><visible>%s</visible>%s%s</control>' % (
            cond, p.image(S + 32, top, TILE, TILE, M + 'r21.png', P(key + 'tint'), border=21),
            u.glyph(p, S + 32 + TILE // 2 - 19, top + TILE // 2 - 19, 38, p.ICONS + P(key + 'icon'), P(key + 'glyph'))))

    one = eq('tl', 1)
    head1 = PAD + TITLE_LINE
    for tl in (1, 2, 3):
        h = PAD + tl * TITLE_LINE
        b = (p.image(S, 0, w, h, M + 'row_first.png', p.SURFACE, '<visible>%s</visible>' % first, border='43,43,43,0') +
             '<control type="group"><visible>![%s]</visible>%s</control>' % (first, plain(h)) +
             p.image(S + TEXT_X, 0, w - TEXT_X, 3, M + 'white.png', '1FEBEBF5', '<visible>![%s]</visible>' % first))
        # One tap area for the whole row: it reaches under the text, Fix and end parts that follow (they have no button
        # of their own; Fix and the next row's title are later in the window, so they stay on top).
        b += u.tap(p, 9500 + n, S, 0, w, h + 4 * TEXT_LINE + 6 + 70 + END_H)
        if tl > 1:   # a one-line title's tile is drawn by the next part (tile_again): drawn twice, its tint would double
            b += p.image(S + 32, PAD, TILE, TILE, M + 'r21.png', P(key + 'tint'), border=21)
            b += u.glyph(p, S + 32 + TILE // 2 - 19, PAD + TILE // 2 - 19, 38, p.ICONS + P(key + 'icon'), P(key + 'glyph'))
        tw = w - TEXT_X - TIME_W - 20
        if tl == 1:
            # The title, then the "×2" chip of folded repeats right after it.
            b += ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
                  '<orientation>horizontal</orientation><itemgap>16</itemgap><usecontrolcoords>true</usecontrolcoords>'
                  '<control type="label"><width max="%d">auto</width><height>%d</height><font>p_pill</font><textcolor>%s</textcolor>'
                  '<aligny>center</aligny><scroll>false</scroll><label>%s</label></control>'
                  '<control type="group"><width>78</width><height>%d</height><visible>%s</visible>%s%s</control>'
                  '</control>') % (S + TEXT_X, PAD, tw, TITLE_LINE, tw - 100, TITLE_LINE, p.WHITE, P(key + 'title'),
                                   TITLE_LINE, u.has(key + 'count'),
                                   p.image(0, 7, 78, 38, M + 'r21.png', '1FEBEBF5', border=12),
                                   u.text(p, 0, 7, 78, 38, P(key + 'count'), 'p_cap', p.GREY, 'center'))
        else:
            b += p.textbox(S + TEXT_X, PAD, tw, tl * TITLE_LINE, P(key + 'title'), 'p_pill', p.WHITE)
            b += '<control type="group"><visible>%s</visible>%s</control>' % (
                u.has(key + 'count'), u.text(p, S + w - 32 - TIME_W, PAD + TITLE_LINE, TIME_W, TITLE_LINE, P(key + 'count'), 'p_cap', p.GREY, 'right'))
        # The time, with the unread dot just before it.
        b += ('<control type="grouplist"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
              '<orientation>horizontal</orientation><align>right</align><itemgap>12</itemgap><usecontrolcoords>true</usecontrolcoords>'
              '<control type="image"><width>20</width><height>%d</height><aspectratio>keep</aspectratio>'
              '<texture colordiffuse="%s">%savatar_s.png</texture><visible>%s</visible></control>'
              '<control type="label"><width max="%d">auto</width><height>%d</height><font>p_foot</font><textcolor>%s</textcolor>'
              '<aligny>center</aligny><scroll>false</scroll><label>%s</label></control></control>') % (
                  S + w - 32 - TIME_W, PAD, TIME_W, TITLE_LINE, TITLE_LINE, u.BLUE, M, u.has(key + 'unread'),
                  TIME_W - 32, TITLE_LINE, p.GREY, P(key + 'ago'))
        out += u.group(p, h, b, '%s + %s' % (on, eq('tl', tl)))
    for ll in (1, 2, 3, 4):
        h = 6 + ll * TEXT_LINE
        b = plain(h) + tile_again(head1, one)
        b += p.textbox(S + TEXT_X, 4, w - TEXT_X - 32, ll * TEXT_LINE, P(key + 'text'), 'p_foot', p.GREY)
        out += u.group(p, h, b, '%s + %s' % (on, eq('ll', ll)))
    # Fix: a blue text action under the text (was a capsule beside it, which took the text's width).
    fix = plain(70) + tile_again(head1, '%s + String.IsEmpty(Window().Property(%sll))' % (one, key)) + ('<control type="button" id="%d"><left>%d</left><top>-24</top><width>260</width><height>118</height>'
                       '<label>%s ›</label><font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
                       '<align>left</align><aligny>center</aligny><textoffsetx>0</textoffsetx><texturefocus /><texturenofocus /></control>') % (
                           9600 + n, S + TEXT_X, P(key + 'fix'), p.ACCENT, p.ACCENT)
    out += u.group(p, 70, fix, '%s + %s' % (on, u.has(key + 'fix')))
    end = (p.image(S, 0, w, END_H, M + 'row_last.png', p.SURFACE, '<visible>%s</visible>' % last, border='43,0,43,43') +
           '<control type="group"><visible>![%s]</visible>%s</control>' % (last, plain(END_H)) +
           tile_again(head1, '%s + String.IsEmpty(Window().Property(%sll)) + String.IsEmpty(Window().Property(%sfix))' % (one, key, key)))
    out += u.group(p, END_H, end, on)
    return out


def page(p):
    S, W, w, P = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE, u.P
    head = p.backdrop() + p.nav_button(9001, S, 36, 'chevron-left.png', 'Close')
    head += u.link(p, 9002, W - S - 300, 41, 300, 118, 'Clear All', font='p_body')
    head += u.text(p, S, 150, w, 96, 'Notifications', 'p_large')
    head += segmented(p, p.NOTICE_FILTERS, y=262)
    rows = u.group(p, 99, u.text(p, S + 10, 0, w - 20, 62, 'RUNNING NOW', 'p_pill', p.GREY), u.has('live'))
    for key, ident, bar in cards():
        rows += compact(p, key, ident, bar)
    nxt = (u.tap(p, 9440, S, 0, w, 118).replace('<texturefocus colordiffuse="14FFFFFF">', '<texturefocus colordiffuse="00FFFFFF">', 1) +
           '<control type="grouplist"><left>%d</left><top>0</top><width>%d</width><height>62</height><orientation>horizontal</orientation>'
           '<itemgap>10</itemgap><usecontrolcoords>true</usecontrolcoords>' % (S, w) +
           # The grey line stops short of the room the link needs, so "Library status" always shows (board 5).
           '<control type="label"><width max="%d">auto</width><scroll>false</scroll><height>62</height><font>p_foot</font><textcolor>%s</textcolor><label>%s</label></control>' % (w - LINK_W - 10, p.GREY, P('next.text')) +
           '<control type="label"><width>auto</width><scroll>false</scroll><height>62</height><font>p_foot</font><textcolor>%s</textcolor><label>Library status</label></control>' % p.ACCENT +
           '</control>')
    rows += u.group(p, 124, nxt, u.has('next.text'))
    for n in range(1, p.NOTICE_ROWS + 1):
        # C1: a TODAY / EARLIER heading before the first message of each (notifications.py sets msg.N.section).
        rows += u.group(p, 105, u.text(p, S + 10, 30, w - 20, 62, u.P('msg.%d.section' % n), 'p_pill', p.GREY),
                        u.has('msg.%d.section' % n))
        rows += message(p, n)
    rows += u.group(p, 180, u.text(p, S, 50, w, 80, "You're all caught up", 'p_h3', p.GREY), u.has('empty'))
    rows += u.group(p, 200, '')
    body = head + ('<control type="grouplist" id="9300"><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
                   '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (TOP, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 194: approved board 5 -->\n<window><defaultcontrol always="true">9001</defaultcontrol>'
            '<controls>' + body + '</controls></window>')
