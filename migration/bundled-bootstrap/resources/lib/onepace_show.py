"""One Pace as a show inside the app (owner, 2026-11-28): the saved copy of the page, the rows the show page lists, the download requests and the new-episode check.
No Kodi imports: the plugin (ios_onepace.py) and the service (service.py) pass in what they have, tests pass fakes. The parsing is onepace.py."""
import json,os,re,time
from pathlib import Path
import onepace

FOLDER='addon_data/service.kodi.ios.bootstrap'
CACHE='onepace-seasons.json'
STATE='onepace-state.json'
SCHEMA=2             # the saved copy's shape (2: pictures and arc descriptions); an older copy is read again at once
FRESH=3600.0          # the page is read at most hourly; a saved copy older than this is used only when the site cannot be reached
CHECK_EVERY=3600.0
UA='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) KodiIOS'

def folder(profile):
 target=Path(str(profile))/FOLDER;target.mkdir(parents=True,exist_ok=True);return target

def read_json(path,default):
 try:return json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def write_json(path,data):
 target=Path(path);temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');os.replace(temp,target)

def fetch(url,timeout=25):
 """The text of a page (the network lives here only; callers inject their own for tests)."""
 import urllib.request
 request=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'en'})
 with urllib.request.urlopen(request,timeout=timeout) as answer:return answer.read().decode('utf-8','replace')

def seasons(profile,get=None,now=time.time,force=False):
 """(seasons, error): the show as onepace.seasons lists it. Read from the site at most hourly and kept in the profile; when the site cannot be read the kept copy
 is used and the reason returned (a first run with no kept copy gives [] and the reason)."""
 get=get or fetch
 path=folder(profile)/CACHE;kept=read_json(path,{})
 if not force and kept.get('seasons') and kept.get('schema')==SCHEMA and 0<=now()-float(kept.get('at') or 0)<FRESH:return kept['seasons'],''
 try:
  found=onepace.seasons(onepace.parse_watch(get(onepace.WATCH)))
  if not found:raise ValueError('the watch page listed no arcs')
 except Exception as error:
  return kept.get('seasons') or [],'%s: %s'%(type(error).__name__,str(error)[:120])
 write_json(path,{'at':now(),'schema':SCHEMA,'seasons':found});return found,''

def find(seasons_list,number):
 for s in seasons_list:
  if s['season']==int(number):return s
 return None

def season_rows(seasons_list):
 """What the arc row lists: one entry per arc, named by the arc (not "Season N"), with its summary, chapter range and picture."""
 rows=[]
 for s in seasons_list:
  plot=[]
  if s.get('description'):plot.append(s['description'])
  if s['chapters']:plot.append('Manga chapters %s.'%s['chapters'])
  if s['upcoming']:plot.append('No episodes released yet.')
  elif s['dubbed']<len(s['episodes']):plot.append('%d of %d episodes have an English dub; the others play in Japanese with English subtitles.'%(s['dubbed'],len(s['episodes'])))
  rows.append({'season':s['season'],'label':s['title'],'plot':' '.join(plot),'episodes':len(s['episodes']),'upcoming':s['upcoming'],
               'fanart':onepace.image_url(s.get('image'),1920),'poster':onepace.image_url(s.get('image'),1080),'chapters':s['chapters']})
 return rows

def episode_rows(season):
 """What an arc's episode list shows: number, title, duration, plot, and whether it is Japanese only."""
 rows=[]
 for e in season['episodes']:
  rows.append({'season':season['season'],'episode':e['number'],'label':e['title'],'minutes':e['minutes'],'plot':e['plot'],'japanese_only':e['japanese_only'],
               'audio':e['audio'],'resolution':e['resolution'],'thumb':onepace.image_url(e.get('image'),640),'fanart':onepace.image_url(season.get('image'),1920)})
 return rows

def play_target(seasons_list,season,episode,prefer='dub'):
 """The file to play for an episode of an arc: onepace.choose's answer plus the arc and episode, or None when it does not exist (yet)."""
 arc=find(seasons_list,season)
 if not arc:return None
 for e in arc['episodes']:
  if e['number']==int(episode):
   got=onepace.choose(e,prefer=prefer)
   return dict(got,season=arc['season'],episode=e['number'],title=e['title'],arc=arc['title'],minutes=e['minutes'],plot=e['plot']) if got else None
 return None

def file_name(arc_number,episode_number,title,resolution):
 """A library-friendly name: 'One Pace - S05E03 - Title.mp4'."""
 clean=re.sub(r'[\\/:*?"<>|]+',' ',str(title)).strip()
 return 'One Pace - S%02dE%02d - %s.mp4'%(int(arc_number),int(episode_number),clean or 'Episode')

def download_requests(seasons_list,season=None,episode=None):
 """[(file address, candidate, request)] for debrid_drive.queue_direct: one episode, one arc, or (season None) the whole show. Japanese-only episodes are queued as they are."""
 out=[]
 for s in seasons_list:
  if season is not None and s['season']!=int(season):continue
  for e in s['episodes']:
   if episode is not None and e['number']!=int(episode):continue
   name=file_name(s['season'],e['number'],e['title'],e['resolution'])
   out.append((e['file'],{'provider':'onepace','_id':e['id'],'name':name},
               {'media_type':'episode','show_title':onepace.SHOW_TITLE,'title':onepace.SHOW_TITLE,'season':str(s['season']),'episode':str(e['number']),'tmdb':'','quality':e['resolution']}))
 return out

