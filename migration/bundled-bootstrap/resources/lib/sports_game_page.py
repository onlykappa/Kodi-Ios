"""The upcoming game's card and sources, approved boards 12 and 13."""
import status_ui as u

WINDOW = 'IOSSportsGame.xml'
BACK, REFRESH, LIST, RETRY = 9001, 9002, 9300, 9003
SEARCH_RETRY = 9004
AUTO = 9005
REMIND, REMIND_ON = 9006, 9008      # Remind me / Reminder on (two buttons, one visible at a time) (board C of docs/design/sports-game-mockups.html)
STANDINGS_SWITCH, STANDINGS_SWITCH_BACK = 9009, 9010      # Divisional / Wild Card (one visible at a time)
SOURCE, SLOTS = 50000, 24
ST_ROWS = 8
DOTS = 5
FORMS = tuple((title, detail) for title in range(1, 5) for detail in range(1, 10))
TEAM_FORMS = range(1, 7)
TITLE_LINE, DETAIL_LINE = 55, 51


def hero_height(lines):
    return 319 + 51*lines + 48


def source_height(title, detail):
    return max(161, 43 + TITLE_LINE*title + DETAIL_LINE*detail)


def _badge(p, x, y, w, text, tint=None, fill=None):
    return (p.image(x,y,w,56,p.MEDIA+'r21.png',fill or p.SURFACE2,border=21) +
            u.text(p,x,y,w,56,text,'p_foot_b',tint or p.WHITE,'center'))


def _hero(p):
    out = ''
    for lines in TEAM_FORMS:
        height = hero_height(lines)
        card = p.surface(p.SIDE,0,972,height,'row_only.png',p.SURFACE,54)
        # Auto-width, label-only badge: short league codes stay whole.
        card += ('<control type="grouplist"><left>92</left><top>43</top><width>300</width><height>56</height>'
                 '<orientation>horizontal</orientation><usecontrolcoords>true</usecontrolcoords>'
                 '<control type="button"><width min="102">auto</width><height>56</height><enable>false</enable>'
                 '<label>%s</label><font>p_foot_b</font><textoffsetx>24</textoffsetx><disabledcolor>%s</disabledcolor>'
                 '<texturefocus /><texturenofocus border="21" colordiffuse="%s">%sr21.png</texturenofocus>'
                 '</control></control>') % (u.P('league'),p.WHITE,p.SURFACE2,p.MEDIA)
        card += u.text(p,420,43,568,56,u.P('starts'),'p_pill',p.ACCENT,'right')
        for side,x in (('away',92),('home',704)):
            cx = x+62
            card += p.image(cx,137,161,161,p.MEDIA+'pill_170.png',p.SURFACE2,border=80)
            card += p.image(cx,137,161,161,u.P(side+'.crest'),extra='<visible>'+u.has(side+'.crest')+'</visible>',aspect='>keep',background=True)
            card += u.text(p,cx,137,161,161,u.P(side+'.code'),'p_pill',align='center').replace(
                '</control>','<visible>'+u.neg(u.has(side+'.crest'))+'</visible></control>')
            card += p.textbox(x,319,285,51*lines,u.P(side+'.name'),'p_pill').replace(
                '<autoscroll>','<align>center</align><autoscroll>')
        card += u.text(p,325,164,430,94,u.P('clock'),'p_title',align='center')
        card += u.text(p,360,263,360,51,u.P('day'),'p_sub',p.GREY,'center')
        out += u.group(p,height,card,'String.IsEqual(Window().Property(hero.lines),%d)' % lines)
    return out


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


