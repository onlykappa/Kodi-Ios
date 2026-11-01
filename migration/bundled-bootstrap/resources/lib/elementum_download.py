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

def torrents(get=None):
 get=get or (lambda url:urllib.request.urlopen(url,timeout=5).read())
 try:return {t['id'] for t in json.loads(get(ENGINE+'/torrents/list')) if t.get('id')}
 except Exception:return set()

def download_all_when_added(before,wait,get=None,attempts=600):
 """After a season download starts: the new torrent (the pack the owner picked) gets every file. wait() sleeps
 ~1 s and returns True to give up. Returns the torrent id, or None if none appeared."""
 get=get or (lambda url:urllib.request.urlopen(url,timeout=10).read())
 for _ in range(attempts):
  new=torrents(get)-set(before)
  if new:
   tid=sorted(new)[0]
   if wait():return None
   get(ENGINE+'/torrents/downloadall/'+tid);return tid
  if wait():return None
 return None
