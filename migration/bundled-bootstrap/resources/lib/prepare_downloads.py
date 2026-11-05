"""Step 3 of kept downloads: one indexed MP4, at source resolution, in the SAME Drive file.

The service scans app-managed Movies/TV Shows at startup and after uploads. Work is serialized with
the uploader/scanner, paused during playback, and checkpointed. Source bytes stay on Drive until a
validated local result is uploaded in place. No permanent AirPlay variant, source-ID switch or extra folder.
"""
import ctypes,hashlib,json,os,shutil,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
import driveupload,drivelibrary,library_scan

PROFILE='source-resolution-mp4-v1'
PROPERTY='kodiAirPlayProfile'
CHECKSUM_PROPERTY='kodiAirPlayMD5'
FILE='airplay-preparation.json'
RESERVE=256*1024*1024
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
  lib.kodi_airplay_probe.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_probe.restype=ctypes.c_int
  lib.kodi_airplay_prepare.argtypes=[ctypes.c_char_p,ctypes.c_char_p,CALLBACK,ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
  lib.kodi_airplay_prepare.restype=ctypes.c_int
 def probe(self,path):
  out=ctypes.create_string_buffer(1024)
  if self.lib.kodi_airplay_probe(os.fsencode(path),out,len(out))<0:raise RuntimeError('Video could not be inspected')
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
  r=self.lib.kodi_airplay_prepare(os.fsencode(source),os.fsencode(output),callback,None,error,len(error))
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

class Queue:
 def __init__(self,profile,drive,native,download_file=download,notify=lambda *args:None,clock=time.time):
  self.profile=Path(profile);self.drive=drive;self.native=native;self.download=download_file;self.notify=notify;self.clock=clock
  self.state=load(profile);self.state.setdefault('jobs',{});self.state.setdefault('sessions',{})
  self.work=location(profile).parent/'preparing-videos';self.work.mkdir(parents=True,exist_ok=True)
 def commit(self):save(self.profile,self.state)
 def scan(self,keep_going=lambda:True,force=False):
  requested=location(self.profile).parent/'airplay-preparation-rescan'
  if not force and not requested.exists() and self.clock()-self.state.get('last_scan',0)<300:return
  self.state['current']={'title':'Movies and shows','stage':'Checking downloaded videos','progress':0,'queued':0,'running':True,'updated':self.clock()};self.commit()
  found=library_scan.remote_files(self.drive,keep_going);seen=set()
  for number,item in enumerate(found):
   if not keep_going():raise driveupload.Stop('Preparation scan paused')
   item=metadata(self.drive,item['id']);slot=key(item);seen.add(slot)
   recovering=[old for old,job in self.state['jobs'].items() if job['source']['id']==item['id'] and job.get('status')=='committing']
   if recovering:seen.update(recovering);continue
   if ready(item):continue
   if slot not in self.state['jobs'] or self.state['jobs'][slot].get('status')=='superseded' or identity(self.state['jobs'][slot]['source'])!=identity(item):
    self.state['jobs'][slot]={'source':item,'status':'waiting','attempts':0,'retry_after':0}
  # A source modified/replaced by another client no longer owns its old work/session.
  for slot,job in list(self.state['jobs'].items()):
   if slot not in seen and job.get('status')!='committing':
    self.state['jobs'].pop(slot,None);self.state['sessions'].pop(slot,None)
    shutil.rmtree(self.work/slot,ignore_errors=True)
  self.state['last_scan']=self.clock();self.state.pop('current',None);self.commit();requested.unlink(missing_ok=True)
 def process_one(self,keep_going=lambda:True):
  candidates=[(slot,job) for slot,job in self.state['jobs'].items() if job.get('status') not in ('done','superseded') and not job.get('blocked') and job.get('retry_after',0)<=self.clock()]
  if not candidates:return False
  working=[slot for slot,job in self.state['jobs'].items() if (self.work/slot).exists() and job.get('status')!='done']
  if working:candidates=[pair for pair in candidates if pair[0] in working]
  if not candidates:return False
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
   self.notify('info','Ready for Kodi and AirPlay',item['name']);return True
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
   job['error']=text[:240];self.notify('problem','Video preparation paused',job['error']);return False
  finally:
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
