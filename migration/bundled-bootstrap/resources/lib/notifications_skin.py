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
TOP = 443            # the list starts with RUNNING NOW (board 5: 225 pt)


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


def compact(p, key, ident, bar):
    """Board 5's running card: poster, title, the model's line, a 4 pt bar, a chevron. 84 pt high."""
    S, w, M, P = p.SIDE, p.WIDTH - 2 * p.SIDE, p.MEDIA, u.P
    b = u.card(p, S, 0, w, 226) + u.tap(p, ident, S, 0, w, 226)
    b += p.image(S + 38, 32, 107, 161, M + 'white.png', u.SURF2, diffuse=M + 'poster16.png')
    b += p.image(S + 38, 32, 107, 161, P(key + 'poster'), p.WHITE, '', '>scale', M + 'poster16.png', background=True)
    b += u.text(p, S + 177, 40, w - 177 - 100, 54, P(key + 'title'), 'p_h3')
    b += u.text(p, S + 177, 103, w - 177 - 100, 43, P(key + 'line'), 'p_foot', p.GREY)
    b += u.id_bar(p, bar, S + 177, 169, w - 177 - 100, 11, P(key + 'tint'), texture='pill11.png', border=5)
    b += u.glyph(p, S + w - 62, 94, 38, 'chevron-right.png', p.GREY)
    return u.group(p, 226 + 38, b, u.has(key + 'title'))


def page(p):
    S, W, w, P = p.SIDE, p.WIDTH, p.WIDTH - 2 * p.SIDE, u.P
    head = p.backdrop() + p.nav_button(9001, S, 36, 'chevron-left.png', 'Close')
    head += u.link(p, 9002, W - S - 300, 41, 300, 118, 'Clear All', font='p_body')
    head += u.text(p, S, 160, w, 110, 'Notifications', 'p_large')
    head += segmented(p, p.NOTICE_FILTERS)
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
    rows += u.group(p, 105, u.text(p, S + 10, 0, w - 20, 62, 'EARLIER', 'p_pill', p.GREY), u.has('has.msg'))
    for n in range(1, p.NOTICE_ROWS + 1):
        key = 'msg.%d.' % n
        b = u.row_back(p, key, w, 165) + u.tap(p, 9500 + n, S, 0, w, 165)
        b += p.image(S + 38, 72, 21, 21, p.MEDIA + 'avatar_s.png', u.BLUE, '<visible>' + u.has(key + 'unread') + '</visible>')
        b += p.image(S + 91, 35, 97, 97, p.MEDIA + 'r27.png', P(key + 'tint'), border=27)
        b += u.glyph(p, S + 115, 59, 48, p.ICONS + P(key + 'icon'), P(key + 'glyph'))
        b += u.text(p, S + 220, 32, w - 220 - 170, 51, P(key + 'title'), 'p_pill')
        b += u.text(p, S + w - 170, 32, 132, 51, P(key + 'ago'), 'p_foot', p.GREY, 'right')
        b += u.text(p, S + 220, 89, w - 258, 43, P(key + 'text'), 'p_foot', p.GREY)
        rows += u.group(p, 165, b, u.has(key + 'title'))
    rows += u.group(p, 180, u.text(p, S, 50, w, 80, "You're all caught up", 'p_h3', p.GREY), u.has('empty'))
    rows += u.group(p, 200, '')
    body = head + ('<control type="grouplist" id="9300"><top>%d</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
                   '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (TOP, W)) + rows + '</control>'
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Build 194: approved board 5 -->\n<window><defaultcontrol always="true">9001</defaultcontrol>'
            '<controls>' + body + '</controls></window>')
