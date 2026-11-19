"""Approved Sports opening surface (docs/design/sports-opening-mockup.html); native choices must remain above this
window. One compact centered card, matching the shape of the existing opening card (pages.busy_dialog, boards
04/05) instead of a bespoke full-screen layout: the earlier version repeated "Opening your game" as both a static
page title and the live stage line, and left a large empty gap above the card."""
import status_ui as u
import pages
WINDOW='IOSSportsOpening.xml'
CANCEL=9001
CARD_W=720
PAD=48
INNER=CARD_W-2*PAD

def page(p):
    # Rows stack by their own height, not fixed offsets: a long team name on both sides can wrap to two lines
    # each (DEC-050, no text is ever cut off), so the matchup textbox must be tall enough for four lines, not two.
    rows=[('title',64),('matchup',200),('detail',80),('gap',16),('bar',11),('gap',8),('elapsed',44),('gap',24),('cancel',124)]
    card_h=2*PAD+sum(h for _,h in rows)
    left=(p.WIDTH-CARD_W)//2
    top=(p.HEIGHT-card_h)//2
    y=PAD
    body=p.surface(left,top,CARD_W,card_h,'round_s.png',p.SURFACE,26)
    for name,h in rows:
        x,w=left+PAD,INNER
        if name=='title':body+=u.text(p,x,top+y,w,h,'Opening your game',font='p_h3',align='center')
        elif name=='matchup':body+=p.textbox(x,top+y,w,h,u.P('matchup'),'p_sub',p.GREY)
        elif name=='detail':body+=p.textbox(x,top+y,w,h,u.P('detail'),'p_foot',p.GREY)
        elif name=='bar':body+=pages.slide_bar(p.MEDIA,x,top+y,w,h)
        elif name=='elapsed':body+=u.text(p,x,top+y,w,h,u.P('elapsed'),font='p_cap',tint=p.GREY,align='center')
        elif name=='cancel':body+=p.pill_button(CANCEL,x,top+y,w,h,'Cancel',[('','noop')],'secondary')
        y+=h
    return '<?xml version="1.0" encoding="UTF-8"?><window><defaultcontrol>9001</defaultcontrol><controls>%s</controls></window>'%body

def files(p):
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
