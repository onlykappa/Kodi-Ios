"""Library › Movies / TV Shows for the iPhone: Kodi's own library together with the videos kept in Google Drive ›
Kodi Downloads (service.kodi.ios.bootstrap/resources/lib/drivelibrary.py reads Drive).

plugin://plugin.video.kodi.ios.watch/?action=library&type=movie        movies
plugin://plugin.video.kodi.ios.watch/?action=library&type=tv           shows (a Drive show opens its episodes)
plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&folder=ID episodes of one show folder in Drive
plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&show=T&merge=1[&folder=ID] one show from the phone and Drive
"""
import json,math,os,re,sys,time,urllib.parse
BOOT='special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib'
STATE='special://profile/addon_data/service.kodi.ios.bootstrap/'
ME='plugin://plugin.video.kodi.ios.watch/'
REFRESH='RunPlugin('+ME+'?action=library_refresh)'

def page_url(params):return ME+'?'+urllib.parse.urlencode(dict(action='library',**params))

def current_params(path):
 """Only our Library can be refreshed; rebuild the URL instead of executing an arbitrary folder path."""
 url=urllib.parse.urlsplit(path);query=urllib.parse.parse_qs(url.query)
 if url.scheme!='plugin' or url.netloc!='plugin.video.kodi.ios.watch' or query.get('action')!=['library']:return None
 return {k:v[0] for k,v in query.items() if k in ('type','folder','show','year','local','loose','merge','season')}

def refresh_current(info,invoke):
 params=current_params(info('Container.FolderPath'))
 if params is not None:invoke('Container.Refresh(%s)'%page_url(dict(params,fresh='1')))

def root_directory(handle):
 """A real destination for Kodi's parent-folder entry and the add-on's root."""
 import xbmcgui,xbmcplugin
 for title,kind in (('Movies','movie'),('TV Shows','tv')):
  li=xbmcgui.ListItem(label=title,offscreen=True)
  xbmcplugin.addDirectoryItem(handle,page_url({'type':kind}),li,isFolder=True)
 xbmcplugin.setPluginCategory(handle,'Library');xbmcplugin.setContent(handle,'files')
 xbmcplugin.endOfDirectory(handle,cacheToDisc=False)

def local_entries(kind,lib):
 """Local completion is independent of a Kodi scan or a future Drive upload."""
 from ios_downloaded import completed_files
 out=[]
 for path in completed_files(kind):
  info=lib.parse(os.path.basename(path))
  # Season packs often use just S01E02.mkv or Episode S01E02.mkv inside a named show folder.
  if info['title'].casefold() in ('movie','video','feature','episode') or re.match(r'^(?:s\d+[ ._-]*e\d+|\d+x\d+)',info['title'],re.I):
   for parent in list(reversed(os.path.dirname(path).split(os.sep))):
    if not parent or parent in ('Movies','TV Shows','Kodi Downloads','Elementum Downloads'):break
    candidate=lib.parse(parent)
    if re.match(r'^(?:season\b|s\d+\b)',parent,re.I):continue
    info['title']=candidate['title'];info['year']=info['year'] or candidate['year'];break
  if (kind=='movie' and info['season']) or (kind=='tv' and not info['season']):continue
  out.append(dict(info,path=path))
 return out

def show_key(title):return re.sub(r'[^0-9a-z]+','',str(title).casefold())

def local_rows(kind,show,year,entries,lib,art_cache,key,get,cached_only=False,any_year=False):
 rows=[];seen=set()
 for entry in entries:
  identity=(entry['title'].casefold(),entry['year'])
  if show and (show_key(entry['title'])!=show_key(show) if any_year else identity!=(show.casefold(),year)):continue
  if kind=='tv' and not show:
   if identity in seen:continue
   seen.add(identity);path=page_url({'type':'tv','local':'1','show':entry['title'],'year':entry['year']})
   label=entry['title'];info={'mediatype':'tvshow','year':entry['year'],'source':'local'};folder=True
  else:
   path=entry['path'];folder=False;label=entry['title'];info={'year':entry['year'],'source':'local','mediatype':'movie'}
   if kind=='tv':
    label='S%02dE%02d'%(int(entry['season']),int(entry['episode']))
    info.update(mediatype='episode',season=entry['season'],episode=entry['episode'],tvshowtitle=entry['title'])
  art=lib.artwork(kind,entry['title'],entry['year'],key,art_cache,get,cached_only=cached_only)
  rows.append((path,label,art,info,folder))
 return sorted(rows,key=lambda r:(int(r[3].get('season') or 0),int(r[3].get('episode') or 0),r[1].casefold()))

