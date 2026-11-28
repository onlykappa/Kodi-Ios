"""The game page (owner mockup page 6, 2026-11-19): the two teams on their colours, the time, Remind me / Play, Sources, Game info."""
import status_ui as u
import sports_hero as hero
import sports_game_facts_page as facts

WINDOW = 'IOSSportsGame.xml'
BACK, REFRESH, LIST, RETRY = 9001, 9002, 9300, 9003
SEARCH_RETRY = 9004
AUTO = 9005
REMIND, REMIND_ON = 9006, 9008      # Remind me / Reminder on (two buttons, one visible at a time) (board C of docs/design/sports-game-mockups.html)
INFO_OPEN = 9011                    # (the old "Game info" card; the facts are now drawn below the sources)
TABS = (9212, 9214, 9213)           # the Game info tabs below the sources: Stats, Play-By-Play, Standings (ids of this page; the strip for a game with no standings adds 20)
OTHER = 9012                        # "Other sources (3)" under the best-source line: jumps to the list
SOURCE, SLOTS = 50000, 24
FORMS = tuple((title, detail) for title in range(1, 5) for detail in range(1, 10))
TITLE_LINE, DETAIL_LINE = 55, 51


PILL_W = 640                    # the action capsule is centred and narrower than the cards (mockup page 6)
PILL_X = (1080 - PILL_W) // 2


def source_height(title, detail):
    return max(161, 43 + TITLE_LINE*title + DETAIL_LINE*detail)


def _badge(p, x, y, w, text, tint=None, fill=None):
    return (p.image(x,y,w,56,p.MEDIA+'r21.png',fill or p.SURFACE2,border=21) +
            u.text(p,x,y,w,56,text,'p_foot_b',tint or p.WHITE,'center'))


CHIP_W = (150, 150, 190)    # picture size, frame rate, bitrate: fixed widths (Kodi cannot size a pill to its text)
CHIP_H, CHIP_GAP = 42, 12
DOT = {'g': 'FF30D158', 'o': 'FFFF9F0A', 'r': 'FFFF453A', 'n': 'FF636366'}   # status only: worked / checking or shaky / failed / unknown (mockup)
GREEN_CHIP, GREEN_TEXT = '2E30D158', 'FF30D158'


