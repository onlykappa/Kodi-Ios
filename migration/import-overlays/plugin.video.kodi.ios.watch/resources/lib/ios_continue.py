"""Continue Watching for the iPhone: what the owner started, movies and episodes together, newest first.

Playback on the phone goes through TMDb Helper and the "How would you like to watch?" chooser, so Kodi's
library usually never learns about it. The chooser records each title it plays here (record); the bootstrap
service updates the position while it plays and drops a title once it is finished (portrait.track_progress).
plugin://plugin.video.kodi.ios.watch/?action=continue&type=all|movie|episode lists them, merged with Kodi's own
in-progress library items (downloaded media), as a Kodi directory the skin shows as a row.
"""
import json,time
STORE='special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json'
HELPER='plugin://plugin.video.themoviedb.helper/'
LIMIT=40
FINISHED=0.92

def key(entry):
 if entry.get('download_key'):return entry['download_key']
 return '%s:%s:%s:%s'%(entry['kind'],entry['tmdb_id'],entry.get('season') or '',entry.get('episode') or '')

def load(read):
 try:data=json.loads(read(STORE) or '{}')
 except ValueError:data={}
 data.setdefault('items',{});return data

def save(data,write):
 items=sorted(data['items'].items(),key=lambda kv:-kv[1].get('played',0))[:LIMIT]
 data['items']=dict(items);write(STORE,json.dumps(data,indent=1))

def player_key(player):
 """key() for the title TMDb Helper is about to play."""
 kind='movie' if getattr(player,'tmdb_type','')=='movie' else 'episode'
 entry={'kind':kind,'tmdb_id':str(getattr(player,'tmdb_id','') or '')}
 if kind=='episode':entry.update(season=str(getattr(player,'season','') or ''),episode=str(getattr(player,'episode','') or ''))
 return key(entry)

def saved_choice(read,item_key):
 """The player ('elementum', 'umbrella', 'local') and version picked last time for this title, or {}."""
 entry=load(read)['items'].get(item_key) or {}
 return {k:entry[k] for k in ('player','version') if entry.get(k)}

def forget_choice(read,write,item_key):
 """Long press › Choose source: ask again next time (and remember the new pick)."""
 data=load(read);entry=data['items'].get(item_key)
 if not entry:return False
 entry.pop('player',None);entry.pop('version',None);save(data,write);return True

def record(player,read,write,now=time.time,choice=None,preserve_player=False):
 """Called by the chooser when it hands a title to a player (choice: 'elementum', 'umbrella' or 'local'). The
 version picked last time is kept while the same player is used; the Choose a version page replaces it."""
 kind='movie' if getattr(player,'tmdb_type','')=='movie' else 'episode'
 details=player.details;info=getattr(details,'infolabels',{}) or {};art=getattr(details,'art',{}) or {}
 entry={'kind':kind,'tmdb_id':str(getattr(player,'tmdb_id','') or ''),'title':str(info.get('title') or ''),
        'tvshowtitle':str(info.get('tvshowtitle') or ''),'year':str(info.get('year') or ''),
        'art':{k:v for k,v in art.items() if k in ('poster','fanart','landscape','thumb','clearlogo','tvshow.poster','tvshow.fanart','tvshow.landscape','tvshow.clearlogo') and v}}
 if kind=='episode':entry.update(season=str(getattr(player,'season','') or ''),episode=str(getattr(player,'episode','') or ''))
 if not entry['tmdb_id']:return None
 data=load(read);old=data['items'].get(key(entry),{})
 entry.update(position=old.get('position',0),total=old.get('total',0),played=now())
 # A downloaded copy is a playback location, not a new provider choice. Keep Umbrella/Elementum for when that
 # copy is moved or removed; an explicit player selection still replaces the old choice/version.
 entry['player']=old.get('player') if preserve_player and old.get('player') in ('umbrella','elementum') else choice or old.get('player')
 if choice:entry['playback_source']=choice
 if old.get('version') and entry['player']==old.get('player'):entry['version']=old['version']
 if not entry['player']:del entry['player']
 data['items'][key(entry)]=entry;data['current']=key(entry);save(data,write)
 return key(entry)

