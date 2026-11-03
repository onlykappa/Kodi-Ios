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
 """The title's words, in order and next to each other, in the name ('The' optional)."""
 got=' %s '%' '.join(w for w in words(name) if w not in ARTICLES)
 want=' '.join(w for w in words(title) if w not in ARTICLES)
 return bool(want) and ' %s '%want in got

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

def find(folders,kind,title,year='',season='',episode='',walk=os.walk):
 """The largest matching video file under the folders, or None. Inside a folder named after the title (a movie
 folder, a season pack) the file only needs the episode number."""
 best=None
 for folder in folders:
  if not folder:continue
  for root,dirs,files in walk(folder):
   parts=[p for p in os.path.relpath(root,folder).split(os.sep) if p not in ('.','')]
   if kind=='movie':inside=any(has_title(p,title) and (not year or has_year(p,year)) for p in parts)
   else:inside=any(has_title(p,title) for p in parts)
   for f in files:
    if not f.lower().endswith(VIDEO) or 'sample' in f.lower():continue
    ok=matches(f,kind,title,year,season,episode) or (inside and (kind=='movie' or has_episode(f,season,episode)))
    if not ok:continue
    path=os.path.join(root,f)
    try:size=os.path.getsize(path)
    except OSError:size=0
    if not best or size>best[0]:best=(size,path)
 return best[1] if best else None

def finished_names(get=None):
 """Names of the torrents Elementum reports 100% done (a finished torrent stays in its download folder while it
 seeds, before Elementum moves it to Kodi Downloads)."""
 import json,urllib.request
 get=get or (lambda url:urllib.request.urlopen(url,timeout=3).read())
 try:return {t.get('name','') for t in json.loads(get('http://127.0.0.1:65220/torrents/list')) if float(t.get('progress') or 0)>=99.9 and t.get('name')}
 except Exception:return set()

def finished_only(path,root,names):
 """True when a file under Elementum's download folder belongs to a finished torrent (file or top folder name)."""
 rel=os.path.relpath(path,root).split(os.sep)
 return bool(names) and (rel[0] in names or os.path.splitext(rel[-1])[0] in names or rel[-1] in names)

def folders():
 """Elementum's completed-download folders (the phone's Kodi Downloads), then its download folder."""
 try:
  import xbmcaddon,xbmcvfs
  e=xbmcaddon.Addon('plugin.video.elementum')
  return [xbmcvfs.translatePath(e.getSetting(k)) for k in ('completed_movies_path','completed_shows_path','download_path') if e.getSetting(k)]
 except Exception:return []

def find_downloaded(kind,title,year='',season='',episode='',folder_list=None,names=None,walk=os.walk):
 """find() over the completed folders, and over Elementum's download folder for finished torrents only (owner
 build-138: a finished movie still seeding in Elementum Downloads was offered for download again)."""
 folder_list=folders() if folder_list is None else folder_list
 done=[f for f in folder_list[:2]];seeding=folder_list[2:]
 path=find(done,kind,title,year,season,episode,walk=walk)
 if path or not seeding:return path
 names=finished_names() if names is None else names
 if not names:return None
 path=find(seeding,kind,title,year,season,episode,walk=walk)
 return path if path and finished_only(path,seeding[0],names) else None
