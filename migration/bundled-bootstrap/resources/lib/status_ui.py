"""Shared Kodi controls for the build-193 boards. All coordinates are portrait units."""
PURPLE, BLUE, TRACK = 'FFBF5AF2', 'FF0A84FF', 'FF3A3A3C'
ORANGE, SEG_GREY, SURF2 = 'FFFF9F0A', 'FF636366', 'FF2C2C2E'
HIT = 118
# Build 194 (owner: "it needs to look exactly like the mocks I approved"): sizes come from
# docs/design/build-193-measurements.md (pt x 2.687). Cards: 16 pt radius (43 units, the row_* textures), 14 pt padding
# (38 units), 14 pt between blocks (38 units).
PAD, GAP, CARD_R = 38, 38, 43


def textures(p):
    """Extra rounded textures at the approved mockups' radii (portrait textures are generated, never committed)."""
    return {'r27.png': p.rounded(64, 64, 27), 'r21.png': p.rounded(48, 48, 21), 'pill21.png': p.rounded(48, 21, 10.5),
            'pill16.png': p.rounded(40, 16, 8), 'pill11.png': p.rounded(30, 11, 5.5), 'poster21.png': p.rounded(140, 210, 21),
            'poster27.png': p.rounded(172, 258, 27), 'poster16.png': p.rounded(108, 161, 16),
            'pill_134.png': p.rounded(134, 134, 67),   # board 3/9's 50 pt Play / Pause capsules
            'thumb16.png': p.rounded(160, 90, 16)}     # DEC-047: episode stills at 16:9


def card(p, x, y, w, h, color=None, extra=''):
    """A grouped card: SURFACE, 16 pt radius."""
    return p.image(x, y, w, h, p.MEDIA + 'row_only.png', color or p.SURFACE, extra, border=43)


def row_back(p, key, w, h, x=None, color=None):
    """A row inside one grouped card: rounded ends only for the first/last row, a hairline above every row but the first."""
    x = p.SIDE if x is None else x
    out = ''.join(p.image(x, 0, w, h, p.MEDIA + tex, color or p.SURFACE,
                          '<visible>String.IsEqual(Window().Property(%spos),%s)</visible>' % (key, pos), border=43 if pos != 'mid' else '')
                  for pos, tex in (('only', 'row_only.png'), ('first', 'row_first.png'), ('mid', 'white.png'), ('last', 'row_last.png')))
    return out + p.image(x, 0, w, 3, p.MEDIA + 'white.png', '1FEBEBF5',
                         '<visible>String.IsEqual(Window().Property(%spos),mid) | String.IsEqual(Window().Property(%spos),last)</visible>' % (key, key))


def id_bar(p, ident, x, y, w, h, tint, track=TRACK, texture='white.png', border=''):
    """A progress bar the page's script fills (Control.setPercent): Kodi's progress control cannot read a percentage from
    a window property (build 193 on the phone and in the Kodi 21.3 rig: such bars stayed empty)."""
    b = ' border="%s"' % border if border != '' else ''
    return ('<control type="progress" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<texturebg%s colordiffuse="%s">%s%s</texturebg><lefttexture /><midtexture%s colordiffuse="%s">%s%s</midtexture>'
            '<righttexture /><overlaytexture /></control>') % (ident, x, y, w, h, b, track, p.MEDIA, texture, b, tint, p.MEDIA, texture)


def link(p, ident, x, y, w, h, title, align='right', font='p_sub', tint=None):
    """A borderless blue text button (ACCENT text, or `tint`), at least 118 units tall."""
    return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><label>%s</label>'
            '<font>%s</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>%s</align><aligny>center</aligny>'
            '<textoffsetx>0</textoffsetx><scroll>false</scroll><texturefocus /><texturenofocus />'
            '<animation effect="fade" start="100" end="70" time="0" condition="Control.HasFocus(%d)">Conditional</animation></control>') % (
                ident, x, y, w, h, p.e(title), font, tint or p.ACCENT, tint or p.ACCENT, align, ident)
NOS = '<scroll>false</scroll>'
P = lambda k: '$INFO[Window().Property(%s)]' % k
has = lambda k: '!String.IsEmpty(Window().Property(%s))' % k


def text(p, x, y, w, h, value, font='p_foot', tint=None, align='left'):
    return p.label(x, y, w, h, value, font, tint or p.WHITE, align, NOS)


def tap(p, ident, x, y, w, h, title='', tint=None, enabled=''):
    return ('<control type="button" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<label>%s</label><font>p_foot_b</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
            '<align>center</align><aligny>center</aligny><scroll>false</scroll><texturefocus colordiffuse="14FFFFFF">%swhite.png</texturefocus>'
            '<texturenofocus />%s</control>') % (ident,x,y,w,h,p.e(title),tint or p.ACCENT,p.WHITE,p.MEDIA,
             '<enable>%s</enable><disabledcolor>%s</disabledcolor>'%(enabled,p.DIM) if enabled else '')


def group(p, height, body, cond='true'):
    return '<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>%s</control>' % (p.WIDTH,height,cond,body)


def section(p, title, cond='true', action=''):
    return group(p,118,text(p,p.SIDE+10,30,p.WIDTH-2*p.SIDE-(300 if action else 20),60,title,'p_foot_b',p.GREY)+action,cond)