def record_downloaded_movie(params,path,position,total,read,write,now=time.time,art=None):
 """A downloaded movie is tracked even before cached artwork supplies a TMDb ID; never invent a provider ID."""
 import hashlib
 from ios_library import show_key
 data=load(read);title=params.get('title','');year=str(params.get('year') or '')
 candidates=[(k,e) for k,e in data['items'].items() if e.get('kind')=='movie' and show_key(e.get('title'))==show_key(title)
             and str(e.get('year') or '')==year]
 if candidates:item_key,old=max(candidates,key=lambda pair:pair[1].get('played',0))
 else:
  tmdb=str(params.get('tmdb_id') or '')
  old={'kind':'movie','tmdb_id':tmdb if tmdb.isdecimal() else ''}
  if not old['tmdb_id']:old['download_key']='downloaded:'+hashlib.sha256((show_key(title)+':'+year).encode()).hexdigest()[:24]
  item_key=key(old)
 entry=dict(old,title=title,year=year,download_path=path,position=position,total=total,played=now(),playback_source='local')
 if art:entry['art']={k:v for k,v in art.items() if k in ('poster','fanart','landscape','thumb','clearlogo') and v}
 data['items'][item_key]=entry;data['current']=item_key;save(data,write);return item_key

def update(read,write,position,total,now=time.time):
 """Progress of the title the chooser last started (bootstrap service, while video plays)."""
 data=load(read);entry=data['items'].get(data.get('current'))
 if not entry or total<=0:return None
 entry.update(position=round(position),total=round(total),played=now());save(data,write)
 return entry

WATCHED_KEEP=2000

def watched_keys(entry):
 """What a finished title is known by in the Library: its Drive file id (item_id= in its play path) and its phone
 path. ISSUE-197: Free Up Space › Watched episodes had no watched set."""
 import urllib.parse
 out=[]
 for value in (entry.get('download_path'),entry.get('path'),entry.get('file')):
  value=str(value or '')
  if not value:continue
  query=urllib.parse.parse_qs(urllib.parse.urlsplit(value).query)
  for inner in query.get('path',[]):
   out+=[i for i in urllib.parse.parse_qs(urllib.parse.urlsplit(inner).query).get('item_id',[])]
  out+=query.get('item_id',[])
  if value.startswith('/'):out.append(value)
 return [k for k in dict.fromkeys(out) if k]

def stopped(read,write,now=time.time):
 """Playback ended: a finished title leaves the row and is remembered as watched (data['watched'], key -> time)."""
 data=load(read);current=data.pop('current',None);entry=data['items'].get(current)
 if entry and entry.get('total') and entry['position']>=FINISHED*entry['total']:
  del data['items'][current]
  watched=data.setdefault('watched',{})
  for k in watched_keys(entry):watched[k]=now()
  if len(watched)>WATCHED_KEEP:data['watched']=dict(sorted(watched.items(),key=lambda kv:-kv[1])[:WATCHED_KEEP])
 save(data,write);return entry

def watched_set(data):
 return set((data or {}).get('watched') or {})

# TMDb Helper hands unknown parameters on untouched; the watch menu (running inside its resolver) sees this one in
# sys.argv and plays the player and version picked last time instead of asking.
CONTINUE_FLAG='ios_continue=1'

def play_url(entry):
 if entry.get('download_key') and entry.get('download_path'):
  from ios_library import play_route
  from urllib.parse import parse_qsl,urlsplit,urlunsplit,urlencode
  route=play_route((entry['download_path'],entry['title'],entry.get('art',{}),
                   {'mediatype':entry['kind'],'year':entry.get('year',''),'resume':{'position':entry.get('position',0),'total':entry.get('total',0)}},False))
  parts=urlsplit(route);query=dict(parse_qsl(parts.query));query['ask']='0'
  return urlunsplit(parts._replace(query=urlencode(query)))
 if entry['kind']=='movie':return HELPER+'?info=play&tmdb_type=movie&tmdb_id='+entry['tmdb_id']+'&'+CONTINUE_FLAG
 return HELPER+'?info=play&tmdb_type=tv&tmdb_id=%s&season=%s&episode=%s&%s'%(entry['tmdb_id'],entry['season'],entry['episode'],CONTINUE_FLAG)

CHOOSE_FLAG='ios_choose=1'

def choose_url(entry):
 """The title's play link that always asks for the source (ios_watch_dialog.choosing)."""
 return play_url(entry).replace(CONTINUE_FLAG,CHOOSE_FLAG)

