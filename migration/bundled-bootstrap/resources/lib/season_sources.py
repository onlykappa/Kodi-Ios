"""Full-season fallback: inspect verified sources before offering quality, then queue exact-quality episodes.

Requests use the existing Elementum picker and cloud redirect interception. Scans never select/download media.
Only a queue receipt counts as success. No credentials or source URLs are persisted.
"""
import datetime,json,time,uuid,urllib.parse
import episode_watch as watch
import elementum_download as dl

QUALITY_NAMES={'4k':'4K','1440p':'1440p','1080p':'1080p','720p':'720p','480p':'480p','sd':'SD'}
ORDER=tuple(QUALITY_NAMES)
SCAN_SECONDS=60
EPISODE_SECONDS=25

def note(xbmc,event,**fields):
 try:
  import diagnostics
  diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'season_sources',event,**fields)
 except Exception:pass

def aired(files,today=None):
 """Episode numbers that have aired. Owner (2026-11-12, Naruto Shippuden S1, 2007): "No aired episodes could be
 verified" for a season that has every episode. An episode is left out only when its air date is in the future;
 one without a date counts as aired unless it comes after an episode still to air (TMDb Helper does not always
 fill firstaired), so only a brand-new season with nothing out yet is empty."""
 today=today or datetime.datetime.now(datetime.timezone.utc).date()
 out=set();undated=set();future=set()
 for row in files or []:
  try:number=int(row.get('episode') or 0)
  except (TypeError,ValueError):continue
  if number<=0 or row.get('filetype')=='directory':continue
  date=watch.day(row.get('firstaired') or row.get('premiered') or row.get('aired'))
  if not date:undated.add(number)
  elif date<=today:out.add(number)
  else:future.add(number)
 # An undated episode before the first future one has aired (a running season's undated tail has not).
 first_future=min(future) if future else None
 out|={n for n in undated if first_future is None or n<first_future}
 return sorted(out)

def availability(sources,numbers):
 """Only qualities actually returned by the verified picker, with per-episode coverage."""
 return [(q,sum(q in sources.get(n,[]) for n in numbers)) for q in ORDER
         if any(q in sources.get(n,[]) for n in numbers)]

FULL_NAMES={'4k':'4K Ultra HD','1440p':'1440p QHD','1080p':'1080p Full HD','720p':'720p HD','480p':'480p','sd':'SD'}
GREEN='FF30D158';ORANGE='FFFF9F0A'

def spans(numbers):
 """[1,2,3,5,7,8] -> '1-3, 5, 7-8' (episode numbers in a sentence)."""
 out=[];run=[]
 for n in sorted(numbers):
  if run and n==run[-1]+1:run.append(n)
  else:
   if run:out.append(run)
   run=[n]
 if run:out.append(run)
 return ', '.join('%d'%r[0] if len(r)==1 else '%d\u2013%d'%(r[0],r[-1]) for r in out)

def quality_rows(choices,sources,remaining):
 """Owner-approved season picker (mockup round 3, board 3): each quality in bold, and under it how many of the
 episodes it covers (green when all of them), or which are ready now and which wait for that quality."""
 rows=[]
 for q,count in choices:
  name='[B]%s[/B]'%FULL_NAMES.get(q,QUALITY_NAMES.get(q,q))
  if count>=len(remaining):
   detail='[COLOR %s]All %d episode%s[/COLOR]'%(GREEN,count,'' if count==1 else 's')
  else:
   have=[n for n in remaining if q in sources.get(n,[])];wait=[n for n in remaining if n not in have]
   # Kept short enough for one line on the phone (rig: the longer wording was cut off).
   detail='[COLOR %s]%d of %d[/COLOR] \u00b7 %s now, %s wait%s'%(ORANGE,count,len(remaining),spans(have),spans(wait),
    's' if len(wait)==1 else '')
  rows.append((name,detail))
 return rows

FOOT='Episodes without your quality are not downloaded in a lower one. They are tried again when you open the app.'

