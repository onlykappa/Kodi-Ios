"""Library › Movies / TV Shows for the iPhone: Kodi's own library together with the videos kept in Google Drive ›
Kodi Downloads (service.kodi.ios.bootstrap/resources/lib/drivelibrary.py reads Drive).

plugin://plugin.video.kodi.ios.watch/?action=library&type=movie        movies
plugin://plugin.video.kodi.ios.watch/?action=library&type=tv           shows (a Drive show opens its episodes)
plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&folder=ID episodes of one show folder in Drive
"""
import json,os,sys,urllib.parse
BOOT='special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib'
STATE='special://profile/addon_data/service.kodi.ios.bootstrap/'
ME='plugin://plugin.video.kodi.ios.watch/'

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

def drive_rows(kind,folder,show,lib,state_dir,art_cache,key,get):
 """Google Drive › Kodi Downloads: [(path, label, art, info, is_folder)]."""
 entries,driveid=lib.listing(kind,state_dir,folder)
 rows=[]
 for e in entries:
  if folder:
   art=lib.artwork('tv',show or e['title'],'',key,art_cache,get)
   label=('S%02dE%02d  '%(int(e['season']),int(e['episode'])) if e['season'] else '')+(e['title'] if not show else '')
   rows.append((lib.play_url(driveid,e['id']),label.strip() or e['name'],{'poster':art.get('poster',''),'fanart':art.get('fanart',''),'thumb':art.get('fanart','')},
                {'mediatype':'episode','season':e['season'],'episode':e['episode'],'tvshowtitle':show,'source':'drive'},False))
  elif kind=='movie':
   art=lib.artwork('movie',e['title'],e['year'],key,art_cache,get)
   rows.append((lib.play_url(driveid,e['id']),e['title'],{'poster':art.get('poster',''),'fanart':art.get('fanart','')},
                {'year':e['year'],'plot':art.get('plot',''),'mediatype':'movie','source':'drive'},False))
  else:
   art=lib.artwork('tv',e['title'],e['year'],key,art_cache,get)
   path=ME+'?'+urllib.parse.urlencode({'action':'library','type':'tv','folder':e['id'],'show':e['title']})
   rows.append((path,e['title'],{'poster':art.get('poster',''),'fanart':art.get('fanart','')},
                {'year':e['year'],'plot':art.get('plot',''),'mediatype':'tvshow','source':'drive'},True))
 return rows

def directory(handle,params):
 import xbmc,xbmcaddon,xbmcgui,xbmcplugin,xbmcvfs
 import urllib.request
 kind='tv' if params.get('type')=='tv' else 'movie';folder=params.get('folder');show=params.get('show','')
 boot=xbmcvfs.translatePath(BOOT)
 if boot not in sys.path:sys.path.insert(0,boot)  # reused interpreter: once
 import drivelibrary as lib
 state_dir=xbmcvfs.translatePath(STATE)
 def rpc(method,args):
  try:return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':args}))).get('result',{})
  except ValueError:return {}
 rows=[] if folder else library_rows(kind,rpc)
 try:
  helper=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path'))
  key=lib.tmdb_key(helper)
 except Exception:key=''
 art_path=os.path.join(state_dir,'drive-library-art.json');art_cache=lib.load_json(art_path,{})
 get=lambda url:urllib.request.urlopen(url,timeout=8).read()
 try:rows+=drive_rows(kind,folder,show,lib,state_dir,art_cache,key,get)
 except Exception as error:
  xbmc.log('Kodi iOS Library: Google Drive listing failed: %s: %s'%(type(error).__name__,error),xbmc.LOGWARNING)
  xbmcgui.Dialog().notification('Library','Google Drive could not be listed',xbmcgui.NOTIFICATION_WARNING,4000)
 lib.save_json(art_path,art_cache)
 for path,label,art,info,is_folder in rows:
  li=xbmcgui.ListItem(label=label,offscreen=True);li.setArt({k:v for k,v in art.items() if v})
  tag=li.getVideoInfoTag();tag.setMediaType(info.get('mediatype','video'));tag.setTitle(label)
  if info.get('year'):
   try:tag.setYear(int(info['year']))
   except (TypeError,ValueError):pass
  if info.get('plot'):tag.setPlot(info['plot'])
  if info.get('tvshowtitle'):tag.setTvShowTitle(info['tvshowtitle'])
  if info.get('season'):tag.setSeason(int(info['season']))
  if info.get('episode'):tag.setEpisode(int(info['episode']))
  resume=info.get('resume') or {}
  if resume.get('position'):tag.setResumePoint(resume['position'],resume.get('total',0))
  if not is_folder:li.setProperty('IsPlayable','true')
  xbmcplugin.addDirectoryItem(handle,path,li,isFolder=is_folder)
 xbmcplugin.setContent(handle,'episodes' if folder else ('movies' if kind=='movie' else 'tvshows'))
 xbmcplugin.setPluginCategory(handle,show or ('Movies' if kind=='movie' else 'TV Shows'))
 xbmcplugin.endOfDirectory(handle,cacheToDisc=False)
