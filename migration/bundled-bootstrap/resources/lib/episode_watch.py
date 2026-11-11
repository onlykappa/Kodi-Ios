"""Follow explicitly downloaded shows. Check release dates on app opening, never as a continuous scraper.

Registry contains TMDb show identity and source preferences only. All media still uses the existing
Elementum -> AllDebrid -> Drive queue. Future/undated entries and unsuccessful searches remain pending.
"""
import datetime,fcntl,json,os,time
from pathlib import Path

FILE='followed-shows.json'
COOLDOWN=30*60
MAX_EPISODES=8
MAX_SHOWS=25
AUTO='KodiIOS.AutoPick'
RESULT='KodiIOS.AutoPick.Result'
CANCELED='KodiIOS.AutoPick.Canceled'
BATCH='KodiIOS.SeasonBatch.Until'

def batch_active(window,now=None):
 try:return float(window.getProperty(BATCH) or 0)>(time.time() if now is None else now)
 except (ValueError,TypeError):return False

def active_request(window,now=None):
 now=time.time() if now is None else now;raw=window.getProperty(AUTO)
 try:request=json.loads(raw or '{}')
 except ValueError:request={}
 if float(request.get('until') or 0)>now:return request
 if raw and window.getProperty(AUTO)==raw:window.clearProperty(AUTO)
 return None

def cancel_request(window,request,now=None):
 """Late provider responses must not fall back to an interactive picker after a background search ends."""
 now=time.time() if now is None else now
 try:pending=json.loads(window.getProperty(CANCELED) or '[]')
 except ValueError:pending=[]
 pending=[p for p in pending if float(p.get('until') or 0)>now][-19:]
 window.setProperty(CANCELED,json.dumps(pending+[{'target':request['target'],'until':now+600}]))

def canceled(window,target,now=None,clear=False):
 now=time.time() if now is None else now
 try:pending=json.loads(window.getProperty(CANCELED) or '[]')
 except ValueError:return False
 matching=lambda p:all(str((p.get('target') or {}).get(k) or '')==str(target.get(k) or '') for k in ('tmdb','season','episode'))
 fresh=[p for p in pending if float(p.get('until') or 0)>now]
 found=any(matching(p) for p in fresh)
 if clear:window.setProperty(CANCELED,json.dumps([p for p in fresh if not matching(p)]))
 return found

def path(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap'/FILE
def load(profile):
 try:
  data=json.loads(path(profile).read_text())
  return data if isinstance(data,dict) and isinstance(data.get('shows'),dict) else {'shows':{}}
 except (OSError,ValueError):return {'shows':{}}

def update(profile,change):
 target=path(profile);target.parent.mkdir(parents=True,exist_ok=True)
 with open(str(target)+'.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  state=load(profile);result=change(state)
  tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=1));os.replace(tmp,target)
  return result

def register(profile,tmdb,title,season,episode,preference,now=None):
 """Only a confirmed TV download with an unambiguous show ID enrolls a show; never a canceled picker."""
 try:tmdb=str(int(tmdb));season=int(season);episode=int(episode or 1)
 except (ValueError,TypeError):return False
 if int(tmdb)<1 or season<1 or episode<1 or not title:return False
 now=time.time() if now is None else now
 prefs={k:preference[k] for k in ('quality','hdr','codec','source','size','strict_quality') if k in preference}
 def change(state):
  show=state['shows'].setdefault(tmdb,{'since':now,'floor':[season,episode],'episodes':{},'last_check':0})
  show.update(tmdb=tmdb,title=str(title),preference=prefs)
  return True
 return update(profile,change)

def plan_season(profile,tmdb,title,season,numbers,quality,now=None):
 """Explicit back-catalogue requests, separate from the date floor for following future releases."""
 register(profile,tmdb,title,season,min(numbers),{'quality':quality,'strict_quality':True},now)
 def change(state):
  show=state['shows'][str(tmdb)]
  for n in numbers:
   show.setdefault('planned',{})['%d:%d'%(int(season),int(n))]={'quality':quality,'status':'not_found'}
 update(profile,change)

def record_planned(profile,tmdb,season,episode,queued):
 def change(state):
  show=state['shows'].get(str(tmdb),{});key='%d:%d'%(int(season),int(episode))
  if key in show.get('planned',{}):show['planned'][key]['status']='queued' if queued else 'not_found'
 update(profile,change)

def cancel_planned(profile,tmdb,season,numbers):
 def change(state):
  show=state['shows'].get(str(tmdb),{});planned=show.get('planned',{})
  for n in numbers:
   key='%d:%d'%(int(season),int(n));planned.pop(key,None)
   show.setdefault('episodes',{})[key]={'status':'canceled'}
 update(profile,change)

def selection(window,choice,now=None):
 """The picker records the show's TMDb ID (Elementum's tmdb field can be an episode ID)."""
 now=time.time() if now is None else now
 try:pick=json.loads(window.getProperty('KodiIOS.SeasonPick') or '{}')
 except (ValueError,AttributeError):return {}
 try:
  if not 0<=now-float(pick.get('time') or 0)<300:return {}
  if int(pick.get('show_tmdb') or 0)<1:return {}
 except (ValueError,TypeError):return {}
 if pick.get('selection_name')!=choice.get('name'):return {}
 return pick