def entry_for(read,item_key):
 return load(read)['items'].get(item_key)

def choose_source_action(entry):
 from urllib.parse import quote
 return 'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=choose_source&key=%s)'%quote(key(entry),safe='')

HIDDEN_KEEP=400

def hide_key(entry):
 """What long press › Remove from Continue Watching remembers a title by: key() for the phone's own titles, the file
 for Kodi's library items (they have no TMDb id here)."""
 if entry.get('source')=='library' or not entry.get('tmdb_id') and not entry.get('download_key'):return 'file:'+str(entry.get('file') or '')
 return key(entry)

def hidden(data,entry):
 """Owner (2026-11-13): "remove from continue watching ... dont make it erase the progress ... if i watch it again it
 can show back up". A title is hidden while it has not been played since it was removed."""
 when=((data or {}).get('hidden') or {}).get(hide_key(entry))
 return when is not None and float(entry.get('played') or 0)<=float(when)

def hide(read,write,item_key,now=time.time):
 """Leave the row; the saved position, player and version stay (Resume still works from the title's own page)."""
 data=load(read);marks=data.setdefault('hidden',{});marks[item_key]=now()
 if len(marks)>HIDDEN_KEEP:data['hidden']=dict(sorted(marks.items(),key=lambda kv:-kv[1])[:HIDDEN_KEEP])
 save(data,write);return True

STAMP='KodiIOS.ContinueStamp'   # ISSUE-284: changed on every removal; part of every Continue Watching row's path


def clear_library_resume(item_key,rpc):
    """ISSUE-284: a library item's resume point in Kodi (file:<path> keys) is set back to 0, so Kodi's own in-progress lists
    leave it too. Returns True when one was cleared."""
    if not str(item_key).startswith('file:'):
        return False
    path=item_key[5:]
    if not path:
        return False
    flt={'field':'path','operator':'is','value':path}
    for kind,method,setter,ident in (('movies','VideoLibrary.GetMovies','VideoLibrary.SetMovieDetails','movieid'),
                                     ('episodes','VideoLibrary.GetEpisodes','VideoLibrary.SetEpisodeDetails','episodeid')):
        try:
            found=[i for i in (rpc(method,{'properties':['file']}).get(kind) or []) if i.get('file')==path]
        except Exception:
            found=[]
        for item in found:
            rpc(setter,{ident:item[ident],'resume':{'position':0,'total':0}})
            return True
    return False


def hide_action(entry):
 from urllib.parse import quote
 return 'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=continue_hide&key=%s)'%quote(hide_key(entry),safe='')

def entries(data,kind='all',library=()):
 """Started (position > 0) titles plus library in-progress items, newest first; removed ones left out until played again."""
 rows=[dict(e,source='phone') for e in data['items'].values() if e.get('position',0)>0 and kind in ('all',e['kind'])]
 rows+=[e for e in library if kind in ('all',e['kind'])]
 return sorted([e for e in rows if not hidden(data,e)],key=lambda e:-e.get('played',0))

def library_items(rpc):
 """Kodi's own in-progress movies and episodes (downloaded media in the library)."""
 out=[];inprogress={'field':'inprogress','operator':'true','value':''}
 stamp=lambda text:time.mktime(time.strptime(text,'%Y-%m-%d %H:%M:%S')) if text else 0
 movies=rpc('VideoLibrary.GetMovies',{'filter':inprogress,'properties':['title','art','resume','lastplayed','file','year']}).get('movies',[])
 for m in movies:
  out.append({'kind':'movie','title':m['title'],'year':str(m.get('year') or ''),'art':m.get('art',{}),'position':m['resume']['position'],
              'total':m['resume']['total'],'played':stamp(m.get('lastplayed')),'file':m['file'],'source':'library'})
 episodes=rpc('VideoLibrary.GetEpisodes',{'filter':inprogress,'properties':['title','showtitle','season','episode','art','resume','lastplayed','file']}).get('episodes',[])
 for ep in episodes:
  out.append({'kind':'episode','title':ep['title'],'tvshowtitle':ep['showtitle'],'season':str(ep['season']),'episode':str(ep['episode']),
              'art':ep.get('art',{}),'position':ep['resume']['position'],'total':ep['resume']['total'],'played':stamp(ep.get('lastplayed')),
              'file':ep['file'],'source':'library'})
 return out

