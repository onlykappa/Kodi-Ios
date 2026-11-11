"""Full-season fallback: inspect verified sources before offering quality, then queue exact-quality episodes.

Requests use the existing Elementum picker and cloud redirect interception. Scans never select/download media.
Only a queue receipt counts as success. No credentials or source URLs are persisted.
"""
import datetime,json,time,uuid,urllib.parse
import episode_watch as watch
import elementum_download as dl

QUALITY_NAMES={'4k':'4K','1440p':'1440p','1080p':'1080p','720p':'720p','480p':'480p','sd':'SD'}
ORDER=tuple(QUALITY_NAMES)

def note(xbmc,event,**fields):
 try:
  import diagnostics
  diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'season_sources',event,**fields)
 except Exception:pass

def aired(files,today=None):
 today=today or datetime.datetime.now(datetime.timezone.utc).date()
 out=set()
 for row in files or []:
  date=watch.day(row.get('firstaired') or row.get('premiered'))
  try:number=int(row.get('episode') or 0)
  except (TypeError,ValueError):continue
  if number>0 and row.get('filetype')!='directory' and date and date<=today:out.add(number)
 return sorted(out)

def availability(sources,numbers):
 """Only qualities actually returned by the verified picker, with per-episode coverage."""
 return [(q,sum(q in sources.get(n,[]) for n in numbers)) for q in ORDER
         if any(q in sources.get(n,[]) for n in numbers)]

def pending_episodes(profile,tmdb,season,numbers):
 """Already accepted episodes must not get another source while their transfer is waiting or paused."""
 import debrid_drive,drivelibrary
 have=set()
 for job in debrid_drive.load(profile).get('jobs',[]):
  if str(job.get('show_tmdb') or '')!=str(tmdb) or str(job.get('season'))!=str(season):continue
  if job.get('status') in ('done','failed'):continue
  if job.get('kind')=='season' and not job.get('files'):return set(numbers)
  try:have.add(int(job.get('episode') or 0))
  except (TypeError,ValueError):pass
  for file in job.get('files') or []:
   info=drivelibrary.parse(file.get('drive_name') or file.get('path',''))
   if str(info.get('season'))==str(season):
    try:have.add(int(info.get('episode') or 0))
    except (TypeError,ValueError):pass
 return have.intersection(numbers)

def request(home,tmdb,season,episode=None,purpose='scan',quality=None,follow=None):
 import elementum_cloud
 if watch.active_request(home):raise RuntimeError('Another episode search is running. Try again when it finishes.')
 ident=uuid.uuid4().hex
 target={'tmdb':str(tmdb),'season':int(season),'episode':int(episode) if episode else None}
 wanted={'request_id':ident,'target':target,'purpose':purpose,'mode':0,'until':time.time()+600,
         'profile':{'quality':quality,'strict_quality':True} if quality else {}}
 watch.canceled(home,target,clear=True)
 home.clearProperty(watch.RESULT);home.clearProperty('KodiIOS.AutoPick.Queued')
 home.setProperty(watch.AUTO,json.dumps(wanted));result={}
 try:
  url=dl.plugin_url('episode' if episode else 'season',tmdb,season,episode)
  route=(lambda url:urllib.parse.urlsplit(url).path.rstrip('/') in ('/play','/download')) if purpose=='scan' else (
    (lambda url:elementum_cloud.route(url)) if purpose=='packs' else
    (lambda url:elementum_cloud.route(url,quiet=True,request_id=ident)))
  # A scan reaches the search route, but consumes any selected-media redirect.
  reached=(follow or dl.follow)(url,timeout=600 if purpose=='packs' else 120,route=route)
  try:result=json.loads(home.getProperty(watch.RESULT) or '{}')
  except ValueError:result={}
  if not result and purpose in ('scan','packs') and reached==url.replace(dl.PLUGIN_PREFIX,dl.ENGINE,1):
   # Elementum answers a no-results search without opening a picker. A failed HTTP request raises above.
   result={'request_id':ident,'qualities':[],'packs':False}
  if result.get('request_id')!=ident or result.get('error'):return {}
  if purpose=='queue':
   try:receipt=json.loads(home.getProperty('KodiIOS.AutoPick.Queued') or '{}')
   except ValueError:receipt={}
   result['queued']=receipt.get('request_id')==ident and receipt.get('queued') is True
  return result
 finally:
  if result.get('request_id')!=ident or (purpose=='queue' and not result.get('queued')):watch.cancel_request(home,wanted)
  try:current=json.loads(home.getProperty(watch.AUTO) or '{}')
  except ValueError:current={}
  if current.get('request_id')==ident:home.clearProperty(watch.AUTO)