def library_rows(kind,rpc):
 """Kodi's own library: [(path, label, art, info, is_folder)]."""
 rows=[]
 if kind=='movie':
  for m in rpc('VideoLibrary.GetMovies',{'properties':['title','year','art','file','plot','resume']}).get('movies',[]):
   rows.append((m['file'],m['title'],m.get('art',{}),{'year':m.get('year'),'plot':m.get('plot',''),'mediatype':'movie',
                'resume':m.get('resume') or {}},False))
 else:
  for s in rpc('VideoLibrary.GetTVShows',{'properties':['title','year','art','plot']}).get('tvshows',[]):
   rows.append(('videodb://tvshows/titles/%d/'%s['tvshowid'],s['title'],s.get('art',{}),{'year':s.get('year'),'plot':s.get('plot',''),
                'mediatype':'tvshow'},True))
 return rows

def drive_rows(kind,folder,show,lib,state_dir,art_cache,key,get,fresh=False,loose=False,year='',cached_only=False):
 """Google Drive › Kodi Downloads: [(path, label, art, info, is_folder)]."""
 entries,driveid=lib.listing(kind,state_dir,folder,strict=True,fresh=fresh)
 rows=[]
 for e in entries:
  if folder and loose and (e['title'].casefold()!=show.casefold() or e['year']!=year):continue
  if folder:
   art=lib.artwork('tv',show or e['title'],'',key,art_cache,get,cached_only=cached_only)
   label=('S%02dE%02d  '%(int(e['season']),int(e['episode'])) if e['season'] else '')+(e['title'] if not show else '')
   rows.append((lib.play_url(driveid,e['id']),label.strip() or e['name'],{'poster':art.get('poster',''),'fanart':art.get('fanart',''),'thumb':art.get('fanart','')},
                {'mediatype':'episode','season':e['season'],'episode':e['episode'],'tvshowtitle':show,'source':'drive'},False))
  elif kind=='movie':
   art=lib.artwork('movie',e['title'],e['year'],key,art_cache,get,cached_only=cached_only)
   rows.append((lib.play_url(driveid,e['id']),e['title'],{'poster':art.get('poster',''),'fanart':art.get('fanart','')},
                {'year':e['year'],'plot':art.get('plot',''),'mediatype':'movie','source':'drive'},False))
  else:
   art=lib.artwork('tv',e['title'],e['year'],key,art_cache,get,cached_only=cached_only)
   params={'type':'tv','folder':e['id'],'show':e['title']}
   if e.get('loose'):params.update(loose='1',year=e['year'])
   path=page_url(params)
   rows.append((path,e['title'],{'poster':art.get('poster',''),'fanart':art.get('fanart','')},
                {'year':e['year'],'plot':art.get('plot',''),'mediatype':'tvshow','source':'drive'},True))
 return rows

