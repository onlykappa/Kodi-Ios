"""Approved Sports opening card (docs/design/sports-opening-options.html, owner: "i like this", 2026-11-21): the page behind dimmed, one centered card with the
game first: LIVE on its own line with the league tag under it, the two teams' crests (no circles) each with its short name on one line under it, the stage in
one line, the thin 4-pt bar (DEC-036), "Source 1 of 2 · 0:03", Cancel. Native choices must remain above this window.

Properties (set by sports_opening.py): live ('1' when the game is on), tag, away.name / away.code / away.logo and home.* (the crest file; the team's code
shows until it is in), stage, sub, failed ('1' after every source failed: the bar and Cancel give way to one button, Back to Sports).
The earlier card (a 720-unit box with the matchup in grey over a hairline bar, floating over an un-dimmed page) is gone: owner, build 623, screenshot IMG_0541."""
import status_ui as u
import pages
WINDOW='IOSSportsOpening.xml'
CANCEL=9001
BACK=9003
CARD_W=900
PAD=54
INNER=CARD_W-2*PAD
AT=72                                  # the column between the teams ("at")
COLUMN=(INNER-AT)//2                   # each team's column: crest and name centered in it
LOGO=172                               # 64 pt
NAME_FIT=COLUMN-20                     # a short name is used only when it measures under this at its size; else the team's code (never cut, DEC-050)
NAME_FONT,NAME_SIZE='p_pill',40
SHADE='9E000000'                       # the page behind: black at 62 %
LIVE_RED='FFFF453A'
BUTTON=118                             # 44 pt: the smallest hit area


def rows():
    """(name, height) of every row of the card, top to bottom; the card is as tall as they add up to."""
    return [('top',59),('live',44),('tag',40),('gap1',40),('logos',LOGO),('gap2',22),('names',52),('gap3',40),('stage',54),('sub',48),('gap4',24),('bar',11),('gap5',36),
            ('buttons',BUTTON),('bottom',54)]


def page(p):
    has=lambda key:u.has(key);P=u.P
    steps=rows()
    card_h=sum(h for _,h in steps)
    left=(p.WIDTH-CARD_W)//2
    top=(p.HEIGHT-card_h)//2
    ok,bad=u.neg(u.has('failed')),u.has('failed')
    y=top;at={}
    for name,h in steps:
        at[name]=y;y+=h
    x=left+PAD;cx=left+CARD_W//2
    body=p.image(0,0,p.WIDTH,p.HEIGHT,p.MEDIA+'white.png',SHADE)   # the page behind is dimmed
    body+=p.surface(left,top,CARD_W,card_h,'round_s.png',p.SURFACE,26)
    # LIVE, its dot and the tag under it, centered
    body+=('<control type="group"><visible>%s</visible>%s%s</control>')%(has('live'),
        p.image(cx-62,at['live']+11,22,22,p.MEDIA+'dot.png',LIVE_RED),u.text(p,cx-26,at['live'],130,44,'LIVE','p_foot_b',LIVE_RED,'left'))
    body+=u.text(p,x,at['tag'],INNER,40,P('tag'),'p_cap',p.GREY,'center')
    for side,colx in (('away',x),('home',x+COLUMN+AT)):
        key=side+'.'
        lx=colx+(COLUMN-LOGO)//2
        body+=p.image(lx,at['logos'],LOGO,LOGO,P(key+'logo'),p.WHITE,'<aspectratio>keep</aspectratio><visible>%s</visible>'%has(key+'logo'))
        body+='<control type="group"><visible>%s</visible>%s</control>'%(u.neg(has(key+'logo')),u.text(p,colx,at['logos'],COLUMN,LOGO,P(key+'code'),'p_h3',p.GREY,'center'))
        body+=u.text(p,colx,at['names'],COLUMN,52,P(key+'name'),NAME_FONT,p.WHITE,'center')
    body+=u.text(p,x+COLUMN,at['logos'],AT,LOGO,'at','p_sub',p.GREY,'center')
    body+=u.text(p,x,at['stage'],INNER,54,P('stage'),NAME_FONT,p.WHITE,'center')
    body+=u.text(p,x,at['sub'],INNER,48,P('sub'),'p_foot',p.GREY,'center')
    body+='<control type="group"><visible>%s</visible>%s</control>'%(ok,pages.slide_bar(p.MEDIA,x,at['bar'],INNER,11))
    body+='<control type="group"><visible>%s</visible>%s</control>'%(ok,p.pill_button(CANCEL,x,at['buttons'],INNER,BUTTON,'Cancel',[('','noop')],'secondary'))
    body+='<control type="group"><visible>%s</visible>%s</control>'%(bad,p.pill_button(BACK,x,at['buttons'],INNER,BUTTON,'Back to Sports',[('','noop')],'primary'))
    return '<?xml version="1.0" encoding="UTF-8"?><window><defaultcontrol>9001</defaultcontrol><controls>%s</controls></window>'%body

def files(p):
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
