"""Approved Sports opening surface; native choices must remain above this window."""
import status_ui as u
import pages
WINDOW='IOSSportsOpening.xml'
CANCEL=9001

def page(p):
    body=p.backdrop()
    body+=u.text(p,p.SIDE,70,972,80,'Opening your game','p_h2')
    body+=p.textbox(p.SIDE,210,972,240,u.P('matchup'),'p_h2')
    body+=p.surface(p.SIDE,1360,972,360,'row_only.png',p.SURFACE,54)
    body+=u.text(p,97,1400,886,70,u.P('stage'),'p_h3')
    body+=p.textbox(97,1480,886,100,u.P('detail'),'p_sub',p.GREY)
    body+=u.text(p,97,1590,886,52,u.P('elapsed'),'p_foot',p.GREY)
    body+=pages.slide_bar(p.MEDIA,97,1660,886)
    body+=p.pill_button(CANCEL,p.SIDE,1760,972,124,'Cancel',[('','noop')],'secondary')
    return '<?xml version="1.0" encoding="UTF-8"?><window><defaultcontrol>9001</defaultcontrol><controls>%s</controls></window>'%body

def files(p):
    return {p.FOLDER+'/'+WINDOW:page(p).encode()}
