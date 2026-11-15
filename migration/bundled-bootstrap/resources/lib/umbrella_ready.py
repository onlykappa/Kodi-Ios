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

# ISSUE-280 (owner-approved board S1, docs/design/stream-opening-mockups.html): the line under the card's bar says which
# step the open is on, with real numbers only. IOSReady.Line / Right / Fill (0-100, empty: the bar slides) / Slow.
STAGE_KEYS=('Line','Right','Fill','Slow')
TARGET_BLOCKS=3          # remote_media asks for the first two blocks and the last one (WARM_BLOCKS + 1)
SLOW_AFTER=10            # seconds before the slow-source note may show
SLOW_BELOW=1.5*1024*1024 # bytes per second under which the note says so

def stage(provider,elapsed,linked,cache,since_link=None):
 """The three approved stages. provider: 'AllDebrid' (the card's name); elapsed: seconds since the source was known;
 linked: True once the debrid link arrived; cache: remote_media stats of the source Kodi reads ({} when none);
 since_link: seconds since the link arrived (for the speed). Returns {Line, Right, Fill, Slow}."""
 who=provider or 'the source'
 out={'Line':'','Right':'%d s'%max(0,int(elapsed)),'Fill':'','Slow':''}
 if not linked:
  out['Line']='Getting the link from %s\u2026'%who
  return out
 size=int((cache or {}).get('block_size') or 0)
 if cache and cache.get('kodi') and size:
  target=TARGET_BLOCKS*size;have=min(int(cache.get('cached_blocks') or 0)*size,target)
  if have<target:
   mb=1024*1024;pct=int(100*have/target)
   out.update(Line='Opening the video \u00b7 %d of %d MB'%(have//mb,target//mb),Right='%d%%'%pct,Fill=str(pct))
  else:
   out['Line']='Starting the video\u2026'
  if elapsed>=SLOW_AFTER and since_link and since_link>=2 and have:
   speed=have/since_link
   if speed<SLOW_BELOW:out['Slow']='%s is sending it slowly right now (%.1f MB/s).'%(who,speed/(1024*1024))
  return out
 out['Line']='Starting the video\u2026'
 return out

def watch(visible,read_text,set_property,clear_property,wait,interval=0.25,linked=None,cache=None,clock=None):
 """While Umbrella's window is up, keep IOSReady.* in step with its text. Callables: visible() -> bool,
 read_text() -> str (textbox 2001), set_property(key, value) / clear_property(key) on the Home window,
 wait(seconds) -> True when Kodi is exiting. ISSUE-280: linked() -> the current debrid link record (a string that
 changes when Umbrella unlocks a link), cache() -> remote_media stats; with them the stage line is kept too."""
 import time
 clock=clock or time.monotonic
 last=None;known=None;link_at=None;start_link=None;shown={}
 while not wait(interval if last is not None else 1.0):
  if not visible():
   if last is not None:
    for key in KEYS+STAGE_KEYS:clear_property(PREFIX+key)
    last=None;known=None;link_at=None;shown={}
   continue
  if last is None and linked:
   try:start_link=linked()
   except Exception:start_link=None
  text=read_text() or ''
  if text!=last:
   last=text;parts=parse(text)
   for key,value in parts.items():set_property(PREFIX+key,value)
   if parts['Ready']=='true' and known is None:known=clock()
  if known is None or not linked:continue
  try:
   now=clock()
   if link_at is None and linked()!=start_link:link_at=now
   stats={}
   if link_at is not None and cache:
    try:stats=cache() or {}
    except Exception:stats={}
   values=stage(parse(last)['Provider'],now-known,link_at is not None,stats,None if link_at is None else now-link_at)
   for key,value in values.items():
    if shown.get(key)!=value:set_property(PREFIX+key,value);shown[key]=value
  except Exception:pass
