"""Hub row copies: Home, Movies and TV show the last TMDb Helper result at once, like a native app's feed cache.

Each hub row and hero is a TMDb Helper list: one Python run of TMDb Helper each (2-3 s on the phone, ~36 at start).
The bootstrap service keeps a JSON copy of each list here and refreshes it in the background, one list at a time
(refresh(), called from portrait.listing_cache). Once a copy is written and read back, the service turns on that
row's skin flag. The skin then asks plugin://plugin.video.kodi.ios.watch/?action=cached&key=<key> for that row
instead of TMDb Helper (portrait.cached_content): Kodi decides this from the saved skin settings as soon as Home
opens, without waiting for any Python.

The cached route (serve) only reads the copy and lists it: no JSON-RPC, no TMDb Helper, no network. (Build-134 ran
Files.GetDirectory on the TMDb Helper path from inside the plugin and asked Kodi for a field that does not exist,
"tvshowtitle"; the owner's Home showed no rows at all.) When the copy is missing, unreadable, too old or for another
hero path, it lists nothing and turns the flag off: Kodi then loads that row's real TMDb Helper path.

Items keep TMDb Helper's own path, folder or playable kind, media type, ids, art, info labels, properties (tmdb_id,
item.*, isplayable...) and long-press entries, as Files.GetDirectory's customproperties returned them, so a tap or a
long press does what it did on the TMDb Helper row.
"""
import hashlib,json,os,re,time
ROUTE='plugin://plugin.video.kodi.ios.watch/?action=cached&key='
FOLDER='special://profile/addon_data/plugin.video.kodi.ios.watch/listings/'
FLAG='PortraitCache.'   # rows: Skin.HasSetting(PortraitCache.<key>); heroes: Skin.String(PortraitCache.hero.<id>) = the hero's path
CACHEABLE=('plugin://plugin.video.themoviedb.helper/',)
FORMAT=1
MAX_AGE=3*3600          # the service refreshes copies older than this
KEEP=3*86400            # the route stops serving a copy this old (the service has not refreshed it): live list again
LIMIT=60
# Files.GetDirectory fields (JSON-RPC v13, Kodi 21): what the rows, the hero, the info page and a long press read.
PROPERTIES=['title','year','genre','rating','votes','plot','mpaa','art','uniqueid','showtitle','season','episode','runtime',
            'premiered','playcount','resume','director','tagline','originaltitle','studio','country','trailer','customproperties']
KEY=re.compile(r'(r[0-9a-f]{15}|hero\.[0-9a-z]{1,16})$')
MENU=re.compile(r'contextmenu(label|action)\((\d+)\)$')

def cacheable(path):return str(path or '').startswith(CACHEABLE)
def row_key(path):return 'r'+hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:15]
def hero_key(spotlight):return 'hero.'+str(spotlight).lower()
def valid_key(key):return bool(KEY.match(str(key or '')))
def hero_skin_path(key):return 'Skin.String(HomeSwitcher.%s.Spotlight.Path)'%key.split('.',1)[1] if key.startswith('hero.') else ''

def parse(text,key,now=None):
 """The copy for key, or None when it is missing, damaged, empty, from another format or too old to show."""
 try:data=json.loads(text or '')
 except (TypeError,ValueError):return None
 if not isinstance(data,dict) or data.get('format')!=FORMAT or data.get('key')!=key or not cacheable(data.get('url')):return None
 if key.startswith('r') and row_key(data['url'])!=key:return None
 items=data.get('items')
 if not isinstance(items,list) or not items or not all(isinstance(i,dict) and isinstance(i.get('path'),str) and i['path'] for i in items):return None
 try:stamp=float(data.get('time'))
 except (TypeError,ValueError):return None
 if now is not None and now-stamp>KEEP:return None
 return data

# --- the cached route (watch plugin, one run per row) ---------------------------------------------------------
def flag_off(key):return 'Skin.Reset(%s%s)'%(FLAG,key)

