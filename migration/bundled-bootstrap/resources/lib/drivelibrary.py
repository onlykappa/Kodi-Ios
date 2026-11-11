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

def show_key(title):
 """Same show or movie name ignoring case, punctuation and year: 'Lanterns' and 'Lanterns (2026)' match
 (the Library's merge rule, ios_library.show_key, applied to a parsed title)."""
 return re.sub(r'[^0-9a-z]+','',str(parse(title)['title'] if title else '').casefold())

def media_key(name,folder=''):
 """('episode', show, season, episode) or ('movie', title, year) for duplicate checks, or None if unknown.
 Bare episode names (S01E02.mkv) take the show from their folder."""
 info=parse(name)
 if info['season'] and info['episode']:
  title=info['title']
  if not title or title.casefold() in ('episode','season') or re.match(r'^(?:s\d+[ ._-]*e\d+|\d+x\d+)',title,re.I):
   title='' if re.match(r'(?i)^(?:season|s)[ ._-]*\d+\b',str(folder)) else folder   # "Season 1" names no show
  key=show_key(title)
  return ('episode',key,int(info['season']),int(info['episode'])) if key else None
 key=re.sub(r'[^0-9a-z]+','',info['title'].casefold())
 return ('movie',key,info['year']) if key else None

QUALITY=re.compile(r'(?i)\b(?:(2160|1440|1080|720|576|480)p|(4k|uhd))\b')
def quality(name):
 """Vertical resolution named in a release (4K/UHD = 2160), 0 when it does not say."""
 m=QUALITY.search(str(name))
 return 0 if not m else (2160 if m.group(2) else int(m.group(1)))

def show_folder(drive,parts):
 """Upload folder for an episode: the existing Drive › Kodi Downloads › TV Shows folder of the same show if there is
 one ('Lanterns (2026)' goes into 'Lanterns'), so one show never gets two folders. Other paths are unchanged."""
 parts=list(parts)
 if len(parts)!=3 or parts[1]!='TV Shows':return parts
 want=show_key(parts[2])
 try:
  for parent in find_folders(drive,parts[:2]):
   names=[item.get('name','') for item in children(drive,parent) if item.get('mimeType')==FOLDER]
   if parts[2] in names:return parts
   for name in names:
    if want and show_key(name)==want:return parts[:2]+[name]
 except Exception:return parts
 return parts

def media_year(name,folder=''):
 """The year a release or its folder names ('' if neither does)."""
 return parse(name)['year'] or (parse(folder)['year'] if folder else '')

def same_year(a,b):
 """Two years that do not contradict each other: 'The Office (2001)' and 'The Office (2005)' are different shows,
 while 'Lanterns' and 'Lanterns (2026)' may be the same one."""
 return not a or not b or a==b

def same_media(name,folder,remote):
 """Drive videos that are the same episode or movie as `name` (another release; exact byte copies are handled by
 the checksum rule), best first."""
 key=media_key(name,folder);year=media_year(name,folder)
 if key is None:return []
 found=[item for item in remote if media_key(item.get('name',''),item.get('folderName',''))==key
        and same_year(year,media_year(item.get('name',''),item.get('folderName','')))]
 return sorted(found,key=lambda item:(-quality(item.get('name','')),-int(item.get('size') or 0)))

def better_on_drive(path,remote):
 """The Drive copy that makes uploading `path` pointless: same episode/movie at equal or higher resolution."""
 name=os.path.basename(path);folder=os.path.basename(os.path.dirname(path))
 for item in same_media(name,folder,remote):
  if quality(item.get('name',''))>=quality(name):return item
 return None

def trash(drive,item_id):
 """Moves a Drive file or folder to Drive's Trash (restorable there for 30 days); never a permanent delete."""
 status,_,_=drive.call('PATCH',API+'/'+urllib.parse.quote(str(item_id),safe='')+'?fields=id,trashed',
                       json.dumps({'trashed':True}).encode(),{'Content-Type':'application/json'})
 if status!=200:raise RuntimeError('Drive trash: HTTP %s'%status)

def trash_if_empty(drive,folder_id,folder_name):
 """A show or release folder left empty by a removed duplicate goes too; Kodi Downloads' own folders never do."""
 if not folder_id or folder_name in ('',TOP,'Movies','TV Shows'):return False
 if children(drive,folder_id):return False
 trash(drive,folder_id);return True

def trash_worse(drive,name,folder,remote,kept_id):
 """After `name` is confirmed on Drive (as kept_id): lower-resolution copies of the same episode/movie go to Drive's
 Trash, and their folder if it is left empty. Returns the folders they were in."""
 gone=[]
 for item in same_media(name,folder,remote):
  if item.get('id')==kept_id or quality(item.get('name',''))>=quality(name):continue
  try:trash(drive,item['id'])
  except Exception:continue
  gone.append(item.get('folderName') or TOP)
  try:trash_if_empty(drive,item.get('folderId'),item.get('folderName',''))
  except Exception:pass
 return gone