# Owner (build 146): one show was listed three times (phone episode, a season pack still seeding with "(2026)" in its
# folder name, and the Drive folder), and the same movie can be both on the phone and on Drive.
def merge_shows(rows):
 """One card per downloaded show (same name ignoring case, punctuation and year), opening one page with the
 phone's and Drive's episodes. Kodi's own library rows are left alone."""
 order=[];groups={}
 for row in rows:
  info=row[3]
  if info.get('mediatype')!='tvshow' or info.get('source') not in ('local','drive'):order.append(row);continue
  k=show_key(row[1])
  if k not in groups:groups[k]=[];order.append(k)
  groups[k].append(row)
 out=[]
 for item in order:
  if not isinstance(item,str):out.append(item);continue
  group=groups[item]
  if len(group)==1:out.append(group[0]);continue
  params={'type':'tv','show':group[0][1],'merge':'1'}
  for path,label,art,info,folder in group:
   found=current_params(path) or {}
   if info['source']=='drive' and found.get('folder') and 'folder' not in params:
    params['folder']=found['folder']
    if found.get('loose'):params.update(loose='1',year=found.get('year',''))
  art=next((r[2] for r in group if r[2].get('poster')),group[0][2])
  sources={r[3]['source'] for r in group}
  info=dict(group[0][3],source='both' if len(sources)>1 else sources.pop())
  out.append((page_url(params),group[0][1],art,info,True))
 return out

def merge_movies(rows):
 """A movie both on the phone and on Drive shows once (the phone copy, listed first, plays without streaming)."""
 out=[];seen=set()
 for row in rows:
  info=row[3]
  if info.get('mediatype')=='movie' and info.get('source') in ('local','drive'):
   k=(show_key(row[1]),str(info.get('year') or ''))
   if k in seen:continue
   seen.add(k)
  out.append(row)
 return out

def episode_rows(rows,show,lib,art_cache,key,get,cached_only=True):
 """The show's episodes once each (phone copy first), in order, with TMDb names, plots, stills and the show's art
 for the page header (the same window TMDb Helper's show pages use)."""
 showart=lib.artwork('tv',show,'',key,art_cache,get,cached_only=cached_only) if show else {}
 showart=dict(showart,**lib.show_details(showart.get('tmdb_id'),key,art_cache,get,cached_only=cached_only))
 tmdb=showart.get('tmdb_id');out=[];seen=set()
 for path,label,art,info,folder in rows:
  if info.get('mediatype')!='episode':out.append((path,label,art,info,folder));continue
  number=(int(info.get('season') or 0),int(info.get('episode') or 0))
  if number!=(0,0):
   if number in seen:continue
   seen.add(number)
  ep=(lib.season(tmdb,number[0],key,art_cache,get,cached_only=cached_only).get(str(number[1]),{}) if tmdb else {})
  fan=showart.get('fanart') or art.get('fanart','');poster=showart.get('poster') or art.get('poster','')
  art=dict(art,**{k:v for k,v in {'fanart':fan,'poster':poster,'tvshow.fanart':fan,'tvshow.poster':poster,
                                  'tvshow.clearlogo':showart.get('clearlogo'),'thumb':ep.get('thumb') or art.get('thumb') or fan}.items() if v})
  info=dict(info,tvshowtitle=info.get('tvshowtitle') or show)
  if ep.get('plot'):info['plot']=ep['plot']
  if ep.get('runtime'):info['duration']=int(ep['runtime'])*60
  if ep.get('aired'):info['premiered']=ep['aired']
  if showart.get('rating'):info['rating']=showart['rating']
  if showart.get('genres'):info['genres']=showart['genres']
  if showart.get('year'):info['year']=showart['year']
  info['tmdb_id']=tmdb or ''
  out.append((path,ep.get('title') or label,art,info,folder))
 return sorted(out,key=lambda r:(int(r[3].get('season') or 0),int(r[3].get('episode') or 0)) if r[3].get('mediatype')=='episode' else (-1,0))

def cloud_entries(params,lib,state_dir,fresh=False):
 """Every matching downloaded-show folder, not just the first phone/Drive duplicate selected on the grid."""
 show=params.get('show','');folders,driveid=lib.listing('tv',state_dir,strict=True,fresh=fresh)
 matches=[entry for entry in folders if show_key(entry.get('title'))==show_key(show)]
 if params.get('folder') and not any(entry.get('id')==params['folder'] for entry in matches):
  matches.append({'id':params['folder'],'loose':params.get('loose')=='1','year':params.get('year','')})
 out=[];seen=set()
 for folder in matches:
  entries,driveid=lib.listing('tv',state_dir,folder['id'],strict=True,fresh=fresh)
  for entry in entries:
   if folder.get('loose') and (show_key(entry.get('title'))!=show_key(show) or entry.get('year','')!=folder.get('year','')):continue
   if entry['id'] in seen:continue
   seen.add(entry['id']);out.append(dict(entry,_driveid=driveid))
 return out

