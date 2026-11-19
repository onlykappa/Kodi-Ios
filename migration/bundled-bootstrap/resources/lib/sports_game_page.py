"""The game page (owner mockup page 6, 2026-11-19): the two teams on their colours, the time, Remind me / Play, Sources, Game info."""
import status_ui as u
import sports_hero as hero

WINDOW = 'IOSSportsGame.xml'
BACK, REFRESH, LIST, RETRY = 9001, 9002, 9300, 9003
SEARCH_RETRY = 9004
AUTO = 9005
REMIND, REMIND_ON = 9006, 9008      # Remind me / Reminder on (two buttons, one visible at a time) (board C of docs/design/sports-game-mockups.html)
INFO_OPEN = 9011                    # the "Game info" card (opens the game's Info / Standings page)
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
                inside += p.textbox(231,top+TITLE_LINE*title,text_w,DETAIL_LINE*detail,u.P(key+'detail'),'p_sub',p.GREY)
                if badge_w:
                    inside += _badge(p,866-badge_w,(h-56)//2,badge_w,'Best' if kind=='best' else 'Also good',
                                     p.ACCENT if kind=='best' else p.GREY,'330A84FF' if kind=='best' else '24EBEBF5')
                b += ('<control type="group"><visible>String.IsEqual(Window().Property(%stag),%s)</visible>%s</control>') % (key,kind,inside)
            b += p.image(898,(h-92)//2,92,92,p.MEDIA+'pill_96.png',p.WHITE,border=46)
            b += p.image(924,(h-43)//2,43,43,p.MEDIA+'play.png','FF000000',aspect='>keep')
            out += u.group(p,h,b,'String.IsEqual(Window().Property(%sform),%d)' % (key,form))
    return out


def page(p):
    header = p.nav_button(BACK, 32, 5, 'chevron-left.png', 'noop')
    header += p.nav_button(REFRESH, 940, 5, p.MEDIA + 'hdr_refresh.png', 'noop', glyph_size=60).replace(p.WHITE, p.ACCENT)
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
    heading = u.text(p, p.SIDE, 43, 700, 70, 'Sources', 'p_h2')
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
    # Game info: one card that opens the facts page (kickoff, venue, recent form, standings).
    content += u.group(p, 134, u.text(p, p.SIDE, 43, 700, 70, 'Game info', 'p_h2'), u.has('hero.lines') + ' + !String.IsEqual(Window().Property(state),error)')
    info = u.card(p, p.SIDE, 0, 972, 190)
    info += u.text(p, 92, 28, 760, 70, u.P('info.title'), 'p_h3') + u.text(p, 92, 98, 760, 56, u.P('info.sub'), 'p_sub', p.GREY)
    info += u.glyph(p, 940, 79, 32, 'chevron-right.png', p.GREY)
    info += u.tap(p, INFO_OPEN, p.SIDE, 0, 972, 190)
    content += u.group(p, 230, info, u.has('hero.lines') + ' + !String.IsEqual(Window().Property(state),error)')
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