def display_title(name):
 """A release or file name as people read it: 'Lanterns · S1 E1', 'Inception (2010)'. Plain text is kept."""
 info=parse(name)
 title=info['title'] or str(name)
 if title.isupper() and len(title)>4:title=title.title()   # INCEPTION -> Inception (short ones may be acronyms)
 if info['season'] and info['episode']:return '%s · S%s E%s'%(title,info['season'],info['episode'])
 return '%s (%s)'%(title,info['year']) if info['year'] else title

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
   found={'tmdb_id':str(r.get('id') or ''),'plot':r.get('overview') or '','rating':r.get('vote_average') or 0,
          'poster':IMAGE+'w500'+r['poster_path'] if r.get('poster_path') else '',
          'fanart':IMAGE+'w1280'+r['backdrop_path'] if r.get('backdrop_path') else ''}
 cache[slot]=found
 return found

def season(tmdb_id,number,key,cache,get,cached_only=False):
 """{episode number (text): {'title','plot','thumb','runtime','aired'}} for one season of a TMDb show, cached.
 Owner (build 146): downloaded shows opened a bare page (no episode names, stills or plots)."""
 slot='season:%s:%s'%(tmdb_id,number)
 if slot in cache:return cache[slot]
 if cached_only or not key or not tmdb_id:return {}
 try:data=json.loads(get(TMDB+'/tv/%s/season/%d?'%(urllib.parse.quote(str(tmdb_id),safe=''),int(number))+urllib.parse.urlencode({'api_key':key})))
 except Exception:return {}   # not cached: try again next time
 found={}
 for ep in data.get('episodes') or []:
  n=ep.get('episode_number')
  if n is None:continue
  found[str(n)]={'title':ep.get('name') or '','plot':ep.get('overview') or '',
                 'thumb':IMAGE+'w780'+ep['still_path'] if ep.get('still_path') else '',
                 'runtime':int(ep.get('runtime') or 0),'aired':ep.get('air_date') or ''}
 cache[slot]=found
 return found

def show_details(tmdb_id,key,cache,get,cached_only=False):
 """Full show metadata for the downloaded seasons header; only the visible-page worker fetches it."""
 slot='show:%s'%tmdb_id
 if slot in cache:return cache[slot]
 if cached_only or not key or not tmdb_id:return {}
 query=urllib.parse.urlencode({'api_key':key,'append_to_response':'images','include_image_language':'en,null'})
 try:data=json.loads(get(TMDB+'/tv/%s?'%urllib.parse.quote(str(tmdb_id),safe='')+query))
 except Exception:return {}
 if not data.get('id'):return {}
 logos=(data.get('images') or {}).get('logos') or []
 logos=sorted((logo for logo in logos if logo.get('file_path')),key=lambda logo:(logo.get('iso_639_1')!='en',-float(logo.get('vote_average') or 0)))
 found={'plot':data.get('overview') or '', 'genres':[g['name'] for g in data.get('genres') or [] if g.get('name')],
        'rating':data.get('vote_average') or 0,'year':str(data.get('first_air_date') or '')[:4],
        'clearlogo':IMAGE+'original'+logos[0]['file_path'] if logos else ''}
 if data.get('poster_path'):found['poster']=IMAGE+'w500'+data['poster_path']
 if data.get('backdrop_path'):found['fanart']=IMAGE+'w1280'+data['backdrop_path']
 cache[slot]=found;return found

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
  import signin_server;server=signin_server.server(drive_addon.getSetting('sign-in-server'))
  body=urllib.parse.urlencode({'provider':'googledrive','refresh_token':refresh_token}).encode()
  status,_,answer=send('POST',server+'/refresh',body,{'Content-Type':'application/x-www-form-urlencoded'})
  if status!=200:raise driveupload.refresh_error(status)
  return json.loads(answer)
 return driveupload.Drive(driveupload.token_source(accounts.get_accounts,accounts.save_account,refresh),send),driveid

def listing(kind,state_dir,folder=None,now=time.time,strict=False,fresh=False,stale_ok=False):
 """Drive entries for the Library page (cached LISTING_TTL seconds): movies, shows, or one show's episodes.
 stale_ok: return the saved list whatever its age (build 192, owner: "pressing movies under library takes a few
 seconds"; each open after 5 minutes, or after any upload, listed Drive live while Kodi showed its progress box). The
 service keeps the saved lists fresh (refresh_stale), so the page opens at once."""
 cache_path=os.path.join(state_dir,'drive-library.json');cache=load_json(cache_path,{})
 slot='%s:%s'%(kind,folder or '')
 hit=cache.get(slot)
 if not fresh and hit and (stale_ok or now()-hit.get('time',0)<LISTING_TTL):return hit['entries'],hit['driveid']
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

def refresh_stale(state_dir,now=time.time,ttl=LISTING_TTL):
 """Build 192: the service's part of stale_ok: every saved list older than ttl (or marked stale by
 driveupload.invalidate_library) is listed again; movies and shows are always kept. Returns the slots refreshed."""
 cache=load_json(os.path.join(state_dir,'drive-library.json'),{})
 slots=set(cache)|{'movie:','tv:'}
 done=[]
 for slot in sorted(slots):
  hit=cache.get(slot) or {}
  if now()-hit.get('time',0)<ttl:continue
  kind,folder=slot.split(':',1)
  listing(kind,state_dir,folder or None,now=now,strict=True,fresh=True);done.append(slot)
 return done

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