def downloaded_rows(params,lib,state_dir,local,art_cache,key,cloud=()):
 """The show's real completed copies only, with phone copies preferred over matching Drive episodes."""
 show=params.get('show','')
 rows=local_rows('tv',show,params.get('year',''),local,lib,art_cache,key,None,cached_only=True,any_year=True)
 for entry in cloud:
  rows.append((lib.play_url(entry['_driveid'],entry['id']),entry.get('title') or entry['name'],{},
               {'mediatype':'episode','season':entry.get('season') or '0','episode':entry.get('episode') or '0',
                'tvshowtitle':show,'source':'drive'},False))
 return episode_rows(rows,show,lib,art_cache,key,None)

def resume_rows(rows,show,rpc,history):
 """Read Kodi bookmarks plus the app's latest episode progress, matching show and coordinates, never 'Pilot'."""
 saved={}
 for entry in history.get('items',{}).values():
  if entry.get('kind')!='episode' or show_key(entry.get('tvshowtitle'))!=show_key(show):continue
  try:number=(int(entry.get('season') or 0),int(entry.get('episode') or 0))
  except (ValueError,TypeError):continue
  if number not in saved or entry.get('played',0)>saved[number].get('played',0):saved[number]=entry
 # Files.GetFileDetails rescans a parent directory and can invoke a plugin directory for a plugin URL.
 # Batch local parents once; Drive/provider URLs are never passed to filesystem RPCs.
 bookmarks={}
 parents={os.path.dirname(row[0]) for row in rows if os.path.isabs(row[0])}
 for parent in sorted(parents):
  try:files=rpc('Files.GetDirectory',{'directory':parent,'media':'video','properties':['resume','playcount','lastplayed']}).get('files') or []
  except (ValueError,RuntimeError):files=[]
  for entry in files:
   if entry.get('file'):bookmarks[entry['file']]=entry
 if any(not os.path.isabs(row[0]) for row in rows):
  try:
   entries=rpc('VideoLibrary.GetEpisodes',{'filter':{'field':'tvshow','operator':'is','value':show},
                  'properties':['file','resume','playcount','lastplayed']}).get('episodes') or []
  except (ValueError,RuntimeError):entries=[]
  for entry in entries:
   if entry.get('file'):bookmarks[entry['file']]=entry
 out=[]
 for path,label,art,info,folder in rows:
  info=dict(info);number=(int(info.get('season') or 0),int(info.get('episode') or 0))
  details=bookmarks.get(path) or {}
  resume=details.get('resume') or {};position=seconds(resume.get('position'));total=seconds(resume.get('total'))
  latest=saved.get(number) or {};played=seconds(latest.get('played'));bookmark_played=0
  try:bookmark_played=time.mktime(time.strptime(details.get('lastplayed') or '','%Y-%m-%d %H:%M:%S'))
  except (ValueError,TypeError,OverflowError):pass
  watched=bool(details.get('playcount'))
  if latest and played>=bookmark_played:
   position=seconds(latest.get('position'));total=seconds(latest.get('total'));watched=False
  info.update(resume={'position':position,'total':total},watched=watched or bool(total and position>=0.92*total),played=max(played,bookmark_played))
  out.append((path,label,art,info,folder))
 return out

def seconds(value):
 try:value=float(value or 0)
 except (ValueError,TypeError):return 0
 return value if math.isfinite(value) and value>0 else 0

