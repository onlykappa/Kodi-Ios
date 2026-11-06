"""The Transfers page (portrait/IOSTransfers.xml), opened by tapping a transfer card in Notifications (owner: "I only
want the graph to show in notifications if i tap on it"). Refreshes every 2 s: the speed graph for the chosen range
(transfer_history), Down / Up / Peak / Today, every running transfer, what is next and what finished today."""
import os,sys,threading,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import transfer_history as th,transfers_page as tp

BACK=(9,10,92,110)
GB=1024**3

def page_state(history,now,range_key,downloads,uploads,preparing,queued,done):
 """Window properties for one refresh (pure: tested without Kodi)."""
 s=th.stats(history,range_key,now)
 props={'range':range_key,
        'down.value':th.mb(s['down']),'down.mbps':th.mbps(s['down']),
        'up.value':th.mb(s['up']),'up.mbps':th.mbps(s['up']),
        'peak.value':th.mb(s['peak']),'peak.mbps':th.mbps(s['peak']),
        'today.value':'%.1f GB'%(s['today']/GB),'today.mbps':'moved today',
        'limit':'– – your upload limit · %s'%th.mbps(th.UPLOAD_LIMIT)}
 jobs=[]
 for d in downloads:
  jobs.append(dict(kind='Downloading',tint=tp.BLUE,title=d.get('title',''),pct=d.get('progress',0),
                   line='  ·  '.join(x for x in (d.get('line',''),d.get('speed','')) if x),poster=d.get('poster','')))
 for u in uploads:
  jobs.append(dict(kind='AllDebrid is fetching it' if u.get('stage')=='fetching' else 'Uploading to Google Drive',tint=tp.GREEN,
                   title=u.get('title',''),pct=u.get('progress',0),line=u.get('line',''),poster=u.get('poster','')))
 for c in preparing:
  jobs.append(dict(kind='Converting',tint=tp.PURPLE,title=c.get('title',''),pct=c.get('progress',0),
                   line=c.get('line',''),poster=c.get('poster','')))
 props['has.jobs']='true' if jobs else ''
 for n in range(1,tp.JOBS+1):
  j=jobs[n-1] if n<=len(jobs) else {}
  for k in ('kind','tint','title','line','poster'):props['job.%d.%s'%(n,k)]=str(j.get(k,''))
 for name,rows in (('next',queued),('done',done)):
  for n in range(1,(tp.NEXT if name=='next' else tp.DONE)+1):
   r=rows[n-1] if n<=len(rows) else ('','')
   props['%s.%d.title'%(name,n)],props['%s.%d.line'%(name,n)]=r
 return props,[j.get('pct',0) for j in jobs[:tp.JOBS]]

def queue_lists(profile,now):
 """(up next, done today) as [(title, line)] from the preparation queue and the AllDebrid jobs."""
 import drivelibrary,prepare_downloads,debrid_drive
 state=prepare_downloads.load(profile);running=(state.get('current') or {}).get('title')
 nexts=[];done=[]
 start=time.mktime(time.localtime(now)[:3]+(0,0,0,0,0,-1))
 for job in (state.get('jobs') or {}).values():
  src=job.get('source') or {};name=src.get('name','')
  if job.get('status') in ('waiting','paused') and name!=running and not job.get('kept') and not job.get('blocked'):
   nexts.append((drivelibrary.display_title(name),'convert · %.1f GB'%(int(src.get('size') or 0)/GB)))
  if job.get('status')=='done' and (job.get('completed') or 0)>=start:
   done.append((drivelibrary.display_title(name),'ready for AirPlay · %.1f GB'%(int(src.get('size') or 0)/GB)))
 for job in debrid_drive.load(profile).get('jobs',[]):
  if job.get('status')=='done' and (job.get('finished') or 0)>=start:
   size=sum(int(f.get('size') or 0) for f in job.get('files',[]))
   done.append((job.get('title') or job.get('name',''),'to Google Drive · %.1f GB'%(size/GB)))
 return nexts,done

def run(args=()):
 import xbmc,xbmcgui,xbmcvfs
 import notices,prepare_downloads
 profile=xbmcvfs.translatePath('special://profile/')
 folder=os.path.join(xbmcvfs.translatePath('special://skin/'),'extras','portrait','graph')
 here=os.path.dirname(os.path.abspath(__file__))
 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.range='5min';self.counter=0;self.stop=threading.Event();self.lock=threading.Lock()
   self.refresh();threading.Thread(target=self.loop,daemon=True).start()
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    try:self.refresh()
    except Exception as error:xbmc.log('Kodi iOS Transfers: %s: %s'%(type(error).__name__,error),xbmc.LOGWARNING)
  def refresh(self):
   with self.lock:
    now=time.time();history=th.load(profile)
    try:downloads=notices.downloads()
    except Exception:downloads=[]
    try:uploads=notices.uploads(profile)
    except Exception:uploads=[]
    try:preparing=[c for c in prepare_downloads.cards(profile) if c.get('running')]
    except Exception:preparing=[]
    nexts,done=queue_lists(profile,now)
    props,bars=page_state(history,now,self.range,downloads,uploads,preparing,nexts,done)
    if any(any(v) for v in th.series(history,self.range,now)):
     self.counter+=1
     props['graph']='special://skin/extras/portrait/graph/'+th.write_graph(folder,self.counter,th.render(th.series(history,self.range,now)))
    else:props['graph']=''
    for k,v in props.items():self.setProperty(k,v)
    for n in range(1,tp.JOBS+1):
     try:self.getControl(tp.JOB_BAR+n).setPercent(float(bars[n-1]) if n<=len(bars) else 0.0)
     except Exception:pass
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def onClick(self,control):
   if control==tp.BACK:self.finish()
   elif 9701<=control<9701+len(tp.RANGES):self.range=tp.RANGES[control-9701][0];self.refresh()
  def finish(self):
   self.stop.set();self.close()
 page=Page(tp.WINDOW,here,'Default','1080i')
 page.doModal()
 if hasattr(page,'stop'):page.stop.set()
 del page

if __name__=='__main__':run(sys.argv[1:])
