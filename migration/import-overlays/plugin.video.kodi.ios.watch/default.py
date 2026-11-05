"""Kodi renders this real directory UI; no mock screen or engine is generated."""
import os,sys
from urllib.parse import parse_qs
# reuselanguageinvoker: this file runs again in the same interpreter for every listing; the path goes in once.
LIB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib')
if LIB not in sys.path:sys.path.insert(0,LIB)
from ios_watch_routes import choices

def run(argv):
 if argv[2].startswith('?action=cached&key='):
  # Hub rows and heroes from their last TMDb Helper result (ios_cache.py): read a file and list it, nothing else.
  import xbmc,xbmcgui,xbmcplugin,xbmcvfs
  key=argv[2].split('&key=',1)[1]
  try:
   import ios_cache
   ios_cache.serve(int(argv[1]),key,xbmc,xbmcgui,xbmcplugin,ios_cache.Store(xbmcvfs.translatePath(ios_cache.FOLDER)).read)
  except Exception:
   # Whatever failed, the row must not stay empty: its flag goes off and Kodi loads the TMDb Helper path.
   if key.replace('.','').isalnum():xbmc.executebuiltin('Skin.Reset(PortraitCache.%s)'%key)
   xbmcplugin.endOfDirectory(int(argv[1]),succeeded=False)
  return
 import xbmc,xbmcaddon,xbmcgui,xbmcplugin
 handle=int(argv[1]);params={k:v[0] for k,v in parse_qs(argv[2].lstrip('?')).items()}
 if params.get('action')=='library_refresh':
  from ios_library import refresh_current,current_params,BOOT,STATE
  if params.get('all')=='1':
   import xbmcvfs
   boot=xbmcvfs.translatePath(BOOT)
   if boot not in sys.path:sys.path.append(boot)
   import driveupload
   driveupload.invalidate_library(xbmcvfs.translatePath(STATE))
   if current_params(xbmc.getInfoLabel('Container.FolderPath')) is None:
    xbmcgui.Dialog().notification('Library','Library will be refreshed when opened',xbmcgui.NOTIFICATION_INFO,3000)
  refresh_current(xbmc.getInfoLabel,xbmc.executebuiltin);return
 if not params or set(params)=={'content_type'}:
  # Kodi's parent (..) item leads here. It is navigation, not a movie to resolve.
  from ios_library import root_directory
  root_directory(handle);return
 if params.get('action')=='library':
  from ios_library import directory;directory(handle,params);return
 if params.get('action')=='library_play':
  from ios_library import play_downloaded;play_downloaded(handle,params);return
 if params.get('action')=='continue':
  from ios_continue import directory;directory(handle,params.get('type','all'));return
 if params.get('action')=='choose_source':
  # Long press › Choose source on Continue Watching: forget last time's pick, then ask for the source of THIS title.
  import xbmcvfs
  from ios_continue import forget_choice
  def read(path):
   f=xbmcvfs.File(path)
   try:return f.read()
   finally:f.close()
  def write(path,text):
   f=xbmcvfs.File(path,'w')
   try:f.write(text)
   finally:f.close()
  from ios_continue import entry_for,choose_url
  key=params.get('key','');entry=entry_for(read,key)
  forget_choice(read,write,key)
  if not entry:xbmcgui.Dialog().notification('Choose source','This title is no longer in Continue Watching');return
  # Owner bug: a simulated tap on the focused control hit whatever had focus after the menu closed and Kodi's resume
  # question led back to the saved pick. Now: our own resume question, then the source menu for THIS title.
  position=int(entry.get('position') or 0);start=0
  if position>=30:
   pick=xbmcgui.Dialog().select('Choose source',['Resume from %d:%02d:%02d'%(position//3600,position%3600//60,position%60),'Play from beginning'])
   if pick<0:return
   start=position if pick==0 else 0
  xbmc.executebuiltin('PlayMedia(%s)'%choose_url(entry))
  if start:
   player=xbmc.Player();monitor=xbmc.Monitor()
   for _ in range(240):  # up to 2 minutes for the source page and buffering
    if monitor.waitForAbort(0.5):return
    if player.isPlayingVideo() and player.getTotalTime()>0:
     player.seekTime(start);break
  return
 if params.get('action')=='engine_status':
  xbmcgui.Dialog().ok('Elementum not available','Elementum is not installed or is switched off in this build. Check Add-ons > Video add-ons > Elementum.')
  xbmcplugin.endOfDirectory(handle,succeeded=False);return
 try:
  enabled=xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)')
  ready=enabled and xbmcaddon.Addon().getSettingBool('offer_elementum')
  entries=choices(params,ready)
 except (ValueError,RuntimeError):
  xbmcgui.Dialog().ok('Watch options','The media route is incomplete; use normal item information/episode navigation and record this failure.')
  xbmcplugin.endOfDirectory(handle,succeeded=False);return
 for entry in entries:
  li=xbmcgui.ListItem(label=entry['label']);li.setArt({k:params[k] for k in ['poster','fanart','thumb'] if params.get(k)})
  li.setInfo('video',{'title':params.get('title',''),'mediatype':params.get('kind','')})
  if not entry['folder']:li.setProperty('IsPlayable','true')
  xbmcplugin.addDirectoryItem(handle,entry['url'],li,isFolder=entry['folder'])
 xbmcplugin.setPluginCategory(handle,'Watch options');xbmcplugin.endOfDirectory(handle)
if __name__=='__main__':run(sys.argv)
