"""Listing cache for the hub rows (Home, Movies, TV): show the last TMDb Helper result at once, refresh it later.

Each hub row used to be a TMDb Helper path: one Python run of TMDb Helper per row, a few seconds each on the phone,
queued one behind another, so the menus said "Loading..." at every launch. The skin now asks
plugin://plugin.video.kodi.ios.watch/?action=cached&url=<TMDb Helper path> instead. This plugin is light (no TMDb
Helper import), answers from the JSON copy kept here, and only on the very first visit of a row (no copy yet) runs
the real list once through Files.GetDirectory. The bootstrap service refreshes stale copies one at a time, after
the start has settled (portrait.listing_refresher), so the next visit shows today's titles.

Items keep the real path and folder/playable kind, so a tap does exactly what it did on the TMDb Helper row.
"""
import hashlib,json,time
from urllib.parse import quote,unquote
ROUTE='plugin://plugin.video.kodi.ios.watch/?action=cached&url='
FOLDER='special://profile/addon_data/plugin.video.kodi.ios.watch/listings/'
MAX_AGE=3*3600       # older copies are still shown, and refreshed by the service
LIMIT=40
ART=('poster','fanart','landscape','thumb','clearlogo','icon','banner','tvshow.poster','tvshow.fanart','tvshow.landscape','tvshow.clearlogo')
# Files.GetDirectory fields the skin rows, the hero and the long-press card read.
PROPERTIES=['title','year','genre','rating','plot','mpaa','art','uniqueid','tvshowtitle','season','episode','runtime','premiered','playcount','resume']
CACHEABLE=('plugin://plugin.video.themoviedb.helper/',)

def cacheable(path):return str(path).startswith(CACHEABLE)

def route(path):
 """The cached form of a row path (others are returned unchanged). url is last and may also be given raw: the hero
 builds it from a skin string at run time, which the skin cannot URL-encode."""
 return ROUTE+quote(path,safe='') if cacheable(path) else path

def url_from_query(query):
 """The wrapped path from the plugin's query string, encoded or raw (everything after url=)."""
 query=query.lstrip('?');at=query.find('url=')
 if at<0:return ''
 value=query[at+4:]
 return unquote(value) if value.startswith('plugin%3A') else value

def name(path):return FOLDER+hashlib.sha1(path.encode('utf-8')).hexdigest()+'.json'

def load(read,path):
 try:data=json.loads(read(name(path)) or '{}')
 except ValueError:return None
 return data if isinstance(data,dict) and isinstance(data.get('items'),list) and data.get('url')==path else None

def stale(entry,now=time.time):return entry is None or now()-float(entry.get('time',0))>MAX_AGE

def store(write,path,items,now=time.time):
 write(name(path),json.dumps({'url':path,'time':now(),'items':items[:LIMIT]}))

def from_rpc(result):
 """Cache items from a Files.GetDirectory result (only what the skin and the tap need)."""
 items=[]
 for f in (result or {}).get('files') or []:
  if not f.get('file'):continue
  kind=f.get('type') if f.get('type') not in (None,'unknown') else ''
  item={'label':f.get('label') or f.get('title') or '','path':f['file'],'folder':f.get('filetype')=='directory',
        'art':{k:v for k,v in (f.get('art') or {}).items() if k in ART and v},'mediatype':kind}
  for k in ('title','year','genre','rating','plot','mpaa','tvshowtitle','season','episode','runtime','premiered','playcount'):
   v=f.get(k)
   if v not in (None,'',[],0,-1):item[k]=v
  ids={k:str(v) for k,v in (f.get('uniqueid') or {}).items() if v}
  if ids:item['uniqueid']=ids
  items.append(item)
 return items

def fetch(rpc,path):
 """The real list, through Kodi (runs TMDb Helper once). None when Kodi gave no answer."""
 result=rpc('Files.GetDirectory',{'directory':path,'media':'video','properties':PROPERTIES})
 return None if result is None else from_rpc(result)

def info(item):
 """setInfo('video', ...) labels."""
 out={k:item[k] for k in ('title','year','genre','rating','plot','mpaa','tvshowtitle','season','episode','premiered','playcount') if k in item}
 if 'runtime' in item:out['duration']=item['runtime']
 if item.get('mediatype'):out['mediatype']=item['mediatype']
 out.setdefault('title',item.get('label',''))
 return out

def properties(item):
 """ListItem properties TMDb Helper's own long-press entries look for."""
 tmdb=(item.get('uniqueid') or {}).get('tmdb')
 kind={'movie':'movie','tvshow':'tv','season':'tv','episode':'tv'}.get(item.get('mediatype'))
 out={}
 if tmdb:out['tmdb_id']=tmdb
 if kind:out['tmdb_type']=kind
 if not item.get('folder'):out['IsPlayable']='true'
 return out

def directory(handle,query,xbmc,xbmcgui,xbmcplugin,read,write):
 path=url_from_query(query)
 entry=load(read,path) if path else None
 if path and entry is None and cacheable(path):
  # First visit of this row: run it once now (as the row did before), keep the copy for next time.
  def rpc(method,params):
   return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))).get('result')
  items=fetch(rpc,path)
  if items is not None:
   if items:store(write,path,items)
   entry={'items':items}
 for item in (entry or {}).get('items') or []:
  li=xbmcgui.ListItem(label=item.get('label',''),offscreen=True)
  li.setArt(item.get('art') or {});li.setInfo('video',info(item))
  if item.get('uniqueid'):li.setUniqueIDs(item['uniqueid'])
  for k,v in properties(item).items():li.setProperty(k,v)
  xbmcplugin.addDirectoryItem(handle,item['path'],li,isFolder=bool(item.get('folder')))
 kinds={i.get('mediatype') for i in (entry or {}).get('items') or []}
 if len(kinds)==1 and kinds<={'movie','tvshow','episode'}:xbmcplugin.setContent(handle,{'movie':'movies','tvshow':'tvshows','episode':'episodes'}[kinds.pop()])
 xbmcplugin.endOfDirectory(handle,cacheToDisc=False)

def refresh(rpc,read,write,paths,wait=lambda s:False,now=time.time,pause=1.0):
 """Refresh stale copies one after another (one TMDb Helper run at a time). wait(seconds) returns True on abort."""
 done=[]
 for path in dict.fromkeys(p for p in paths if cacheable(p)):
  if not stale(load(read,path),now):continue
  try:items=fetch(rpc,path)
  except Exception:items=None
  if items:store(write,path,items,now);done.append(path)
  if wait(pause):break
 return done