def list_item(xbmcgui,item):
 li=xbmcgui.ListItem(label=item.get('label',''),path=item['path'],offscreen=True)
 if item.get('art'):li.setArt(item['art'])
 info=item.get('info') or {}
 tag=li.getVideoInfoTag()
 for name,setter,kind in (('mediatype','setMediaType',str),('title','setTitle',str),('year','setYear',int),('genre','setGenres',list),
                          ('plot','setPlot',str),('mpaa','setMpaa',str),('tvshowtitle','setTvShowTitle',str),('season','setSeason',int),
                          ('episode','setEpisode',int),('duration','setDuration',int),('premiered','setPremiered',str),
                          ('playcount','setPlaycount',int),('director','setDirectors',list),('tagline','setTagLine',str),
                          ('originaltitle','setOriginalTitle',str),('studio','setStudios',list),('country','setCountries',list),
                          ('trailer','setTrailer',str)):
  if name in info:
   try:getattr(tag,setter)(kind(info[name]))
   except (TypeError,ValueError,AttributeError):pass
 try:
  if 'rating' in info:tag.setRating(float(info['rating']),int(info.get('votes') or 0))
  if item.get('ids'):tag.setUniqueIDs(item['ids'],'tmdb' if 'tmdb' in item['ids'] else '')
  if info.get('resume'):tag.setResumePoint(float(info['resume'][0]),float(info['resume'][1]))
 except (TypeError,ValueError,IndexError,AttributeError):pass
 if item.get('props'):li.setProperties(item['props'])
 if item.get('menu'):li.addContextMenuItems([tuple(m) for m in item['menu']])
 return li

def content(items):
 kinds={(i.get('info') or {}).get('mediatype') for i in items}-{None,''}
 return {'movie':'movies','tvshow':'tvshows','episode':'episodes','season':'seasons'}.get(kinds.pop()) if len(kinds)==1 else ''

def serve(handle,key,xbmc,xbmcgui,xbmcplugin,read,now=time.time):
 """List the copy for key; with no usable copy, list nothing and turn the row's flag off (the skin then loads the
 real TMDb Helper path). Never runs TMDb Helper or JSON-RPC, so it cannot hang a row."""
 items=[];kind=''
 try:
  entry=parse(read(key),key,now()) if valid_key(key) else None
  if entry and key.startswith('hero.') and xbmc.getInfoLabel(hero_skin_path(key))!=entry['url']:entry=None
  for item in (entry or {}).get('items') or []:
   try:items.append((item['path'],list_item(xbmcgui,item),bool(item.get('folder'))))
   except Exception:continue
  kind=content(entry['items']) if entry else ''
 except Exception:items=[]
 if not items:
  # No usable copy: the flag goes off and Kodi loads this row's TMDb Helper path instead.
  if valid_key(key):xbmc.executebuiltin(flag_off(key))
  xbmc.log('Kodi iOS listing cache: no copy for %s; the row goes back to its TMDb Helper list'%str(key)[:40],xbmc.LOGWARNING)
 else:
  try:
   xbmcplugin.addDirectoryItems(handle,items,len(items))
   if kind:xbmcplugin.setContent(handle,kind)
  except Exception:
   xbmc.executebuiltin(flag_off(key));items=[]
 xbmcplugin.endOfDirectory(handle,succeeded=True,cacheToDisc=False)
 return len(items)

# --- copies (bootstrap service) -------------------------------------------------------------------------------
def from_rpc(result):
 """Copy items from a Files.GetDirectory answer: what the skin, a tap and a long press need."""
 items=[]
 for f in (result or {}).get('files') or []:
  if not isinstance(f,dict) or not f.get('file'):continue
  custom=f.get('customproperties') if isinstance(f.get('customproperties'),dict) else {}
  info={}
  kind=f.get('type')
  if kind and kind!='unknown':info['mediatype']=kind
  for src,dst in (('title','title'),('year','year'),('genre','genre'),('plot','plot'),('mpaa','mpaa'),('showtitle','tvshowtitle'),
                  ('season','season'),('episode','episode'),('runtime','duration'),('premiered','premiered'),('playcount','playcount'),
                  ('director','director'),('tagline','tagline'),('originaltitle','originaltitle'),('studio','studio'),
                  ('country','country'),('trailer','trailer'),('rating','rating'),('votes','votes')):
   v=f.get(src)
   if v in (None,'',[],-1) or (src in ('year','season','episode','runtime','rating') and not v):continue
   info[dst]=v
  resume=f.get('resume') or {}
  if resume.get('position'):info['resume']=[resume.get('position',0),resume.get('total',0)]
  menu={}
  for k,v in custom.items():
   m=MENU.match(k)
   if m:menu.setdefault(int(m.group(2)),{})[m.group(1)]=v
  item={'label':f.get('label') or f.get('title') or '','path':f['file'],'folder':f.get('filetype')=='directory','info':info,
        'art':{k:v for k,v in (f.get('art') or {}).items() if v and not re.match(r'fanart\d+$',k)},
        'ids':{k:str(v) for k,v in (f.get('uniqueid') or {}).items() if v and k!='unknown'},
        'props':{k:str(v) for k,v in custom.items() if not MENU.match(k) and v not in (None,'')},
        'menu':[[menu[n]['label'],menu[n]['action']] for n in sorted(menu) if menu[n].get('label') and menu[n].get('action')]}
  items.append({k:v for k,v in item.items() if v or k in ('label','path','folder')})
 return items[:LIMIT]