def _chips(p, key, y):
    """The picture chips (mockup: 1080p and sharper in green, the rest grey): one row, each shown only when it has text."""
    out, x = '', 231
    for i, width in enumerate(CHIP_W):
        name = '%schip%d' % (key, i)
        has = u.has('%schip%d' % (key, i))
        for sharp in (True, False):
            cond = has + ' + ' + ('String.IsEqual(Window().Property(%schipq),true)' % key if (sharp and i == 0) else ('!String.IsEqual(Window().Property(%schipq),true)' % key if i == 0 else 'true'))
            if i and not sharp:
                continue
            back = p.image(x, y + 5 + (DETAIL_LINE - CHIP_H) // 2, width, CHIP_H, p.MEDIA + 'r21.png', GREEN_CHIP if sharp and i == 0 else p.SURFACE2, '<visible>%s</visible>' % cond, border=21)
            label = u.text(p, x, y + 5 + (DETAIL_LINE - CHIP_H) // 2, width, CHIP_H, u.P(name), 'p_cap', GREEN_TEXT if sharp and i == 0 else p.WHITE, 'center').replace('</control>', '<visible>%s</visible></control>' % cond)
            out += back + label
        x += width + CHIP_GAP
    return out


def _dot(p, key, y):
    """The status dot beside the status line (first line of the text)."""
    return ''.join(p.image(231, y + (DETAIL_LINE - 22) // 2, 22, 22, p.MEDIA + 'pill_96.png', color,
                           '<visible>String.IsEqual(Window().Property(%sdot),%s)</visible>' % (key, name)) for name, color in DOT.items())


def _sources(p):
    out = ''
    for n in range(SLOTS):
        key = 'source.%d.' % n
        for form,(title,detail) in enumerate(FORMS):
            h = source_height(title,detail)
            top = (h-TITLE_LINE*title-DETAIL_LINE*detail)//2
            b = u.row_back(p,key,972,h)
            b += u.tap(p,SOURCE+n*len(FORMS)+form,p.SIDE,0,972,h)
            b += p.image(92,(h-108)//2,108,108,p.MEDIA+'r27.png',p.SURFACE2,border=27)
            b += u.text(p,92,(h-108)//2,108,108,u.P(key+'code'),'p_foot_b',align='center')
            for kind,badge_w in (('best',119),('good',207),('plain',0)):
                text_w = 635-(badge_w+32 if badge_w else 0)
                inside = p.textbox(231,top,text_w,TITLE_LINE*title,u.P(key+'title'),'p_h3')
                if badge_w:   # the badge sits on the title line, at the right (mockup), so the chips below keep the whole width
                    inside += _badge(p,866-badge_w,top+(TITLE_LINE-56)//2,badge_w,'Best' if kind=='best' else 'Also good',
                                     p.ACCENT if kind=='best' else p.GREY,'330A84FF' if kind=='best' else '24EBEBF5')
                b += ('<control type="group"><visible>String.IsEqual(Window().Property(%stag),%s)</visible>%s</control>') % (key,kind,inside)
            below = top+TITLE_LINE*title
            # with chips the first detail line is the chip row and the status starts under it; without, the status starts at once
            for with_chips in (True, False):
                y = below + (DETAIL_LINE if with_chips else 0)
                lines = detail - (1 if with_chips else 0)
                if lines < 1:
                    continue
                inner = (_chips(p,key,below) if with_chips else '') + _dot(p,key,y)
                inner += p.textbox(265,y,601,DETAIL_LINE*lines,u.P(key+'detail'),'p_sub',p.GREY)
                b += '<control type="group"><visible>%s</visible>%s</control>' % (u.has(key+'chip0') if with_chips else 'String.IsEmpty(Window().Property(%schip0))' % key, inner)
            b += p.image(898,(h-92)//2,92,92,p.MEDIA+'pill_96.png',p.WHITE,border=46)
            b += p.image(924,(h-43)//2,43,43,p.MEDIA+'play.png','FF000000',aspect='>keep')
            out += u.group(p,h,b,'String.IsEqual(Window().Property(%sform),%d)' % (key,form))
    return out


def page(p):
    header = p.nav_button(BACK, 32, 5, 'chevron-left.png', 'noop')
    # No refresh button: ESPN's answer is kept fresh by the service (sports_data loop), so nothing needs refreshing by hand (owner, build 619)
    content = u.group(p, 134, header) + hero.hero(p)
    auto = p.pill_button(AUTO, PILL_X, 27, PILL_W, 128, 'Play', [('', 'noop')], 'primary', 'play.png', inline=True)
    content += u.group(p, 182, auto, u.has('sources.count'))
    # "Best source: The Loop · 1080p · English", under Play (owner: "providing you with best source").
    content += u.group(p, 70, u.text(p, p.SIDE, 0, 972, 60, u.P('play.best'), 'p_sub', p.GREY, 'center'), u.has('play.best'))
    content += u.group(p, 130, u.link(p, OTHER, p.SIDE, 6, 972, 118, '', 'center', 'p_body').replace('<label></label>', '<label>%s</label>' % u.P('other.text')), u.has('other.text'))
    # No source yet and the game has not started: Remind me (white) or Reminder on (frosted); the line under says what happens next.
    no_source = 'String.IsEqual(Window().Property(state),empty) + String.IsEmpty(Window().Property(game.live))'
    remind = p.pill_button(REMIND, PILL_X, 27, PILL_W, 128, 'Remind me', [('', 'noop')], 'primary', 'bell.png', inline=True)
    content += u.group(p, 182, remind, no_source + ' + String.IsEmpty(Window().Property(remind.on))')
    on = p.pill_button(REMIND_ON, PILL_X, 27, PILL_W, 128, 'Reminder on', [('', 'noop')], 'glass', 'check.png', inline=True)
    content += u.group(p, 182, on, no_source + ' + !String.IsEmpty(Window().Property(remind.on))')
    content += u.group(p, 134, p.textbox(92, 0, 896, 120, u.P('remind.note'), 'p_sub', p.GREY).replace('<autoscroll>', '<align>center</align><autoscroll>'),
                       'String.IsEqual(Window().Property(state),empty) + !String.IsEmpty(Window().Property(remind.note))')
    heading = u.text(p, p.SIDE, 43, 600, 70, 'Sources', 'p_h2') + u.text(p, 600, 52, 426, 56, u.P('sources.checked'), 'p_sub', p.GREY, 'right')   # "Checking…" / "Checked 12 s ago"
    content += u.group(p, 134, heading, u.has('hero.lines')) + _sources(p)
    # None yet: when it was last looked at, and a link to look again now (mockup page 6).
    none = u.card(p, p.SIDE, 0, 972, 190)
    none += u.text(p, 92, 28, 600, 70, 'None yet', 'p_h3')
    none += u.text(p, 92, 98, 600, 56, u.P('checked'), 'p_sub', p.GREY)
    none += u.link(p, SEARCH_RETRY, 650, 36, 338, 118, 'Check now')
    content += u.group(p, 190, none, 'String.IsEqual(Window().Property(state),empty)')
    searching = u.card(p, p.SIDE, 0, 972, 180) + u.text(p, 97, 48, 886, 80, 'Searching for sources', 'p_h3', align='center')
    content += u.group(p, 180, searching, 'String.IsEqual(Window().Property(state),searching)')
    error = p.textbox(108, 118, 864, 160, u.P('error.title'), 'p_h2').replace('<autoscroll>', '<align>center</align><autoscroll>')
    error += p.pill_button(RETRY, 270, 320, 540, 134, 'Try again', [('', 'noop')], 'primary', extra='<visible>String.IsEqual(Window().Property(state),error)</visible>')
    content += u.group(p, 520, error, u.has('error.title'))
    content += u.group(p, 160, p.textbox(92, 21, 896, 120, u.P('play.error'), 'p_sub', p.GREY), u.has('play.error'))
    # Game info, below the sources (owner, 2026-11-28: "the game info tabs should be when I scroll down"): the Stats / Play-By-Play / Standings tabs and their cards,
    # the same ones the Info window drew (sports_game_facts_page.inline), filled by sports_game_facts.Section.
    shown = u.has('hero.lines') + ' + !String.IsEqual(Window().Property(state),error)'
    content += u.group(p, 134, u.text(p, p.SIDE, 43, 700, 70, 'Game info', 'p_h2'), shown)
    content += facts.inline(p, TABS, shown)
    content += u.group(p, 260, '')
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s</control>') % (LIST, content)
    body += p.tabbar('library')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>' % body


def files(p):
    out = {p.FOLDER + '/' + WINDOW: page(p).encode()}
    out.update({'extras/portrait/' + name: data for name, data in hero.textures(p).items()})
    return out
