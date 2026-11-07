"""portrait/IOSRows.xml: a tab's rows (round-4 mockups 04-07), filled by customise_rows.py from rows_editor.

Page "" (the list): each row with its style and source, faded when off; Edit (top right) gives every row a red
delete disc and ▲ ▼ to move it; Add Row and Restore Default Rows below. Page "row": one row's settings (Show This
Row, Name, Style, where it comes from, Delete Row). portrait.py passes its helpers in `p`.
"""
NAME='IOSRows.xml'
BACK,EDIT,LIST,ONE=9001,9002,9300,9600
ROW_BASE,UP,DOWN,REMOVE=9100,9810,9840,9870   # slot n: row 9100+n, ▲ 9810+n, ▼ 9840+n, delete 9870+n
ADD,RESTORE=9501,9502
SHOW,RENAME,STYLE,DELETE=9601,9602,9604,9605
SLOTS=30;ROW=150;HIT=118

def P(k):return '$INFO[Window().Property(%s)]'%k
def has(k):return '!String.IsEmpty(Window().Property(%s))'%k
EDITING=has('editing');ON_LIST='String.IsEmpty(Window().Property(page))';ON_ROW='String.IsEqual(Window().Property(page),row)'

def _arrow(p,id,x,glyph,key):
 return ('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'%(x,(ROW-HIT)//2,HIT,HIT)+
  p.image(7,7,104,104,p.MEDIA+'close_disc.png','2EFFFFFF','<visible>%s</visible>'%has(key))+
  p.image(25,25,68,68,p.MEDIA+glyph,p.WHITE,'<visible>%s</visible>'%has(key))+
  p.image(25,25,68,68,p.MEDIA+glyph,p.DIM,'<visible>!%s</visible>'%has(key))+
  '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus /><enable>%s</enable></control></control>'%(id,HIT,HIT,has(key)))

def slot(p,n):
 S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE;key='row.%d.'%n
 off='<animation effect="fade" start="100" end="45" time="0" condition="%s">Conditional</animation>'%has(key+'off')
 indent='<animation effect="slide" end="110,0" time="180" tween="cubic" easing="out" condition="%s">Conditional</animation>'%EDITING
 remove=('<control type="group"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><visible>%s</visible>'%(S+6,(ROW-HIT)//2,HIT,HIT,EDITING)+
  p.image(29,29,60,60,p.MEDIA+'avatar_s.png','FFFF453A')+p.image(44,56,30,6,p.MEDIA+'white.png',p.WHITE)+
  '<control type="button" id="%d"><width>%d</width><height>%d</height><label></label><texturefocus /><texturenofocus /></control></control>'%(REMOVE+n,HIT,HIT))
 arrows=('<control type="group"><visible>%s</visible>'%EDITING+_arrow(p,UP+n,S+w-2*HIT-20,'arrow_up.png',key+'up')+
         _arrow(p,DOWN+n,S+w-HIT-6,'arrow_down.png',key+'down')+'</control>')
 return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>'%(W,ROW+12,has(key+'title'))+
  p.surface(S-6,0,w+12,ROW,'round.png',p.SURFACE,32)+
  '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
  '<texturefocus border="32" colordiffuse="1FFFFFFF">%sround.png</texturefocus><texturenofocus /><enable>!%s</enable></control>'%(ROW_BASE+n,S-6,w+12,ROW,p.MEDIA,EDITING)+
  '<control type="group">%s%s'%(off,indent)+
  p.label(S+24,22,w-48-2*HIT-140,58,P(key+'title'),'p_pill',p.WHITE)+p.label(S+24,78,w-48-2*HIT-140,50,P(key+'sub'),'p_pill_s',p.GREY)+
  '</control>'+
  p.icon(S+w-60,(ROW-34)//2,34,'chevron-right.png',p.GREY,'<visible>!%s</visible>'%EDITING)+remove+arrows+'</control>')

def action_row(p,id,text,color,height=ROW,extra=''):
 S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
 return ('<control type="group"><width>%d</width><height>%d</height>'%(W,height+12)+p.surface(S-6,0,w+12,height,'round.png',p.SURFACE,32)+
  '<control type="button" id="%d"><left>%d</left><top>0</top><width>%d</width><height>%d</height><label></label>'
  '<texturefocus border="32" colordiffuse="1FFFFFFF">%sround.png</texturefocus><texturenofocus /></control>'%(id,S-6,w+12,height,p.MEDIA)+
  p.label(S+24,0,w-48,height,text,'p_pill',color)+extra+'</control>')

def value_row(p,id,text,value):
 S,w=p.SIDE,p.WIDTH-2*p.SIDE
 return action_row(p,id,text,p.WHITE,extra=p.label(S+300,0,w-408,ROW,value,'p_pill',p.GREY,'right')+p.icon(S+w-60,(ROW-34)//2,34,'chevron-right.png',p.GREY))

def text(p,body,height=150):
 S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
 return ('<control type="group"><width>%d</width><height>%d</height>'%(W,height)+
         p.label(S+12,16,w-24,height-30,body,'p_cap',p.GREY,'left','<wrapmultiline>true</wrapmultiline><aligny>top</aligny>')+'</control>')

def page(p):
 S,W,w=p.SIDE,p.WIDTH,p.WIDTH-2*p.SIDE
 head=(p.backdrop()+p.nav_button(BACK,S,36,'chevron-left.png',[])+
  '<control type="button" id="%d"><left>%d</left><top>36</top><width>220</width><height>108</height><label>%s</label><font>p_btn</font>'
  '<textcolor>FF0A84FF</textcolor><focusedcolor>FF64D2FF</focusedcolor><align>right</align><aligny>center</aligny><textoffsetx>0</textoffsetx>'
  '<texturefocus /><texturenofocus /><visible>%s</visible></control>'%(EDIT,W-S-220,P('edit_label'),ON_LIST)+
  p.label(S,160,w,110,P('title'),'p_large',p.WHITE,'left','<scroll>false</scroll>')+
  p.label(S,268,w,56,P('sub'),'p_sub',p.GREY,'left','<scroll>true</scroll>'))
 rows=('<control type="grouplist" id="%d"><left>0</left><top>340</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>'%(LIST,W,ON_LIST)+
  text(p,P('empty'),110).replace('<control type="group">','<control type="group"><visible>%s</visible>'%has('empty'),1)+
  ''.join(slot(p,n) for n in range(1,SLOTS+1))+text(p,P('more'),90)+
  '<control type="image"><height>40</height><texture /></control>'+
  action_row(p,ADD,'+  Add Row','FF0A84FF')+action_row(p,RESTORE,'Restore Default Rows','FFFF453A')+
  text(p,'The rows show in this order on the page. Faded rows are off. Edit to move or delete rows.',200)+'</control>')
 toggle=(p.image(w-150,(ROW-58)//2,130,58,p.MEDIA+'toggle_on.png',p.WHITE,'<visible>%s</visible>'%has('one.on'))+
         p.image(w-150,(ROW-58)//2,130,58,p.MEDIA+'toggle_off.png',p.WHITE,'<visible>!%s</visible>'%has('one.on')))
 one=('<control type="grouplist" id="%d"><left>0</left><top>340</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
  '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords><visible>%s</visible>'%(ONE,W,ON_ROW)+
  action_row(p,SHOW,'Show This Row',p.WHITE,extra='<control type="group"><left>%d</left>%s</control>'%(S,toggle))+
  value_row(p,RENAME,'Name',P('one.title'))+value_row(p,STYLE,'Style',P('one.style'))+
  '<control type="group"><width>%d</width><height>%d</height>'%(W,190)+p.surface(S-6,0,w+12,178,'round.png',p.SURFACE,32)+
  p.label(S+24,20,w-48,60,'Content: '+P('one.source'),'p_pill',p.WHITE)+p.label(S+24,88,w-48,60,P('one.path'),'p_pill_s',p.GREY,'left','<scroll>true</scroll>')+'</control>'+
  text(p,'Content picks what fills the row. To change it, delete this row and add another.',140)+
  action_row(p,DELETE,'Delete Row','FFFF453A')+'</control>')
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s tab rows -->\n<window><defaultcontrol always="true">%d</defaultcontrol>'
  '<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation><controls>%s%s%s</controls></window>\n')%(p.MARKER,BACK,head,rows,one)

def files(p):return {p.FOLDER+'/'+NAME:page(p).encode()}
