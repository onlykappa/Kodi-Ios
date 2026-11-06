"""Step 3 of kept downloads: one indexed MP4, at source resolution, in the SAME Drive file.

The service scans app-managed Movies/TV Shows at startup and after uploads. Work is serialized with
the uploader/scanner, paused during playback, and checkpointed. Source bytes stay on Drive until a
validated local result is uploaded in place. No permanent AirPlay variant, source-ID switch or extra folder.
"""
import ctypes,hashlib,json,os,re,shutil,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import driveupload,drivelibrary,library_scan

PROFILE='source-resolution-mp4-v1'
PROPERTY='kodiAirPlayProfile'
CHECKSUM_PROPERTY='kodiAirPlayMD5'
FILE='airplay-preparation.json'
RESERVE=256*1024*1024
# Owner (build 157): "we need to ensure storage is never an issue". Preparation never takes the phone below this, and
# a video starts only when its whole working set (the Drive file plus the prepared copy) fits above it.
KEEP_FREE=5*1024**3

def folder_bytes(path):
 try:return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
 except OSError:return 0

def space_needed(item,streaming=False):
 """Phone space one video takes while it is prepared: the prepared copy (about the Drive file's size: the picture is
 copied, not re-encoded) and a margin, plus what must stay free for the owner. Without streaming (KodiAirPlay before
 r14) the Drive file is downloaded first as well, so twice the size."""
 size=int(item.get('size') or 0)
 return (1 if streaming else 2)*size+RESERVE+KEEP_FREE
CALLBACK=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_int,ctypes.c_double,ctypes.c_double,ctypes.c_void_p)

def location(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap'/FILE
def load(profile):return drivelibrary.load_json(str(location(profile)),{'jobs':{},'sessions':{},'last_scan':0})
def save(profile,state):drivelibrary.save_json(str(location(profile)),state)
def ready(item):
 props=item.get('appProperties') or {}
 return bool(item.get('md5Checksum')) and props.get(PROPERTY)==PROFILE and props.get(CHECKSUM_PROPERTY)==item['md5Checksum'].lower()
def metadata(drive,item_id):
 status,headers,body=drive.call('GET',driveupload.API+'/'+urllib.parse.quote(str(item_id),safe='')+'?fields=id,name,size,md5Checksum,version,mimeType,appProperties,trashed')
 if status!=200:raise RuntimeError('Drive file check: HTTP %d'%status)
 item=json.loads(body)
 if item.get('trashed') or not item.get('id') or not item.get('md5Checksum') or int(item.get('size') or 0)<=0:
  raise RuntimeError('Drive video is unavailable or incomplete')
 item['_etag']=headers.get('ETag') or headers.get('etag') or ''
 return item
def identity(item):return (str(item['id']),str(item.get('md5Checksum','')).lower(),int(item.get('size') or 0),str(item.get('version') or ''))
def key(item):return hashlib.sha256(('|'.join(map(str,identity(item)[:3]))).encode()).hexdigest()[:32]

class Native:
 def __init__(self,lib):
  if not hasattr(lib,'kodi_airplay_prepare') or not hasattr(lib,'kodi_airplay_probe'):
   raise RuntimeError('Install the build with download preparation support')
  self.lib=lib
  # r14: probe/prepare read an http://127.0.0.1 source, so a Drive file is streamed, never downloaded first.
  self.streams=bool(hasattr(lib,'kodi_airplay_prepare_streams') and lib.kodi_airplay_prepare_streams()==1)
  lib.kodi_airplay_probe.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_probe.restype=ctypes.c_int
  lib.kodi_airplay_prepare.argtypes=[ctypes.c_char_p,ctypes.c_char_p,CALLBACK,ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
  lib.kodi_airplay_prepare.restype=ctypes.c_int
 def probe(self,path):
  out=ctypes.create_string_buffer(1024)
  if self.lib.kodi_airplay_probe(os.fsencode(str(path)),out,len(out))<0:raise RuntimeError('Video could not be inspected')
  return json.loads(out.value.decode())
 def convert(self,source,output,keep_going,progress):
  error=ctypes.create_string_buffer(512);callback_error=[]
  cpu_clock=getattr(time,'thread_time',time.process_time)
  window=[time.monotonic(),cpu_clock()]
  def update(stage,done,total,context):
   try:
    if not keep_going():return 0
    # Offline work can yield: keep this worker around half a CPU core instead of recreating the
    # previous iOS CPU-resource kill while repackaging a large movie in the background.
    wall=time.monotonic()-window[0];cpu=cpu_clock()-window[1]
    if wall>=0.1:
     time.sleep(min(0.1,max(0.0,2*cpu-wall)))
     window[:]=[time.monotonic(),cpu_clock()]
    progress(stage,done,total);return 1
   except Exception as error:callback_error.append(error);return 0
  callback=CALLBACK(update) # keep Python's callback alive until the synchronous native job exits
  r=self.lib.kodi_airplay_prepare(os.fsencode(str(source)),os.fsencode(str(output)),callback,None,error,len(error))
  if callback_error:raise callback_error[0]
  if r==-2:raise driveupload.Stop('Preparation paused')
  if r:raise RuntimeError(error.value.decode('utf-8','replace') or 'Preparation failed; existing file retained')

def download(drive,item,path,keep_going,progress,context=None,open_url=None):
 """Read once into one working file, resuming exact ranges. Never buffer a movie in RAM."""
 size=int(item['size']);offset=os.path.getsize(path) if os.path.isfile(path) else 0
 if offset>size:os.remove(path);offset=0
 if offset==size:return
 request=urllib.request.Request(driveupload.API+'/'+urllib.parse.quote(item['id'],safe='')+'?alt=media',
  headers={'Authorization':'Bearer '+drive.token(),'Range':'bytes=%d-'%offset})
 if open_url is None:
  class NoRedirect(urllib.request.HTTPRedirectHandler):
   def redirect_request(self,*args,**kwargs):return None
  opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context))
  open_url=lambda req:opener.open(req,timeout=30)
 with open_url(request) as response:
  status=response.status
  if offset and status==200:offset=0
  elif status not in (200,206):raise RuntimeError('Drive download: HTTP %d'%status)
  if status==206:
   expected='bytes %d-'%offset
   value=response.headers.get('Content-Range','')
   if not value.startswith(expected) or not value.endswith('/%d'%size):raise RuntimeError('Drive returned the wrong byte range')
  with open(path,'ab' if offset else 'wb') as output:
   while True:
    if not keep_going():raise driveupload.Stop('Preparation paused')
    chunk=response.read(1024*1024)
    if not chunk:break
    if offset+len(chunk)>size:raise RuntimeError('Drive download size changed')
    output.write(chunk);offset+=len(chunk);progress(offset,size)
 if offset!=size:raise RuntimeError('Drive download incomplete; will resume')