def remember_selection(profile,window,choice,title,now=None):
 now=time.time() if now is None else now
 pick=selection(window,choice,now)
 return register(profile,pick.get('show_tmdb'),title,choice.get('season') or pick.get('season'),
                 choice.get('episode') or pick.get('episode') or 1,pick,now)

def library_preference(profile,title):
 """An existing show's best known downloaded resolution; no new source search or media read."""
 import drivelibrary,prepare_downloads
 state=prepare_downloads.load(profile);quality=0
 for item in (state.get('library') or {}).get('items') or []:
  media=drivelibrary.media_key(item.get('name',''),item.get('folder',''))
  if media and media[0]=='episode' and media[1]==drivelibrary.show_key(title):
   quality=max(quality,drivelibrary.quality(item.get('name','')))
 return {'quality':'4k' if quality>=2160 else '1080p' if quality>=1080 or not quality else '720p' if quality>=720 else '480p'}

def day(value):
 try:return datetime.date.fromisoformat(str(value))
 except (ValueError,TypeError):return None

def seasons(details,show,today):
 """Current and announced seasons, without refetching decades of back-catalogue."""
 since=datetime.datetime.fromtimestamp(show['since'],datetime.timezone.utc).date()
 rows=[r for r in details.get('seasons') or [] if int(r.get('season_number') or 0)>=show['floor'][0]]
 aired=[r['season_number'] for r in rows if day(r.get('air_date')) and day(r['air_date'])<=today]
 wanted={max(aired)} if aired else set()
 wanted.update(r['season_number'] for r in rows if day(r.get('air_date')) and day(r['air_date'])>=since)
 for key in ('last_episode_to_air','next_episode_to_air'):
  n=(details.get(key) or {}).get('season_number')
  if isinstance(n,int) and n>=show['floor'][0]:wanted.add(n)
 return sorted(wanted)[:4]

def sweep(profile,get_show,get_season,existing,download,clock=time.time,keep_going=lambda:True,log=lambda *args,**kwargs:None):
 """One bounded opening pass. Dependencies allow future release dates and restarts to be tested now."""
 now=clock();today=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).date();started=now;attempted=queued=0
 shows=sorted(load(profile)['shows'].values(),key=lambda s:s.get('last_check',0))[:MAX_SHOWS]
 for show in shows:
  if not keep_going() or clock()-started>=180 or attempted>=MAX_EPISODES:break
  if now-show.get('last_check',0)<COOLDOWN:continue
  ident=show['tmdb'];since=datetime.datetime.fromtimestamp(show['since'],datetime.timezone.utc).date()
  try:
   details=get_show(ident)
   if not isinstance(details,dict) or str(details.get('id'))!=ident:raise ValueError('Show metadata unavailable')
   episodes={}
   planned=show.get('planned') or {}
   pending_seasons={int(k.split(':')[0]) for k,v in planned.items() if v.get('status')!='owned'}
   for number in sorted(set(seasons(details,show,today))|pending_seasons):
    if not keep_going():return queued
    data=get_season(ident,number)
    if not isinstance(data,dict) or not isinstance(data.get('episodes'),list):raise ValueError('Season metadata unavailable')
    for row in data['episodes']:
     s,e=row.get('season_number',number),row.get('episode_number');aired=day(row.get('air_date'))
     if not isinstance(s,int) or not isinstance(e,int) or s!=number or s<1 or e<1 or not aired:continue
     explicit='%d:%d'%(s,e) in planned
     if aired>today or (not explicit and ((s,e)<tuple(show['floor']) or aired<since)):continue
     episodes[(s,e)]=dict(row,season_number=s,episode_number=e)
   for row in sorted(episodes.values(),key=lambda r:(r['season_number'],r['episode_number'])):
    if not keep_going() or attempted>=MAX_EPISODES or clock()-started>=180:break
    key='%d:%d'%(row['season_number'],row['episode_number'])
    # Queue success, rather than a selected source alone, owns the durable marker.
    prior=planned.get(key) or (show.get('episodes') or {}).get(key) or {}
    if prior.get('status') in ('owned','canceled'):continue
    owned=existing(show,row)
    if prior.get('status')=='queued' and owned!='failed':continue
    if owned and owned!='failed':status='owned'
    else:
     attempted+=1
     wanted=dict(show,preference={'quality':prior['quality'],'strict_quality':True}) if key in planned else show
     status='queued' if download(wanted,row) else 'not_found'
     if status=='queued':queued+=1
    def record(state):
     target=state['shows'].get(ident)
     if target:
      target.setdefault('episodes',{})[key]={'status':status,'checked':clock()}
      if key in target.get('planned',{}):target['planned'][key].update(status=status,checked=clock())
    update(profile,record)
    log('episode_checked',status=status,season=row['season_number'],episode=row['episode_number'])
  except Exception as error:
   # A failed ownership/metadata check never becomes permission for a duplicate download.
   log('check_deferred',error=type(error).__name__)
  finally:
   def checked(state):
    if ident in state['shows']:state['shows'][ident]['last_check']=clock()
   update(profile,checked)
 return queued

def run_open_checks(monitor,ready,foreground,busy,enabled,check):
 """Only a launch/foreground transition schedules a pass. Busy UI defers it; no periodic episode scraping."""
 previous=False;pending=True
 while not monitor.waitForAbort(15):
  active=foreground()
  if active and not previous:pending=True
  previous=active
  if not pending or not active or not ready() or not enabled() or busy():continue
  pending=False
  check()