def bar(p, x, y, w, key, ident=None):
    return ('<control type="progress"%s><left>%d</left><top>%d</top><width>%d</width><height>11</height>'
            '<info>Window().Property(%spct)</info><texturebg colordiffuse="%s">%swhite.png</texturebg><lefttexture />'
            '<midtexture colordiffuse="%s">%swhite.png</midtexture><righttexture /></control>') % (
                ' id="%d"'%ident if ident else '',x,y,w,key,TRACK,p.MEDIA,P(key+'tint'),p.MEDIA)


def working(p, key, ident, compact=False, menu=None):
    """Poster + one canonical status line, shared by Library and Notifications."""
    S,w,M=p.SIDE,p.WIDTH-2*p.SIDE,p.MEDIA
    h=220 if compact else 360
    body=p.surface(S,0,w,h,'round.png',p.SURFACE,p.RADIUS)
    body+=tap(p,ident,S,0,w,h)
    body+=p.image(S+30,30,140,180 if compact else 210,M+'white.png',p.SURFACE2,diffuse=M+'poster_mask.png')
    body+=p.image(S+30,30,140,180 if compact else 210,P(key+'poster'),p.WHITE,'','>scale',M+'poster_mask.png',background=True)
    x=S+200
    if compact:
        body+=text(p,x,24,w-350,58,P(key+'title'),'p_pill')
        body+=text(p,x,88,w-350,50,P(key+'line'),'p_cap',p.GREY)
        body+=bar(p,x,164,w-280,key)
        if menu:body+=tap(p,menu,S+w-124,0,124,118,'•••',p.GREY)
    else:
        body+=text(p,x,20,w-420,44,'WORKING ON NOW','p_cap',PURPLE)
        body+=text(p,x,68,w-420,62,P(key+'title'),'p_pill')
        body+=text(p,x,136,w-420,50,P(key+'step'),'p_foot',p.GREY)
        body+=p.image(S+w-182,48,150,150,M+'ring_20.png',TRACK)
        body+=p.image(S+w-182,48,150,150,M+P(key+'ring'),P(key+'tint'))
        body+=text(p,S+w-182,48,150,150,P(key+'percent'),'p_foot_b',p.WHITE,'center')
        moving='String.IsEqual(Window().Property(%sstate),running)'%key
        body+=p.image(S+30,250,360,80,P(key+'graph'),p.WHITE,'<visible>'+moving+'</visible>','>stretch')
        body+='<control type="group"><visible>'+moving+'</visible>'+text(p,S+420,262,w-510,54,P(key+'metrics'),'p_foot',p.GREY)+'</control>'
        body+='<control type="group"><visible>!'+moving+'</visible>'+text(p,S+30,262,w-110,54,P(key+'line'),'p_foot',p.GREY)+'</control>'
    body+=p.icon(S+w-60,h-78,32,'chevron-right.png',p.GREY)
    return group(p,h+20,body,has(key+'title'))


def needs(p, key='need.', ident=9004, elevated=False):
    S,w=p.SIDE,p.WIDTH-2*p.SIDE
    body=p.surface(S,0,w,290,'round.png',p.SURFACE2 if elevated else p.SURFACE,p.RADIUS)
    body+=p.surface(S+30,30,80,80,'round_s.png','33FF9F0A',p.RADIUS)
    body+=glyph(p,S+46,46,48,'triangle-exclamation.png','FFFF9F0A')
    body+=text(p,S+140,22,w-170,56,P(key+'title'),'p_foot_b')
    body+=text(p,S+140,84,w-170,50,P(key+'text'),'p_cap',p.GREY)
    body+=p.pill_button(ident,S+140,154,300,124,P(key+'button'),[('','noop')],'primary',extra=NOS)
    return group(p,310,body,has(key+'title'))


def graph(p, key, x, y, w, h):
    """Raster is only the plot. Axis, units, time and peak stay sharp Kodi labels."""
    return (p.image(x+70,y+44,w-80,h-100,P(key+'graph'),p.WHITE,'','>stretch')+
            text(p,x,y,160,40,'MB/s','p_cap',p.GREY)+
            text(p,x+w-300,y,300,40,'peak '+P(key+'peak'),'p_cap',p.GREY,'right')+
            ''.join(text(p,x,y+44+i*(h-140)//2,65,40,P(key+'axis%d'%i),'p_cap',p.GREY) for i in range(3))+
            text(p,x+70,y+h-48,(w-80)//2,40,P(key+'from'),'p_cap',p.GREY)+
            text(p,x+70+(w-80)//2,y+h-48,(w-80)//2,40,'now','p_cap',p.GREY,'right'))


def paragraph(p, x, y, w, h, text, font='p_sub', color=None, align='left'):
    """Build 194: a few lines of plain text (board 2's sign-in card, board 3's sentence, board 7's note) as a Kodi
    textbox, which wraps by itself; one-line text stays a label with scroll off and "…"."""
    return ('<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font>'
            '<textcolor>%s</textcolor><align>%s</align><autoscroll>false</autoscroll><label>%s</label></control>'
            % (x, y, w, h, font, color or p.GREY, align, text))


def glyph(p, x, y, size, name, color, extra=''):
    """An icon whose drawn shape is `size` units across with its top-left at x, y (board 1, 2, 5 and 8 sizes). The
    icon PNGs keep the shape in the middle half of their 128 px canvas, so the image is drawn at twice the size
    around the same centre."""
    return p.icon(x - size // 2, y - size // 2, size * 2, name, color, extra)


def neg(cond):
    """The opposite of a Kodi visibility condition. Kodi reads "!!X" as "!X", so "!" + has(x) would not mean empty."""
    return cond[1:] if cond.startswith('!') and '+' not in cond and '|' not in cond else '!' + cond if '+' not in cond and '|' not in cond else '![%s]' % cond
