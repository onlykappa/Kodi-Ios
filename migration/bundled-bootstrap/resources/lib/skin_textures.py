"""Shared textures and Kodi's invisible background progress box (ISSUE-287: they outlived the activity pill).

- ring_00..ring_20: a ring filled clockwise to n/20, used by Notifications and Library status (library_rows.ring).
- sheet_bg.png and row_only/row_first/row_last.png: rounded corners for sheets and grouped rows.
- DialogExtendedProgressBar.xml (portrait and 1080i): Kodi's background progress box, never drawn. Its three controls
  stay so Kodi can fill them; background_box.py reads them for Elementum Burst errors.
"""
import math

RING=140


def arc(p,size,stroke,frac):
 """A ring filled clockwise from 12 o'clock to `frac` (white, tinted by colordiffuse)."""
 c=size/2.0;r=c-stroke/2.0-1
 def pixel(x,y):
  dx,dy=x+0.5-c,y+0.5-c;d=math.hypot(dx,dy)
  a=max(0.0,min(1.0,stroke/2.0-abs(d-r)+0.5))
  if a<=0:return (255,255,255,0)
  ang=(math.degrees(math.atan2(dx,-dy))+360)%360
  return (255,255,255,int(255*a)) if frac>=1 or ang<=frac*360 else (255,255,255,0)
 return p.png(size,size,pixel)


def corner_texture(p,size,radius,top,bottom):
 """White rounded square with only the chosen ends rounded (nine-sliced with border=radius)."""
 if top and bottom:cover=lambda x,y:p.coverage(x,y,size,size,radius)
 elif top:cover=lambda x,y:p.coverage(x,y,size,2*size,radius)
 else:cover=lambda x,y:p.coverage(x,y+size,size,2*size,radius)
 return p.png(size,size,lambda x,y:(255,255,255,int(255*cover(x,y))))


def textures(p):
 out={'ring_%02d.png'%k:arc(p,RING,10,k/20.0) for k in range(21)}
 out['sheet_bg.png']=corner_texture(p,240,102,True,False)
 for name,top,bottom in (('row_only',True,True),('row_first',True,False),('row_last',False,True)):out[name+'.png']=corner_texture(p,160,43,top,bottom)
 return out


BOX='DialogExtendedProgressBar.xml'
LANDSCAPE_MARKER='Kodi-iOS player controls: background box'


def hidden_box(marker):
 """Kodi's background progress box, never drawn: 30 and 31 are buttons so Python can read their labels from Kodi."""
 font='p_cap' if 'portrait' in marker else 'font_mini'
 return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s: Kodi background progress, never drawn -->\n'
         '<window><controls><control type="group"><left>-4000</left><top>-4000</top><width>10</width><height>10</height><visible>false</visible>'
         '<control type="button" id="30"><width>900</width><height>10</height><font>%s</font><texturefocus /><texturenofocus /></control>'
         '<control type="button" id="31"><width>900</width><height>10</height><font>%s</font><texturefocus /><texturenofocus /></control>'
         '<control type="progress" id="32"><width>10</width><height>10</height><texturebg /><lefttexture /><midtexture /><righttexture /></control>'
         '</control></controls></window>\n')%(marker,font,font)


# Files of the removed activity pill that earlier builds wrote into the skin (portrait.write deletes them).
OBSOLETE=('Custom_1187_Activity.xml','IOSActivity.xml')


def files(p):
 out={p.FOLDER+'/'+BOX:hidden_box('Kodi-iOS portrait '+p.REVISION).encode(),'1080i/'+BOX:hidden_box(LANDSCAPE_MARKER).encode()}
 for name,data in textures(p).items():out['extras/portrait/'+name]=data
 return out
