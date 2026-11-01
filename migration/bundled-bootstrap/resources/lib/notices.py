"""Notification center: what the app has to tell the owner, kept in one place instead of toasts.

Messages (Drive uploads, Play on TV refusals, Elementum restarts, new builds, problems) are kept in
addon_data/service.kodi.ios.bootstrap/notices.json, newest first, at most MAX. Live work (Elementum downloads from
its engine, the Drive upload in progress) is read when the page is open. The bootstrap service publishes the unread
count and whether a download runs as Home window properties for the bell (Notices.Unread, Notices.Active).
"""
import json,os,time,urllib.request
from pathlib import Path

MAX=50
ENGINE='http://127.0.0.1:65220'
KINDS=('download','drive','problem','update','info')
FILTERS={'all':KINDS,'downloads':('download','drive'),'problems':('problem',)}

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

def downloads(get=None):
 """Elementum's torrents that are still downloading or paused, for the Downloading cards."""
 get=get or (lambda url:urllib.request.urlopen(url,timeout=3).read())
 try:torrents=json.loads(get(ENGINE+'/torrents/list'))
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
