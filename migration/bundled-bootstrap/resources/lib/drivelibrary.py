"""Library › Movies / TV Shows: the videos in Google Drive › Kodi Downloads (where kept Elementum downloads are
uploaded, driveupload.py) together with Kodi's own library.

The owner keeps downloads in the cloud, not on the phone, and wants them in Library rather than behind the gear
menu's Google Drive browser (2026-11-02). The watch add-on lists them (plugin://plugin.video.kodi.ios.watch/
?action=library&type=movie|tv); playing one goes through the Google Drive add-on, which streams from Drive.

Names come from Elementum's release folders, so titles, years and SxxEyy are read from them; posters and
backgrounds are looked up on TMDb once per title (TMDb Helper's API key, read from its add-on at run time) and kept.
"""
import json,os,re,tempfile,time,urllib.parse
API='https://www.googleapis.com/drive/v3/files'
FOLDER='application/vnd.google-apps.folder'
VIDEO=('.mkv','.mp4','.m4v','.avi','.mov','.webm','.ts','.m2ts','.mts','.wmv','.mpg','.mpeg')
TOP='Kodi Downloads'
SECTION={'movie':'Movies','tv':'TV Shows'}
TMDB='https://api.themoviedb.org/3'
IMAGE='https://image.tmdb.org/t/p/'
LISTING_TTL=300
# Words that end a title in a release name (quality, source, codec, language...).
STOP=re.compile(r'\b(2160p|1080p|720p|576p|480p|4k|uhd|hdr\d*|dv|dovi|web[ .-]?dl|webrip|web|blu[ .-]?ray|bdrip|brrip|bdremux|remux|'
                r'hdtv|dvdrip|dvd|x26[45]|h[ .]?26[45]|hevc|avc|aac\d?|ac3|eac3|dts|ddp?\d|atmos|truehd|10bit|proper|repack|'
                r'extended|unrated|imax|multi|dual|complete|season|s\d{1,2}(?:e\d{1,3})?)\b',re.I)

def _escape(text):return str(text).replace('\\','\\\\').replace("'","\\'")

def children(drive,folder_id):
 """Everything directly in a Drive folder: [{id, name, mimeType, size}]."""
 out=[];token=None
 while True:
  query={'q':"'%s' in parents and trashed=false"%_escape(folder_id),'fields':'nextPageToken,files(id,name,mimeType,size,md5Checksum)',
         'pageSize':'1000','spaces':'drive'}
  if token:query['pageToken']=token
  status,_,body=drive.call('GET',API+'?'+urllib.parse.urlencode(query))
  if status!=200:raise RuntimeError('Drive listing: HTTP %s'%status)
  data=json.loads(body);out+=data.get('files',[]);token=data.get('nextPageToken')
  if not token:return out

def find_folders(drive,parts,strict=False):
 """All matching branches. Drive permits duplicate names, including folders made by older upload retries."""
 parents=['root']
 for name in parts:
  found=[]
  for parent in parents:
   token=None
   while True:
    query={'q':"name='%s' and mimeType='%s' and '%s' in parents and trashed=false"%(_escape(name),FOLDER,parent),
           'fields':'nextPageToken,files(id)','pageSize':'1000','spaces':'drive'}
    if token:query['pageToken']=token
    status,_,body=drive.call('GET',API+'?'+urllib.parse.urlencode(query))
    if status!=200:
     if strict:raise RuntimeError('Drive download check: HTTP %s'%status)
     return []
    data=json.loads(body);found.extend(item['id'] for item in data.get('files',[]));token=data.get('nextPageToken')
    if not token:break
  parents=list(dict.fromkeys(found))
  if not parents:break
 return parents

def find_folder(drive,parts,strict=False):
 """First matching folder, or None, for older callers. Library discovery uses all matching branches."""
 found=find_folders(drive,parts,strict)
 return found[0] if found else None

def is_video(name):return os.path.splitext(str(name))[1].lower() in VIDEO

def videos(drive,folder_id,depth=3):
 """Video files in a folder and its subfolders (Elementum keeps each release in its own folder)."""
 out=[]
 for item in children(drive,folder_id):
  if item.get('mimeType')==FOLDER:
   if depth>0:out+=videos(drive,item['id'],depth-1)
  elif is_video(item.get('name')) and not str(item.get('name')).lower().startswith('sample'):out.append(item)
 return out