def replace(drive,source,path,sessions,commit,keep_going,progress):
 """Resumable files.update, never files.create. Commit to the original ID only after local validation.

Fresh version/checksum checks prevent overwriting a changed source; conditional headers are used
when Drive returns an ETag. A completed-but-unacknowledged upload is recovered by its content hash.
"""
 size=os.path.getsize(path);digest=driveupload.checksum(path,keep_going,pace=1)
 current=metadata(drive,source['id'])
 if int(current['size'])==size and current['md5Checksum'].lower()==digest:return current
 if identity(current)!=identity(source):raise RuntimeError('Drive source changed; preparation will rescan')
 slot=key(source);session=sessions.get(slot)
 if session and (session.get('size')!=size or session.get('md5')!=digest):session=None
 offset=0
 if session:
  status,headers,body=drive.call('PUT',session['url'],b'',{'Content-Range':'bytes */%d'%size})
  if status in (200,201):
   result=metadata(drive,source['id'])
   if int(result['size'])!=size or result['md5Checksum'].lower()!=digest:raise RuntimeError('Prepared Drive file checksum differs; working files kept')
   sessions.pop(slot,None);commit();return result
  if status==308:offset=driveupload._next_offset(headers)
  else:session=None
 if not session:
  name=os.path.splitext(source['name'])[0]+'.mp4'
  headers={'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Length':str(size),'X-Upload-Content-Type':'video/mp4'}
  if current.get('_etag'):headers['If-Match']=current['_etag']
  status,answer,_=drive.call('PATCH',driveupload.UPLOAD+'/'+urllib.parse.quote(source['id'],safe='')+'?uploadType=resumable&fields=id,size,md5Checksum',
   json.dumps({'name':name,'mimeType':'video/mp4'}).encode(),headers)
  url=answer.get('Location') or answer.get('location')
  if status!=200 or not url:raise RuntimeError('Prepared file upload start: HTTP %d'%status)
  session={'url':url,'size':size,'md5':digest};sessions[slot]=session;commit()
 with open(path,'rb') as stream:
  stream.seek(offset)
  while offset<size:
   if not keep_going():raise driveupload.Stop('Preparation upload paused')
   data=stream.read(min(driveupload.CHUNK,size-offset));end=offset+len(data)
   headers={'Content-Range':'bytes %d-%d/%d'%(offset,end-1,size)}
   if end==size:
    fresh=metadata(drive,source['id'])
    if identity(fresh)!=identity(source):raise RuntimeError('Drive source changed during preparation; not replaced')
    if fresh.get('_etag'):headers['If-Match']=fresh['_etag']
   status,answer,_=drive.call('PUT',session['url'],data,headers)
   if status in (200,201):
    result=metadata(drive,source['id'])
    if int(result['size'])!=size or result['md5Checksum'].lower()!=digest:raise RuntimeError('Prepared Drive file checksum differs; working files kept')
    sessions.pop(slot,None);commit();progress(size,size);return result
   if status!=308:raise RuntimeError('Prepared file upload: HTTP %d'%status)
   next_offset=driveupload._next_offset(answer)
   if next_offset<offset or next_offset>end:raise RuntimeError('Drive upload offset is invalid')
   if next_offset==offset:raise RuntimeError('Drive upload made no progress; will retry')
   offset=next_offset;stream.seek(offset);progress(offset,size)
 raise RuntimeError('Drive did not confirm the prepared upload')