def play_target(rows):
 """Resume the latest unfinished available episode; otherwise choose the first available unwatched episode."""
 if not rows:return None
 unfinished=[row for row in rows if row[3].get('resume',{}).get('position',0)>0 and not row[3].get('watched')]
 if unfinished:return max(unfinished,key=lambda row:row[3].get('played',0))
 return next((row for row in rows if not row[3].get('watched')),rows[0])

def play_route(row):
 path,label,art,info,folder=row
 values={'action':'library_play','path':path,'title':label,'show':info.get('tvshowtitle',''),
         'season':info.get('season','0'),'episode':info.get('episode','0'),'tmdb_id':info.get('tmdb_id',''),
         'resume':info.get('resume',{}).get('position',0),'total':info.get('resume',{}).get('total',0)}
 return ME+'?'+urllib.parse.urlencode(values)

def play_properties(rows):
 target=play_target(rows);props={'KodiIOS.DownloadedShow':'true','KodiIOS.PlayLabel':'','KodiIOS.PlayPath':'','KodiIOS.PlayResume':'0'}
 if target:
  resume=target[3].get('resume',{}).get('position',0);number=int(target[3].get('episode') or 0)
  props.update({'KodiIOS.PlayLabel':('Continue Episode %d' if resume and not target[3].get('watched') else 'Play Episode %d')%number,
                'KodiIOS.PlayPath':play_route(target),'KodiIOS.PlayResume':str(resume)})
 return props

def season_rows(rows,params,lib,art_cache,key):
 show=params.get('show','');search=lib.artwork('tv',show,'',key,art_cache,None,cached_only=True)
 details=lib.show_details(search.get('tmdb_id'),key,art_cache,None,cached_only=True);metadata=dict(search,**details)
 out=[]
 for number in sorted({int(row[3].get('season') or 0) for row in rows}):
  episodes=[row for row in rows if int(row[3].get('season') or 0)==number]
  props=play_properties(episodes);art={}
  for name in ('poster','fanart','clearlogo'):
   if metadata.get(name):art[name]=metadata[name];art['tvshow.'+name]=metadata[name]
  info={'mediatype':'season','season':str(number),'tvshowtitle':show,'year':metadata.get('year') or params.get('year',''),
        'plot':metadata.get('plot',''),'genres':metadata.get('genres',[]),'rating':metadata.get('rating',0),'properties':props}
  route={k:v for k,v in params.items() if k in ('type','folder','show','year','local','loose','merge')};route['season']=str(number)
  out.append((page_url(route),'Specials' if number==0 else 'Season %d'%number,art,info,True))
 return out

def play_downloaded(handle,params):
 """Resolve a completed copy directly and retain progress in the same history used by Continue Watching."""
 import xbmc,xbmcgui,xbmcplugin,xbmcvfs
 from types import SimpleNamespace
 path=params.get('path','');url=urllib.parse.urlsplit(path);query=urllib.parse.parse_qs(url.query)
 local=os.path.isabs(path) and os.path.isfile(path) and os.path.getsize(path)>0
 drive=url.scheme=='plugin' and url.netloc=='plugin.googledrive' and query.get('action')==['play'] and bool(query.get('item_id'))
 if local:
  from ios_downloaded import completed_files
  local=os.path.realpath(path) in {os.path.realpath(copy) for copy in completed_files('tv')}
 if not (local or drive):
  xbmcplugin.setResolvedUrl(handle,False,xbmcgui.ListItem());return
 position=seconds(params.get('resume'));total=seconds(params.get('total'))
 if total and position>=0.92*total:position=0
 li=xbmcgui.ListItem(label=params.get('title',''),path=path);li.setProperty('IsPlayable','true')
 li.getVideoInfoTag().setResumePoint(position,total)
 if position:li.setProperty('StartOffset',str(position))
 import ios_continue
 def read(location):
  source=xbmcvfs.File(location)
  try:return source.read()
  finally:source.close()
 def write(location,text):
  target=xbmcvfs.File(location,'w')
  try:target.write(text)
  finally:target.close()
 try:
  if str(params.get('tmdb_id','')).isdecimal():
   player=SimpleNamespace(tmdb_type='tv',tmdb_id=params['tmdb_id'],season=params.get('season','0'),episode=params.get('episode','0'),
                          details=SimpleNamespace(infolabels={'title':params.get('title',''),'tvshowtitle':params.get('show','')},art={}))
   ios_continue.record(player,read,write,choice='local',preserve_player=True)
  else:
   data=ios_continue.load(read);data.pop('current',None);ios_continue.save(data,write)
 except (OSError,ValueError,RuntimeError):xbmc.log('Kodi iOS Library: playback history could not be updated',xbmc.LOGWARNING)
 xbmcplugin.setResolvedUrl(handle,True,li)