def parse(name):
 """Title, year, season and episode from a release or file name."""
 base=os.path.splitext(str(name))[0] if is_video(name) else str(name)
 text=re.sub(r'[._]+',' ',base)
 text=re.sub(r'\[[^\]]*\]','',text).strip()
 found={'title':'','year':'','season':'','episode':''}
 m=re.search(r'\bS(\d{1,2})[ .-]?E(\d{1,3})\b',text,re.I) or re.search(r'\b(\d{1,2})x(\d{2,3})\b',text)
 if m:found.update(season=str(int(m.group(1))),episode=str(int(m.group(2))))
 y=None
 for match in re.finditer(r'\(?\b(19[2-9]\d|20[0-4]\d)\b\)?',text):
  if match.start()>0:y=match;break
 if y:found['year']=y.group(1)
 cut=len(text)
 for mark in (y,m,STOP.search(text)):
  if mark and mark.start()>0:cut=min(cut,mark.start())
 title=re.sub(r'[\s\-–(]+$','',text[:cut]).strip()
 found['title']=re.sub(r'\s{2,}',' ',title) or text.strip()
 return found

def play_url(driveid,item_id):
 """Plays one Drive file through the Google Drive add-on (it streams from Drive)."""
 return 'plugin://plugin.googledrive/?'+urllib.parse.urlencode({'action':'play','content_type':'video','driveid':driveid,
                                                               'item_driveid':driveid,'item_id':item_id})

def movies(files):
 """One entry per file in Movies, newest name first not assumed: sorted by title."""
 out=[]
 for item in files:
  info=parse(item['name'])
  if not info['title'] or info['season']:continue
  out.append(dict(info,id=item['id'],name=item['name'],size=int(item.get('size') or 0)))
 return sorted(out,key=lambda e:(e['title'].lower(),e['year']))

def shows(folders,top=None):
 """Show folders and episodes uploaded directly into TV Shows (single-file torrents have no show folder)."""
 out=[]
 loose=set()
 for item in folders:
  info=parse(item['name'])
  if item.get('mimeType')!=FOLDER:
   if top and is_video(item['name']) and info['season'] and int(item.get('size') or 0)>0:
    identity=(info['title'].casefold(),info['year'])
    if identity not in loose:
     loose.add(identity);out.append({'title':info['title'],'year':info['year'],'id':top,'name':info['title'],'loose':True})
   continue
  out.append({'title':info['title'] or item['name'],'year':info['year'],'id':item['id'],'name':item['name']})
 return sorted(out,key=lambda e:e['title'].lower())

def episodes(files,show_title=''):
 """Episodes of one show, in season/episode order."""
 out=[]
 for item in files:
  info=parse(item['name'])
  out.append(dict(info,id=item['id'],name=item['name'],show=show_title,size=int(item.get('size') or 0)))
 key=lambda e:(int(e['season'] or 0),int(e['episode'] or 0),e['name'].lower())
 return sorted(out,key=key)

# --- TMDb artwork (cached) ---------------------------------------------------------------------------------------
def tmdb_key(helper_path):
 """TMDb Helper's API key, read from its add-on folder (resources/tmdbhelper/lib/api/api_keys/tmdb.py)."""
 try:
  with open(os.path.join(helper_path,'resources','tmdbhelper','lib','api','api_keys','tmdb.py'),encoding='utf-8') as f:
   found=re.search(r"API_KEY\s*=\s*['\"]([0-9a-f]{20,})['\"]",f.read())
  return found.group(1) if found else ''
 except OSError:return ''

def artwork(kind,title,year,key,cache,get,cached_only=False):
 """{'poster','fanart','tmdb_id','plot'} for a title (kind 'movie' or 'tv'); cache is a dict kept between calls."""
 slot='%s:%s:%s'%(kind,title.lower(),year)
 if slot in cache:return cache[slot]
 if cached_only or not key or not title:return {}
 found={}
 if key and title:
  query={'api_key':key,'query':title}
  if year:query['year' if kind=='movie' else 'first_air_date_year']=year
  try:
   results=json.loads(get(TMDB+'/search/%s?'%('movie' if kind=='movie' else 'tv')+urllib.parse.urlencode(query))).get('results') or []
  except Exception:results=None
  if results is None:return {}   # not cached: try again next time
  if results:
   r=results[0]
   found={'tmdb_id':str(r.get('id') or ''),'plot':r.get('overview') or '',
          'poster':IMAGE+'w500'+r['poster_path'] if r.get('poster_path') else '',
          'fanart':IMAGE+'w1280'+r['backdrop_path'] if r.get('backdrop_path') else ''}
 cache[slot]=found
 return found

