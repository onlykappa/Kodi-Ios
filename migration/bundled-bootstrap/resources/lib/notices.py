"""Notification center: what the app has to tell the owner, kept in one place instead of toasts.

Messages (Drive uploads, Play on TV refusals, Elementum restarts, new builds, problems) are kept in
addon_data/service.kodi.ios.bootstrap/notices.json, newest first, at most MAX. Live work (Elementum downloads from
its engine, the Drive upload in progress) is read when the page is open. The bootstrap service publishes the unread
count and whether a download runs as Home window properties for the bell (Notices.Unread, Notices.Active).

Every Kodi pop-up (any add-on's or Kodi's own toast) lands here too and is never shown: the portrait Kodi app (r10)
appends each one to toasts.jsonl in the same folder (creating it on a first start), and ingest() moves them into the
store (General, or Problems for warnings and errors).
"""
import json,os,time,urllib.request
from pathlib import Path

MAX=50
ENGINE='http://127.0.0.1:65220'
KINDS=('download','drive','problem','update','info','general')
FILTERS={'all':KINDS,'general':('general','info','update'),'downloads':('download','drive'),'problems':('problem',)}

def store(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap/notices.json'

def load(profile):
 try:items=json.loads(store(profile).read_text(encoding='utf-8'))
 except (OSError,ValueError):return []
 return [i for i in items if isinstance(i,dict) and i.get('title')] if isinstance(items,list) else []

def save(profile,items):
 path=store(profile);path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(items[:MAX],indent=1),encoding='utf-8');os.replace(temp,path)

def add(profile,kind,title,text='',action='',now=None):
 """Record a message (newest first). The same message within a minute is not repeated."""
 now=time.time() if now is None else now;kind=kind if kind in KINDS else 'info'
 items=load(profile)
 if items and items[0].get('title')==title and items[0].get('text')==text and now-items[0].get('time',0)<60:return items[0]
 item={'id':'%d-%d'%(int(now*1000),len(items)),'time':now,'kind':kind,'title':title,'text':text,'action':action,'read':False}
 save(profile,[item]+items);return item

