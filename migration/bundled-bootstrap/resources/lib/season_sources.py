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