REQUESTS='preparation-requests.json'
def request(profile,action,item_id):
 """Queue an owner request for the service (next, retry, keep, prepare); applied at its next pass."""
 path=location(profile).parent/REQUESTS;path.parent.mkdir(parents=True,exist_ok=True)
 try:pending=json.loads(path.read_text())
 except (OSError,ValueError):pending=[]
 pending=[r for r in pending if r.get('id')!=str(item_id)]+[{'action':action,'id':str(item_id)}]
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(pending));os.replace(tmp,path)

def entry(item,state):
 return {'id':str(item.get('id','')),'name':item.get('name',''),'folder':item.get('folderName',''),'size':int(item.get('size') or 0),'state':state}

def quality_text(name,size=0):
 """'2160p HDR · 14.2 GB' from a release name and size."""
 q=drivelibrary.quality(name);parts=['%dp'%q if q else '']
 if re.search(r'(?i)\b(hdr10\+?|hdr|dv|dovi|dolby[ ._-]?vision)\b',str(name)):parts[0]=(parts[0]+' HDR').strip()
 if size:parts.append('%.1f GB'%(size/1024**3))
 return ' · '.join(p for p in parts if p)

def library_view(state,downloads=(),uploads=(),free=None,working=0,now=time.time):
 """Settings › Library › Library status: counts, phone space and the rows of each section, in plain words."""
 library=state.get('library') or {};jobs={j['source']['id']:j for j in (state.get('jobs') or {}).values()}
 current=state.get('current') or {};rows={'preparing':[],'downloading':[],'waiting':[],'ready':[],'kept':[]}
 title=lambda name:drivelibrary.display_title(name)
 for d in downloads:
  rows['downloading'].append({'id':'dl:'+str(d.get('id','')),'title':d.get('title',''),'state':'downloading','pct':int(d.get('progress') or 0),
   'sub':'Downloading · %s'%' · '.join(x for x in (str(d.get('line','')).replace('  ',' '),str(d.get('speed','')).replace('  ',' ')) if x)})
 for u in uploads:
  rows['downloading'].append({'id':'up','title':u.get('title',''),'state':'uploading','pct':int(u.get('progress') or 0),
   'sub':'Uploading to Google Drive · %d%%'%int(u.get('progress') or 0)})
 order=[]
 for e in library.get('items') or []:
  job=jobs.get(e['id']);base={'id':e['id'],'title':title(e['name']),'name':e['name'],'folder':e['folder'],'size':e['size']}
  if e['state']=='ready':rows['ready'].append(dict(base,state='ready',sub=quality_text(e['name'],e['size'])));continue
  if job and (job.get('blocked') or job.get('kept')):
   why=job.get('error') or 'Kept as it is'
   rows['kept'].append(dict(base,state='kept',owner=bool(job.get('kept')) and not job.get('blocked'),
    sub='Kept as it is · %s'%('you chose to keep it' if job.get('kept') and not job.get('blocked') else plain(why))));continue
  if job and current.get('running') and current.get('title') in (e['name'],title(e['name'])):
   rows['preparing'].append(dict(base,state='preparing',pct=int(current.get('progress',0)),sub='%s · %d%%'%(str(current.get('stage','Preparing')).replace('Step 3 of 3 · ',''),current.get('progress',0))));continue
  if e['state']=='unreadable':rows['waiting'].append(dict(base,state='problem',warn=True,sub='Google Drive could not describe it; checking again next time'));continue
  if job and job.get('status')=='failed':
   wait=max(0,int((job.get('retry_after',0)-now())//60))
   rows['waiting'].append(dict(base,state='problem',warn=True,reason=plain(job.get('error')),sub='Will try again%s · %s'%(' in %d min'%wait if wait else ' soon',plain(job.get('error')))));continue
  if job and job.get('space'):
   rows['waiting'].append(dict(base,state='space',warn=True,needs=job['space'],sub='Needs %.0f GB free · %.0f GB free now'%(job['space']/1024**3,(free or 0)/1024**3)));continue
  order.append(dict(base,state='waiting',priority=(job or {}).get('priority',0)))
 order.sort(key=lambda r:-r['priority'])
 for n,r in enumerate(order,1):r['sub']='%s · %s'%('Next' if n==1 else '%s in line'%ordinal(n),quality_text(r['name'],r['size']))
 rows['waiting']=order+rows['waiting']
 todo=len(rows['preparing'])+len(rows['waiting']);total=len(rows['ready'])+todo+len(rows['kept'])
 checked=library.get('checked')
 minutes=int(max(0,now()-checked)//60) if checked else None
 return {'rows':rows,'ready':len(rows['ready']),'todo':todo,'downloading':len(rows['downloading']),'kept':len(rows['kept']),'total':total,
         'pct':int(round(100*len(rows['ready'])/total)) if total else 0,
         'checked':'not checked yet' if minutes is None else ('checked just now' if minutes<1 else 'checked %d min ago'%minutes),
         'free':free,'working':working}

REASONS=(('tracks MP4 cannot preserve','picture subtitles or extra video tracks cannot go into MP4'),
         ('without changing HDR','its HDR picture cannot be kept'),
         ('HTTP','Google Drive did not answer'),('connection','the connection dropped'),
         ('Free phone space','not enough phone space'),('checksum','Google Drive returned a different copy'),
         ('validation','the prepared copy did not pass its checks'))
def plain(reason):
 """A known preparation problem in everyday words; anything else as it is, first clause only."""
 text=str(reason or '')
 for marker,words in REASONS:
  if marker.lower() in text.lower():return words
 return text.split(';')[0].strip() or 'a problem'

def ordinal(n):return '%d%s'%(n,'th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th'))

RESCAN='airplay-preparation-rescan'
def request_check(profile):
 """Ask the service to check Google Drive › Kodi Downloads now (Settings › Library › Check library for conversion)."""
 marker=location(profile).parent/RESCAN;marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(str(time.time()))
def check_requested(profile):return (location(profile).parent/RESCAN).exists()

def summary(state,now=time.time):
 """Plain-words status for Settings › Library › Check library for conversion."""
 library=state.get('library') or {};jobs=list((state.get('jobs') or {}).values())
 waiting=[j for j in jobs if j.get('status') not in ('done','superseded','failed') and not j.get('blocked')]
 paused=[j for j in jobs if j.get('status')=='failed' and not j.get('blocked')]
 blocked=[j for j in jobs if j.get('blocked')]
 plural=lambda n,one,many:'%d %s'%(n,one if n==1 else many)
 lines=[]
 if library:
  lines.append('Google Drive › Kodi Downloads has %s.'%plural(library.get('videos',0),'video','videos'))
  lines.append('%d ready for Kodi and AirPlay.'%library.get('ready',0))
 else:lines.append('The library has not been checked yet.')
 current=state.get('current') or {}
 now_line=' Preparing now: %s, %d%%.'%(drivelibrary.display_title(current.get('title','')),current.get('progress',0)) if current.get('running') and current.get('title') else ''
 lines.append('%d waiting to be prepared.%s'%(len(waiting),now_line))
 if paused:
  reasons=sorted({j.get('error','Will try again') for j in paused})
  lines.append('%d paused, will try again: %s'%(len(paused),'; '.join(reasons)[:200]))
 spaced=[j for j in waiting if j.get('space')]
 if spaced:lines.append('%d of the waiting videos need more phone space (up to %.0f GB free); they start when there is room.'%(
  len(spaced),max(j['space'] for j in spaced)/1024**3))
 if blocked:lines.append('%d cannot be prepared without losing quality; kept as they are.'%len(blocked))
 if library.get('unreadable'):lines.append('%d could not be read from Drive this time.'%library['unreadable'])
 if library.get('checked'):
  minutes=int(max(0,now()-library['checked'])//60)
  lines.append('Last checked %s.'%('just now' if minutes<1 else '%s ago'%plural(minutes,'minute','minutes')))
 return '\n'.join(lines)

class Queue:
 def __init__(self,profile,drive,native,download_file=download,notify=lambda *args:None,clock=time.time,stream=None):
  self.profile=Path(profile);self.drive=drive;self.native=native;self.download=download_file;self.notify=notify;self.clock=clock
  # drive_stream.DriveStream when the framework can read a loopback source: no downloaded copy of the Drive file.
  self.stream=stream if stream is not None and getattr(native,'streams',False) else None
  self.state=load(profile);self.state.setdefault('jobs',{});self.state.setdefault('sessions',{})
  self.work=location(profile).parent/'preparing-videos';self.work.mkdir(parents=True,exist_ok=True)
 def commit(self):save(self.profile,self.state)
 def scan(self,keep_going=lambda:True,force=False):
  requested=location(self.profile).parent/'airplay-preparation-rescan'
  if not force and not requested.exists() and self.clock()-self.state.get('last_scan',0)<300:return
  self.state['current']={'title':'Movies and shows','stage':'Checking downloaded videos','progress':0,'queued':0,'running':True,'updated':self.clock()};self.commit()
  listed_all=library_scan.remote_files(self.drive,keep_going)
  found=self.unique(listed_all);seen=set();counts={'videos':len(found),'ready':0,'unreadable':0};entries=[]
  for number,listed in enumerate(found):
   if not keep_going():raise driveupload.Stop('Preparation scan paused')
   try:item=dict(metadata(self.drive,listed['id']),folderName=listed.get('folderName',''))
   except Exception:
    # One file Drive cannot describe right now must not stop the whole library check (owner, build 156: no
    # movies were being converted). Its existing work, if any, is kept for the next check.
    counts['unreadable']+=1;entries.append(entry(listed,'unreadable'))
    seen.update(slot for slot,job in self.state['jobs'].items() if job['source']['id']==listed['id'])
    continue
   slot=key(item);seen.add(slot)
   recovering=[old for old,job in self.state['jobs'].items() if job['source']['id']==item['id'] and job.get('status')=='committing']
   if recovering:seen.update(recovering);continue
   if ready(item):counts['ready']+=1;entries.append(entry(item,'ready'));continue
   entries.append(entry(item,'todo'))
   if slot not in self.state['jobs'] or self.state['jobs'][slot].get('status')=='superseded' or identity(self.state['jobs'][slot]['source'])!=identity(item):
    self.state['jobs'][slot]={'source':item,'status':'waiting','attempts':0,'retry_after':0}
  # A source modified/replaced by another client no longer owns its old work/session.
  for slot,job in list(self.state['jobs'].items()):
   if slot not in seen and job.get('status')!='committing':
    self.state['jobs'].pop(slot,None);self.state['sessions'].pop(slot,None)
    shutil.rmtree(self.work/slot,ignore_errors=True)
  self.state['library']=dict(counts,checked=self.clock(),items=entries)
  self.state['last_scan']=self.clock();self.state.pop('current',None);self.commit();requested.unlink(missing_ok=True)
 def unique(self,found):
  """One copy per episode or movie (owner, build 152: 'Lanterns' and 'Lanterns (2026)' each held S1 E1, and both
  were queued; the owner then asked for the extra copy to be deleted). Keeps, in order: a copy already prepared, one
  being saved or with downloaded working files, the highest resolution, the largest. The others go to Drive's Trash
  once the kept copy is confirmed on Drive. Copies whose years disagree are never treated as one."""
  started={job['source']['id']:(2 if job.get('status')=='committing' else 1) for slot,job in self.state['jobs'].items()
           if job.get('status')=='committing' or (self.work/slot).exists()}
  groups={};out=[]
  for item in found:
   k=drivelibrary.media_key(item.get('name',''),item.get('folderName',''))
   if k is None:out.append(item)
   else:groups.setdefault(k,[]).append(item)
  for k,items in groups.items():
   years={drivelibrary.media_year(i.get('name',''),i.get('folderName','')) for i in items}-{''}
   if len(items)==1 or len(years)>1:out.extend(items);continue
   rank=lambda item:(ready(item),started.get(item['id'],0),drivelibrary.quality(item.get('name','')),int(item.get('size') or 0))
   items.sort(key=rank,reverse=True);keep=items[0];out.append(keep)
   removed=self.remove_copies(keep,items[1:],started)
   kept_back=[i for i in items[1:] if i not in removed]
   out.extend(kept_back)   # a copy that could not be removed safely is still handled as its own video
   if removed:
    where=lambda item:'“%s”'%item['folderName'] if item.get('folderName') else 'Drive'
    self.notify('drive','Duplicate removed from Google Drive','%s: kept the copy in %s; moved the copy in %s to Drive’s Trash.'%(
     drivelibrary.display_title(keep.get('name','')),where(keep),', '.join(where(i) for i in removed)))
  return out
 def remove_copies(self,keep,others,started):
  """Trash `others` after confirming `keep` is a complete, untrashed Drive file; never a copy being saved."""
  try:metadata(self.drive,keep['id'])
  except Exception:return []
  removed=[]
  for item in others:
   if started.get(item['id'])==2:continue
   try:
    current=metadata(self.drive,item['id'])
    if (current.get('md5Checksum','').lower(),int(current['size']))!=(str(item.get('md5Checksum','')).lower(),int(item.get('size') or 0)):continue
    drivelibrary.trash(self.drive,item['id']);removed.append(item)
   except Exception:continue
   for slot,job in list(self.state['jobs'].items()):
    if job['source']['id']==item['id']:self.state['jobs'].pop(slot,None);self.state['sessions'].pop(slot,None);shutil.rmtree(self.work/slot,ignore_errors=True)
   try:drivelibrary.trash_if_empty(self.drive,item.get('folderId'),item.get('folderName',''))
   except Exception:pass
  if removed:driveupload.invalidate_library(str(location(self.profile).parent))
  return removed
 def note_space(self,waiting,free):
  """One notification when more videos start waiting for phone space; none while the list stays the same."""
  ids=sorted(job['source']['id'] for slot,job in waiting)
  before=self.state.get('space_waiting') or []
  self.state['space_waiting']=ids
  if not ids or set(ids)<=set(before):return
  biggest=max(job['space'] for slot,job in waiting)
  gb=lambda n:'%.0f GB'%(n/1024**3)
  self.notify('info','Waiting for phone space','%d video%s will be prepared when there is room: the largest needs %s free, %s is free now. Kodi always leaves %s free for you.'%(
   len(ids),'' if len(ids)==1 else 's',gb(biggest),gb(free),gb(KEEP_FREE)))
 def apply_requests(self):
  """What the owner asked for on Settings › Library › Library status (a separate file: the page never writes the
  queue's own state). next: prepare it first once it can run; retry: try a paused one now; keep / prepare: keep it
  as it is, or put it back in the queue."""
  path=location(self.profile).parent/REQUESTS
  try:requests=json.loads(path.read_text())
  except (OSError,ValueError):return False
  path.unlink(missing_ok=True)
  jobs={job['source']['id']:job for job in self.state['jobs'].values()}
  for request in requests if isinstance(requests,list) else []:
   job=jobs.get(str(request.get('id')));action=request.get('action')
   if not job:continue
   if action=='next':job['priority']=self.clock()
   elif action=='retry':job.update(retry_after=0,attempts=0);job.pop('error',None);job['status']='waiting'
   elif action=='keep':job['kept']=True
   elif action=='prepare':job.pop('kept',None)
  self.commit();return True
 def process_one(self,keep_going=lambda:True):
  self.apply_requests()
  candidates=[(slot,job) for slot,job in self.state['jobs'].items() if job.get('status') not in ('done','superseded') and not job.get('blocked') and not job.get('kept') and job.get('retry_after',0)<=self.clock()]
  if not candidates:return False
  working=[slot for slot,job in self.state['jobs'].items() if (self.work/slot).exists() and job.get('status')!='done']
  # Finish a half-downloaded video before starting another (phone space), but only while it can actually run: one
  # stuck in a retry wait must not hold the whole queue (owner, build 156). Every job checks free space itself.
  resumable=[pair for pair in candidates if pair[0] in working]
  free=shutil.disk_usage(self.work).free
  def fits(pair):
   slot,job=pair;return free+folder_bytes(self.work/slot)>=space_needed(job['source'],bool(self.stream))
  if resumable and not any(fits(pair) for pair in resumable):
   # A half-prepared video that cannot finish gives its space back instead of keeping gigabytes on the phone.
   for slot,job in resumable:
    shutil.rmtree(self.work/slot,ignore_errors=True);job['status']='waiting';job.pop('retry_after',None)
   free=shutil.disk_usage(self.work).free;resumable=[]
  if resumable:candidates=resumable
  # Only videos that fit start; the others wait (smallest first once space frees up) without failing or notifying.
  waiting=[pair for pair in candidates if not fits(pair)]
  for slot,job in waiting:job['space']=space_needed(job['source'],bool(self.stream))
  for slot,job in candidates:
   if (slot,job) not in waiting:job.pop('space',None)
  self.note_space(waiting,free)
  # A half-prepared video finishes first, then what the owner asked to prepare next (latest request first).
  candidates=sorted([pair for pair in candidates if fits(pair)],key=lambda pair:(0 if pair in resumable else 1,-pair[1].get('priority',0)))
  if not candidates:self.commit();return False
  # Always resume the one downloaded working source before allocating space for another movie.
  candidates.sort(key=lambda pair:0 if (self.work/pair[0]).exists() else 1)
  slot,job=candidates[0];folder=self.work/slot;folder.mkdir(exist_ok=True)
  source=folder/'source';output=folder/'prepared.mp4';item=job['source'];last=[0]
  def progress(stage,value):
   if not keep_going():raise driveupload.Stop('Preparation paused during playback')
   now=self.clock()
   if now-last[0]<0.5 and value<100:return
   last[0]=now
   self.state['current']={'title':item['name'],'stage':stage,'progress':max(0,min(100,value)),
                         'queued':len(candidates),'running':True,'updated':now};self.commit()
  try:
   if not keep_going():raise driveupload.Stop('Preparation paused')
   current=metadata(self.drive,item['id'])
   if ready(current):job['status']='done';self.commit();shutil.rmtree(folder);return True
   # A completed upload can survive a process exit before tagging/cleanup. Recover it from the local output.
   already_uploaded=False
   if output.is_file():
    digest=driveupload.checksum(str(output),keep_going,pace=1)
    already_uploaded=int(current['size'])==output.stat().st_size and current['md5Checksum'].lower()==digest
   if not already_uploaded:
    if identity(current)!=identity(item):raise RuntimeError('Drive source changed; preparation will rescan')
    if self.stream:
     # Streamed from Drive as the converter reads it: nothing downloaded, no copy of the source on the phone.
     # A Drive change meanwhile is caught by replace()'s fresh version/checksum check, and the output is validated.
     source.unlink(missing_ok=True)   # a copy left by an older build gives its space back
     source=self.stream.url(item['id'])
     progress('Step 3 of 3 · Reading from Google Drive',2)
    else:
     if not source.is_file() or source.stat().st_size!=int(item['size']):
      required=max(0,int(item['size'])-(source.stat().st_size if source.exists() else 0))+RESERVE
      if shutil.disk_usage(folder).free<required:raise RuntimeError('Free phone space is needed for temporary preparation')
      progress('Step 3 of 3 · Reading the downloaded video',0)
      self.download(self.drive,item,str(source),keep_going,lambda n,t:progress('Step 3 of 3 · Reading the downloaded video',20*n/t))
     if driveupload.checksum(str(source),keep_going,pace=1)!=item['md5Checksum'].lower():
      source.unlink();raise RuntimeError('Source checksum differs; will read it again')
    before=self.native.probe(str(source))
    # Never trade the selected 4K/HDR source for the live converter's 1080p fallback.
    if not output.is_file():
     audio=int(before.get('audio_work_bytes',0));size=int(item['size'])
     if before.get('copy_video'):
      # One MP4 output plus only the audio tracks which actually need bridging. No H.264 re-encode estimate
      # for the usual 4K HEVC download: those video bytes remain unchanged.
      needed=size+2*audio+16*1024*1024+RESERVE
     else:
      video=int(before.get('duration',0)*max(1.5e6,7e6*before['width']*before['height']/(1920*1080))/8)
      needed=size+2*(video+audio)+RESERVE
     used=sum(p.stat().st_size for p in folder.glob('prepared.mp4.track*') if p.is_file())
     if shutil.disk_usage(folder).free<max(RESERVE,needed-used):raise RuntimeError('Free phone space is needed to finish this video; existing Drive file is unchanged')
     progress('Step 3 of 3 · Preparing at source resolution',20)
     self.native.convert(str(source),str(output),keep_going,
      lambda stage,n,t:progress('Step 3 of 3 · '+('Preparing video','Preparing audio','Packaging MP4','Verifying video')[stage],(20,35,50,74)[stage]+(15,15,24,1)[stage]*(n/t if t else 0)))
    after=self.native.probe(str(output))
    if not after.get('ready') or (before['width'],before['height'],before['hdr'])!=(after['width'],after['height'],after['hdr']):
     output.unlink(missing_ok=True);raise RuntimeError('Prepared video did not preserve resolution/HDR; original retained')
    if abs(before.get('duration',0)-after.get('duration',0))>2:raise RuntimeError('Prepared duration differs; original retained')
    progress('Step 3 of 3 · Saving the prepared file to Drive',75)
    job['status']='committing';self.commit()
    current=replace(self.drive,item,str(output),self.state['sessions'],self.commit,keep_going,
                    lambda n,t:progress('Step 3 of 3 · Saving the prepared file to Drive',75+24*n/t))
   # Mark only after a fresh checksum check; app properties changing alone never imply video conversion.
   digest=driveupload.checksum(str(output),keep_going,pace=1)
   if not driveupload.confirmed(self.drive,item['id'],output.stat().st_size,digest):raise RuntimeError('Prepared Drive file could not be verified; working files kept')
   props=dict(current.get('appProperties') or {});props.update({PROPERTY:PROFILE,CHECKSUM_PROPERTY:digest})
   status,_,_=self.drive.call('PATCH',driveupload.API+'/'+urllib.parse.quote(item['id'],safe=''),json.dumps({'appProperties':props}).encode(),{'Content-Type':'application/json'})
   if status!=200:raise RuntimeError('Preparation verification marker: HTTP %d'%status)
   job['status']='done';job['completed']=self.clock();self.commit()
   driveupload.invalidate_library(str(location(self.profile).parent));shutil.rmtree(folder)
   self.notify('info','Ready for Kodi and AirPlay',drivelibrary.display_title(item['name']));return True
  except driveupload.Stop:
   if job.get('status')!='committing':job['status']='paused'
   job['retry_after']=0;return False
  except Exception as error:
   if job.get('status')!='committing':job['status']='failed'
   job['attempts']=job.get('attempts',0)+1;job['retry_after']=self.clock()+min(3600,60*2**min(job['attempts']-1,6))
   # HTTP exceptions can embed signed URLs: publish only known application errors, never transport text.
   text=str(error) if type(error) is RuntimeError else 'Preparation paused (%s)'%type(error).__name__
   if 'http://' in text or 'https://' in text:text='Preparation paused; connection needs a retry'
   if 'source changed' in text:
    job['status']='superseded';self.state['last_scan']=0;shutil.rmtree(folder,ignore_errors=True)
   elif 'tracks MP4 cannot preserve' in text or 'cannot be prepared without changing HDR' in text:
    job['blocked']=True;shutil.rmtree(folder,ignore_errors=True)
   elif 'Free phone space' in text:
    # Space ran out after all (the phone filled up meanwhile): give the space back and wait, quietly.
    shutil.rmtree(folder,ignore_errors=True);job['status']='waiting';job['space']=space_needed(item,bool(self.stream));job['retry_after']=self.clock()+600
    job['error']=text[:240];return False
   # One notification per video and reason, not one per retry (owner, build 157: the same message five times).
   if job.get('error')!=text[:240]:self.notify('problem','Video preparation paused','%s: %s'%(drivelibrary.display_title(item.get('name','')),text[:200]))
   job['error']=text[:240];return False
  finally:
   if self.stream:self.stream.forget(item['id'])
   current=self.state.get('current') or {}
   current.update(running=False,stage='Paused' if job.get('status')=='paused' else job.get('error','Waiting for the next video'),updated=self.clock())
   if job.get('status')=='done':self.state.pop('current',None)
   else:self.state['current']=current
   self.commit()

def cards(profile,now=time.time):
 state=load(profile);current=state.get('current') or {}
 waiting=[j for j in state.get('jobs',{}).values() if j.get('status')!='done']
 if not current and not waiting:return []
 current=dict(current)
 if not current:
  job=waiting[0];current={'title':job['source']['name'],'stage':job.get('error') or 'Queued','progress':0,'running':False}
 fresh=current.get('running') and now()-current.get('updated',0)<15
 current['running']=bool(fresh)
 # One fact per line (ISSUE-101): the count lives in the card's summary, the line says what is happening now.
 current['title']=drivelibrary.display_title(current.get('title',''))
 current['queued']=len(waiting)
 current['line']='%s · %d%%'%(current.get('stage','Queued'),current.get('progress',0))
 return [current]