# --- Kodi side -----------------------------------------------------------------------------------------------------
def load_json(path,default):
 try:
  with open(path,encoding='utf-8') as f:return json.load(f)
 except (OSError,ValueError):return default

def save_json(path,data):
 # Listings and the visible-page watcher can save concurrently; each writer owns its temporary file.
 folder=os.path.dirname(path);os.makedirs(folder,exist_ok=True)
 with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=folder,delete=False) as f:
  temp=f.name
  try:json.dump(data,f)
  except Exception:
   os.unlink(temp);raise
 try:os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)

def client():
 """(Drive, driveid) with the Google Drive add-on's first account, or (None, None) when it is not signed in."""
 import sys,urllib.request,xbmcaddon,xbmcvfs
 sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
 import driveupload
 common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
 if common not in sys.path:sys.path.append(common)
 from clouddrive.common.account import AccountManager
 from clouddrive.common.remote.request import tls_context
 drive_addon=xbmcaddon.Addon('plugin.googledrive')
 accounts=AccountManager(xbmcvfs.translatePath(drive_addon.getAddonInfo('profile')))
 found=accounts.get_accounts()
 if not found:return None,None
 account=next(iter(found.values()))
 drives=account.get('drives') or []
 driveid=(drives[0].get('id') if drives else None) or account.get('id')
 send=driveupload.sender(tls_context(),timeout=8)
 def refresh(refresh_token):
  server=(drive_addon.getSetting('sign-in-server') or 'https://drive.signinserver.com').strip().rstrip('/')
  body=urllib.parse.urlencode({'provider':'googledrive','refresh_token':refresh_token}).encode()
  status,_,answer=send('POST',server+'/refresh',body,{'Content-Type':'application/x-www-form-urlencoded'})
  if status!=200:raise RuntimeError('Drive sign-in refresh: HTTP %s'%status)
  return json.loads(answer)
 return driveupload.Drive(driveupload.token_source(accounts.get_accounts,accounts.save_account,refresh),send),driveid

def listing(kind,state_dir,folder=None,now=time.time,strict=False,fresh=False):
 """Drive entries for the Library page (cached LISTING_TTL seconds): movies, shows, or one show's episodes."""
 cache_path=os.path.join(state_dir,'drive-library.json');cache=load_json(cache_path,{})
 slot='%s:%s'%(kind,folder or '')
 hit=cache.get(slot)
 if not fresh and hit and now()-hit.get('time',0)<LISTING_TTL:return hit['entries'],hit['driveid']
 drive,driveid=client()
 if not drive:return [],None
 if folder:entries=episodes(videos(drive,folder))
 else:
  entries=[]
  for top in find_folders(drive,[TOP,SECTION[kind]],strict=strict):
   if kind=='movie':entries+=movies(videos(drive,top))
   else:entries+=shows(children(drive,top),top)
  entries.sort(key=lambda entry:(entry['title'].casefold(),entry['year']))
 cache[slot]={'time':now(),'entries':entries,'driveid':driveid};save_json(cache_path,cache)
 return entries,driveid

def completed_copy(kind,title,year,season,episode,state_dir):
 """Match a kept download by title/year or show/episode, without art lookups or source scraping. Local phone
 matching and this Drive check share the same strict title rule. A Drive error propagates to stop silent redownload."""
 from ios_downloaded import has_title,has_episode
 if kind=='movie':
  for fresh in (False,True):
   entries,driveid=listing('movie',state_dir,strict=True,fresh=fresh)
   matches=[e for e in entries if has_title(e.get('title',''),title) and (not year or str(e.get('year'))==str(year)) and int(e.get('size') or 0)>0]
   if matches or not driveid:break
 else:
  for fresh in (False,True):
   shows,driveid=listing('tv',state_dir,strict=True,fresh=fresh)
   shows=[s for s in shows if has_title(s.get('title',''),title)]
   if shows or not driveid:break
  matches=[]
  for show in shows:
   for fresh in (False,True):
    entries,driveid=listing('tv',state_dir,show['id'],strict=True,fresh=fresh)
    found=[e for e in entries if has_episode(e.get('name',''),season,episode) and int(e.get('size') or 0)>0
           and (not show.get('loose') or has_title(e.get('title',''),title))]
    if found or not driveid:break
   matches+=found
 if not matches or not driveid:return None
 item=max(matches,key=lambda e:int(e.get('size') or 0))
 return play_url(driveid,item['id'])
