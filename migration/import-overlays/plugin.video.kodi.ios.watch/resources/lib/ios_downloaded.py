"""Downloaded copies on the phone. Elementum moves a finished download to Kodi Downloads/Movies or /TV Shows and
forgets the torrent, so playing the title again from Home made it fetch the torrent again (owner, build-132); Library
browses the folder and played the file. The watch menu asks here first and plays the file when there is one."""
import os,re,unicodedata
VIDEO=('.mkv','.mp4','.m4v','.mov','.avi','.ts','.m2ts','.webm')

def words(text):
 text=unicodedata.normalize('NFKD',str(text or '')).encode('ascii','ignore').decode().lower().replace('&',' and ')
 return [w for w in re.split(r'[^a-z0-9]+',text) if w]

ARTICLES={'the','a','an'}

def has_title(name,title):
 """A title at the beginning of a release, followed only by a release marker (not a different sequel/title)."""
 name=re.sub(r'\[[^\]]*\]','',str(name))
 got=[w for w in words(os.path.splitext(name)[0] if name.lower().endswith(VIDEO) else name) if w not in ARTICLES]
 want=[w for w in words(title) if w not in ARTICLES]
 if not want or got[:len(want)]!=want:return False
 if len(got)==len(want):return True
 return bool(re.fullmatch(r'(?:19\d{2}|20\d{2}|\d{3,4}p|[1248]k|s\d{1,2}(?:e\d{1,3})?|\d{1,2}x\d{1,3}|season|complete|bluray|blu|web|webrip|hdtv|dvd|dvdrip|remux|hevc|x26[45]|h26[45]|extended|unrated|remastered|proper|repack)',got[len(want)]))

def has_year(name,year):return str(year) in words(name)

def has_episode(name,season,episode):
 try:s,e=int(season),int(episode)
 except (TypeError,ValueError):return False
 return bool(re.search(r'(?:^|[^a-z0-9])(?:s0*%d[ ._-]?e0*%d|0*%dx0*%d)(?:[^0-9]|$)'%(s,e,s,e),str(name).lower()))

def matches(name,kind,title,year='',season='',episode=''):
 """A movie: its title and (when known) its year. An episode: the show's title and SxxEyy / 1x02."""
 if not has_title(name,title):return False
 if kind=='movie':return has_year(name,year) if year else True
 return has_episode(name,season,episode)

def find(folders,kind,title,year='',season='',episode='',walk=None,accept=lambda path:True):
 """The largest matching video file under the folders, or None. Inside a folder named after the title (a movie
 folder, a season pack) the file only needs the episode number."""
 best=None
 def onerror(error):
  if not isinstance(error,FileNotFoundError):raise error
 for folder in folders:
  if not folder:continue
  for root,dirs,files in (walk(folder) if walk else os.walk(folder,onerror=onerror)):
   parts=[p for p in os.path.relpath(root,folder).split(os.sep) if p not in ('.','')]
   if kind=='movie':inside=any(has_title(p,title) and (not year or has_year(p,year)) for p in parts)
   else:inside=any(has_title(p,title) for p in parts)
   for f in files:
    if not f.lower().endswith(VIDEO) or 'sample' in f.lower():continue
    ok=matches(f,kind,title,year,season,episode) or (inside and (kind=='movie' or has_episode(f,season,episode)))
    if not ok:continue
    path=os.path.join(root,f)
    try:size=os.path.getsize(path)
    except FileNotFoundError:continue
    if size<=0 or not accept(path):continue
    if not best or size>best[0]:best=(size,path)
 return best[1] if best else None

def finished_names(get=None,strict=False):
 """Names of the torrents Elementum reports 100% done (a finished torrent stays in its download folder while it
 seeds, before Elementum moves it to Kodi Downloads)."""
 import json,urllib.request
 get=get or (lambda url:urllib.request.urlopen(url,timeout=3).read())
 try:return {t.get('name','') for t in json.loads(get('http://127.0.0.1:65220/torrents/list')) if float(t.get('progress') or 0)>=100 and t.get('name')}
 except Exception:
  if strict:raise LookupError('Could not verify completion of an existing torrent')
  return set()