def sheet_spec(title,season,choices,sources,remaining):
 """Board 15: each quality with a tag (green ALL n, orange k OF n), what is ready now, and a coverage bar."""
 rows=[]
 for q,count in choices:
  full=count>=len(remaining)
  have=[n for n in remaining if q in sources.get(n,[])];wait=[n for n in remaining if n not in have]
  rows.append({'label':FULL_NAMES.get(q,QUALITY_NAMES.get(q,q)),'tag':'ALL %d'%count if full else '%d OF %d'%(count,len(remaining)),
               'tag_kind':'best' if full else 'warn',
               'detail':'%d of %d episodes'%(count,len(remaining)) if full else 'Episodes %s now \u00b7 %s wait'%(spans(have),spans(wait)),
               'cover':100.0*count/max(1,len(remaining))})
 return {'heading':'%s \u00b7 Season %s'%(title,season),'sub':'No full-season pack found. These get each episode separately.',
         'rows':rows,'foot':FOOT}

def pick_quality(gui,dialog,title,season,choices,sources,remaining):
 try:
  import choice_sheet
  if hasattr(gui,'WindowXMLDialog'):return choice_sheet.choose(sheet_spec(title,season,choices,sources,remaining),xbmcgui=gui)
 except ImportError:pass
 rows=quality_rows(choices,sources,remaining)
 items=[gui.ListItem(label=n,label2=d) for n,d in rows] if hasattr(gui,'ListItem') else ['%s\x1f%s'%r for r in rows]
 return dialog.select('%s \u00b7 Season %s'%(title,season),items)

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

def request(home,tmdb,season,episode=None,purpose='scan',quality=None,follow=None,cancel=None,timeout=None,lane=''):
 import elementum_cloud
 if watch.active_request(home,lane=lane):raise RuntimeError('Another episode search is running. Try again when it finishes.')
 ident=uuid.uuid4().hex
 target={'tmdb':str(tmdb),'season':int(season),'episode':int(episode) if episode else None}
 wanted={'request_id':ident,'target':target,'purpose':purpose,'mode':0,'until':time.time()+600,
         'profile':{'quality':quality,'strict_quality':True} if quality else {}}
 watch.canceled(home,target,clear=True)
 home.clearProperty(watch.RESULT+lane);home.clearProperty('KodiIOS.AutoPick.Queued'+lane)
 home.setProperty(watch.AUTO+lane,json.dumps(wanted));result={}
 try:
  url=dl.plugin_url('episode' if episode else 'season',tmdb,season,episode)
  route=(lambda url:urllib.parse.urlsplit(url).path.rstrip('/') in ('/play','/download')) if purpose=='scan' else (
    (lambda url:elementum_cloud.route(url)) if purpose=='packs' else
    (lambda url:elementum_cloud.route(url,quiet=True,request_id=ident)))
  # A scan reaches the search route, but consumes any selected-media redirect.
  options={'timeout':timeout if timeout is not None else (600 if purpose=='packs' else 120),'route':route}
  if cancel is not None:options['cancel']=cancel
  reached=(follow or dl.follow)(url,**options)
  try:result=json.loads(home.getProperty(watch.RESULT+lane) or '{}')
  except ValueError:result={}
  if not result and purpose in ('scan','packs') and reached==url.replace(dl.PLUGIN_PREFIX,dl.ENGINE,1):
   # Elementum answers a no-results search without opening a picker. A failed HTTP request raises above.
   result={'request_id':ident,'qualities':[],'packs':False}
  if result.get('request_id')!=ident or result.get('error'):return {}
  if purpose=='queue':
   try:receipt=json.loads(home.getProperty('KodiIOS.AutoPick.Queued'+lane) or '{}')
   except ValueError:receipt={}
   result['queued']=receipt.get('request_id')==ident and receipt.get('queued') is True
  if cancel and cancel() and not result.get('queued'):raise dl.Canceled('Source search canceled')
  return result
 finally:
  if result.get('request_id')!=ident or (purpose=='queue' and not result.get('queued')):watch.cancel_request(home,wanted)
  try:current=json.loads(home.getProperty(watch.AUTO+lane) or '{}')
  except ValueError:current={}
  if current.get('request_id')==ident:home.clearProperty(watch.AUTO+lane)

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
 have=set(owned)|pending_episodes(profile,tmdb,season,numbers)
 remaining=[n for n in numbers if n not in have]
 if not remaining:
  dialog.ok('Download season','Every aired episode is already downloaded or queued.');return []
 progress=gui.DialogProgress();progress.create('Checking available sources','Finding episode qualities…')
 sources={};deadline=time.monotonic()+SCAN_SECONDS;monitor=xbmc.Monitor()
 def canceled():return progress.iscanceled() or monitor.abortRequested()
 def lookup(n,purpose,q=None):
  if search:return search(n,purpose,q)
  scanning=purpose=='scan'
  stop=(lambda:canceled() or time.monotonic()>=deadline) if scanning else canceled
  timeout=min(EPISODE_SECONDS,max(.1,deadline-time.monotonic())) if scanning else 120
  return request(home,tmdb,season,n,purpose,q,cancel=stop,timeout=timeout)
 try:
  for i,n in enumerate(remaining):
   if canceled():return []
   if time.monotonic()>=deadline:break
   progress.update(int(100*i/len(remaining)),'Episode %d · %d of %d'%(n,i+1,len(remaining)))
   try:sources[n]=lookup(n,'scan').get('qualities') or []
   except Exception as error:
    note(xbmc,'scan_deferred',episode=n,error=type(error).__name__);sources[n]=[]
  if canceled():return []
 finally:progress.close()
 choices=availability(sources,remaining)
 note(xbmc,'scan_complete',episodes=len(remaining),coverage=dict(choices))
 if not choices:
  dialog.ok('Download season','No usable episode sources were found. Try again later.');return []
 index=pick_quality(gui,dialog,title,season,choices,sources,remaining)
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
   if quality in sources.get(n,[]):
    try:result=lookup(n,'queue',quality)
    except Exception as error:
     note(xbmc,'queue_deferred',episode=n,error=type(error).__name__)
     if canceled():
      watch.cancel_planned(profile,tmdb,season,remaining[i:]);break
   success=result.get('queued') is True
   watch.record_planned(profile,tmdb,season,n,success)
   note(xbmc,'episode_result',episode=n,quality=quality,queued=success)
   processed+=1
   if success:queued.append(n)
 finally:progress.close()
 text='%d queued · %d waiting for %s'%(len(queued),processed-len(queued),QUALITY_NAMES[quality])
 dialog.notification('Season %s'%season,text,gui.NOTIFICATION_INFO,6000)
 return queued