def toasts(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap/toasts.jsonl'

def ingest(profile):
 """Move the pop-ups Kodi recorded (toasts.jsonl, one JSON object per line, oldest first) into the store. The file is
 renamed before it is read, so a pop-up Kodi writes meanwhile starts a new file and is taken next time. Returns how
 many were added."""
 source=toasts(profile);taken=source.with_suffix('.taking')
 try:
  if not taken.exists():os.replace(source,taken)
  lines=taken.read_text(encoding='utf-8',errors='replace').splitlines()
 except OSError:return 0
 added=0
 for line in lines:
  try:entry=json.loads(line)
  except ValueError:continue
  if not isinstance(entry,dict):continue
  title=str(entry.get('caption') or '').strip();text=str(entry.get('description') or '').strip()
  if not title and not text:continue
  kind='problem' if entry.get('type') in ('warning','error') else 'general'
  try:when=float(entry.get('time'))
  except (TypeError,ValueError):when=None
  add(profile,kind,title or 'Kodi',text,now=when);added+=1
 try:taken.unlink()
 except OSError:pass
 return added

def unread(profile):return sum(1 for i in load(profile) if not i.get('read'))

def mark_all_read(profile):
 items=load(profile)
 if any(not i.get('read') for i in items):save(profile,[dict(i,read=True) for i in items])

def clear(profile):save(profile,[])

def ago(then,now=None):
 seconds=max(0,(time.time() if now is None else now)-then)
 if seconds<60:return 'now'
 if seconds<3600:return '%dm'%(seconds//60)
 if seconds<86400:return '%dh'%(seconds//3600)
 return '%dd'%(seconds//86400)

def size_text(num):
 for unit,scale in (('GB',1024**3),('MB',1024**2),('KB',1024)):
  if num>=scale:return ('%.1f %s'%(num/scale,unit)) if unit=='GB' else '%d %s'%(num//scale,unit)
 return '%d B'%num

def eta_text(seconds):
 if seconds<=0:return ''
 if seconds<3600:return '%d min'%max(1,seconds//60)
 return '%dh %02dm'%(seconds//3600,(seconds%3600)//60)

_LIST={'at':-1e9,'data':None}
def torrent_list(get=None,ttl=2.0,clock=None):
 """Elementum's /torrents/list, shared for `ttl` seconds: the bell (every 3 s) and the background keep-alive (every
 5 s) asked the engine for it separately (performance pass). A custom get() always asks."""
 import time
 now=(clock or time.monotonic)()
 if get is None and _LIST['data'] is not None and now-_LIST['at']<ttl:return _LIST['data']
 data=json.loads((get or (lambda url:urllib.request.urlopen(url,timeout=3).read()))(ENGINE+'/torrents/list'))
 if get is None:_LIST.update(at=now,data=data)
 return data

def downloads(get=None):
 """Elementum's torrents that are still downloading or paused, for the Downloading cards."""
 try:torrents=torrent_list(get)
 except Exception:return []
 out=[]
 for t in torrents or []:
  progress=float(t.get('progress') or 0);status=str(t.get('status') or '')
  if progress>=100 or status.lower() in ('seeding','finished'):continue
  size=float(t.get('size_bytes') or 0);rate=float(t.get('download_rate') or 0)*1024  # engine reports KB/s
  done=size*progress/100;paused=status.lower()=='paused'
  out.append({'id':t.get('id',''),'title':t.get('name',''),'progress':progress,'paused':paused,
              'line':'%d%%  ·  %s of %s'%(progress,size_text(done),size_text(size)),
              'speed':'Paused' if paused else ('%.1f MB/s  ·  %s'%(rate/1024**2,eta_text((size-done)/rate)) if rate>0 else 'Waiting for peers')})
 return out

def uploads(profile):
 """The Google Drive upload in progress (driveupload records it), for the Uploading card."""
 try:state=json.loads((Path(profile)/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return []
 now=state.get('current') if isinstance(state,dict) else None
 if not now or not now.get('total'):return []
 progress=100.0*now.get('sent',0)/now['total']
 return [{'title':now.get('name',''),'folder':now.get('folder',''),'progress':progress,
          'line':'%d%%  ·  %s of %s'%(progress,size_text(now.get('sent',0)),size_text(now['total']))}]

def engine_action(command,torrent,get=None):
 """Pause, resume or cancel (delete, keeping nothing) one Elementum download from the page."""
 get=get or (lambda url:urllib.request.urlopen(url,timeout=5).read())
 path={'pause':'/torrents/pause/','resume':'/torrents/resume/','cancel':'/torrents/delete/'}[command]+torrent
 if command=='cancel':path+='?files=true&torrent=true'
 try:get(ENGINE+path);return True
 except Exception:return False

def note(kind,title,text='',action=''):
 """add() from any Kodi script (cast, updates, menus): the profile comes from Kodi. Never raises."""
 try:
  import xbmcvfs
  return add(xbmcvfs.translatePath('special://profile/'),kind,title,text,action)
 except Exception:return None

def badge(profile,get=None):
 """What the bell shows: (unread count as text, '' when none; 'true' while a download runs, else '')."""
 count=unread(profile);active=any(not d['paused'] for d in downloads(get)) or bool(uploads(profile))
 return (str(min(count,99)) if count else '','true' if active else '')

def publish(window,profile,wait,busy=lambda:False,every=3):
 """Keep the bell's Home properties current for the session (not while a video plays: the bell is hidden). Pop-ups
 Kodi recorded are taken in first, also the ones from before the service started (startup failures)."""
 last=None
 while not wait(every):
  try:ingest(profile)
  except Exception:pass
  if busy():continue
  try:now=badge(profile)
  except Exception:continue
  if now!=last:
   window.setProperty('Notices.Unread',now[0]);window.setProperty('Notices.Active',now[1]);last=now
