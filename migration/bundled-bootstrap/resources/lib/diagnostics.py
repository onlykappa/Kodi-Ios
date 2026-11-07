"""Small, structured support records with build identity and redacted failure detail.

Never reads credentials, account stores, HTTP bodies/headers or full queue items.
The same records go into kodi.log and the optional Files diagnostic export.
"""
import collections,datetime,json,os,re,shutil,threading,time,traceback,uuid
from pathlib import Path

SCHEMA=1
PRIVATE=re.compile(r'(?i)(?:authorization|cookie|password|passwd|secret|token|api[_-]?key|client[_-]?secret|signed[_-]?url|refresh|magnet|session[_-]?url)')
URL=re.compile(r'(?i)\b(?:https?|plugin|ftp|smb)://[^\s\]<>"\']+(?:\|[^\s\]<>"\']+)?')
_SECRET_VALUE=re.compile(r'''(?ix)(["']?(?:authorization|proxy-authorization|cookie|set-cookie|password|passwd|access_token|refresh_token|token|api[_-]?key|client_secret|alldebridtoken|github_token)["']?\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;}]+)''')
_BEARER=re.compile(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*')
_HEADER=re.compile(r'(?im)(\b(?:authorization|proxy-authorization|cookie|set-cookie)\s*:\s*)[^\r\n]+')
_MAGNET=re.compile(r'(?i)magnet:\?[^\s"\']+')
_context={'build':'unknown','commit':'unknown','session':uuid.uuid4().hex[:12]}
_lock=threading.Lock()

def redact(value,limit=2000):
 text=str(value)
 marker='Kodi iOS diagnostic '
 at=text.find(marker)
 if at>=0:
  try:record=json.loads(text[at+len(marker):])
  except ValueError:pass
  else:return text[:at+len(marker)]+json.dumps(safe(record),sort_keys=True,separators=(',',':'))+('\n' if text.endswith('\n') else '')
 text=_HEADER.sub(lambda m:m.group(1)+'[redacted]',text)
 text=URL.sub('[URL redacted]',text)
 text=_MAGNET.sub('[magnet redacted]',text)
 text=_BEARER.sub(r'\1 [redacted]',text)
 text=_SECRET_VALUE.sub(lambda m:m.group(1)+'[redacted]',text)
 return text[:limit] if limit else text

def safe(value):
 if isinstance(value,dict):return {str(k):('[redacted]' if PRIVATE.search(str(k)) else safe(v)) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [safe(v) for v in value[:100]]
 if value is None or isinstance(value,(int,float,bool)):return value
 return redact(value)

def build_info(root):
 """build.json is generated from the IPA workflow, never from updater availability."""
 try:data=json.loads((Path(root)/'build.json').read_text())
 except (OSError,ValueError):data={}
 if not isinstance(data,dict):data={}
 result={key:data[key] for key in ('build','commit','source_ref','built_at','workflow_run','workflow_attempt','frameworks') if key in data}
 try:result['build']=str(int(result.get('build') or 0)) if int(result.get('build') or 0)>0 else 'unknown'
 except (ValueError,TypeError):result['build']='unknown'
 result.setdefault('commit','unknown')
 return safe(result)

def configure(root,profile=None,clock=time.time):
 global _context
 context=dict(build_info(root),schema=SCHEMA,session=uuid.uuid4().hex[:12],started_utc=datetime.datetime.fromtimestamp(clock(),datetime.timezone.utc).isoformat())
 with _lock:_context=context
 if profile:
  dest=Path(profile)/'addon_data/service.kodi.ios.bootstrap/diagnostic-session.json'
  try:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(context,sort_keys=True)+'\n')
  except OSError:pass
 return dict(context)

def attach(root,profile):
 """UI scripts use the running service's launch ID (Kodi gives scripts separate interpreters)."""
 global _context
 identity=build_info(root)
 session=_read(Path(profile)/'addon_data/service.kodi.ios.bootstrap/diagnostic-session.json')
 if session.get('build')==identity['build'] and session.get('commit')==identity['commit']:
  with _lock:_context=safe(session)
  return dict(_context)
 return configure(root)

def event(write,component,event_name,**fields):
 with _lock:record=dict(_context)
 record.update(component=component,event=event_name,**safe(fields))
 # INFO records are available without enabling verbose Kodi debug (which records URLs).
 write('Kodi iOS diagnostic '+json.dumps(record,sort_keys=True,separators=(',',':')))

def exception(write,component,error,**fields):
 chain=[];seen=set();current=error
 while current is not None and id(current) not in seen and len(chain)<5:
  seen.add(id(current))
  detail={'type':type(current).__name__,'message':redact(current)}
  for key in ('errno','winerror','code','status'):
   value=getattr(current,key,None)
   if isinstance(value,(int,str)):detail[key]=safe(value)
  # File + function + line locate the failure without locals or source-line secrets.
  detail['frames']=[dict(file=os.path.basename(frame.filename),line=frame.lineno,function=frame.name) for frame in traceback.extract_tb(current.__traceback__)[-12:]]
  reason=getattr(current,'reason',None)
  if reason is not None and not isinstance(reason,BaseException):detail['reason']=redact(reason)
  chain.append(detail)
  current=(reason if isinstance(reason,BaseException) else None) or current.__cause__ or current.__context__
 event(write,component,'failure',errors=chain,**fields)

def _read(path):
 try:
  if path.stat().st_size>4*1024*1024:return {}
  value=json.loads(path.read_text())
  return value if isinstance(value,dict) else {}
 except (OSError,ValueError):return {}

def snapshot(profile,clock=time.time):
 """Allowlisted queue summary: no source IDs, URL/session fields, filenames or tokens."""
 folder=Path(profile)/'addon_data/service.kodi.ios.bootstrap';result={}
 for label,name in (('preparation','airplay-preparation.json'),('debrid','debrid-drive.json'),('uploads','drive-uploads.json')):
  state=_read(folder/name)
  if not state:continue
  jobs=state.get('jobs') or []
  jobs=list(jobs.values()) if isinstance(jobs,dict) else jobs if isinstance(jobs,list) else []
  item={'statuses':dict(collections.Counter(str(j.get('status','unknown')) for j in jobs if isinstance(j,dict))),
        'jobs':len(jobs),'cleanup_pending':len(state.get('staging_cleanup') or []),
        'resumable_sessions':len(state.get('sessions') or {}),'verified_files':len(state.get('verified') or {})}
  current=state.get('current') or {}
  if isinstance(current,dict):
   item['current']={key:current[key] for key in ('stage','progress','indeterminate','queued','running','done','sent','total','speed','bytes','size') if key in current}
   if isinstance(current.get('updated'),(int,float)):item['current']['age_s']=max(0,int(clock()-current['updated']))
  retry=[j.get('retry_after',0) for j in jobs if isinstance(j,dict) and isinstance(j.get('retry_after'),(int,float)) and j['retry_after']>clock()]
  if retry:item.update(waiting_for_retry=len(retry),next_retry_s=max(0,int(min(retry)-clock())))
  result[label]=item
 runtime=_read(folder/'preparation-runtime.json')
 if runtime:
  result['worker']={k:runtime[k] for k in ('phase','known','read_bytes','last_read','read_error') if k in runtime}
  if isinstance(runtime.get('updated'),(int,float)):result['worker']['heartbeat_age_s']=max(0,int(clock()-runtime['updated']))
 try:result['storage']={'free_bytes':shutil.disk_usage(profile).free}
 except OSError:pass
 return safe(result)

def watch(profile,write,wait,settings=lambda:{},every=60):
 """One bounded summary per minute; continues through probing before numeric progress exists."""
 while True:
  try:event(write,'runtime','snapshot',queues=snapshot(profile),settings=settings())
  except Exception as error:exception(write,'diagnostics',error)
  if wait(every):break

def export(root,profile,log_folder,destination,clock=time.time):
 """Save a separate, redacted support log. Originals remain available to Kodi."""
 identity=build_info(root);session=_read(Path(profile)/'addon_data/service.kodi.ios.bootstrap/diagnostic-session.json')
 stamp=datetime.datetime.fromtimestamp(clock(),datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 folder=Path(destination);folder.mkdir(parents=True,exist_ok=True)
 dest=folder/('Kodi-build-%s-%s.log'%(identity['build'],stamp))
 with dest.open('w',encoding='utf-8') as out:
  out.write('=== Kodi iOS support log ===\n')
  out.write('Installed build: %s | commit: %s\n'%(identity['build'],identity['commit']))
  out.write('Build metadata: '+json.dumps(identity,sort_keys=True)+'\n')
  out.write('Session: '+json.dumps(safe(session),sort_keys=True)+'\n')
  out.write('Exported UTC: '+stamp+'\n')
  # Put the preceding launch first, current launch last; preserve original timestamps.
  for name in ('kodi.old.log','kodi.log'):
   path=Path(log_folder)/name
   if not path.is_file():continue
   out.write('\n=== %s ===\n'%name)
   with path.open('r',encoding='utf-8',errors='replace') as source:
    size=path.stat().st_size
    if size>32*1024*1024:
     source.seek(size-32*1024*1024);source.readline()
     out.write('[Earlier log data omitted: last 32 MiB retained]\n')
    for line in source:out.write(redact(line,limit=0))
  out.write('\n=== Current queue summary (no credentials or source URLs) ===\n')
  out.write(json.dumps(snapshot(profile,clock),sort_keys=True)+'\n')
 return dest


def log_exception(xbmc,component,error,**fields):
 exception(lambda message:xbmc.log(message,xbmc.LOGWARNING),component,error,**fields)