def build(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,names=None,search=None):
 """Build Season (owner, 2026-11-12: always, never a ready-made pack; season-pack-mockups boards B, C, D): pick a
 quality, look up every episode at it (the next quality down when an episode only exists lower), show what was found,
 then queue each episode. Returns the queued episode numbers."""
 if watch.batch_active(home) or watch.active_request(home):
  dialog.ok('Download season','Another episode search is running. Try again when it finishes.');return []
 lease=str(time.time()+600*(len(numbers)+1))
 home.setProperty(watch.BATCH,lease)
 try:return _build(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,names or {},search)
 finally:
  if home.getProperty(watch.BATCH)==lease:home.clearProperty(watch.BATCH)

def lanes(items,work,show,stop,halt,count):
 """Owner (2026-11-12): "fix the speed for shows" (32 episodes took about 3 minutes to look up and as long to add, one
 at a time). work(item, lane) runs for every item, up to `count` at once, each in its own lane (episode_watch.LANES);
 this thread keeps show(done, current) up to date and stop() checked (its short wait lets the card's Close and
 Cancel through); stop() true sets halt['stop'] and the lanes take no new item."""
 import threading
 todo=list(items);lock=threading.Lock();state={'done':0,'current':items[0] if items else None}
 def worker(lane):
  while not halt['stop']:
   with lock:
    if not todo:return
    item=todo.pop(0);state['current']=item
   try:work(item,lane)
   finally:
    with lock:state['done']+=1
 if count<=1:
  for item in items:
   if stop():halt['stop']=True;return
   show(state['done'],item);state['current']=item
   work(item,'');state['done']+=1
  if stop():halt['stop']=True
  return
 threads=[threading.Thread(target=worker,args=(watch.LANES[k],),daemon=True) for k in range(min(count,len(items)))]
 for t in threads:t.start()
 while any(t.is_alive() for t in threads):
  show(state['done'],state['current'])
  if stop():halt['stop']=True
  for t in threads:t.join(0.1)
 if stop():halt['stop']=True