def _info(p):
    """Board D3 / D4: one scrolling Info section under the sources: when and where, recent form, the standings table."""
    out = u.group(p, 50, '', u.has('info.kickoff'))
    card_x, card_w = p.SIDE, 972
    # Kickoff (and Venue, when ESPN has one) in one grouped card.
    for with_venue in (False, True):
        h = 290 if with_venue else 130
        body = u.card(p, card_x, 0, card_w, h)
        body += u.text(p, 92, 0, 300, 130, 'Kickoff', 'p_sub', p.GREY)
        body += u.text(p, 400, 0, 588, 130, u.P('info.kickoff'), 'p_pill', align='right')
        if with_venue:
            body += p.image(92, 130, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
            body += u.text(p, 92, 133, 250, 157, 'Venue', 'p_sub', p.GREY)
            body += p.textbox(330, 148, 658, 51 * 2, u.P('info.venue'), 'p_pill').replace('<autoscroll>', '<align>right</align><autoscroll>')
            body += u.text(p, 330, 232, 658, 51, u.P('info.place'), 'p_foot', p.GREY, 'right')
        cond = u.has('info.kickoff') + (' + ' + u.has('info.venue') if with_venue else ' + String.IsEmpty(Window().Property(info.venue))')
        out += u.group(p, h + 40, body, cond)
    # Recent form: a grouped card, one row per team, five W / L / D dots.
    out += u.group(p, 118, u.text(p, p.SIDE + 10, 30, 700, 60, 'Recent form', 'p_foot_b', p.GREY), u.has('form.0.name'))
    rows = ''
    for n in range(2):
        key = 'form.%d.' % n
        y = n * 190
        rows += p.textbox(92, y + 14, 500, 102, u.P(key + 'name'), 'p_pill')
        rows += u.text(p, 92, y + 116, 560, 54, u.P(key + 'line'), 'p_foot', p.GREY)
        for d in range(DOTS):
            x = 988 - (DOTS - d) * 68 + 12
            for letter, tint in (('W', p.GREEN), ('L', 'FFFF453A'), ('D', '66EBEBF5')):
                cond = 'String.IsEqual(Window().Property(%sd%d),%s)' % (key, d, letter)
                dot = p.image(x, y + 62, 56, 56, p.MEDIA + 'r27.png', tint, border=27)
                dot += u.text(p, x, y + 62, 56, 56, letter, 'p_foot_b', 'FF000000', 'center')
                rows += '<control type="group"><visible>%s</visible>%s</control>' % (cond, dot)
        if n == 0:
            rows += p.image(92, 190, 896, 3, p.MEDIA + 'white.png', '1FEBEBF5')
    out += u.group(p, 420, u.card(p, card_x, 0, card_w, 380) + rows, u.has('form.0.name'))
    # Standings: header, up to ST_ROWS rows (the game's two teams tinted), the Divisional / Wild Card switch.
    out += u.group(p, 118, u.text(p, p.SIDE + 10, 30, 960, 60, u.P('st.title'), 'p_foot_b', p.GREY), u.has('st.title'))
    head = p.image(card_x, 0, card_w, 100, p.MEDIA + 'row_first.png', p.SURFACE, border=43)
    cols = ((560, 90), (655, 90), (750, 90), (858, 130))
    for i, (x, w) in enumerate(cols):
        head += u.text(p, x, 0, w, 100, u.P('st.h%d' % i), 'p_foot', p.GREY, 'right')
    head += u.text(p, 92, 0, 120, 100, '#', 'p_foot', p.GREY) + u.text(p, 250, 0, 300, 100, 'Team', 'p_foot', p.GREY)
    out += u.group(p, 100, head, u.has('st.title'))
    for n in range(ST_ROWS):
        key = 'st.%d.' % n
        h = 134
        b = u.row_back(p, key, card_w, h)
        b += p.image(card_x + 14, 8, card_w - 28, h - 16, p.MEDIA + 'r21.png', '330A84FF', '<visible>' + u.has(key + 'me') + '</visible>', border=21)
        b += u.text(p, 92, 0, 80, h, u.P(key + 'rank'), 'p_foot', p.GREY)
        b += p.image(172, (h - 72) // 2, 72, 72, u.P(key + 'crest'), extra='<visible>' + u.has(key + 'crest') + '</visible>', aspect='>keep', background=True)
        b += u.text(p, 262, 0, 290, h, u.P(key + 'team'), 'p_foot')
        for i, (x, w) in enumerate(cols):
            b += u.text(p, x, 0, w, h, u.P(key + 'c%d' % i), 'p_foot', align='right')
        out += u.group(p, h, b, u.has(key + 'team'))
    for ident, cond in ((STANDINGS_SWITCH, 'String.IsEqual(Window().Property(st.switch),wild)'),
                        (STANDINGS_SWITCH_BACK, 'String.IsEqual(Window().Property(st.switch),div)')):
        label = 'Wild Card' if ident == STANDINGS_SWITCH else 'Divisional'
        out += u.group(p, 190, p.pill_button(ident, p.SIDE, 40, 972, 128, label, [('', 'noop')], 'glass'), cond)
    return out


def page(p):
    header = p.nav_button(BACK,32,5,'chevron-left.png','noop')
    header += p.nav_button(REFRESH,940,5,p.MEDIA+'hdr_refresh.png','noop',glyph_size=60).replace(p.WHITE,p.ACCENT)
    content = u.group(p,134,header) + _hero(p)
    auto = p.pill_button(AUTO,p.SIDE,27,972,128,'Play',[('','noop')],'primary','play.png',inline=True)
    content += u.group(p,182,auto,u.has('sources.count'))
    # "Best source: The Loop · 1080p · English", under Play (owner: "providing you with best source").
    content += u.group(p,70,u.text(p,p.SIDE,0,972,60,u.P('play.best'),'p_sub',p.GREY,'center'),u.has('play.best'))
    # No source yet and the game has not started: Remind me (white) or Reminder on (frosted, with what it will do).
    no_source = 'String.IsEqual(Window().Property(state),empty) + String.IsEmpty(Window().Property(game.live))'
    remind = p.pill_button(REMIND,p.SIDE,27,972,128,'Remind me',[('','noop')],'primary','bell.png',inline=True)
    content += u.group(p,182,remind,no_source+' + String.IsEmpty(Window().Property(remind.on))')
    on = p.pill_button(REMIND_ON,p.SIDE,27,972,128,'Reminder on',[('','noop')],'glass','check.png',inline=True)
    content += u.group(p,182,on,no_source+' + !String.IsEmpty(Window().Property(remind.on))')
    content += u.group(p,134,p.textbox(92,0,896,120,u.P('remind.note'),'p_sub',p.GREY).replace('<autoscroll>','<align>center</align><autoscroll>'),
                       no_source+' + !String.IsEmpty(Window().Property(remind.on))')
    heading = u.text(p,p.SIDE,43,700,70,'Sources','p_h2')
    heading += u.text(p,800,43,226,70,u.P('sources.count'),'p_sub',p.GREY,'right')
    content += u.group(p,134,heading,u.has('hero.lines')) + _sources(p)
    empty = u.card(p,p.SIDE,0,972,274)
    empty += u.text(p,97,48,886,56,'No sources yet','p_h3',align='center')
    empty += p.textbox(97,115,886,112,u.P('empty.text'),'p_sub',p.GREY).replace(
        '<autoscroll>','<align>center</align><autoscroll>')
    content += u.group(p,274,empty,'String.IsEqual(Window().Property(state),empty)')
    searching = u.card(p,p.SIDE,0,972,180) + u.text(p,97,48,886,80,'Searching for sources','p_h3',align='center')
    content += u.group(p,180,searching,'String.IsEqual(Window().Property(state),searching)')
    retry = p.pill_button(SEARCH_RETRY,p.SIDE,20,972,128,'Find sources',[('','noop')],'primary')
    content += u.group(p,168,retry,"String.IsEqual(Window().Property(state),empty) + String.IsEqual(Window().Property(game.live),true)")
    content += u.group(p,110,p.textbox(70,27,940,70,'Choose a source to play.','p_foot',p.GREY),u.has('sources.count'))
    error = p.textbox(108,118,864,160,u.P('error.title'),'p_h2').replace('<autoscroll>','<align>center</align><autoscroll>')
    error += p.pill_button(RETRY,270,320,540,134,'Try again',[('','noop')],'primary',extra='<visible>String.IsEqual(Window().Property(state),error)</visible>')
    content += u.group(p,520,error,u.has('error.title'))
    content += u.group(p,160,p.textbox(92,21,896,120,u.P('play.error'),'p_sub',p.GREY),u.has('play.error'))
    content += _info(p)
    content += u.group(p,260,'')
    body = p.backdrop()
    body += ('<control type="grouplist" id="%d"><top>0</top><width>1080</width><bottom>0</bottom>'
             '<orientation>vertical</orientation><itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>'
             '<scrolltime tween="cubic" easing="out">220</scrolltime>%s</control>') % (LIST,content)
    body += p.tabbar('library')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<window><defaultcontrol always="false">9001</defaultcontrol><controls>%s</controls></window>' % body


def files(p):
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