def directory(handle,params):
 import xbmc,xbmcaddon,xbmcgui,xbmcplugin,xbmcvfs
 kind='tv' if params.get('type')=='tv' else 'movie';folder=params.get('folder');show=params.get('show','')
 local=params.get('local')=='1';merge=params.get('merge')=='1';episodes=bool(folder or local or merge);year=params.get('year','')
 show_page=kind=='tv' and episodes and bool(show)
 boot=xbmcvfs.translatePath(BOOT)
 if boot not in sys.path:sys.path.insert(0,boot)  # reused interpreter: once
 import drivelibrary as lib
 state_dir=xbmcvfs.translatePath(STATE)
 def rpc(method,args):
  try:return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':args}))).get('result',{})
  except ValueError:return {}
 rows=[] if episodes else library_rows(kind,rpc)
 try:
  helper=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path'))
  key=lib.tmdb_key(helper)
 except Exception:key=''
 art_path=os.path.join(state_dir,'drive-library-art.json');art_cache=lib.load_json(art_path,{})
 # Posters must never hold up a directory: the visible-page worker fills missing art later.
 get=None
 if show_page:
  phone=[];cloud=[]
  try:phone=local_entries('tv',lib)
  except OSError:
   xbmcgui.Dialog().notification('Library','Phone downloads could not be checked',xbmcgui.NOTIFICATION_WARNING,4000)
  try:
   if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.googledrive)'):
    cloud=cloud_entries(params,lib,state_dir,params.get('fresh')=='1')
  except Exception as error:
   xbmc.log('Kodi iOS Library: Google Drive listing failed: '+type(error).__name__,xbmc.LOGWARNING)
   xbmcgui.Dialog().notification('Library','Google Drive could not be listed',xbmcgui.NOTIFICATION_WARNING,4000)
  rows=downloaded_rows(params,lib,state_dir,phone,art_cache,key,cloud)
  try:
   import ios_continue
   history_file=xbmcvfs.File(ios_continue.STORE)
   try:history=json.loads(history_file.read() or '{}')
   finally:history_file.close()
  except (OSError,ValueError,AttributeError):history={}
  rows=resume_rows(rows,show,rpc,history)
  if params.get('season') is not None:
   rows=[row for row in rows if str(row[3].get('season') or '0')==params['season']]
  props=play_properties(rows)
  search=lib.artwork('tv',show,'',key,art_cache,None,cached_only=True)
  details=dict(search,**lib.show_details(search.get('tmdb_id'),key,art_cache,None,cached_only=True))
  props.update({'KodiIOS.ShowPlot':details.get('plot',''),'KodiIOS.ShowYear':str(details.get('year') or year),
                'KodiIOS.ShowRating':str(details.get('rating') or ''),'KodiIOS.ShowGenres':' / '.join(details.get('genres') or [])})
  if params.get('season') is None:rows=season_rows(rows,params,lib,art_cache,key)
  else:rows=[(play_route(row),row[1],row[2],dict(row[3],properties=play_properties([row])),row[4]) for row in rows]
 else:
  props={key:'' for key in ('KodiIOS.DownloadedShow','KodiIOS.PlayLabel','KodiIOS.PlayPath','KodiIOS.PlayResume',
                           'KodiIOS.ShowPlot','KodiIOS.ShowYear','KodiIOS.ShowRating','KodiIOS.ShowGenres')}
 if not show_page and (not folder or merge):
  try:rows+=local_rows(kind,show if (local or merge) else '',year,local_entries(kind,lib),lib,art_cache,key,get,cached_only=True,any_year=merge)
  except OSError as error:
   xbmc.log('Kodi iOS Library: phone download listing failed: '+type(error).__name__,xbmc.LOGWARNING)
   xbmcgui.Dialog().notification('Library','Phone downloads could not be checked',xbmcgui.NOTIFICATION_WARNING,4000)
 try:
  if not show_page and not local and (folder or not merge) and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.googledrive)'):
   rows+=drive_rows(kind,folder,show,lib,state_dir,art_cache,key,get,params.get('fresh')=='1',params.get('loose')=='1',year,cached_only=True)
 except Exception as error:
  xbmc.log('Kodi iOS Library: Google Drive listing failed: '+type(error).__name__,xbmc.LOGWARNING)
  xbmcgui.Dialog().notification('Library','Google Drive could not be listed',xbmcgui.NOTIFICATION_WARNING,4000)
 if kind=='tv' and episodes and not show_page:rows=episode_rows(rows,show,lib,art_cache,key,get)
 elif kind=='tv':rows=merge_shows(rows)
 else:rows=merge_movies(rows)
 seen=set()
 for name,value in props.items():xbmcplugin.setProperty(handle,name,value)
 for path,label,art,info,is_folder in rows:
  if path in seen:continue
  seen.add(path)
  li=xbmcgui.ListItem(label=label,offscreen=True);li.setArt({k:v for k,v in art.items() if v})
  li.addContextMenuItems([('Refresh Library',REFRESH)])
  for name,value in info.get('properties',{}).items():li.setProperty(name,value)
  if info.get('source'):li.setLabel2({'local':'On this iPhone','drive':'Google Drive'}.get(info['source'],'iPhone and Google Drive'))
  tag=li.getVideoInfoTag();tag.setMediaType(info.get('mediatype','video'));tag.setTitle(label)
  if info.get('year'):
   try:tag.setYear(int(info['year']))
   except (TypeError,ValueError):pass
  if info.get('plot'):tag.setPlot(info['plot'])
  if info.get('tvshowtitle'):tag.setTvShowTitle(info['tvshowtitle'])
  if info.get('season'):tag.setSeason(int(info['season']))
  if info.get('episode'):tag.setEpisode(int(info['episode']))
  if info.get('duration'):tag.setDuration(int(info['duration']))
  if info.get('premiered'):tag.setPremiered(info['premiered']);tag.setFirstAired(info['premiered'])
  if info.get('rating'):
   try:tag.setRating(float(info['rating']))
   except (TypeError,ValueError):pass
  if info.get('genres'):tag.setGenres(info['genres'])
  resume=info.get('resume') or {}
  if resume.get('position'):tag.setResumePoint(resume['position'],resume.get('total',0))
  if not is_folder:li.setProperty('IsPlayable','true')
  xbmcplugin.addDirectoryItem(handle,path,li,isFolder=is_folder)
 # Always offer refresh, including an empty Library; Kodi ignores this non-media action in playlists.
 if not show_page:
  refresh=xbmcgui.ListItem(label='Refresh Library',offscreen=True)
  refresh.setArt({'icon':'DefaultFolder.png'});refresh.setProperty('IsPlayable','false')
  clean={k:v for k,v in params.items() if k in ('type','folder','show','year','local','loose','merge','season')}
  xbmcplugin.addDirectoryItem(handle,page_url(dict(clean,fresh='1')),refresh,isFolder=True)
 content='seasons' if show_page and params.get('season') is None else ('episodes' if episodes else ('movies' if kind=='movie' else 'tvshows'))
 xbmcplugin.setContent(handle,content)
 xbmcplugin.setPluginCategory(handle,show or ('Downloaded Movies' if kind=='movie' else 'Downloaded TV Shows'))
 xbmcplugin.endOfDirectory(handle,cacheToDisc=False)