def download(profile,seasons_list,queue_direct,season=None,episode=None,log=lambda text:None):
 """Queue what download_requests lists through the Drive copier. Returns (queued, failed, japanese_only_queued)."""
 queued=failed=japanese=0
 japanese_names={(s['season'],e['number']) for s in seasons_list for e in s['episodes'] if e['japanese_only']}
 for url,candidate,request in download_requests(seasons_list,season,episode):
  try:
   queue_direct(profile,url,candidate,request)
   queued+=1
   if (int(request['season']),int(request['episode'])) in japanese_names:japanese+=1
  except Exception as error:
   failed+=1;log('One Pace: could not queue S%sE%s: %s: %s'%(request['season'],request['episode'],type(error).__name__,str(error)[:100]))
 return queued,failed,japanese

def search_rows(query):
 """The One Pace entry for the TV SHOWS part of a search, when the query is about it ('one pace', 'onepace', 'pace', 'one piece' fan edit); else []."""
 text=re.sub(r'[^a-z0-9]+','',str(query or '').lower())
 if text and (text.startswith('onepace') or text in ('pace','onepac','onepa')):
  return [{'label':onepace.SHOW_TITLE,'title':onepace.SHOW_TITLE,'plot':'The One Piece anime re-cut to follow the manga. Arcs are the seasons; English dub where it exists, otherwise Japanese with English subtitles.','file':'plugin://plugin.video.kodi.ios.watch/?action=onepace','filetype':'directory'}]
 return []

def sentence(change):
 if change['kind']=='arc':return ('New One Pace arc: %s'%change['arc'],'%d episode%s so far'%(change['episodes'],'' if change['episodes']==1 else 's'))
 if change['kind']=='episode':return ('New One Pace episode',('%s: %d new episode%s'%(change['arc'],change['count'],'' if change['count']==1 else 's')))
 return ('One Pace English dub added','%s: %d episode%s now dubbed'%(change['arc'],change['count'],'' if change['count']==1 else 's'))

def check(profile,get=None,notify=lambda title,text:None,log=lambda text:None,now=time.time):
 """The hourly look for new One Pace episodes, arcs and dubs. The first look only records what exists. A site that cannot be read is a quiet log line. Returns the changes."""
 get=get or fetch
 state_path=folder(profile)/STATE;state=read_json(state_path,{})
 found,error=seasons(profile,get,now,force=True)
 if error and not found:
  state.update(last_check=now(),last_error=error);write_json(state_path,state);log('One Pace: cannot check right now (%s)'%error);return []
 if error:
  state.update(last_check=now(),last_error=error);write_json(state_path,state);log('One Pace: the site could not be read (%s); the saved copy stays'%error);return []
 changed=onepace.changes(state.get('signature') or {},found)
 for change in changed:
  title,text=sentence(change)
  try:notify(title,text)
  except Exception as problem:log('One Pace: notice failed: %s'%type(problem).__name__)
 state.update(signature=onepace.signature(found),last_check=now(),last_error='',arcs=len(found),episodes=sum(len(s['episodes']) for s in found))
 write_json(state_path,state)
 log('One Pace: checked %d arcs, %d episodes, %d new'%(len(found),state['episodes'],len(changed)))
 return changed

def run(monitor,profile,ready,foreground,notify,log,get=None,now=time.time):
 """Service thread: once setup is done and a little later, look for new One Pace episodes, arcs and dubs every CHECK_EVERY seconds while the app is in front.
 `monitor` has waitForAbort / abortRequested; nothing here can stop the service."""
 while not ready():
  if monitor.waitForAbort(5):return
 if monitor.waitForAbort(120):return
 while not monitor.abortRequested():
  if foreground():
   try:check(profile,get,notify,log,now)
   except Exception as error:log('One Pace: check failed (%s)'%type(error).__name__)
  if monitor.waitForAbort(CHECK_EVERY):return

def arc_name(profile,season):
 """The arc's name for a season number from the saved copy only (no network), or '' (Library status names a One Pace season by its arc)."""
 try:
  saved=read_json(folder(profile)/CACHE,{})
  for arc in saved.get('seasons') or []:
   if int(arc.get('season') or 0)==int(season):return str(arc.get('title') or '')
 except Exception:pass
 return ''

QUIET='onepace-quiet-arcs.json'

def is_quiet(profile,season):
 """True when the owner chose "Continue, don't ask again in this arc" for this arc (ISSUE-502)."""
 try:return int(season) in {int(n) for n in read_json(folder(profile)/QUIET,[])}
 except (TypeError,ValueError):return False

def make_quiet(profile,season):
 """Remember that this arc plays its Japanese-only episodes without asking."""
 try:
  known={int(n) for n in read_json(folder(profile)/QUIET,[])}|{int(season)}
  write_json(folder(profile)/QUIET,sorted(known))
 except (OSError,TypeError,ValueError):pass