class Store:
 """The copies, one JSON file per row or hero in folder (an OS path), written atomically."""
 def __init__(self,folder):self.folder=folder
 def path(self,key):return os.path.join(self.folder,key+'.json')
 def read(self,key):
  try:
   with open(self.path(key),encoding='utf-8') as f:return f.read()
  except OSError:return ''
 def load(self,key,now=None):return parse(self.read(key),key,now)
 def write(self,key,url,items,now):
  """Write and read back; True only when the copy on disk is complete and valid."""
  os.makedirs(self.folder,exist_ok=True)
  tmp=self.path(key)+'.tmp'
  with open(tmp,'w',encoding='utf-8') as f:json.dump({'format':FORMAT,'key':key,'url':url,'time':now,'items':items},f,separators=(',',':'))
  os.replace(tmp,self.path(key))
  return self.load(key) is not None
 def remove(self,key):
  try:os.remove(self.path(key))
  except OSError:pass
 def keys(self):
  try:return [n[:-5] for n in os.listdir(self.folder) if n.endswith('.json') and valid_key(n[:-5])]
  except OSError:return []

class Flags:
 """The skin flags, through Kodi: rows a bool, heroes a string holding the path the copy was made from (the skin
 compares it with the hero's current path, so a changed spotlight goes live at once)."""
 def __init__(self,visible,info,run):self.visible,self.info,self.run=visible,info,run
 def on(self,key,url):
  if key.startswith('hero.'):return self.info('Skin.String(%s%s)'%(FLAG,key))==url
  return bool(self.visible('Skin.HasSetting(%s%s)'%(FLAG,key)))
 def set(self,key,url):
  if key.startswith('hero.'):
   if '"' in url or '\\' in url:return False   # not safe to quote in a builtin: this hero stays live
   self.run('Skin.SetString(%s%s,"%s")'%(FLAG,key,url))
  else:self.run('Skin.SetBool(%s%s)'%(FLAG,key))
  return True
 def clear(self,key):self.run(flag_off(key))
 def any_on(self,key):
  if key.startswith('hero.'):return bool(self.info('Skin.String(%s%s)'%(FLAG,key)))
  return bool(self.visible('Skin.HasSetting(%s%s)'%(FLAG,key)))

def targets(spotlights,rows):
 """[(key, url)] for the hub heroes ({spotlight id: path}) and rows (paths), heroes first; TMDb Helper lists only."""
 out=[];seen=set()
 for key,path in [(hero_key(s),p) for s,p in spotlights.items()]+[(row_key(p),p) for p in rows]:
  if cacheable(path) and key not in seen:seen.add(key);out.append((key,path))
 return out

def check(lists,store,flags,now=time.time):
 """At service start: a flag whose copy is missing or unusable goes off (the row loads TMDb Helper again); a good
 copy whose flag was lost (the app ended before Kodi saved its skin settings) gets it back. Returns (on, cleared)."""
 on=cleared=0
 for key,url in lists:
  entry=store.load(key,now())
  good=entry is not None and entry['url']==url
  if good and not flags.on(key,url):good=flags.set(key,url)
  elif not good and flags.any_on(key):flags.clear(key);cleared+=1
  on+=bool(good)
 return on,cleared

def stale(entry,now):
 age=now-float(entry['time'])
 return age>MAX_AGE or age<-600

def refresh(lists,store,flags,fetch,wait,now=time.time,pause=1.0,log=lambda text:None):
 """Fill missing copies and refresh stale ones, one TMDb Helper run at a time; turn each row's flag on once its
 copy is on disk and reads back. A failed run keeps the old copy. wait(seconds) returns True when Kodi is exiting.
 Returns (refreshed keys, failures)."""
 done=[];failed=[]
 for key,url in lists:
  entry=store.load(key,now())
  if entry is not None and entry['url']==url and not stale(entry,now()):
   if not flags.on(key,url):flags.set(key,url)
   continue
  try:
   items=from_rpc(fetch(url))
   if not items:raise ValueError('empty list')
   if not store.write(key,url,items,now()):raise ValueError('copy did not read back')
  except Exception as error:
   failed.append('%s: %s'%(key,str(error)[:120]))
  else:
   done.append(key)
   if not flags.on(key,url):flags.set(key,url)
  if wait(pause):break
 return done,failed

def prune(store,lists,now=time.time,older=7*86400):
 """Copies of rows no longer on any hub, untouched for a week."""
 wanted={k for k,_ in lists};gone=[]
 for key in store.keys():
  if key in wanted:continue
  try:age=now()-os.path.getmtime(store.path(key))
  except OSError:continue
  if age>older:store.remove(key);gone.append(key)
 return gone
