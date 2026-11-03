"""Download with Elementum (long press › Download, and Download on a show's seasons page).

Elementum's own download action searches the sources and fetches in the background without playing. For a
season it picks a season pack but fetches only one file of it, so the pack is then switched to "download all".
Kept downloads go to Google Drive through the bootstrap service (driveupload), as before."""
import json,time,urllib.parse,urllib.request
ENGINE='http://127.0.0.1:65220'
PLUGIN='plugin://plugin.video.elementum'

def ids(kind,path='',values=None):
 """(tmdb id, season, episode) from what Kodi knows about the item: TMDb Helper puts the show's id in
 Property(tvshow.tmdb_id) and both ids in its folder paths (…&tmdb_id=1399&season=2)."""
 values={k:str(v).strip() for k,v in (values or {}).items() if v not in (None,'')}
 query={k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(path or '').query).items()}
 num=lambda v:v if v and v.isdigit() else None
 if kind=='movie':
  tmdb=num(values.get('tmdb')) or (num(query.get('tmdb_id')) if query.get('tmdb_type','movie')=='movie' else None)
  return tmdb,None,None
 show=num(values.get('tvshow.tmdb_id')) or num(query.get('tmdb_id')) or (num(values.get('tmdb')) if kind=='tvshow' else None)
 season=num(values.get('season')) or num(query.get('season'))
 episode=num(values.get('episode')) or num(query.get('episode'))
 return show,season,episode

def plugin_url(kind,tmdb,season=None,episode=None):
 if kind=='movie':return '%s/movie/%s/download'%(PLUGIN,tmdb)
 if kind=='episode':return '%s/show/%s/season/%s/episode/%s/download'%(PLUGIN,tmdb,season,episode)
 return '%s/show/%s/season/%s/download'%(PLUGIN,tmdb,season)

PLUGIN_PREFIX='plugin://plugin.video.elementum'

def follow(url,opener=None,hops=6,timeout=600):
 """Run an Elementum plugin link over its HTTP API, following its redirects. Owner (build-133): a season download
 picked a version, then Elementum answered with a redirect to plugin://.../download (and that to /play?background)
 which Kodi dropped when the link was run with RunPlugin, so no torrent was added. Returns the last URL reached."""
 import urllib.error
 class Stop(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*a,**k):return None
 opener=opener or urllib.request.build_opener(Stop)
 url=url.replace(PLUGIN_PREFIX,ENGINE,1)
 for _ in range(hops):
  try:
   response=opener.open(url,timeout=timeout);response.read();return url
  except urllib.error.HTTPError as error:
   location=error.headers.get('Location') if error.code in (301,302,303,307,308) else None
   if not location:raise
   url=urllib.parse.urljoin(url,location.replace(PLUGIN_PREFIX,ENGINE,1))
 return url

def torrents(get=None):
 get=get or (lambda url:urllib.request.urlopen(url,timeout=5).read())
 try:return {t['id'] for t in json.loads(get(ENGINE+'/torrents/list')) if t.get('id')}
 except Exception:return set()

def added(before,wait,get=None,attempts=600):
 """The torrent Elementum adds after a download starts (the version the owner picked), or None if none appeared
 (cancelled, or after `attempts` seconds). wait() sleeps ~1 s and returns True to give up."""
 for _ in range(attempts):
  new=torrents(get)-set(before)
  if new:return sorted(new)[0]
  if wait():return None
 return None

def download_all_when_added(before,wait,get=None,attempts=600):
 """After a season download starts: the new torrent (the pack the owner picked) gets every file. wait() sleeps
 ~1 s and returns True to give up. Returns the torrent id, or None if none appeared."""
 get=get or (lambda url:urllib.request.urlopen(url,timeout=10).read())
 tid=added(before,wait,get,attempts)
 if tid is None or wait():return None
 get(ENGINE+'/torrents/downloadall/'+tid);return tid

# "Download only" or "Download and watch": both start Elementum's download, which shows the quality and Choose a version
# pages; watching then plays from that same torrent once it is added, so it keeps downloading after the video stops.
MODES=['Download only','Download and watch']

def mode_labels(kind,episodes=None):
 """The two choices; with several episodes the watched one is the first."""
 if kind=='season' and episodes:return [MODES[0],'Download and watch episode %d'%min(episodes)]
 if kind=='season':return [MODES[0],'Download and watch episode 1']
 return list(MODES)

def watch_url(kind,tmdb,torrent=None,season=None,episode=None):
 """Play from the downloading torrent: a movie by its torrent id; an episode through Elementum's episode page with
 silent=1, which plays the matching file of the torrent already on the phone (also a season pack) without asking."""
 if kind=='movie':return '%s/play?%s'%(PLUGIN,urllib.parse.urlencode({'resume':torrent,'tmdb':tmdb,'type':'movie'}))
 return '%s/show/%s/season/%s/episode/%s/play?silent=1'%(PLUGIN,tmdb,season,episode)

def season_path(tmdb,season):
 """TMDb Helper's episode list for a season (what the seasons page shows)."""
 return 'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_id=%s&season=%s&tmdb_type=tv'%(tmdb,season)

def episode_choices(files):
 """[(episode number, label)] from a Files.GetDirectory result, in episode order; folders and specials skipped."""
 out=[]
 for f in files or []:
  number=f.get('episode')
  if f.get('filetype')=='directory' or not isinstance(number,int) or number<1:continue
  title=f.get('title') or f.get('label') or ''
  label=title if title.startswith('%d.'%number) else '%d. %s'%(number,title)
  out.append((number,label.strip()))
 return sorted(set(out))

def download_each(episodes,start,wait,get=None,per_episode=300):
 """Start one episode download at a time: Elementum may ask which source to use, so the next one starts once
 the previous torrent was added (or after per_episode seconds, if the owner cancelled that one).
 start(n) begins episode n. Returns the episodes whose torrent appeared."""
 added=[]
 for n in episodes:
  before=torrents(get);start(n)
  for _ in range(per_episode):
   if wait():return added
   if torrents(get)-before:added.append(n);break
 return added