def _build(xbmc,gui,dialog,home,profile,tmdb,title,season,numbers,owned,names,search):
 import season_sheet as ss
 have=set(owned)|pending_episodes(profile,tmdb,season,numbers)
 remaining=[n for n in numbers if n not in have]
 if not remaining:
  dialog.ok('Download season','Every aired episode is already downloaded or queued.');return []
 quality=ss.pick_quality(gui,title,season,len(remaining))
 if not quality:return []
 monitor=xbmc.Monitor();card=ss.Card(gui)
 # Owner log 5169a460 (build 290): Close and Cancel on the card did nothing. Kodi hands a window's taps to this script
 # only while it waits in Kodi (sleep / waitForAbort); the lookups waited on Elementum the whole time. stop() runs every
 # 0.1 s during those waits, and its short waitForAbort lets the taps through.
 def stop():return monitor.waitForAbort(0.01) or card.canceled
 halt={'stop':False}
 def lookup(n,purpose,q=None,lane=''):
  if search:return search(n,purpose,q)
  return request(home,tmdb,season,n,purpose,q,cancel=lambda:halt['stop'] or card.canceled,
                 timeout=EPISODE_SECONDS if purpose=='scan' else 120,lane=lane)
 picks={};details={}
 def scan(n,lane):
  try:found=lookup(n,'scan',lane=lane)
  except Exception as error:
   note(xbmc,'scan_deferred',episode=n,error=type(error).__name__);found={}
  got=ss.best_for(found.get('qualities') or [],quality)
  details[n]=(found.get('details') or {}).get(got,'') if got else ''
  picks[n]=(got,(found.get('sizes') or {}).get(got) if got else None)
 try:
  lanes(remaining,scan,lambda done,current:card.show(ss.building_props(season,quality,title,done,len(remaining),
        sum(1 for v in picks.values() if v[0]),current)),stop,halt,len(watch.LANES) if not search else 1)
  if halt['stop']:return []
 finally:card.close()
 model=ss.ready_model(title,season,quality,picks,names,details)
 note(xbmc,'build_scanned',episodes=len(remaining),quality=quality,found=len(model['episodes']),
      lower=sum(1 for n in model['episodes'] if picks[n][0]!=quality))
 if not model['episodes']:
  dialog.ok('Download season','No episode of Season %s was found. Try again later.'%season);return []
 if not ss.confirm_ready(gui,model):return []
 import transfer_control
 if transfer_control.paused(profile,'up'):transfer_control.set_paused(profile,'up',False)   # Download All means now
 episodes=model['episodes']
 watch.plan_season(profile,tmdb,title,season,episodes,quality)
 queued=[];tried=set();card=ss.Card(gui);halt['stop']=False
 def add(n,lane):
  result={}
  try:result=lookup(n,'queue',picks[n][0],lane=lane)
  except Exception as error:note(xbmc,'queue_deferred',episode=n,error=type(error).__name__)
  success=result.get('queued') is True
  watch.record_planned(profile,tmdb,season,n,success)
  note(xbmc,'episode_result',episode=n,quality=picks[n][0],queued=success)
  tried.add(n)
  if success:queued.append(n)
 try:
  lanes(episodes,add,lambda done,current:card.show(ss.queueing_props(season,quality,title,done,len(episodes))),stop,halt,
        len(watch.LANES) if not search else 1)
  if halt['stop']:watch.cancel_planned(profile,tmdb,season,[n for n in episodes if n not in tried])
 finally:card.close()
 queued.sort()
 if len(queued)>1 and not search:
  try:
   import debrid_drive
   debrid_drive.order_season(profile,tmdb,season)   # added three at a time: back into episode order
  except Exception as error:note(xbmc,'order_failed',error=type(error).__name__)
 if queued or stop():
  dialog.notification('Season %s'%season,'%d episode%s added to your downloads'%(len(queued),'' if len(queued)==1 else 's'),gui.NOTIFICATION_INFO,6000)
 else:   # owner log 15e6cbc4: "0 episodes added" read like success
  dialog.notification('Season %s'%season,'No episode could be added. Try again in a moment.',gui.NOTIFICATION_WARNING,8000)
 return queued