def run(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,search=None):
 """An explicit season interaction owns the search lane until its chooser/queueing finishes."""
 if watch.batch_active(home) or watch.active_request(home):
  dialog.ok('Download season','Another episode search is running. Try again when it finishes.');return []
 lease=str(time.time()+600*(len(numbers)+1))
 home.setProperty(watch.BATCH,lease)
 try:return _run(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,search)
 finally:
  if home.getProperty(watch.BATCH)==lease:home.clearProperty(watch.BATCH)

def _run(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,search=None):
 """Return queued episode numbers. A cancelled scan/quality chooser creates no durable plan."""
 search=search or (lambda n,purpose,q=None:request(home,tmdb,season,n,purpose,q))
 have=set(owned)|pending_episodes(profile,tmdb,season,numbers)
 remaining=[n for n in numbers if n not in have]
 if not remaining:
  dialog.ok('Download season','Every aired episode is already downloaded or queued.');return []
 progress=gui.DialogProgress();progress.create('Checking available sources','Finding episode qualities…')
 sources={}
 try:
  for i,n in enumerate(remaining):
   if progress.iscanceled() or xbmc.Monitor().abortRequested():return []
   progress.update(int(100*i/len(remaining)),'Episode %d · %d of %d'%(n,i+1,len(remaining)))
   try:sources[n]=search(n,'scan').get('qualities') or []
   except Exception as error:
    note(xbmc,'scan_deferred',episode=n,error=type(error).__name__);sources[n]=[]
 finally:progress.close()
 choices=availability(sources,remaining)
 note(xbmc,'scan_complete',episodes=len(remaining),coverage=dict(choices))
 if not choices:
  dialog.ok('Download season','No usable episode sources were found. Try again later.');return []
 labels=['%s · %d of %d available'%(QUALITY_NAMES[q],count,len(remaining)) for q,count in choices]
 index=dialog.select('Season %s: download quality'%season,labels)
 if index<0 or index>=len(choices):return []
 quality=choices[index][0]
 import transfer_control
 if transfer_control.paused(profile,'up'):
  action=dialog.select('Uploads paused',['Download now · resume uploads','Keep queued · uploads stay paused'])
  if action<0:return []
  if action==0:transfer_control.set_paused(profile,'up',False)
 watch.plan_season(profile,tmdb,title,season,remaining,quality)
 queued=[];processed=0;progress=gui.DialogProgress();progress.create('Downloading season %s'%season,'Queueing episodes…')
 try:
  for i,n in enumerate(remaining):
   if progress.iscanceled() or xbmc.Monitor().abortRequested():
    watch.cancel_planned(profile,tmdb,season,remaining[i:]);break
   progress.update(int(100*i/len(remaining)),'Episode %d · %s'%(n,QUALITY_NAMES[quality]))
   result={}
   if quality in sources[n]:
    try:result=search(n,'queue',quality)
    except Exception as error:note(xbmc,'queue_deferred',episode=n,error=type(error).__name__)
   success=result.get('queued') is True
   watch.record_planned(profile,tmdb,season,n,success)
   note(xbmc,'episode_result',episode=n,quality=quality,queued=success)
   processed+=1
   if success:queued.append(n)
 finally:progress.close()
 text='%d queued · %d waiting for %s'%(len(queued),processed-len(queued),QUALITY_NAMES[quality])
 dialog.notification('Season %s'%season,text,gui.NOTIFICATION_INFO,6000)
 return queued
