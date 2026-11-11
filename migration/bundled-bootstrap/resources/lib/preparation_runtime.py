"""Independent heartbeat while scanning, probing, converting or uploading a movie.

The native converter can spend minutes opening an index before its first progress
callback. That does not mean the worker is idle. This small separate file avoids
concurrent writes to the queue/checkpoint JSON and expires after a process exit.
"""
import contextlib,json,os,re,threading,time,urllib.error
from pathlib import Path

NAME='preparation-runtime.json'
_active=threading.Event()

def location(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap'/NAME

def read(profile,clock=time.time):
 try:
  item=json.loads(location(profile).read_text())
  return item if 0<=clock()-item.get('updated',0)<15 else {}
 except (OSError,ValueError):return {}

def active():return _active.is_set()

def current(item,runtime):
 """Merge independent transport evidence; a blocked producer cannot refresh native progress itself."""
 item=dict(item)
 if not runtime or not item.get('running'):return item
 item['updated']=runtime.get('updated',item.get('updated',0))
 item['indeterminate']=not runtime.get('known')
 item['stage']=runtime.get('phase') or item.get('stage')
 for name in ('up_rate','out_bytes','upload_inflight_s'):
  if name in runtime:item[name]=runtime[name]
 phase=runtime.get('transfer_phase')
 if phase in ('uploading','waiting_drive') and not item.get('paused'):
  item.update(stage='Uploading to Google Drive' if phase=='uploading' else 'Waiting for Drive',
              rate=runtime.get('up_rate',0),eta='',eta_s=0,indeterminate=False)
  item['detail']='Drive is receiving the upload' if phase=='uploading' else 'Waiting for the current upload to finish'
 elif item['indeterminate'] and runtime.get('read_bytes'):
  item['stage']+=' · %.0f MB read'%(runtime['read_bytes']/1024**2)
 return item

def pending(state):
 return bool(state.get('staging_cleanup')) or any(j.get('status') not in ('done','superseded') and not j.get('blocked') and not j.get('kept')
                                               for j in (state.get('jobs') or {}).values())

def schedule(state,paused=False,now=None):
 """Explain the worker gate without media names, IDs or credentials."""
 now=time.time() if now is None else now
 jobs=[j for j in (state.get('jobs') or {}).values()
       if j.get('status') not in ('done','superseded') and not j.get('blocked') and not j.get('kept')]
 eligible=sum(float(j.get('retry_after') or 0)<=now for j in jobs)
 active=bool((state.get('current') or {}).get('running'))
 reason='running' if active else 'owner_paused' if paused and jobs else 'ready' if eligible else 'retry_wait' if jobs else 'no_jobs'
 return {'reason':reason,'queued_jobs':len(jobs),'eligible_jobs':eligible,'owner_paused':bool(paused)}

def problem(error):
 """Useful transport diagnostics without signed URLs, access tokens or request headers."""
 if isinstance(error,urllib.error.URLError):
  reason=error.reason
  if isinstance(reason,TimeoutError):return 'Google Drive connection timed out; will retry'
  if 'CERTIFICATE_VERIFY_FAILED' in str(reason):return 'Google Drive TLS certificate verification failed'
  if isinstance(reason,ConnectionRefusedError):return 'The local Drive stream refused the connection; will retry'
  if isinstance(reason,OSError):
   return 'Google Drive connection failed (%s%s); will retry'%(type(reason).__name__,', errno %s'%reason.errno if reason.errno else '')
  return 'Google Drive connection failed (%s); will retry'%type(reason).__name__
 if isinstance(error,TimeoutError):return 'Google Drive connection timed out; will retry'
 if isinstance(error,RuntimeError):
  text=re.sub(r'https?://\S+','[connection]',str(error))
  return text[:240]
 return 'Preparation failed (%s); will retry'%type(error).__name__

class Lease:
 def __init__(self,profile,stats=lambda:{},clock=time.time,every=2):
  self.path=location(profile);self.stats=stats;self.clock=clock;self.every=every
  self.stop=threading.Event();self.lock=threading.Lock();self.state={'phase':'Checking downloaded videos','known':False}
 def phase(self,text,known=False,title=''):
  with self.lock:self.state.update(phase=text,known=bool(known),title=title)
 def pulse(self):
  with self.lock:item=dict(self.state)
  try:item.update(self.stats() or {})
  except Exception:pass
  item['updated']=self.clock();self.path.parent.mkdir(parents=True,exist_ok=True)
  tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(item));os.replace(tmp,self.path)
 def _run(self):
  while not self.stop.wait(self.every):
   try:self.pulse()
   except OSError:pass
 def __enter__(self):
  _active.set();self.pulse();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start();return self
 def __exit__(self,*args):
  self.stop.set();self.thread.join(timeout=self.every+1);_active.clear()
  self.path.unlink(missing_ok=True)
