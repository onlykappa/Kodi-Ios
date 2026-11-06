"""The Transfers page (portrait/IOSTransfers.xml), opened by tapping a transfer card in Notifications (owner: "I only
want the graph to show in notifications if i tap on it"). One job at a time (owner, build 172): the graph follows the
card that was tapped; when that job ends it moves on to the next one still running. Refreshes every 2 s."""
import os,sys,threading,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import transfer_history as th,transfers_page as tp

BACK=(9,10,92,110)
GB=1024**3

def page_state(history,now,wanted,queued):
 """(window properties, bar percent, shown kind, the other running kinds) for one refresh (pure: tested without Kodi)."""
 kind=th.pick(history,wanted,now)
 props={k:'' for k in ('kind','tint','title','now','peak','avg','started','from','line','graph')}
 pct=0.0;others=[]
 if kind:
  job=history['jobs'][kind]
  pts=job.get('points') or []
  done,total=float(job.get('done') or 0),float(job.get('total') or 0)
  rate=pts[-1][1] if pts else 0.0
  if kind=='conv':
   pct=float(job.get('pct') or 0)
   line=' · '.join(x for x in ('%s read'%th.size(done) if done else '','%d%% done'%pct if pct>=1 else '') if x) or 'Starting'
  else:
   pct=100.0*done/total if total else 0.0
   line='%s of %s'%(th.size(done),th.size(total)) if total else ''
  left=_left(kind,job,rate,pct,now)
  if left:line=' · '.join(x for x in (line,left) if x)
  props.update(kind=th.LABELS[kind].upper(),tint=th.TINTS[kind],title=job['title'],now=th.mb(rate),peak=th.mb(job.get('peak')),
               avg=th.mb(job.get('sum',0)/max(1,job.get('n',1))),started=th.ago(now-job['start']),line=line)
  props['from']=th.ago(now-job['start']).replace('just now','a moment ago')
  others=[k for k in th.running(history,now) if k!=kind]
 for n in range(1,tp.OTHERS+1):
  k=others[n-1] if n<=len(others) else ''
  j=(history.get('jobs') or {}).get(k,{})
  props['other.%d.label'%n]=('%s %s'%(th.LABELS[k],j.get('title',''))) if k else ''
  props['other.%d.tint'%n]=th.TINTS.get(k,'')
  props['other.%d.rate'%n]=th.mb((j.get('points') or [[0,0]])[-1][1]) if k else ''
 finished=[f for f in history.get('finished') or [] if now-f.get('end',0)<24*3600]
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
 return props,pct,kind,others

def _left(kind,job,rate,pct,now):
 """'about 25 min left' from the job's own pace, or ''."""
 import prepare_downloads
 if kind=='conv':
  if pct<1 or now<=job['start']:return ''
  seconds=(now-job['start'])*(100-pct)/pct
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
   nexts.append((drivelibrary.display_title(name),'convert · %.1f GB'%(int(src.get('size') or 0)/GB)))
 return nexts

def run(args=()):
 import xbmc,xbmcgui,xbmcvfs
 wanted=(list(args) or ['conv'])[0]
 profile=xbmcvfs.translatePath('special://profile/')
 folder=os.path.join(xbmcvfs.translatePath('special://skin/'),'extras','portrait','graph')
 here=os.path.dirname(os.path.abspath(__file__))
 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.wanted=wanted;self.others=[];self.counter=0;self.stop=threading.Event();self.lock=threading.Lock()
   self.refresh();threading.Thread(target=self.loop,daemon=True).start()
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    try:self.refresh()
    except Exception as error:xbmc.log('Kodi iOS Transfers: %s: %s'%(type(error).__name__,error),xbmc.LOGWARNING)
  def refresh(self):
   with self.lock:
    now=time.time();history=th.load(profile)
    try:nexts=queue_lists(profile,now)
    except Exception:nexts=[]
    props,pct,kind,self.others=page_state(history,now,self.wanted,nexts)
    if kind:
     job=history['jobs'][kind]
     self.counter+=1
     props['graph']='special://skin/extras/portrait/graph/'+th.write_graph(folder,self.counter,th.render(job.get('points') or [],th.TINTS[kind],start=job['start'],now=now))
    for k,v in props.items():self.setProperty(k,v)
    try:self.getControl(tp.BAR).setPercent(float(pct))
    except Exception:pass
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def onClick(self,control):
   if control==tp.BACK:self.finish()
   elif control==tp.HISTORY:
    import tool_windows;tool_windows.open_history(profile)
   elif tp.OTHER<control<=tp.OTHER+tp.OTHERS and control-tp.OTHER<=len(self.others):
    self.wanted=self.others[control-tp.OTHER-1];self.refresh()
  def finish(self):
   self.stop.set();self.close()
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
