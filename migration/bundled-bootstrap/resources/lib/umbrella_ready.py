"""Umbrella's "getting ready to play" screen (its source_progress.xml window), redrawn by portrait/source_progress.xml.

Umbrella gives that window one block of text (textbox 2001), built in its sources.py while it resolves a source:
  [plot [CR][CR]] DEBRID-OR-SOURCE [CR] PROVIDER [CR] QUALITY [CR] info words [CR] NN - file name
all inside [COLOR] tags. While the window is up, the bootstrap service reads that text and publishes the parts as
Home window properties (IOSReady.*) for the badges and the source card. Whatever does not fit the pattern is
published as IOSReady.Text, and the page shows it as plain text, so nothing is hidden.
"""
import re

WINDOW='source_progress.xml'
PREFIX='IOSReady.'
KEYS=('Provider','Via','Quality','Size','Badges','File','Index','Text','Ready')
TAG=re.compile(r'\[/?(?:COLOR|B|I|UPPERCASE|LOWERCASE|CAPITALIZE)[^\]]*\]',re.I)
SIZE=re.compile(r'^\d+(?:\.\d+)?\s*[GMT]B$',re.I)
INDEX=re.compile(r'^(\d{1,3})\s*-\s*(.+)$')
QUALITIES={'4K','2160P','1080P','720P','SD','SCR','CAM','HD'}
# Badge spelling the page uses for common release words (anything else is shown as Umbrella wrote it).
BADGE={'DOLBY-VISION':'DOLBY VISION','DOLBYVISION':'DOLBY VISION','DV':'DOLBY VISION','HDR10+':'HDR10+','HDR10':'HDR10',
       'BLURAY':'BLU-RAY','BLU-RAY':'BLU-RAY','WEB-DL':'WEB-DL','WEBDL':'WEB-DL','WEBRIP':'WEBRIP','MULTI-LANG':'MULTI-LANG',
       'ATMOS':'ATMOS','TRUEHD':'TRUEHD','DTS-HD':'DTS-HD','DTS-X':'DTS:X','DD+':'DD+','HEVC':'HEVC','H265':'HEVC','X265':'HEVC',
       'AVC':'AVC','H264':'AVC','X264':'AVC','REMUX':'REMUX','HDR':'HDR','3D':'3D','10BIT':'10-BIT'}
MAX_BADGES=8
# Debrid and provider names as the services write them.
NAMES={'ALLDEBRID':'AllDebrid','REALDEBRID':'Real-Debrid','REAL-DEBRID':'Real-Debrid','PREMIUMIZE':'Premiumize','TORBOX':'TorBox',
       'EASYNEWS':'Easynews','OFFCLOUD':'Offcloud','DEBRIDLINK':'Debrid-Link','TORRENTIO':'Torrentio','COMET':'Comet',
       'MEDIAFUSION':'MediaFusion','JACKETTIO':'Jackettio','ORIONOID':'Orionoid','PLEX':'Plex','GDRIVE':'Google Drive'}
def service_name(text):
 return NAMES.get(text.upper().replace(' ',''),text.title() if text.isupper() else text)

def clean(text):
 return TAG.sub('',str(text or '')).replace('[CR]','\n')

def parse(text):
 """{'Provider','Via','Quality','Size','Badges','File','Index','Text','Ready'} from Umbrella's resolve text.
 Ready is 'true' only when the source lines were found; otherwise Text carries everything."""
 lines=[l.strip() for l in clean(text).split('\n')]
 lines=[l for l in lines if l]
 out=dict.fromkeys(KEYS,'')
 # The source block is the last five lines when the last one is "NN - name".
 if len(lines)>=5 and INDEX.match(lines[-1]) and lines[-3].upper() in QUALITIES:
  debrid,provider,quality,info,last=lines[-5:]
  number,name=INDEX.match(last).groups()
  words=[w for w in re.split(r'[\s|]+',info) if w]
  size=next((w for w in words if SIZE.match(w)),'')
  if not size:
   joined=re.search(r'(\d+(?:\.\d+)?)\s*([GMT]B)\b',info,re.I)
   size=(joined.group(1)+' '+joined.group(2).upper()) if joined else ''
  badges=[]
  for w in words:
   if SIZE.match(w) or re.fullmatch(r'\d+(?:\.\d+)?|[GMT]B',w,re.I):continue
   b=BADGE.get(w.upper(),w.upper())
   if b not in badges and b!=quality.upper():badges.append(b)
  out.update({'Provider':service_name(debrid),'Via':service_name(provider),
              'Quality':'4K' if quality.upper() in ('4K','2160P') else quality.upper(),'Size':size.upper().replace('GB',' GB').replace('  ',' ').strip(),
              'Badges':'   '.join(badges[:MAX_BADGES]),'File':name,'Index':number,'Ready':'true'})
  out['Text']=''
 elif len(lines)>=3 and INDEX.match(lines[-2]) and re.fullmatch(r'\d+(?:\.\d+)?\s*[GMT]B',lines[-1],re.I):
  # Umbrella's other progress layouts: SOURCE [CR] NN - name [CR] size GB (no quality line, so no badges)
  number,name=INDEX.match(lines[-2]).groups()
  out.update({'Provider':service_name(lines[-3]),'File':name,'Index':number,'Size':lines[-1].upper().replace('GB',' GB').replace('  ',' ').strip(),
              'Ready':'true'})
 else:
  # "Resolving...name", the source counts while scraping, or a layout we do not know.
  out['Text']='\n'.join(lines)
 return out

def watch(visible,read_text,set_property,clear_property,wait,interval=0.25):
 """While Umbrella's window is up, keep IOSReady.* in step with its text. Callables: visible() -> bool,
 read_text() -> str (textbox 2001), set_property(key, value) / clear_property(key) on the Home window,
 wait(seconds) -> True when Kodi is exiting."""
 last=None
 while not wait(interval if last is not None else 1.0):
  if not visible():
   if last is not None:
    for key in KEYS:clear_property(PREFIX+key)
    last=None
   continue
  text=read_text() or ''
  if text==last:continue
  last=text
  for key,value in parse(text).items():set_property(PREFIX+key,value)