def heal(entry,lookup):
 """Owner (build 252): Continue Watching cards recorded from Library playback had the file's name ("the maze
 runner", "phony") and no picture. A card missing art, or named in lower case, takes the Library's saved TMDb name and
 art (lookup(kind, title, year, tmdb_id) -> {'name', 'poster', 'fanart', ...}); nothing is fetched."""
 episode=entry.get('kind')=='episode'
 title=entry.get('tvshowtitle') if episode else entry.get('title')
 needs=not entry.get('art') or (title and title==title.lower())
 if not needs or not title:return entry
 found=lookup('tv' if episode else 'movie',title,'' if episode else entry.get('year',''),entry.get('tmdb_id','')) or {}
 if not found:return entry
 fixed=dict(entry)
 name=found.get('name') or ' '.join(w[:1].upper()+w[1:] for w in title.split(' '))
 if episode:fixed['tvshowtitle']=name
 else:fixed['title']=name
 if not entry.get('art'):
  pre='tvshow.' if episode else ''
  fixed['art']={pre+k:found[k] for k in ('poster','fanart','clearlogo') if found.get(k)}
 return fixed

def filler(xbmcvfs):
 """heal() with the Library's saved art (drive-library-art.json), or a no-op when it cannot be read."""
 try:
  import os,sys
  boot=xbmcvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')
  if boot not in sys.path:sys.path.insert(0,boot)
  import drivelibrary as lib
  cache=lib.load_json(os.path.join(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/'),'drive-library-art.json'),{})
 except Exception:return lambda entry:entry
 def lookup(kind,title,year,tmdb):
  found=dict(lib.artwork(kind,title,year,'',cache,None,cached_only=True) or {})
  if not found and kind=='movie':found=dict(lib.artwork(kind,title,'','',cache,None,cached_only=True) or {})
  tmdb=found.get('tmdb_id') or tmdb
  if kind=='tv' and tmdb:found.update({k:v for k,v in (lib.show_details(tmdb,'',cache,None,cached_only=True) or {}).items() if v})
  return found
 return lambda entry:heal(entry,lookup)

def directory(handle,kind):
 import xbmc,xbmcgui,xbmcplugin,xbmcvfs
 def read(path):
  f=xbmcvfs.File(path)
  try:return f.read()
  finally:f.close()
 def rpc(method,params):
  try:return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))).get('result',{})
  except ValueError:return {}
 data=load(read) if xbmcvfs.exists(STORE) else {'items':{}}
 fill=filler(xbmcvfs)
 for entry in entries(data,kind,library_items(rpc)):
  entry=fill(entry)
  episode=entry['kind']=='episode'
  li=xbmcgui.ListItem(label=entry['tvshowtitle'] if episode else entry['title'],offscreen=True)
  art=dict(entry.get('art',{}))
  for name in ('fanart','landscape','poster','clearlogo'):
   if episode and art.get('tvshow.'+name):art.setdefault(name,art['tvshow.'+name])
  li.setArt(art)
  tag=li.getVideoInfoTag();tag.setMediaType(entry['kind']);tag.setTitle(entry['title'])
  if episode:
   tag.setTvShowTitle(entry['tvshowtitle']);tag.setSeason(int(entry['season'] or 0));tag.setEpisode(int(entry['episode'] or 0))
  elif entry.get('year','').isdigit():tag.setYear(int(entry['year']))
  tag.setResumePoint(entry.get('position',0),entry.get('total',0))
  li.setProperty('subtitle','S%s, E%s'%(entry['season'],entry['episode']) if episode else entry.get('year',''))
  li.setProperty('IsPlayable','true')
  # Long press: pick the player and version again (a tap reuses last time's).
  menu=[('Choose source',choose_source_action(entry))] if entry.get('source')=='phone' and entry.get('tmdb_id') else []
  li.addContextMenuItems(menu+[('Remove from Continue Watching',hide_action(entry))])
  xbmcplugin.addDirectoryItem(handle,entry.get('file') or play_url(entry),li,isFolder=False)
 xbmcplugin.setContent(handle,'videos');xbmcplugin.setPluginCategory(handle,'Continue Watching');xbmcplugin.endOfDirectory(handle)