def finished_only(path,root,names):
 """True when a file under Elementum's download folder belongs to a finished torrent (file or top folder name)."""
 rel=os.path.relpath(path,root).split(os.sep)
 return bool(names) and (rel[0] in names or os.path.splitext(rel[-1])[0] in names or rel[-1] in names)

def folders():
 """Elementum's completed-download folders (the phone's Kodi Downloads), then its download folder."""
 try:
  import xbmcaddon,xbmcvfs
  e=xbmcaddon.Addon('plugin.video.elementum')
  # Retain empty slots: removing one reclassified the active download folder as a completed folder.
  return [xbmcvfs.translatePath(e.getSetting(k)) if e.getSetting(k) else '' for k in ('completed_movies_path','completed_shows_path','download_path')]
 except Exception:return []

def default_completed_folder(kind):
 """The app's current Kodi Downloads location, also when Elementum is disabled or its saved absolute container
 path belongs to an earlier installation. Same Documents/home rule as bootstrap's updates.updates_folder."""
 try:
  import xbmcvfs
  from pathlib import Path
  home=Path(xbmcvfs.translatePath('special://home/'))
  if not home.is_absolute():return []
  parent=next((p for p in (home,*home.parents) if p.name=='Documents'),home.parent)
  return [str(parent/'Kodi Downloads'/('Movies' if kind=='movie' else 'TV Shows'))]
 except (ImportError,AttributeError,TypeError,ValueError):return []

def find_downloaded(kind,title,year='',season='',episode='',folder_list=None,names=None,walk=None,strict=False):
 """find() over the completed folders, and over Elementum's download folder for finished torrents only (owner
 build-138: a finished movie still seeding in Elementum Downloads was offered for download again)."""
 defaults=default_completed_folder(kind) if folder_list is None else []
 folder_list=folders() if folder_list is None else folder_list
 # A movie must not match a same-named TV episode, and active/partial files must not become "completed" merely
 # because a user's completed-folder setting overlaps the active folder.
 done=(folder_list[:1] if kind=='movie' else folder_list[1:2])+defaults
 seeding=folder_list[2:]
 def active(path):
  return any(root and os.path.commonpath([os.path.abspath(path),os.path.abspath(root)])==os.path.abspath(root) for root in seeding)
 path=find(done,kind,title,year,season,episode,walk=walk,accept=lambda path:not active(path))
 if path or not seeding:return path
 # No matching file on disk means there is no torrent completion to check (and no reason to wake the engine).
 if not find(seeding,kind,title,year,season,episode,walk=walk):return None
 names=finished_names(strict=strict) if names is None else names
 if not names:return None
 return find(seeding,kind,title,year,season,episode,walk=walk,
             accept=lambda path:any(finished_only(path,root,names) for root in seeding if root))

def completed_copy(kind,title,year='',season='',episode='',cloud=False):
 """Completed phone copy first, then the app's Drive downloads for Continue Watching. A failed check is not a
 confirmed absence: never silently turn a failed lookup into a new Elementum download."""
 failure=None
 try:
  path=find_downloaded(kind,title,year,season,episode,strict=cloud)
  if path:return {'path':path,'source':'local'}
 except Exception as error:failure=error
 if cloud:
  import sys,xbmc,xbmcvfs
  if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.googledrive)'):
   boot=xbmcvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')
   if boot not in sys.path:sys.path.insert(0,boot)
   import drivelibrary
   state=xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')
   path=drivelibrary.completed_copy(kind,title,year,season,episode,state)
   if path:return {'path':path,'source':'drive'}
 if failure:raise LookupError('Could not check completed phone downloads') from failure
 return None
