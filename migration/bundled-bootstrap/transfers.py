"""The Transfers page (portrait/IOSTransfers.xml), opened by tapping a transfer card in Notifications (owner: "I only
want the graph to show in notifications if i tap on it"). One job at a time (owner, build 172): the graph follows the
card that was tapped; when that job ends it moves on to the next one still running. Refreshes every 2 s."""
import os,sys,threading,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import transfer_history as th,transfers_page as tp

BACK=(9,10,92,110)
GB=1024**3

MODEL_KIND={'conv':'conv','repack':'conv','copy':'up','upload':'up','down':'down'}

def live(history,model):
 """History with only the jobs the status model has moving or paused (build 193: one rule for "running" everywhere;
 a history record up to 30 s old used to keep a stopped job on screen, or a quiet one off it)."""
 if model is None:return history
 import work_state
 kinds={MODEL_KIND[j['kind']] for j in model.get('jobs') or [] if j.get('kind') in MODEL_KIND and j.get('state')!=work_state.STALE_STATE}
 return dict(history,jobs={k:v for k,v in (history.get('jobs') or {}).items() if k in kinds})

def model_entries(model):
 """Every published job has its own chip, including simultaneous jobs of the same kind."""
 counts={}
 out=[]
 for j in (model or {}).get('jobs') or []:
  base=MODEL_KIND.get(j.get('kind'))
  if not base:continue
  counts[base]=counts.get(base,0)+1
  key=base if counts[base]==1 else '%s.%d'%(base,counts[base])
  out.append((key,j))
 return out

def model_job(model,kind):
 return next((j for key,j in model_entries(model) if key==kind),None)


def page_state(history,now,wanted,queued,model=None,first_seen=None):
 """(window properties, bar percent, shown kind, the other running kinds) for one refresh (pure: tested without Kodi).
 model: the status model (work_state.load); it decides what runs, its words and the empty state's words."""
 history=live(history,model)
 if model is not None:
  import work_state
  entries=model_entries(model)
  first_seen={} if first_seen is None else first_seen
  active={work_state.job_key(j) for _,j in entries}
  for identity in list(first_seen):
   if identity not in active:first_seen.pop(identity)
  jobs={}
  for k,j in entries:
   old=(history.get('jobs') or {}).get(k) or (history.get('jobs') or {}).get(k.split('.')[0],{})
   if old.get('title')!=j['title']:old={}
   identity=work_state.job_key(j)
   start=first_seen.setdefault(identity,old.get('start',now))
   start=min(start,old.get('start',start));first_seen[identity]=start
   jobs[k]=dict(old,kind=k,title=j['title'],start=start,last=now,
                pct=j.get('pct'),done=j.get('sent') or 0,total=j.get('total') or 0)
  history=dict(history,jobs=jobs)
 kind=(wanted if wanted in history.get('jobs',{}) else next(iter(history.get('jobs',{})),None)) if model is not None else th.pick(history,wanted,now)
 base=(kind or '').split('.')[0]
 props={k:'' for k in ('kind','tint','title','now','peak','avg','started','from','line','graph','number','units','step','axis0','axis1','axis2','wait')}
 pct=0.0;others=[]
 if kind:
  job=history['jobs'][kind]
  pts=job.get('points') or []
  done,total=float(job.get('done') or 0),float(job.get('total') or 0)
  rate=pts[-1][1] if pts else 0.0
  if kind=='conv':
   pct=float(job.get('pct') or 0);extra=job.get('extra') or {}
   # Build 177 (approved mockup): how much of the film is done and how fast, not how much was read.
   film=film_text(extra.get('film_done'),extra.get('film_total'))
   pace='%.1f× the film\'s speed'%float(extra['pace']) if extra.get('pace') else ''
   line=' · '.join(x for x in ('%d%%'%pct if pct>=1 else '',film,pace) if x) or 'Starting'
  else:
   pct=100.0*done/total if total else 0.0
   line='%s of %s'%(th.size(done),th.size(total)) if total else ''
  left=_left(kind,job,rate,pct,now)
  if left:line=' · '.join(x for x in (line,left) if x)
  m=model_job(model,kind)
  if m is not None:
   # Slowed, paused by you or waiting for the network: the model's own words (never "Starting…" or a stale speed).
   line=m['line'];rate=float(m.get('rate') or 0);pct=float(m.get('pct') or 0)
  props.update(kind=th.LABELS[base].upper(),tint=th.TINTS[base],title=job['title'],
               now=th.mb(rate) if rate>0 else ((m or {}).get('line') if m is not None and m.get('state')!='running' else 'Starting…'),
               peak=th.mb(job.get('peak')),
               avg=th.mb(job.get('sum',0)/max(1,job.get('n',1))),started=th.ago(now-job['start']),line=line)
  props['from']=th.ago(now-job['start']).replace('just now','a moment ago')
  props['tint']=(m or {}).get('tint_now') or props['tint']
  props['step']=((m or {}).get('step') or th.LABELS[base]) + (' · %d%%'%pct if not (m or {}).get('indeterminate') else '')
  props['number']='%.1f'%(rate/1048576.) if rate else '–'
  props['units']='MB/s'+(' · '+_left(kind,job,rate,pct,now) if model is None else '')
  if m and m.get('eta_s'):
   import prepare_downloads
   props['units']='MB/s · '+prepare_downloads.eta_text(m['eta_s']).replace('about ','')
  props.update({k:v for k,v in th.graph_labels(pts,job['start'],now).items() if isinstance(v,str)})
  props['peak']=th.mb(job.get('peak'))
  import library_rows
  props['started']=library_rows.clock12(job['start'])
  props['wait']='' if len(pts)>1 and any(pt[1]>0 for pt in pts) else ((m or {}).get('step') or 'Measuring…')
  others=list(history.get('jobs') or {})
 props['headline']=(model or {}).get('headline','')
 for n in range(1,tp.OTHERS+1):
  k=others[n-1] if n<=len(others) else ''
  j=(history.get('jobs') or {}).get(k,{})
  props['other.%d.label'%n]=('Converting' if k.startswith('conv') else 'Downloading') if k else ''
  props['other.%d.tint'%n]=(model_job(model,k) or {}).get('tint_now') or th.TINTS.get(k,'')
  props['other.%d.rate'%n]=''
  props['other.%d.on'%n]='true' if k and k==kind else ''
 if model is not None:
  queued=[(j['title'],'%s · %.1f GB'%(j['what'],float(j.get('size') or 0)/GB)) for j in model.get('next') or []]
 # Owner (build 176): "it says finished? but its clearly not finished": stopped attempts stay in History only.
 finished=[f for f in history.get('finished') or [] if now-f.get('end',0)<24*3600 and th.outcome(f)=='done']
 for n in range(1,tp.DONE+1):
  f=finished[n-1] if n<=len(finished) else None
  props['done.%d.title'%n]=f['title'] if f else ''
  # A job that ended part-way says so (build 174: a restarted conversion looked finished).
  stopped=f and th.outcome(f)=='stopped'
  props['done.%d.line'%n]=' · '.join(x for x in (('stopped at %d%%'%float(f['pct']) if f.get('kind')=='conv' else 'stopped') if stopped else
                                                 (th.size(f['size']) if f.get('size') else ''),th.took(f['end']-f['start']),
                                                 'peak '+th.mb(f['peak'])) if x) if f else ''
 for n in range(1,tp.NEXT+1):
  r=queued[n-1] if n<=len(queued) else ('','')
  props['next.%d.title'%n],props['next.%d.line'%n]=r
  shown=min(len(queued),tp.NEXT)
  props['next.%d.pos'%n]='' if n>shown else 'only' if shown==1 else 'first' if n==1 else 'last' if n==shown else 'mid'
 # "Nothing is moving" only when nothing runs, waits or needs you (owner, build 192: it said so while converting).
 import work_state
 mode=(model or {}).get('mode',work_state.STALE_STATE)
 props['empty.title']='Nothing is moving right now' if mode==work_state.IDLE else ((model or {}).get('headline') or 'Updating…')[:1].upper()+((model or {}).get('headline') or 'Updating…')[1:]
 props['empty.text']=('Downloads, Drive copies and conversions show here while they run.' if mode==work_state.IDLE else
                      (((model or {}).get('needs') or [{}])[0].get('text') or (model or {}).get('wait') or 'The next one starts on its own.'))
 return props,pct,kind,others

def film_text(done,total):
 """'46 of 148 min of film' ('' before the film's length is known)."""
 try:done,total=float(done or 0),float(total or 0)
 except (TypeError,ValueError):return ''
 return '%d of %d min of film'%(done//60,round(total/60)) if total>0 else ''

def _left(kind,job,rate,pct,now):
 """'about 25 min left' from the job's own pace, or ''."""
 import prepare_downloads
 if kind=='conv':
  # This attempt's own estimate (prepare_cloud): a restarted conversion keeps its history job, so its start is older.
  return str((job.get('extra') or {}).get('eta') or '')
 else:
  total,done=float(job.get('total') or 0),float(job.get('done') or 0)
  if not rate or not total:return ''
  seconds=(total-done)/rate
 return prepare_downloads.eta_text(seconds)

def queue_lists(profile,now):
 """Up next as [(title, line)] from the preparation queue."""
 import drivelibrary,prepare_downloads
 state=prepare_downloads.load(profile);running=(state.get('current') or {}).get('title')
 nexts=[]
 for job in (state.get('jobs') or {}).values():
  src=job.get('source') or {};name=src.get('name','')
  if job.get('status') in ('waiting','paused') and name!=running and not job.get('kept') and not job.get('blocked'):
   # A repack (prepared before build 191) is already Ready and plays; it is only rearranged to open faster (owner,
   # build 192: "all my stuff is re converting even though it says ready").
   what='faster start' if job.get('repack') else 'convert'
   nexts.append((drivelibrary.display_title(name),'%s · %.1f GB'%(what,int(src.get('size') or 0)/GB)))
 return nexts

def run(args=()):
 import xbmc,xbmcgui,xbmcvfs
 wanted=(list(args) or ['conv'])[0]
 profile=xbmcvfs.translatePath('special://profile/')
 folder=os.path.join(xbmcvfs.translatePath('special://skin/'),'extras','portrait','graph')
 here=os.path.dirname(os.path.abspath(__file__))
 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   import live_window
   self.guard=live_window.Guard(self)   # ISSUE-123: controls only while this page is open
   self.wanted=wanted;self.others=[];self.first_seen={};self.graphs=th.GraphCache('transfers');self.stop=threading.Event();self.lock=threading.Lock()
   self.refresh();threading.Thread(target=self.loop,daemon=True).start()
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    try:self.refresh()
    except Exception as error:xbmc.log('Kodi iOS Transfers: %s: %s'%(type(error).__name__,error),xbmc.LOGWARNING)
  def refresh(self):
   with self.lock:
    now=time.time();history=th.load(profile)
    nexts=[]   # queue order and words come from the same published snapshot as the jobs
    import work_state
    model=work_state.load(profile,now) or {'mode':'stale','headline':'Updating…','jobs':[],'next':[]}
    props,pct,kind,self.others=page_state(history,now,self.wanted,nexts,model,self.first_seen)
    if kind:
     job=(history.get('jobs') or {}).get(kind) or (history.get('jobs') or {}).get(kind.split('.')[0]) or {}
     if job.get('title')!=props['title']:job={}
     pts=job.get('points') or []
     # Build 194: no flat zero graph while nothing is measured yet; the card says what it is doing instead (props['wait']).
     props['graph']=self.graphs.image(work_state.job_key(model_job(model,kind)),pts,
      props['tint'],folder,'special://skin/extras/portrait/graph',width=tp.PLOT[2],height=tp.PLOT[3],scale=th.device_scale(),
      start=job.get('start'),now=(pts or [[now]])[-1][0]) if not props.get('wait') else ''
    for k,v in props.items():self.setProperty(k,v)
    self.guard.percent(tp.BAR,pct or 0)
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def onClick(self,control):
   if control==tp.BACK:self.finish()
   elif control==tp.HISTORY:
    import tool_windows;tool_windows.open_history(profile)
   elif tp.OTHER<control<=tp.OTHER+tp.OTHERS and control-tp.OTHER<=len(self.others):
    self.wanted=self.others[control-tp.OTHER-1];self.refresh()
  def finish(self):
   self.stop.set();self.guard.close()
 skin=xbmcvfs.translatePath('special://skin/')
 try:page=Page(tp.WINDOW,here,'Default','1080i')
 except RuntimeError:
  # Added while Kodi was running: Kodi's directory cache may not list it yet (build 173). Re-read and try once more.
  xbmcvfs.listdir(os.path.join(skin,'portrait')+'/')
  page=Page(tp.WINDOW,here,'Default','1080i')
 page.doModal()
 if hasattr(page,'stop'):page.stop.set()
 del page

if __name__=='__main__':run(sys.argv[1:])
