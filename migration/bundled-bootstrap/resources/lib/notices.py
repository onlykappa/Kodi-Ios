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
import drivelibrary
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

# ---- Each message's part of kodi.log (owner, build 159: "when i tap a notification it brings me to that log") ----
# Kodi starts a new kodi.log at every launch, so the lines are copied next to the message as soon as it arrives.
import re
LOG_LINE=re.compile(r'^\ufeff?(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.(\d{3}) T:\d+\s+(\w+) <[^>]*>: ?(.*)$')
# Kodi's 'has been asked to focus, but it can't' is skin navigation (a hidden control), never the cause of a message
# (owner, build 191: an AllDebrid failure showed one as "What happened").
NOISE=('[GIN]','JSONRPC Server:','Touch at ','Tap at ','Click at ','has been asked to focus, but it can')
ANSI=re.compile(r'\x1b?\[\d+(?:;\d+)*m')
TROUBLE=re.compile(r'\b(fail\w*|errors?|paused|skipped|refused|unavailable|cannot|could not|denied|missing|timed out)\b')
def logs(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap/notice-logs'

def parse_log(text):
 """kodi.log text -> [{'time','level','text','more':[continuation lines]}] (a Python error report is one record)."""
 records=[]
 for line in text.splitlines():
  m=LOG_LINE.match(line)
  if m:
   try:when=time.mktime(time.strptime(m.group(1),'%Y-%m-%d %H:%M:%S'))+int(m.group(2))/1000.0
   except (ValueError,OverflowError):continue
   records.append({'time':when,'level':m.group(3).lower(),'text':ANSI.sub('',m.group(4)).strip(),'more':[]})
  elif records and line.strip():records[-1]['more'].append(line.strip())
 return records

def plain_record(record):
 """One record in a sentence: a Python error report becomes 'RuntimeError: … (library_status.py, line 39)'."""
 more=record.get('more') or []
 error=next((l for l in reversed(more) if re.match(r'^[A-Za-z_.]+(Error|Exception|Stop|Exit)\b',l)),'')
 if not error:
  contents=next((l for l in more if l.startswith('Error Contents:')),'')
  error=contents[len('Error Contents:'):].strip()
 where=[re.search(r'([^/"]+\.py)", line (\d+)',l) for l in more]
 where=[w for w in where if w and not w.group(1).startswith('<')]
 if error:return error+(' (%s, line %s)'%(where[-1].group(1),where[-1].group(2)) if where else '')
 return record['text']

GENERIC={'kodi','automatic','setup','recovery','check','information','more','with','from','this','that','have','will'}
ROUTINE=('listing cache','portrait files checked','startup:','background: may sleep')
def excerpt(records,when,title='',before=90,after=1,limit=30):
 """The records that explain a message at `when`, from `before` seconds before it to `after` seconds after: every
 error; warnings that name the message's add-on (title words, not generic ones); Kodi iOS lines from the last 15
 seconds that report trouble. Elementum's web server and its own info lines, touch tracing and routine lines are left out, the bare 'EXCEPTION:' line before a
 Python error report is dropped, and repeats are merged (count). The newest `limit`, oldest first."""
 words={w.lower() for w in re.findall(r'[A-Za-z]{4,}',title or '')}-GENERIC
 def wanted(r):
  if not when-before<=r['time']<=when+after or any(n in r['text'] for n in NOISE):return False
  low=r['text'].lower()
  if 'preparation' in words and not ('preparation' in low or 'prepare_cloud.py' in str(r.get('more','')) or 'prepare_downloads.py' in str(r.get('more',''))):return False
  if r['level'] in ('error','fatal'):return not (low.startswith('exception:') and not r['more'])
  if any(n in low for n in ROUTINE):return False
  inner=re.search(r'\b(INFO|NOTI|DEBU|WARN|ERRO|FATA)\b',r['text'])
  if inner and (inner.group(1) in ('INFO','NOTI','DEBU') or 'logAlerts' in r['text']):return False   # Elementum's own levels
  if re.match(r'^\[[a-z0-9_.]+\]',r['text']) and not inner and not TROUBLE.search(low):return False   # an add-on's chatter
  if 'kodi ios' in low:return r['time']>=when-15 and (r['level']!='info' or TROUBLE.search(low))
  return r['level']=='warning' and any(w in low for w in words)
 out=[]
 for r in records:
  if not wanted(r):continue
  key=(r['level'],plain_record(r))
  same=next((o for o in out if (o['level'],plain_record(o))==key),None)
  if same:out.remove(same);r=dict(r,count=same.get('count',1)+1)
  out.append(r)
 return out[-limit:]

def attach_logs(profile,log_path,now=None,settle=2,window=900):
 """Copy each new message's part of kodi.log next to it (notice-logs/<id>.json). A message gets its lines once,
 `settle` seconds after it arrived (Kodi writes the error report first, the pop-up after); older than `window`
 seconds it gets none (its lines may be in a previous launch's log). Returns how many were attached."""
 now=time.time() if now is None else now
 items=load(profile);due=[i for i in items if 'log' not in i and now-window<=i.get('time',0)<=now-settle]
 if not due:return 0
 try:
  with open(log_path,'rb') as handle:
   handle.seek(0,2);size=handle.tell();handle.seek(max(0,size-2*1024*1024))
   records=parse_log(handle.read().decode('utf-8','replace'))
 except OSError:records=[]
 folder=logs(profile);folder.mkdir(parents=True,exist_ok=True)
 for item in due:
  lines=excerpt(records,item['time'],item.get('title',''))
  item['log']=bool(lines)
  if lines:(folder/(item['id']+'.json')).write_text(json.dumps([dict(r,more=r['more'][:40]) for r in lines]),encoding='utf-8')
 keep={i['id']+'.json' for i in items}
 for path in folder.glob('*.json'):
  if path.name not in keep:path.unlink(missing_ok=True)
 current=load(profile)    # a message added meanwhile stays; only the attached flags are written back
 marks={i['id']:i['log'] for i in due}
 for i in current:
  if i.get('id') in marks:i['log']=marks[i['id']]
 save(profile,current);return len(due)

def log_of(profile,item):
 """The records copied for a message, or []."""
 if not item.get('log'):return []
 try:return json.loads((logs(profile)/(item['id']+'.json')).read_text(encoding='utf-8'))
 except (OSError,ValueError,KeyError):return []

def unread(profile):return sum(1 for i in load(profile) if not i.get('read'))

def mark_all_read(profile):
 items=load(profile)
 if any(not i.get('read') for i in items):save(profile,[dict(i,read=True) for i in items])

def clear(profile):
 save(profile,[])
 for path in logs(profile).glob('*.json'):path.unlink(missing_ok=True)

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
  out.append({'id':t.get('id',''),'title':drivelibrary.display_title(t.get('name','')),'progress':progress,'paused':paused,
              'sent':done,'total':size,'rate':0 if paused else rate,'eta_s':(size-done)/rate if rate>0 and not paused else 0,
              'line':'%d%%  ·  %s of %s'%(progress,size_text(done),size_text(size)),
              'speed':'Paused' if paused else ('%.1f MB/s  ·  %s'%(rate/1024**2,eta_text((size-done)/rate)) if rate>0 else 'Waiting for peers')})
 return out

def uploads(profile):
 """The Google Drive upload in progress (driveupload records it), and a download going straight to Drive through
 AllDebrid (debrid_drive), for the Uploading card, the activity pill and Library status."""
 out=[]
 try:state=json.loads((Path(profile)/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):state={}
 now=state.get('current') if isinstance(state,dict) else None
 if now and now.get('total'):
  progress=100.0*now.get('sent',0)/now['total']
  out.append({'title':drivelibrary.display_title(now.get('name','')),'folder':now.get('folder',''),'progress':progress,'source':'phone',
              'line':'%d%%  ·  %s of %s'%(progress,size_text(now.get('sent',0)),size_text(now['total']))})
 try:
  import debrid_drive
  jobs=[j for j in debrid_drive.load(profile).get('jobs',[]) if j.get('status') not in ('done','failed')]
  copy_hash=jobs[0].get('hash','') if jobs else ''   # the job debrid_drive.step works on (long press › Cancel)
  for d in debrid_drive.uploads(profile):
   progress=100.0*d.get('sent',0)/d['total']
   import prepare_downloads
   rate=float(d.get('rate') or 0);eta=prepare_downloads.eta_text(d.get('eta_s') or 0)
   speed='%.1f MB/s'%(rate/1024**2) if rate else ''
   if d.get('stage')=='fetching':
    line='AllDebrid is fetching it · %d%%'%progress;short=line
   else:
    line='  ·  '.join(x for x in ('%d%%'%progress,'%s of %s'%(size_text(d.get('sent',0)),size_text(d['total'])),speed,eta) if x)
    short=' · '.join(x for x in ('%d%%'%progress,speed,eta) if x)
   out.append({'title':drivelibrary.display_title(d.get('name','')),'folder':d.get('folder',''),'progress':progress,'line':line,
               'short':short,'source':'debrid','hash':copy_hash,'sent':d.get('sent',0),'total':d['total'],'rate':rate,'eta':eta,'stage':d.get('stage','')})
 except Exception as error:_quiet('notices:debrid',error)
 return out

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
 import prepare_downloads
 count=unread(profile);active=any(not d['paused'] for d in downloads(get)) or bool(uploads(profile)) or any(c.get('running') for c in prepare_downloads.cards(profile))
 return (str(min(count,99)) if count else '','true' if active else '')

def publish(window,profile,wait,busy=lambda:False,every=3,log_path=None):
 """Keep the bell's Home properties current for the session (not while a video plays: the bell is hidden). Pop-ups
 Kodi recorded are taken in first, also the ones from before the service started (startup failures)."""
 last=None
 while not wait(every):
  try:ingest(profile)
  except Exception as error:_quiet('notices:152',error)
  if log_path:
   try:attach_logs(profile,log_path)
   except Exception as error:_quiet('notices:attach',error)
  if busy():continue
  try:now=badge(profile)
  except Exception:continue
  if now!=last:
   window.setProperty('Notices.Unread',now[0]);window.setProperty('Notices.Active',now[1]);last=now

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass
