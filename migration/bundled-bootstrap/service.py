import json,os,sys,time,threading
_IMPORT_STARTED=time.monotonic()
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
try:   # first thing: every add-on builds its SSL contexts later, and the phone's default has no CA roots (tls_roots.py: Crew's streamers failed TLS, build 623)
 import tls_roots;_TLS_ROOTS=tls_roots.apply()
except Exception:_TLS_ROOTS=''
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
# Request the navigation UI before importing the setup/generator/provider stack. Recovery runs beside the existing
# service and must not create a second owner. Every controller/action still has one implementation.
_EARLY_UI_STARTED=False
if __name__=='__main__' and not (len(sys.argv)>1 and sys.argv[1]=='--recover'):
 import xbmc,xbmcvfs
 if xbmc.getCondVisibility('System.Platform.IOS'):
  import native_ui
  threading.Thread(target=native_ui.run,args=(xbmc,xbmcvfs,xbmc.Monitor()),daemon=True).start()
  _EARLY_UI_STARTED=True
_PARTS=[('start',time.monotonic())]   # build 623 log f5848994: imports took 2.06 s on the phone (0.08 s on a computer) and a Sports tap in that time waited for them; this says which line
from bootstrap import initialize,restore,ensure_enabled,install_players,elementum_defaults,elementum_upload_cap,install_payload,umbrella_defaults,media_folders,elementum_library,umbrella_streaming_only,phone_housekeeping
_PARTS.append(('bootstrap',time.monotonic()))
from navigation import upgrade,sync_skin_preferences,update_nodes,phone_defaults,REVISION
_PARTS.append(('navigation',time.monotonic()))
from startup import generate,failure,LOCK,FUSE
_PARTS.append(('startup',time.monotonic()))
import airplay,notices,updates,threading,diagnostics,transfer_control
_PARTS.append(('airplay..transfer_control',time.monotonic()))
class _Late:
 """A module imported on first use (performance 1E.4: 1.74 s of imports before the service ran; portrait.py alone is
 147 KB). Each of these is first used in a worker thread or well after start-up, so the import leaves the main path."""
 def __init__(self,name):self._name=name;self._module=None
 def __getattr__(self,attribute):
  if self._module is None:
   import importlib;self._module=importlib.import_module(self._name)
  return getattr(self._module,attribute)
signin_server,background,calibration,driveupload,portrait,umbrella_ready=[_Late(n) for n in ('signin_server','background','calibration','driveupload','portrait','umbrella_ready')]
_IMPORT_SECONDS=time.monotonic()-_IMPORT_STARTED

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 begun=time.monotonic()
 xbmc.log('Kodi iOS startup: TLS roots %s'%('set from certifi for every add-on' if _TLS_ROOTS else 'left as they were (SSL_CERT_FILE %s)'%('is a file' if os.path.isfile(os.environ.get('SSL_CERT_FILE','')) else 'is not set; certifi not found')),xbmc.LOGINFO)
 xbmc.log('Kodi iOS startup: bootstrap entered (imports %.3fs: %s)'%(_IMPORT_SECONDS,', '.join('%s %.2f'%(b[0],b[1]-a[1]) for a,b in zip(_PARTS,_PARTS[1:]))),xbmc.LOGINFO)
 monitor=xbmc.Monitor()
 root=Path(__file__).resolve().parent;profile=Path(xbmcvfs.translatePath('special://profile/')).resolve()
 diagnostics.configure(root,profile)
 diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'startup','installed_build',
  kodi=xbmc.getInfoLabel('System.BuildVersion'),os=xbmc.getInfoLabel('System.OSVersion'),python=sys.version.split()[0])
 window=xbmcgui.Window(10000);state={'stage':'prepare'};generated=False
 # ESPN's games, scores and times are fetched here and kept on the phone, so every Sports page opens on a current answer without asking ESPN itself
 # (owner, build 619: "it should always know what is live and upcoming ... load instantly ... never need to refresh"). Faster while Sports is in use.
 def sports_data_loop():
  import sports_provider,cache_tune
  home=xbmcgui.Window(10000)
  # Build 623 (owner: the Sports hub must be instant after a force-quit): this thread starts first thing, loads the hub's modules so the first page open
  # finds them ready, and asks ESPN at once (build 622 waited 0.5 s, and the thread itself only started at the end of set-up).
  try:
   import sports,sports_upcoming,sports_live,sports_leagues,sports_rows,sports_filter,sports_hybrid,sports_espn
  except Exception:pass
  said=[False,False]
  while True:
   live=False
   try:
    if xbmc.Player().isPlayingVideo():raise RuntimeError('video playing')
    provider=sports_provider.real()
    began=time.time();provider.refresh(block=True)
    live=bool(provider.live_games())
    if not said[1]:   # build 620 log had no sign of this loop: say once that it saved an answer, and how long ESPN took
     said[1]=True;xbmc.log('Kodi iOS Sports: background refresh: ESPN saved in %.1f s (%d live)'%(time.time()-began,len(provider.live_games())),xbmc.LOGINFO)
   except Exception as error:
    if not said[0]:said[0]=True;xbmc.log('Kodi iOS Sports: background refresh: %s'%type(error).__name__,xbmc.LOGINFO)
   try:idle=time.time()-float(home.getProperty('KodiIOS.SportsSeen') or 0)
   except ValueError:idle=1e9
   wait=(10 if live else 30) if idle<900 else 60 if idle<6*3600 else 300
   try:
    if cache_tune.link_kind()=='cellular':wait*=3   # cellular: a third of the requests
    if xbmc.Player().isPlayingVideo():wait=max(wait,60)   # never competes with a video for the connection
   except Exception:pass
   if monitor.waitForAbort(wait):return
 threading.Thread(target=sports_data_loop,daemon=True).start()
 def dns_override_loop():
  # Build 634 log 89646295: the phone's DNS gives Crew's embedsports host addresses that fail TLS, DNS over HTTPS gives one that works (dns_override.py)
  import dns_override,sports_crew_patch
  log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO)
  try:sports_crew_patch.ensure(lambda text:log('Sports: '+text))   # Crew's module gets the lookup wrapper before the first game, not at it
  except Exception:pass
  file=dns_override.path()
  if file:dns_override.watch(file,monitor.waitForAbort,log)
 threading.Thread(target=dns_override_loop,daemon=True).start()
 def continue_guard_loop():
  # Build 634 log 4b37fc5b: Continue's remembered Umbrella link did not open (30 s, then "could not open file") and the person was left with nothing: when the
  # link has not put a picture up in 25 s, or Kodi shows its failure box, play the title the normal way (continue_guard.py)
  import continue_guard
  home=xbmcgui.Window(10000);player=xbmc.Player()
  box=lambda:xbmc.getCondVisibility('Window.IsActive(yesnodialog) | Window.IsActive(okdialog)')
  def close_boxes():
   for name in ('yesnodialog','okdialog'):xbmc.executebuiltin('Dialog.Close(%s,true)'%name)
  playing=lambda:bool(player.isPlayingVideo()) and xbmc.getCondVisibility('Player.HasVideo') and player.getTime()>0.5
  circle=continue_guard.Circle(home,playing,box,lambda:xbmc.getCondVisibility('Window.IsVisible(busydialognocancel)'),
   lambda:xbmc.executebuiltin('ActivateWindow(busydialognocancel)'),lambda:xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)'),lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
  continue_guard.watch(home,playing,box,
   lambda:player.stop(),close_boxes,lambda url:xbmc.executebuiltin('PlayMedia(%s)'%url),lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO),monitor.waitForAbort,
   opened=lambda:bool(xbmc.getCondVisibility('Player.HasVideo')),circle=circle,probe=continue_guard.Probe(__import__('link_warm').link_answers))
 threading.Thread(target=continue_guard_loop,daemon=True).start()
 def link_warm_loop():
  # Owner, 2026-11-23, log d78de521 (Wi-Fi): reading 1.3 MB of a link did nothing (the first Continue took 24.4 s to a picture); the kept opening (resume_cache)
  # made the next two 6.6 s and 7.2 s. So the first 3 Continue Watching titles get their opening kept (resume_cache.capture), on Wi-Fi, only while nothing plays
  # and the person has not touched the screen for 6 s, two blocks at a time (link_warm.watch picks the titles).
  import link_warm,importlib.util,xbmcaddon,resume_cache,remote_media,cache_tune
  lib=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path'))+'/resources/lib/ios_continue.py'
  spec=importlib.util.spec_from_file_location('ios_continue',lib);ios_continue=importlib.util.module_from_spec(spec);spec.loader.exec_module(ios_continue)
  def read(location):
   source=xbmcvfs.File(location)
   try:return source.read()
   finally:source.close()
  home=xbmcgui.Window(10000);log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO)
  busy=lambda:bool(xbmc.getCondVisibility('Player.HasVideo') or home.getProperty('KodiIOS.ContinueOpening'))
  def keep(url,size,fraction=None,seconds=None):
   began=home.getProperty('KodiIOS.OpenWanted')
   return resume_cache.capture(url,fraction,lambda link:remote_media.Foreground(link),log=log,stop=lambda:busy() or home.getProperty('KodiIOS.OpenWanted')!=began,
                               idle=lambda:xbmc.getGlobalIdleTime()>=resume_cache.IDLE_SECONDS,seconds=seconds)
  link_warm.watch(lambda:ios_continue.entries(ios_continue.load(read),'all'),busy,monitor.waitForAbort,log,warm_it=keep,
   allowed=lambda:cache_tune.link_kind()=='wifi')
 threading.Thread(target=link_warm_loop,daemon=True).start()
 def thumb_strip_loop():
  # Owner, 2026-11-23: the seek bar's card shows the real frame near the finger. The first Continue Watching titles get their preview strip made in the background
  # (thumb_strip.py; the AirPlay framework's kodi_thumbs_make), on Wi-Fi, only while nothing plays or opens.
  import thumb_strip,airplay,importlib.util,xbmcaddon,cache_tune
  lib_py=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path'))+'/resources/lib/ios_continue.py'
  spec=importlib.util.spec_from_file_location('ios_continue',lib_py);ios_continue=importlib.util.module_from_spec(spec);spec.loader.exec_module(ios_continue)
  def read(location):
   source=xbmcvfs.File(location)
   try:return source.read()
   finally:source.close()
  home=xbmcgui.Window(10000);log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO)
  busy=lambda:bool(xbmc.getCondVisibility('Player.HasVideo') or home.getProperty('KodiIOS.ContinueOpening') or home.getProperty('KodiIOS.OpenWanted') and time.time()-float(home.getProperty('KodiIOS.OpenWanted') or 0)<30)
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'));root=thumb_strip.root_folder();said=[]
  def make_it(link):
   lib=airplay.cached_load(path)
   if not thumb_strip.available(lib):
    if not said:said.append(1);log('preview strip: this AirPlay framework cannot make them yet')
    return
   thumb_strip.make(lib,link,root,log,stop=lambda:busy() or cache_tune.link_kind()!='wifi')   # a build that began on Wi-Fi ends when the phone leaves it (build 679 log: 25 MB on mobile data)
  thumb_strip.watch(lambda:ios_continue.entries(ios_continue.load(read),'all'),busy,monitor.waitForAbort,log,make_it,root,
   allowed=lambda:cache_tune.link_kind()=='wifi')
 threading.Thread(target=thumb_strip_loop,daemon=True).start()
 def ends_at_loop():
  # The video controls' "Ends at" under the finger (ends_at.py): Kodi's own end time ignores a drag until it lands.
  import ends_at,json
  home=xbmcgui.Window(10000);player=xbmc.Player()
  def tempo():
   try:
    answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Player.GetProperties','params':{'playerid':1,'properties':['tempo']}})))
    return float(answer['result']['tempo'])
   except Exception:return 1.0
  ends_at.run(lambda:player.isPlayingVideo(),lambda:xbmc.getCondVisibility('Player.Seeking'),lambda:xbmc.getInfoLabel('Player.SeekTime'),
   lambda:player.getTotalTime(),tempo,lambda:xbmc.getRegion('time'),lambda text:home.setProperty(ends_at.PROPERTY,text),monitor.waitForAbort)
 threading.Thread(target=ends_at_loop,daemon=True).start()
 keys={'changed':False}   # roadmap 3.6: Kodi reads the keymaps at launch; they are reloaded only when a file changed
 # Settings shows it beside Kodi's version: "Kodi 21.3 (build 157)" (owner request).
 window.setProperty('KodiIOS.Build',updates.installed_build(root))
 window.setProperty('KodiIOS.ServiceStart',str(time.time()))   # library plays in the first seconds wait for the Drive proxy (ios_library.live_proxy_port)
 # Settings › AI Upscale's row: "On · 4K" or "Off" (the page updates it after each change).
 try:
  import picture,upscale_page,upscale_queue
  window.setProperty('KodiIOS.UpscaleSummary',upscale_page.summary(picture.load(profile),upscale_queue.load(profile).get('engine')))
 except Exception:pass
 def diagnostic_settings():
  addon=xbmcaddon.Addon()
  return {key:addon.getSettingBool(key) for key in ('background_transfers','drive_upload','prepare_downloads','airplay_button')}
 threading.Thread(target=diagnostics.watch,args=(profile,lambda message:xbmc.log(message,xbmc.LOGINFO),monitor.waitForAbort),
  kwargs={'settings':diagnostic_settings},daemon=True).start()
 # A hint whether a VPN carries the phone's traffic (vpn_hint.py), logged whenever it changes, for the torrent popup and for comparing logs: names only, no addresses.
 def vpn_look_loop():
  import cache_tune,vpn_hint
  last=None
  while not monitor.waitForAbort(3):
   try:
    found=vpn_hint.current(cache_tune.local_address,cache_tune.interfaces)
    key=(found['state'],found['route'],tuple(found['tunnels']))
    if key!=last:
     last=key;xbmc.log('Kodi iOS '+vpn_hint.line(found),xbmc.LOGINFO)
    window.setProperty('KodiIOS.VPNLook',found['state'])
   except Exception as error:xbmc.log('Kodi iOS vpn check: %s'%type(error).__name__,xbmc.LOGWARNING)
 threading.Thread(target=vpn_look_loop,daemon=True).start()
 def stage(value):
  state['stage']=value
  xbmc.log('Kodi iOS startup: %s +%.3fs'%(value,time.monotonic()-begun),xbmc.LOGINFO)
 def api(method,params):return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 def invoke(command):xbmc.executebuiltin(command,True)
 # r11: portrait rows follow the owner's widgets, Continue Watching follows playback, the glass tab bar. Started now:
 # the tab bar and the rest no longer wait for setup (build-132: ~4 s of setup, then the ~3 s refresh, before the tab
 # bar showed); only the portrait refresh waits for setup_done, set once setup and its reload are over.
 setup_done=threading.Event()
 # Not for the gear menu's Recover (recover.py runs this with --recover next to the running service).
 if not (len(sys.argv)>1 and sys.argv[1]=='--recover'):
  import episode_watch_runtime
  threading.Thread(target=episode_watch_runtime.run,args=(monitor,profile,setup_done.is_set),daemon=True).start()
  # The show page's bell (anticipated.py): shows only for a show with an episode still to come.
  import anticipated,source_match,xbmcgui
  threading.Thread(target=anticipated.bell_service,args=(monitor,profile,xbmcgui.Window(10000),xbmc.getInfoLabel,source_match.tmdb_key),daemon=True).start()
  portrait_thread=threading.Thread(target=portrait.run_service,args=(xbmc,xbmcvfs,monitor,profile,invoke),kwargs={'ready':setup_done,'native_ui_started':_EARLY_UI_STARTED},daemon=True);portrait_thread.start()
 # Owner build-136 log: the tab bar answered ~8 s after launch, 2 s of it this fixed wait. Only setup waits now.
 if monitor.waitForAbort(2):return
 def prepare_generated(sync=True):
  nonlocal generated
  stage('skin_preferences')
  if sync:sync_skin_preferences(root/'seed',api,invoke,lambda id,is_bool:xbmc.getCondVisibility('Skin.HasSetting('+id+')') if is_bool else xbmc.getInfoLabel('Skin.String('+id+')'))
  # Before generation, so the rebuilt menus include Drive/recovery in the gear menu.
  stage('phone_menus');update_nodes(profile);phone_defaults(lambda id:xbmc.getInfoLabel('Skin.String('+id+')'),invoke)
  skin=Path(xbmcvfs.translatePath('special://skin/')).resolve()
  if skin.name!=FUSE or not skin.is_relative_to(home):raise RuntimeError('Writable Fuse path not selected')
  generate(skin,xbmc.getSkinDir,invoke,monitor.waitForAbort,xbmc.getInfoLabel('Skin.String(SkinVariables.SkinUser)'),stage)
  generated=True
 try:
  if len(sys.argv)>1 and sys.argv[1]=='--recover':
   if xbmcgui.Dialog().yesno('Recover Kodi setup','Restore pre-setup files and return to Estuary?'):restore(profile,api)
   return
  # The patched Home onloads honor this lock before Settings changes the skin.
  window.setProperty(LOCK,'true')
  def verify_skin():
   stage('await_skin_confirmation');start=time.monotonic()
   while time.monotonic()-start<30:
    if monitor.waitForAbort(0.25):return False
    if time.monotonic()-start>3 and xbmc.getSkinDir()==FUSE and not xbmc.getCondVisibility('Window.IsVisible(yesnodialog)'):
     prepare_generated();return True
   return False
  def refresh(paths):
   invoke('UpdateLocalAddons')
   for expected in paths:
    actual=Path(xbmcvfs.translatePath(xbmcaddon.Addon(expected.name).getAddonInfo('path'))).resolve()
    if actual!=expected.resolve():raise RuntimeError('Kodi did not select the writable skin copy')
  home=Path(xbmcvfs.translatePath('special://home/')).resolve()
  if not profile.is_relative_to(home):raise RuntimeError('Profile is outside the app home')
  stage('navigation');navigation=upgrade(home,profile)
  keys['changed']|=bool(navigation.get('keymap_changed'))
  # Load the guarded XML before a legacy completed profile runs its helpers again.
  if navigation.get('changed_files') and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  stage('initialize')
  result=initialize(root/'seed',profile,api,verify_skin=verify_skin,home=home,refresh=refresh)
  keys['changed']|=bool(upgrade(home,profile).get('keymap_changed'))
  stage('enable_addons')
  for addon in ensure_enabled(root/'seed',profile,api):xbmc.log('Kodi iOS setup enabled bundled add-on '+addon,xbmc.LOGINFO)
  # e.g. Umbrella, once installed, appears in "How would you like to watch?" through its TMDb Helper player.
  for name in install_players(root,profile,lambda addon:xbmc.getCondVisibility('System.HasAddon('+addon+')')):xbmc.log('Kodi iOS setup added TMDb Helper player '+name,xbmc.LOGINFO)
  # CocoScrapers goes into the writable add-ons folder, where Umbrella looks for its scraper module.
  try:
   copied=install_payload(root,home)
   if copied:
    invoke('UpdateLocalAddons');monitor.waitForAbort(2)
    for addon in copied:api('Addons.SetAddonEnabled',{'addonid':addon,'enabled':True});xbmc.log('Kodi iOS setup installed '+addon,xbmc.LOGINFO)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)'):
    # Umbrella's sources open on the Deck's "Choose a version" page (again after each Umbrella update).
    import umbrella_picker,umbrella_recovery
    # (Not "window": that name is the Home window, used again when setup finishes.)
    source_window=Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path')))/'resources/lib/windows/source_results.py'
    if umbrella_picker.umbrella_hook(str(source_window)):xbmc.log('Kodi iOS setup added the Deck source page to Umbrella',xbmc.LOGINFO)
    elif source_window.is_file() and umbrella_picker.HOOK_MARK not in source_window.read_text(encoding='utf-8',errors='replace'):
     xbmc.log('Kodi iOS setup: this Umbrella version has a different source window; its own list stays',xbmc.LOGWARNING)
    import provider_fallback_hooks   # the backup providers (PR #32) hook Umbrella's sources module, whichever source window it has
    provider_fallback_hooks.install(str(source_window.parent.parent/'modules/sources.py'))
    resolver=source_window.parents[1]/'debrid/alldebrid.py'
    if umbrella_recovery.hook(resolver):xbmc.log('Kodi iOS setup added selected-stream link recovery to Umbrella AllDebrid',xbmc.LOGINFO)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)') and xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)'):
    umbrella=xbmcaddon.Addon('plugin.video.umbrella')
    if umbrella_defaults(umbrella.getSetting,umbrella.setSetting):xbmc.log('Kodi iOS setup set Umbrella to CocoScrapers',xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS scraper setup skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
  if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)'):
   try:
    engine=xbmcaddon.Addon('plugin.video.elementum')
    folder=elementum_defaults(updates.updates_folder(home).with_name('Elementum Downloads'),engine.getSetting,engine.setSetting)
    if folder:xbmc.log('Kodi iOS setup set Elementum downloads to '+folder,xbmc.LOGINFO)
    if elementum_upload_cap(engine.getSetting,engine.setSetting):xbmc.log('Kodi iOS setup capped Elementum torrent upload at 1 MB/s',xbmc.LOGINFO)
   except Exception as error:xbmc.log('Kodi iOS Elementum defaults skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
  try:
   if xbmc.getCondVisibility('System.HasAddon(script.elementum.burst)'):
    import bootstrap
    burst=xbmcaddon.Addon('script.elementum.burst')
    off=bootstrap.burst_providers(profile/'addon_data/service.kodi.ios.bootstrap/burst-providers-r1',burst.getSetting,burst.setSetting)
    if off:xbmc.log('Kodi iOS setup turned off search providers that never answer: '+', '.join(off),xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS Burst providers skipped: '+type(error).__name__,xbmc.LOGWARNING)
  # Board 07: the long-press menu without TMDb Helper's extra entries (owner, 2026-11-12).
  try:
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.themoviedb.helper)'):
    import bootstrap
    helper=xbmcaddon.Addon('plugin.video.themoviedb.helper')
    off=bootstrap.tmdbhelper_context(profile/'addon_data/service.kodi.ios.bootstrap/tmdb-context-r1',helper.getSetting,helper.setSetting)
    if off:xbmc.log('Kodi iOS setup removed TMDb Helper long-press entries: '+', '.join(off),xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS TMDb Helper menu skipped: '+type(error).__name__,xbmc.LOGWARNING)
  # Once per phone: folders the Deck config expects, phone-useless network discovery off (ISSUE-070).
  try:
   engine=xbmcaddon.Addon('plugin.video.elementum') if xbmc.getCondVisibility('System.HasAddon(plugin.video.elementum)') else None
   done=phone_housekeeping(profile,(engine.getSetting,engine.setSetting) if engine else None,api)
   if done:xbmc.log('Kodi iOS setup housekeeping: '+', '.join(done),xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS housekeeping skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
  # Elementum videos you choose to keep land in Files › On My iPhone › Kodi › Kodi Downloads › Movies / TV Shows.
  # Umbrella only streams.
  try:
   folders=media_folders(updates.updates_folder(home).with_name('Kodi Downloads'))
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.elementum)'):
    engine=xbmcaddon.Addon('plugin.video.elementum')
    if elementum_library(folders,engine.getSetting,engine.setSetting):xbmc.log('Kodi iOS setup filed Elementum downloads into Movies and TV Shows',xbmc.LOGINFO)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)'):
    umbrella=xbmcaddon.Addon('plugin.video.umbrella')
    if umbrella_streaming_only(folders,umbrella.getSetting,umbrella.setSetting):xbmc.log('Kodi iOS setup set Umbrella back to streaming only',xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS download folders skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
  if result=='IN PROGRESS':
   restore(profile,api);xbmcgui.Dialog().ok('Setup interrupted','Original files restored. Estuary remains available. Record this failure before retrying.')
  elif not generated and xbmc.getSkinDir()==FUSE:
   # One repair per revision on old COMPLETE profiles; preserve owner preferences.
   ready=profile/'addon_data/service.kodi.ios.bootstrap/startup-ready.json'
   previous=json.loads(ready.read_text()) if ready.exists() else {}
   if previous.get('revision')!=REVISION or navigation.get('changed_files'):prepare_generated(sync=False)
  if generated:
   ready=profile/'addon_data/service.kodi.ios.bootstrap/startup-ready.json'
   ready.parent.mkdir(parents=True,exist_ok=True);ready.write_text(json.dumps({'revision':REVISION,'host_contract_only':True,'device_verified':False})+'\n')
  stage('complete')
 except Exception as error:
  diagnostics.log_exception(xbmc,'startup',error,stage=state['stage'])
  receipt=failure(error,state['stage']);dest=profile/'addon_data/service.kodi.ios.bootstrap/startup-error.json'
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(receipt,indent=2)+'\n')
  xbmc.log('Kodi iOS setup failed: '+json.dumps(receipt),xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Kodi setup needs review','Automatic setup failed at '+state['stage']+'. Settings and Recovery remain available. Report startup-error.json; do not share credentials.')
 finally:
  window.clearProperty(LOCK)
  if keys['changed'] or generated or '--recover' in sys.argv:invoke('Action(reloadkeymaps)')
  else:xbmc.log('Kodi iOS startup: keymaps unchanged, not reloaded',xbmc.LOGINFO)
  # Exactly one reload after verified generation, never during Keep Skin confirmation.
  if generated and state['stage']=='complete' and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  setup_done.set()
  # After any reload has settled: the one-time calibration reset, then a quiet check for a newer build. In the
  # background (performance pass): the tab bar, Continue Watching and the rest below used to wait for these ten
  # seconds too (the glass bar appeared ~19 s after launch in the owner's log).
  def later():
   if xbmc.getSkinDir()!=FUSE or monitor.waitForAbort(10):return
   try:calibration.reset_once(profile,lambda command:xbmc.executebuiltin(command),xbmc.getCondVisibility,monitor.waitForAbort)
   except Exception as error:xbmc.log('Kodi iOS calibration reset skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
   try:
    if xbmcaddon.Addon().getSettingBool('check_on_start'):updates.run(check_only=True)
   except Exception as error:xbmc.log('Kodi iOS update check skipped: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
  threading.Thread(target=later,daemon=True).start()
 import slowdown
 playback_lib=airplay.cached_load(airplay.library_path(xbmcvfs.translatePath('special://xbmc/')))
 slowdown.configure(lambda:slowdown.play_reason(airplay.playback_active(playback_lib,xbmcgui.Window(10000),time.time()),xbmc.getCondVisibility('Player.Caching'),xbmc.getCondVisibility('Player.HasVideo'),xbmcgui.Window(10000).getProperty('KodiIOS.Open')))   # ISSUE-309: an opening holds downloads too
 # Build 207: one thread asks Kodi; the downloads only read its answer (slowdown.reason).
 threading.Thread(target=slowdown.watch,args=(monitor.waitForAbort,),kwargs={'log':lambda m:xbmc.log(m,xbmc.LOGINFO)},daemon=True).start()
 # The bell in the hub headers: unread messages and whether a download or Drive upload runs. Each message also gets
 # its part of kodi.log, shown when it is tapped.
 threading.Thread(target=notices.publish,args=(window,profile,monitor.waitForAbort,lambda:xbmc.Player().isPlayingVideo()),
  kwargs={'log_path':os.path.join(xbmcvfs.translatePath('special://logpath/'),'kodi.log')},daemon=True).start()
 # The Transfers page's speed history (transfer_history): what each running job does, every 2 s, for its graph.
 def transfer_rates():
  import transfer_history,debrid_drive,prepare_downloads
  try:torrents=notices.torrent_list()
  except Exception:torrents=[]
  d=debrid_drive.load(profile)
  return transfer_history.activity(torrents,d.get('current'),prepare_downloads.load(profile).get('current'),d.get('lanes'))
 import transfer_history
 threading.Thread(target=transfer_history.watch,args=(profile,transfer_rates,monitor.waitForAbort),daemon=True).start()
 # Roadmap 1A.1: the app's own Drive streaming proxy (Library playback of Drive copies), started once Drive is signed in.
 def drive_proxy_loop():
  import drive_proxy,drivelibrary
  home_window=xbmcgui.Window(10000)
  while not monitor.abortRequested():
   try:
    drive,_=drivelibrary.client()
    if drive:
     def publish(port):
      if port:home_window.setProperty(drive_proxy.PROPERTY,str(port))
      else:home_window.clearProperty(drive_proxy.PROPERTY)
     # Playback cache (owner, 2026-11-20): Drive video blocks on the phone's temporary folder while it plays, filled in the background on Wi-Fi only,
     # wiped the moment playback stops (and at every start, so a crash leaves nothing).
     link=[0.0,'other']
     def wifi_ok():
      if time.time()-link[0]>15:
       try:
        import cache_tune
        link[:]=[time.time(),cache_tune.link_kind()]
       except Exception:link[:]=[time.time(),'other']
      return link[1]!='cellular'
     # owner log f93a3233 (build 657): Play on TV stops Kodi's player, and this wiped the cache and the filler exactly when the converter began reading the
     # same Drive file. cast_cache.Keep keeps them while a TV is being fed and clears them once when it is over.
     import cast_cache
     def casting():
      now=time.time();return airplay.starting(home_window,now) or airplay.busy(home_window,now) or airplay.serve_busy(home_window,now)
     def clear_playback_cache():
      try:drive_proxy.clear_cache()
      except Exception as error:xbmc.log('Kodi iOS Drive cache: clear failed (%s)'%type(error).__name__,xbmc.LOGWARNING)
     keep=cast_cache.Keep(casting,lambda:xbmc.Player().isPlaying(),clear_playback_cache,lambda text:xbmc.log(text,xbmc.LOGINFO))
     class CacheCleaner(xbmc.Monitor):
      def onNotification(self,sender,method,data):
       if method=='Player.OnStop':keep.stopped()
     cleaner=CacheCleaner()   # kept referenced for the life of the service
     def cast_cache_loop():
      while not monitor.waitForAbort(cast_cache.RECHECK):keep.tick()
     threading.Thread(target=cast_cache_loop,daemon=True).start()
     cast_cache.DIAG.log=lambda text:xbmc.log(text,xbmc.LOGINFO);cast_cache.DIAG.state=drive_proxy.filler_state   # one line every 30 s while a TV is fed
     pacing=cast_cache.Pacing(casting,lambda:int(home_window.getProperty(cast_cache.CUSHION_PROPERTY) or 0),lambda text:xbmc.log(text,xbmc.LOGINFO))
     drive_proxy.supervise(lambda port:drive_proxy.start(drive.token,port=port,hold=lambda:airplay.starting(home_window),   # roadmap 1G.3
                                   state_dir=profile/'addon_data/service.kodi.ios.bootstrap',log=lambda text:xbmc.log(text,xbmc.LOGINFO),   # 1A.3
                                   cache_dir=str(Path(xbmcvfs.translatePath('special://temp/'))/'drive-playback-cache'),wifi_ok=wifi_ok,pace=pacing),
                           monitor.waitForAbort,publish,lambda text:xbmc.log(text,xbmc.LOGINFO),
                           nudge=lambda port:home_window.getProperty(drive_proxy.DEAD)==str(port) and (home_window.clearProperty(drive_proxy.DEAD) or True))
     return
   except Exception as error:xbmc.log('Kodi iOS Drive proxy: not started (%s)'%type(error).__name__,xbmc.LOGWARNING)
   if monitor.waitForAbort(60):return
 threading.Thread(target=drive_proxy_loop,daemon=True).start()
 # Sports discovery (DEC-058): the walk of the Loop add-ons' and The Crew's menus lives here, not on the Sports page's own script (ISSUE-356).
 def sports_discovery_loop():
  import sports_loop, sports_loop_routes
  sports_loop_routes.warmup_proxy(monitor.waitForAbort,lambda text:xbmc.log('Kodi iOS Sports: '+text,xbmc.LOGINFO))
  sports_loop.serve(xbmc,xbmcvfs,xbmcgui,monitor.waitForAbort,lambda text:xbmc.log('Kodi iOS Sports '+text,xbmc.LOGINFO))
 threading.Thread(target=sports_discovery_loop,daemon=True).start()
 # Sports reminders (board C of the game page): a notification when a source appears for a game the owner asked about, and 15 minutes before it starts.
 def sports_reminder_loop():
  import sports_provider,sports_reminders
  def notify(title,text,action):
   notices.add(profile,'general',title,text,action=action)
   try:xbmcgui.Dialog().notification(title,text,xbmcgui.NOTIFICATION_INFO,6000)
   except Exception:pass
  sports_reminders.watch(xbmcvfs.translatePath('special://profile/'),sports_provider.get,notify,monitor.waitForAbort,
                         log=lambda text:xbmc.log('Kodi iOS Sports '+text,xbmc.LOGINFO))
 threading.Thread(target=sports_reminder_loop,daemon=True).start()
 # Sources for live games are looked for ahead of time (owner, 2026-11-20), one search at a time, never while a video plays or a game page searches.
 def sports_prefetch_loop():
  import sports_provider,sports_sources_prefetch
  home=xbmcgui.Window(10000)
  launched=time.time()
  def busy():
   # Not while a video plays or a game page searches, and not until the owner has opened Sports this session (build 616: the search began 30 s after
   # launch, on the Home screen, and Crew's busy dialog covered it). Then for 3 hours.
   if xbmc.Player().isPlayingVideo() or home.getProperty('KodiIOS.SportsCrewOnlyLeague'):return True
   # Before Sports has been opened: from 30 s after launch, on Wi-Fi, so the first game's sources are ready when the owner gets there (sports_sources_prefetch.idle_for_search).
   try:
    import cache_tune
    wifi=cache_tune.link_kind()=='wifi'
   except Exception:wifi=False
   if xbmc.getCondVisibility('System.HasModalDialog'):return True   # a dialog (Crew's, a chooser) is up: not now
   if not xbmc.getCondVisibility('System.IdleTime(5)'):return True   # a finger touched the screen in the last 5 s: the pages draw first (owner, 2026-11-22, log 71e31b26: Sports pages took 2-5 s while the search ran back to back)
   try:moving=float(xbmc.getInfoLabel('System.FPS') or 0)>=15   # the screen is animating or being scrolled: the look waits for it to settle
   except ValueError:moving=False
   return moving or sports_sources_prefetch.idle_for_search(home.getProperty('KodiIOS.SportsSeen'),launched,time.time(),wifi)
  def poke():
   if home.getProperty('KodiIOS.SportsPoke'):
    try:opened=time.time()-float(home.getProperty('KodiIOS.SportsSeen') or 0)
    except ValueError:opened=99
    if opened<3:return False   # a Sports page is opening: it draws first (build 634 log: the hub's first frame took 1.6-1.9 s while the source search started with it)
    home.clearProperty('KodiIOS.SportsPoke');return True
   return False
  sports_sources_prefetch.watch(sports_provider.get,busy,monitor.waitForAbort,log=lambda text:xbmc.log('Kodi iOS Sports: '+text,xbmc.LOGINFO),poke=poke,first=sports_sources_prefetch.WARM_AFTER)
 threading.Thread(target=sports_prefetch_loop,daemon=True).start()
 # Safety net: a modal busy dialog nobody lowers is closed after 4 s unless a video is opening or playing (busy_watchdog.py).
 def busy_watchdog_loop():
  import busy_watchdog
  busy_watchdog.watch(lambda name:xbmc.getCondVisibility('Window.IsVisible(%s)'%name),
                      lambda:xbmc.getCondVisibility('Player.HasMedia') or xbmc.getCondVisibility('Player.Caching') or bool(xbmcgui.Window(10000).getProperty('KodiIOS.ContinueOpening')),
                      lambda name:xbmc.executebuiltin('Dialog.Close(%s,true)'%name),monitor.waitForAbort,
                      log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
 threading.Thread(target=busy_watchdog_loop,daemon=True).start()
 # The Loop's background work stays off (owner, 2026-11-20; loop_quiet.py): checked at start and every 15 minutes, in case an update switched it on.
 def loop_quiet_loop():
  import loop_quiet
  def rpc(method,params):
   return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))).get('result') or {}
  if monitor.waitForAbort(2):return   # before the Loop's own service has imported its scrapers (build 616 log: 45 failing imports at launch)
  while True:
   try:loop_quiet.apply(xbmcaddon.Addon().getSettingBool('loop_quiet'),rpc,str(profile/'addon_data/service.kodi.ios.bootstrap/loop-quiet.json'),log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
   except Exception as error:xbmc.log('Kodi iOS loop: check failed (%s)'%type(error).__name__,xbmc.LOGWARNING)
   if monitor.waitForAbort(900):return
 threading.Thread(target=loop_quiet_loop,daemon=True).start()
 # Crew's client lacks the parseDOM name its own downloaded streamers call (build 616 log: "Streamer [generic] failed"): added once at start, for Movies and TV too.
 def crew_alias():
  try:
   import sports_crew_patch
   sports_crew_patch.ensure(lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
  except Exception as error:xbmc.log('Kodi iOS crew: alias check failed (%s)'%type(error).__name__,xbmc.LOGWARNING)
 threading.Thread(target=crew_alias,daemon=True).start()
 # Roadmap 1C.1: "open timing" log line per video (tap to picture).
 import open_timing
 # Owner, 2026-11-20 (a stream took 20 s to open): remember how fast each Umbrella source opened, so the version page lists the fast ones first.
 import source_speed
 _speed=source_speed.open_store()
 def _credit(ok,via):
  if via!='umbrella':return
  done=source_speed.settle(xbmcgui.Window(10000),_speed,ok)
  if done:xbmc.log('Kodi iOS Umbrella source %s: %s'%(done[0],'opened in %.1f s from the choice to the streams being ready'%done[1] if done[1] is not None else 'did not open'),xbmc.LOGINFO)
 open_timing.LISTENERS.append(_credit)
 import cache_tune   # roadmap 1B.3: Kodi's cache read factor follows Wi-Fi / cellular, set as a video is about to open
 threading.Thread(target=open_timing.watch,args=(xbmcgui.Window(10000),lambda:xbmc.getCondVisibility('Player.HasVideo + Player.Playing'),
                  lambda text:xbmc.log(text,xbmc.LOGINFO),monitor.waitForAbort),
                  kwargs={'moving':lambda:xbmc.getCondVisibility('Player.Playing + !Player.Caching') and xbmc.Player().getTime()>0.4,'on_open':lambda:cache_tune.apply(xbmc,str(profile),lambda text:xbmc.log(text,xbmc.LOGINFO)),
                          'probe':lambda:{'media':xbmc.getCondVisibility('Player.HasMedia'),'video':xbmc.getCondVisibility('Player.HasVideo')}},daemon=True).start()
 # DEC-039 V2: each video starts with its own Saturation (Picture menu: this video, its show, or the default).
 def saturation_loop():
  import picture,picture_page
  sync=picture.SaturationSync()
  while not monitor.waitForAbort(2):
   try:
    playing=xbmc.getCondVisibility('Player.HasVideo')
    command=sync.step(playing,picture_page.playing_media(xbmc,xbmcgui.Window(10000)) if playing else {},picture.load(str(profile)) if playing else {})
    if command:xbmc.executebuiltin(command)
   except Exception as error:xbmc.log('Kodi iOS picture: saturation not set (%s)'%type(error).__name__,xbmc.LOGWARNING)
 threading.Thread(target=saturation_loop,daemon=True).start()
 # Check subtitle identity when each video starts, without opening the Subtitles menu.
 import subtitle_match
 threading.Thread(target=subtitle_match.run,args=(xbmc,xbmcgui,monitor),daemon=True).start()
 # Roadmap 3.5: one performance line a minute (list runs, opens, Drive proxy requests and seeks), only when something happened.
 import perf_summary,drive_proxy
 threading.Thread(target=perf_summary.watch,args=(xbmcgui.Window(10000),open_timing.take,
                  lambda:drive_proxy.CURRENT[0].stats.take() if drive_proxy.CURRENT else {},
                  lambda text:xbmc.log(text,xbmc.LOGINFO),monitor.waitForAbort),daemon=True).start()
 # Owner, 2026-11-20 (Sports Upcoming and Favourites flick choppily): the frame rate while a finger is on the screen, per window, one line a minute.
 import scroll_probe
 _probe=scroll_probe.Probe(lambda:xbmc.getInfoLabel('System.FPS'),lambda:not xbmc.getCondVisibility('System.IdleTime(1)'),
                           lambda:scroll_probe.page(xbmcgui.getCurrentWindowId(),xbmcgui.getCurrentWindowDialogId(),xbmc.getInfoLabel),lambda text:xbmc.log(text,xbmc.LOGINFO),
                           lambda:xbmc.getCondVisibility('Player.HasVideo'))
 threading.Thread(target=scroll_probe.watch,args=(_probe,monitor.waitForAbort),daemon=True).start()
 # page_cover: a covering page that died leaves its token behind; with no modal dialog open nothing covers, so the list is cleared (every 2 s).
 def cover_tidy():
  import page_cover
  home=xbmcgui.Window(10000)
  while not monitor.waitForAbort(2):
   try:page_cover.tidy(home,xbmc.getCondVisibility('System.HasActiveModalDialog'))
   except Exception:pass
 threading.Thread(target=cover_tidy,daemon=True).start()
 # Build 193: one status model for every page and the bell (work_state.py), every 2 s, with the reason stored.
 import work_state,slowdown
 # ISSUE-228 (owner: "cancel all upscaling isn't working"): the page's cancel / cancel all / order requests were applied only
 # when the worker next reached an AI Upscale pass, which waits behind every preparation. They are applied within seconds
 # here, except while a copy is being made (that copy sees the request itself and stops).
 def upscale_control():
  import upscale_queue
  while not monitor.waitForAbort(2):
   try:
    if not upscale_queue.RUNNING[0] and upscale_queue.has_pending(profile):
     data=upscale_queue.load(profile)
     if upscale_queue.apply_control(profile,data):upscale_queue.save(profile,data)
   except Exception as error:diagnostics.log_exception(xbmc,'upscale_control',error)
 threading.Thread(target=upscale_control,daemon=True).start()
 def work_inputs():
  import debrid_drive,prepare_downloads,preparation_runtime
  import transfer_speed
  phone=transfer_speed.phone_uploads(profile)
  prep=prepare_downloads.load(profile);flags=work_state.flags(profile)
  import problem_ignore
  need=prepare_downloads.problem_need(prep,problem_ignore.hidden_prep_ids(profile,prep))   # board E3, minus Don't Show Again
  if need:flags=dict(flags,needs=list(flags['needs'])+[need])
  return {'prep':prep,'runtime':preparation_runtime.read(profile),'debrid':debrid_drive.load(profile),
          'phone':phone,'torrents':notices.downloads(),
          'paused':{k:transfer_control.paused(profile,k) for k in transfer_control.KINDS},'slow':slowdown.reason(),
          **flags}
 threading.Thread(target=work_state.publish,args=(profile,work_inputs,monitor.waitForAbort),
                  kwargs={'every':1,'set_property':window.setProperty,'log':lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGWARNING)},daemon=True).start()
 # A torrent whose real name turns out to be another film (owner, build 156: Fall 2022 → Fall.2.Deadpoint.2026) is
 # stopped once Elementum knows its name, and explained in Notifications.
 import source_guard
 threading.Thread(target=source_guard.run,args=(window,notices.torrent_list,driveupload.remove_torrent,
  lambda title,text:notices.add(profile,'problem',title,text),monitor.waitForAbort),daemon=True).start()
 import library_watch
 threading.Thread(target=library_watch.run,args=(xbmc,xbmcaddon,xbmcvfs,monitor,profile),daemon=True).start()
 # Umbrella's getting-ready-to-play screen: its source text, split into the badges the portrait page shows.
 threading.Thread(target=umbrella_ready.watch,args=(lambda:xbmc.getCondVisibility('Window.IsVisible(%s)'%umbrella_ready.WINDOW),
  lambda:xbmc.getInfoLabel('Control.GetLabel(2001)'),window.setProperty,window.clearProperty,monitor.waitForAbort),
  # ISSUE-280 (board S1): the stage line, from the unlocked link (umbrella_recovery) and the stream cache's own counts.
  kwargs={'linked':lambda:window.getProperty('KodiIOS.UmbrellaRenewal'),
          'cache':lambda:__import__('remote_media').stats(window)},daemon=True).start()
 # ISSUE-287: no activity pill. Elementum Burst's error lines in Kodi's (invisible) background box still reach Notifications.
 import background_box
 threading.Thread(target=background_box.watch,args=(lambda:background_box.read_box(xbmc,xbmcgui),
  lambda text:notices.add(profile,'problem','Elementum Burst',text),monitor.waitForAbort),daemon=True).start()
 # ISSUE-267: the add-ons the app patches stay its own copies (a repository update had hidden them; no copy ran).
 try:
  import pinned_addons
  write=lambda text:xbmc.log(text,xbmc.LOGINFO)
  pinned_addons.block_updates(pinned_addons.addons_database(xbmcvfs.translatePath('special://database/')),log=write)
  moved=pinned_addons.restore(xbmcvfs.translatePath('special://home/addons/'),xbmcvfs.translatePath('special://xbmc/addons/'),
                              xbmcvfs.translatePath('special://temp/shadowed-addons/'),log=write)
  if moved:
   xbmc.executebuiltin('UpdateLocalAddons');monitor.waitForAbort(3)
   notices.add(profile,'general','Add-ons put back',"%s had been updated from a repository without the app's fixes; the app's own copies are back. Restart Kodi iOS to finish."%
               ' and '.join({'plugin.googledrive':'Google Drive','script.module.clouddrive.common':'its library',
                             'plugin.video.elementum':'Elementum','script.elementum.burst':'Burst'}.get(a,a) for a,_,_ in moved))
 except Exception as error:diagnostics.log_exception(xbmc,'pinned_addons',error)
 # Kept Elementum videos go to Google Drive in the background, never during playback.
 try:
  if xbmcaddon.Addon().getSettingBool('drive_upload') or xbmcaddon.Addon().getSettingBool('prepare_downloads'):
   threading.Thread(target=keep_copying,args=(monitor,home,profile),daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS Drive upload unavailable: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
 # Downloads and Drive uploads keep going when Kodi leaves the screen (KodiAirPlay r3 plays silence meanwhile).
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=airplay.cached_load(path)
  if lib is not None and hasattr(lib,'kodi_background_keep'):
   kept=str(updates.updates_folder(home).with_name('Kodi Downloads'))
   def why():
    # AirPlay playback has its own lifetime, even when background downloads are switched off.
    if airplay.playback_active(lib,xbmcgui.Window(10000),time.time()):return 'AirPlay'
    if not xbmcaddon.Addon().getSettingBool('background_transfers'):return ''
    if xbmc.Player().isPlayingAudio():return ''  # Kodi's own music keeps it running; the silence would make it mixable
    # Build 188 (owner: "airplay also stops if my screen turns off"): the TV reads the movie from Kodi's own server,
    # so Kodi stays awake while AirPlay plays, even with nothing else to do.
    uploading=xbmcaddon.Addon().getSettingBool('drive_upload') and xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)')
    import prepare_downloads,preparation_runtime,debrid_drive
    if debrid_drive.active(profile):return 'AllDebrid download or Drive transfer'
    preparing=xbmcaddon.Addon().getSettingBool('prepare_downloads') and (preparation_runtime.active() or preparation_runtime.pending(prepare_downloads.load(profile)))
    return ('video preparation' if preparing else background.reason(notices.downloads(),notices.uploads(profile),uploading and background.videos_waiting(kept)))
   threading.Thread(target=background.watch,args=(lib.kodi_background_keep,why,monitor.waitForAbort,lambda m:xbmc.log(m,xbmc.LOGINFO)),kwargs={"status":getattr(lib,"kodi_background_state",lambda:0),"notify":lambda title,text:notices.note("info",title,text)},daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS background transfers unavailable: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
 # r6: the AirPlay stream's requests, CODECS and Apple's player events into kodi.log (owner build-133: sound only).
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=airplay.cached_load(path)
  if lib is not None and hasattr(lib,'kodi_airplay_log'):
   import library_tools,airplay_diagnostics
   def slow_note(lines):
    # E18: a stream too slow for AirPlay says so once, instead of a long silent wait.
    if airplay.slow_source(lines,xbmcgui.Window(10000),time.time()):
     notices.note('problem','AirPlay: this stream is too slow',airplay.SLOW_TEXT)
     xbmcgui.Dialog().notification('AirPlay',airplay.SLOW_TEXT,xbmcgui.NOTIFICATION_WARNING,10000)
   import airplay_recover
   def cast_stuck(position):
    notices.note('problem','AirPlay: the TV is not receiving',airplay_recover.TEXT)
    xbmcgui.Dialog().notification('AirPlay',airplay_recover.TEXT,xbmcgui.NOTIFICATION_WARNING,10000)
   recover=airplay_recover.Recover(lambda position:airplay.restart(lib,xbmcgui.Window(10000),position,log=lambda m:xbmc.log('Kodi iOS '+m,xbmc.LOGINFO)),cast_stuck,lambda m:xbmc.log('Kodi iOS '+m,xbmc.LOGINFO))
   threading.Thread(target=airplay_diagnostics.watch,args=(lib,profile,xbmcgui.Window(10000),lambda m:xbmc.log(m,xbmc.LOGINFO),monitor.waitForAbort),kwargs={'recover':recover},daemon=True).start()
   threading.Thread(target=airplay.relay,args=(lib,lambda m:xbmc.log(m,xbmc.LOGINFO),monitor.waitForAbort),
                    kwargs={'keep':lambda lines:(library_tools.note_airplay(profile,lines),airplay.activity(lines,xbmcgui.Window(10000),time.time()),
                                                  slow_note(lines))},daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS AirPlay log unavailable: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
 # Stays running for the rest of the session: Apple's AirPlay button in the top-right corner during playback.
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if path and xbmcaddon.Addon().getSettingBool('airplay_button'):
   airplay.watch(airplay.cached_load(path),lambda:xbmc.getCondVisibility(airplay.PLAYING),monitor.waitForAbort)
 except Exception as error:xbmc.log('Kodi iOS AirPlay button unavailable: '+type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
 while not monitor.waitForAbort(60):pass

def keep_copying(monitor,home,profile,run=None,wait=None):
 """ISSUE-269 (owner log b98d5fc2, build 421: the copy thread died at start and every download sat at "new" with no word):
 drive_uploads runs under this watchdog. If it stops with an error, one notice says so in plain words ("Downloads
 stopped") and it starts again after a pause (30 s, then up to 10 min), so a crash is never a silent freeze."""
 import xbmc
 try:
  import netwatch;netwatch.start()   # ISSUE-271: Wi-Fi <-> cellular is seen within seconds, not at the next copy run
 except Exception:pass
 run=run or drive_uploads;wait=wait or monitor.waitForAbort
 failures=0
 while True:
  try:
   run(monitor,home,profile);return            # it returns only when Kodi closes (or Drive is not set up)
  except Exception as error:
   failures+=1
   diagnostics.log_exception(xbmc,'drive_uploads',error)
   why=diagnostics.redact(error)[:140] if hasattr(diagnostics,'redact') else type(error).__name__
   notices.add(profile,'problem','Downloads stopped',"The download and upload service stopped (%s). It starts again by itself; if this keeps "
               "coming back, share the log."%why,group='downloads-stopped')
   delay=min(600,30*2**min(failures-1,5))
   # ISSUE-282 (log 6cf2a4c5: "downloads stopped (NameError)" on every start, with no hint which name): the message too.
   xbmc.log('Kodi iOS Drive: downloads stopped (%s: %s); starting again in %d s (try %d)'%(type(error).__name__,diagnostics.redact(str(error))[:200],delay,failures),xbmc.LOGWARNING)
   if wait(delay):return


def drive_uploads(monitor,home,profile):
 """Download → upload → one-file preparation (build 193: slower, never stopped, while a video or AirPlay plays). Startup scan and new uploads share one queue/lock."""
 import urllib.parse,urllib.request,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 # (slowdown.configure is also called in run(); this keeps the same rule here.)
 # Build 186 held the AllDebrid copies, the uploads and the conversion while AirPlay played. Build 193 (owner: "stuff
 # should ALWAYS be moving even if an AirPlay movie is playing, just slower"): nothing waits for playback any more; every
 # worker slows to a share of the line and the CPU (slowdown.py). Only the owner's Pause still holds.
 playback_lib=airplay.cached_load(airplay.library_path(xbmcvfs.translatePath('special://xbmc/')))
 airplay_busy=lambda:airplay.playback_active(playback_lib,xbmcgui.Window(10000),time.time())
 import slowdown
 slowdown.configure(lambda:slowdown.play_reason(airplay_busy(),xbmc.getCondVisibility('Player.Caching'),xbmc.getCondVisibility('Player.HasVideo'),xbmcgui.Window(10000).getProperty('KodiIOS.Open')))   # ISSUE-309
 if not xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)'):return
 # ISSUE-267 / ISSUE-270: the app's patched copy first, whatever Kodi resolved, and nothing left from a moved copy.
 import pinned_addons;pinned_addons.use_clouddrive(xbmcaddon,xbmcvfs)
 from clouddrive.common.account import AccountManager
 try:from clouddrive.common.remote.request import tls_context
 except ImportError:
  # An unpatched clouddrive (a repository update): copies must still run, not stop for good (ISSUE-267).
  xbmc.log('Kodi iOS Drive: clouddrive has no tls_context (not the app\'s patched copy); using a plain one',xbmc.LOGWARNING)
  def tls_context(mode=None):
   import ssl
   try:
    import certifi;return ssl.create_default_context(cafile=certifi.where())
   except Exception:return ssl.create_default_context()
 import remote_media
 drive_addon=xbmcaddon.Addon('plugin.googledrive')
 if signin_server.migrate(drive_addon):xbmc.log('Kodi iOS Drive: sign-in server set to the owner worker',xbmc.LOGINFO)
 accounts=AccountManager(xbmcvfs.translatePath(drive_addon.getAddonInfo('profile')))
 native=None;native_reader=None;native_copier=None
 try:
  import native_http   # airplay is the module imported at the top; importing it here made it local (build-232 crash)
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  native_lib=airplay.load(path) if path else None
  native=native_http.sender(native_lib);native_reader=native_http.opener(native_lib)
  native_copier=native_http.copier(native_lib)
 except Exception as error:xbmc.log('Kodi iOS Drive: system networking unavailable (%s)'%type(error).__name__,xbmc.LOGWARNING)
 xbmc.log('Kodi iOS Drive: uploads use %s'%('system networking' if native else 'Python networking'),xbmc.LOGINFO)
 xbmc.log('Kodi iOS Drive: media reads use %s'%('system networking' if native_reader else 'Python networking'),xbmc.LOGINFO)
 # ISSUE-281: the broker keeps a source Kodi still has open (paused too), so Resume never meets a closed address.
 try:remote_media.start(monitor,xbmcgui.Window(10000),context=tls_context(),open_url=native_reader,
                        playing=lambda:xbmc.Player().getPlayingFile() if xbmc.getCondVisibility('Player.HasVideo') else '')
 except Exception as error:diagnostics.log_exception(xbmc,'media_source_bridge',error)
 # ISSUE-259: read the start and the index of a video playing in Kodi (Wi-Fi only) so a later Play on TV starts sooner.
 if airplay.converts(playback_lib):
  def playing_file():
   try:return xbmc.Player().getPlayingFile() if xbmc.getCondVisibility('Player.HasVideo') else ''
   except Exception:return ''
  import cache_tune
  threading.Thread(target=remote_media.watch,args=(xbmcgui.Window(10000),playing_file,
                   lambda:xbmc.getCondVisibility('Player.Playing + !Player.Caching'),lambda:cache_tune.link_kind()=='wifi',
                   monitor.waitForAbort),kwargs={'log':lambda text:xbmc.log(text,xbmc.LOGINFO)},daemon=True).start()
 send=driveupload.sender(tls_context(),log=lambda message:xbmc.log(message,xbmc.LOGINFO),native=native)
 def refresh(refresh_token):
  server=signin_server.server(drive_addon.getSetting('sign-in-server'))
  body=urllib.parse.urlencode({'provider':'googledrive','refresh_token':refresh_token}).encode()
  status,_,answer=send('POST',server+'/refresh',body,{'Content-Type':'application/x-www-form-urlencoded'})
  if status!=200:raise driveupload.refresh_error(status)
  return json.loads(answer)
 drive=driveupload.Drive(driveupload.token_source(accounts.get_accounts,accounts.save_account,refresh),send)
 drive.copy_piece=native_copier
 root=str(updates.updates_folder(home).with_name('Kodi Downloads'))
 state=str(profile/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json')
 # Downloads through AllDebrid go straight to Drive (debrid_drive): its own loop, so a long copy never holds up the
 # phone-to-Drive uploads or preparation below, and it runs during playback too (network only, no phone storage).
 link_seen=[0.0,'other']
 def wifi_only_hold():
  """E15: True while 'Copy downloads to Google Drive only on Wi-Fi' is on and the phone is on cellular (checked at most
  every 15 s; an unknown link never holds)."""
  try:
   if not xbmcaddon.Addon().getSettingBool('copy_wifi_only'):return False
   import cache_tune
   if time.time()-link_seen[0]>15:link_seen[:]=[time.time(),cache_tune.link_kind()]
   return link_seen[1]=='cellular'
  except Exception:return False
 def debrid_loop():
  import alldebrid,debrid_drive,prepare_downloads,transfer_control
  delay=10
  def remember_shows(jobs):
   try:
    import drivelibrary
    state_dir=str(profile/'addon_data/service.kodi.ios.bootstrap')
    return debrid_drive.remember_shows(profile,jobs,lambda names,tmdb:drivelibrary.remember_show(state_dir,names,tmdb))
   except Exception as error:diagnostics.log_exception(xbmc,'remember_show',error)
  # Roadmap 2.2: copies finished by earlier builds get their show's TMDb id once too.
  if remember_shows(debrid_drive.load(profile).get('jobs') or []):
   driveupload.invalidate_library(str(profile/'addon_data/service.kodi.ios.bootstrap'))
  # Build 224: pauses carried over from earlier builds are lifted once; AirPlay's pause ends with AirPlay.
  try:
   lifted=transfer_control.reset_once(profile)
   if lifted:
    xbmc.log('Kodi iOS transfers: build 224 resumed paused %s'%', '.join(lifted),xbmc.LOGINFO)
    notices.note('info','Downloads resumed','Uploads to Google Drive were paused from an earlier build; they are running again.')
  except Exception as error:xbmc.log('Kodi iOS transfers: pause reset skipped: %s'%diagnostics.error_text(error),xbmc.LOGWARNING)
  quiet=[None]
  elementum_down=[0]
  def nap(seconds):
   # ISSUE-208: a Cancel or Cancel All wakes the copier within a second instead of after its wait (20-300 s).
   end=time.time()+seconds
   while time.time()<end:
    if monitor.waitForAbort(min(1,max(0.1,end-time.time()))):return True
    try:
     if transfer_control.cancelled_copies(profile):return False
    except Exception:pass
   return False
  while not nap(delay):
   delay=20
   try:
    lifted=transfer_control.release_airplay(profile,airplay_busy(),quiet_since=quiet)
    if lifted:
     xbmc.log('Kodi iOS transfers: AirPlay is over, resumed %s'%', '.join(lifted),xbmc.LOGINFO)
     notices.note('info','Uploads running again','AirPlay is over, so downloads and uploads to Google Drive continue.')
   except Exception as error:xbmc.log('Kodi iOS transfers: AirPlay pause check failed: %s'%diagnostics.error_text(error),xbmc.LOGWARNING)
   try:token=xbmcaddon.Addon('plugin.video.umbrella').getSetting('alldebridtoken')
   except Exception:token=''
   # A version played from the source page keeps downloading onto the phone after playback (Elementum's keep
   # downloading): once nothing plays, AllDebrid takes it to Drive and Elementum drops it (owner, build 160).
   import work_state
   work_state.need('alldebrid_key',not token and debrid_drive.active(profile))
   work_state.need('uploads_paused',transfer_control.paused(profile,'up') and debrid_drive.active(profile),profile)
   if token and accounts.get_accounts():
    try:
     for tid in debrid_drive.adopt(profile,notices.torrent_list(),xbmc.Player().isPlayingVideo()):
      driveupload.remove_torrent(tid);xbmc.log('Kodi iOS AllDebrid to Drive: took %s from Elementum'%tid,xbmc.LOGINFO)
     elementum_down[0]=0
    except Exception as error:
     # Build 615 log: Elementum's list was asked for every 20 s and failed every time. Ask less and less often while it does not answer
     # (20 s, 40, 80 ... at most 5 minutes) and log the failure once, then every tenth time.
     elementum_down[0]+=1
     delay=min(300,20*2**min(elementum_down[0],4))
     if elementum_down[0]==1 or elementum_down[0]%10==0:
      xbmc.log('Kodi iOS AllDebrid to Drive: Elementum list unavailable (%s), asking again in %d s'%(type(error).__name__,delay),xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
   try:
    def ready_to_watch(item_id):return prepare_downloads.playback_ready(profile,prepare_downloads.metadata(drive,item_id))
    item_id=debrid_drive.next_watch(profile,ready_to_watch,xbmc.Player().isPlayingVideo())
    if item_id:
     import drivelibrary
     found=accounts.get_accounts();account=next(iter(found.values()))
     drives=account.get('drives') or [];driveid=(drives[0].get('id') if drives else None) or account.get('id')
     xbmc.executebuiltin('PlayMedia(%s)'%drivelibrary.play_url(driveid,item_id))
   except Exception as error:xbmc.log('Kodi iOS watch after preparation: %s'%type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
   if not debrid_drive.active(profile) or not accounts.get_accounts():continue
   # E15: Copy only on Wi-Fi (Transfer settings): on cellular the copies wait, the card says so.
   if wifi_only_hold():
    debrid_drive.hold(profile,'wifi');delay=60;continue
   debrid_drive.hold(profile,'')
   try:
    def done(job):
     remember_shows([job])
     try:   # DEC-047 board D: a Better Version saved; the old file goes to Drive's Trash
      import better_version,drivelibrary
      better_version.finished(profile,job,lambda i:drivelibrary.trash(drive,i),lambda ids:prepare_downloads.forget(profile,ids),
                              log=lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO))
     except Exception as error:xbmc.log('Kodi iOS better version: %s'%type(error).__name__,xbmc.LOGWARNING)
     driveupload.invalidate_library(str(profile/'addon_data/service.kodi.ios.bootstrap'))
     prepare_downloads.request_check(profile)   # preparation for Kodi and AirPlay picks it up from Drive
    def ready_copy(with_link,name,size,parent,going,progress,key,quality=''):
     # F1 (PR #24): made ready while it copies, with the preparation queue's converter and Drive stream. None: plain copy.
     try:q=preparation
     except NameError:return None
     if q is None:return None
     addon=xbmcaddon.Addon()
     import debrid_ready,slowdown
     if not addon.getSettingBool('prepare_downloads') or not addon.getSettingBool('prepare_while_copying'):
      debrid_ready.check_quality(q,with_link,key,going,quality)   # ISSUE-236: a plain copy is checked too
      return None
     return debrid_ready.copy(q,profile,with_link,name,size,parent,going,progress,key,
                              log=lambda text:xbmc.log('Kodi iOS AllDebrid: '+diagnostics.redact(text),xbmc.LOGINFO),hold=slowdown.holding,
                              quality=quality)
    delay=debrid_drive.step(profile,alldebrid.AllDebrid(token),drive,lambda kind,title,text,group='':notices.add(profile,kind,title,text,group=group),ready_copy=ready_copy,
                            keep_going=lambda:not monitor.abortRequested() and not transfer_control.paused(profile,'up') and not wifi_only_hold(),on_done=done,
                            cancelled=lambda:transfer_control.cancelled_copies(profile),
                            forget=lambda h:transfer_control.clear_cancelled(profile,h),
                            log=lambda text:xbmc.log('Kodi iOS AllDebrid: '+text,xbmc.LOGWARNING)) or 20
   except alldebrid.Problem as problem:
    diagnostics.log_exception(xbmc,'alldebrid_to_drive',problem)
    notices.add(profile,'problem',"Couldn't download to Google Drive",str(problem));delay=300
   except Exception as error:
    diagnostics.log_exception(xbmc,'alldebrid_to_drive',error);delay=60
 threading.Thread(target=debrid_loop,daemon=True).start()
 # Roadmap 1A.1 (ISSUE-167): measure how long Python threads wait for the interpreter, only while a copy runs.
 def interpreter_wait():
  import interpreter_probe,debrid_drive
  while not monitor.waitForAbort(30):
   try:
    if not debrid_drive.active(profile):continue
    interpreter_probe.run(lambda:monitor.abortRequested() or not debrid_drive.active(profile),
                          lambda median,p95,n:xbmc.log('Kodi iOS interpreter wait: median %.1f ms, p95 %.1f ms (%d samples)'%(median,p95,n),xbmc.LOGINFO))
   except Exception as error:diagnostics.log_exception(xbmc,'interpreter_probe',error)
 threading.Thread(target=interpreter_wait,daemon=True).start()
 # Build 192 (owner: Library › Movies "takes a few seconds"): the page shows the saved Drive lists at once; they are
 # listed again here when older than 5 minutes or marked stale after an upload or a conversion.
 drive_health={'ok':True,'checked':0,'error':''}   # DEC-052 item 4: the health line every Library page shows
 def library_lists():
  import drivelibrary
  state_dir=str(profile/'addon_data/service.kodi.ios.bootstrap')
  while not monitor.waitForAbort(10):
   try:
    if not accounts.get_accounts():continue
    done=drivelibrary.refresh_stale(state_dir)
    if done:log('Library lists refreshed from Google Drive: %s'%', '.join(done))
    if any(slot.startswith('tv:') for slot in done):   # ISSUE-329: Drive problems reach Notifications
     try:
      import library_delete
      library_delete.notify_drive_problems(drivelibrary.load_json(os.path.join(state_dir,'drive-library.json'),{}),
                                           os.path.join(state_dir,'drive-problems-seen.json'),
                                           lambda title,text,action:notices.add(profile,'problem',title,text,action))
     except Exception as error:diagnostics.log_exception(xbmc,'drive_problems',error)
    drive_health.update(ok=True,checked=time.time(),error='')
   except (driveupload.SignedOut,driveupload.RefreshBusy):monitor.waitForAbort(60)   # the uploads loop tells the owner
   except Exception as error:
    # ISSUE-276 (log 8d661d6e: this failed 207 times and every page kept old numbers in silence): the index says so.
    drive_health.update(ok=False,error="Can't reach Google Drive")
    diagnostics.log_exception(xbmc,'library_lists',error)
 threading.Thread(target=library_lists,daemon=True).start()
 # DEC-052 (PR #27): one Library index every screen reads, rebuilt when its inputs change; the counter property makes
 # open pages redraw at once.
 import library_index
 threading.Thread(target=library_index.publish,args=(profile,monitor.waitForAbort),
                  kwargs={'set_property':xbmcgui.Window(10000).setProperty,'drive_health':lambda:dict(drive_health),   # ISSUE-282: not `window` (NameError)
                          'log':lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGWARNING),
                          'note':lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGINFO)},daemon=True).start()
 # Build 193: "idle" only means Kodi is not closing (build-192 log: one busy look made the queue wait 120 s).
 idle=lambda:not monitor.abortRequested()
 log=lambda message:xbmc.log('Kodi iOS '+diagnostics.redact(message),xbmc.LOGINFO)
 import library_scan,prepare_downloads,work_state
 preparation=None
 def preparation_queue():
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if not path:raise RuntimeError('AirPlay preparation framework is missing')
  native=prepare_downloads.Native(airplay.load(path))
  # r25 (owner, build 178): "keep our audio only and original if different": Kodi's audio language (or Kodi's own).
  def setting(name):
   try:return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Settings.GetSettingValue','params':{'setting':name}}))).get('result',{}).get('value','')
   except Exception:return ''
  languages=prepare_downloads.audio_languages(setting('locale.audiolanguage'),setting('locale.language'))
  native.set_audio_languages(languages)
  # Owner (build 180): "only keep english subtitles": the same language for subtitles (and untagged ones).
  native.set_subtitle_languages(languages)
  xbmc.log('Kodi iOS preparation: audio kept: the original track%s; subtitles kept: %s'%(' and '+languages if languages else ' and every other one',languages or 'all'),xbmc.LOGINFO)
  diagnostics.event(log,'preparation','capabilities',streams=native.streams,hdr=native.hdr,outputs=native.outputs,image_subtitles=native.keeps_image_subs,
                    dvd_subtitles=getattr(native,'keeps_dvd_subs',False))
  prepare_downloads.save_capabilities(profile,dvd_subs=getattr(native,'keeps_dvd_subs',False))   # the Library pages read it (P6)
  # KodiAirPlay r14 reads the Drive file through this loopback stream: no downloaded copy on the phone.
  stream=None
  if native.streams:
   import drive_stream
   stream=drive_stream.DriveStream(drive.token,context=tls_context(),open_url=native_reader,refresh_token=drive.token)
   xbmc.log('Kodi iOS preparation: streaming from Google Drive (no downloaded copy)',xbmc.LOGINFO)
  return prepare_downloads.Queue(profile,drive,native,
    download_file=lambda *args:prepare_downloads.download(*args,context=tls_context()),
    notify=lambda kind,title,text:notices.add(profile,kind,title,text),stream=stream,log=log)
 # Start automatically after 5 s; discover new idle work within 20 s without opening Library status.
 delay=5;last_schedule=None
 while not monitor.waitForAbort(delay):
  delay=20
  if not idle():continue
  if not accounts.get_accounts():
   schedule={'reason':'drive_account_missing'}
   if schedule!=last_schedule:
    diagnostics.event(log,'preparation','scheduler',**schedule);last_schedule=schedule
   continue
  # Finished torrents still seeding in Elementum's folder go to Drive too (owner: nothing should stay on the phone).
  seeding=[]
  try:
   torrents=json.loads(urllib.request.urlopen('http://127.0.0.1:65220/torrents/list',timeout=5).read())
   download=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.elementum').getSetting('download_path') or '')
   if download:seeding=driveupload.seeding_pending(download,torrents)
  except Exception:seeding=[]
  waiting=driveupload.pending(root)
  if waiting or seeding:log('Drive: %d phone video%s and %d finished torrent file%s to check'%(len(waiting),'' if len(waiting)==1 else 's',len(seeding),'' if len(seeding)==1 else 's'))
  try:
   state_dir=str(profile/'addon_data/service.kodi.ios.bootstrap')
   with driveupload.transfer_lock(state_dir):
    count=0
    if (waiting or seeding) and xbmcaddon.Addon().getSettingBool('drive_upload'):
     uploading=lambda:idle() and not transfer_control.paused(profile,'up')   # long press › Pause uploads
     count=driveupload.run_once(root,drive,state,log,uploading,xbmcaddon.Addon().getSettingBool('drive_upload_delete'),
                              lambda:driveupload.invalidate_library(state_dir),seeding,driveupload.remove_torrent,
                              remote=lambda:library_scan.remote_files(drive,idle),pace=1,
                              notify=lambda title,text:notices.add(profile,'drive',title,text))
    if xbmcaddon.Addon().getSettingBool('prepare_downloads'):
     if preparation is None:
      preparation=preparation_queue()
      import watch_next
      prepare_downloads.WATCH_NEXT[0]=watch_next.cached(profile)   # F4: next-to-watch episodes are prepared first
      # Build 191 (owner: "If i press refresh in the library status it doesnt do anything"): a check asked for while a
      # movie converts (hours) runs beside it instead of waiting for the movie to finish.
      def check_beside(q):
       seen={'at':time.time(),'bytes':None}
       while not monitor.waitForAbort(5):
        # Build 192 (owner: Fall 2 "stuck on starting / 67%"; the log could not show whether Drive was being read): once a
        # minute while a movie converts, how much was read from Drive, how long since the last read, and the last error.
        try:
         # Build 193 (build-192 log: "103 MB in 187 s" spanned a held and an idle queue): the window starts with each run.
         if not q.busy:seen.update(at=time.time(),bytes=None)
         elif q.stream and time.time()-seen['at']>=60:
          stats=q.stream.stats();got=int(stats.get('read_bytes') or 0);now=time.time()
          if seen['bytes'] is not None:
           since=now-float(stats.get('last_read') or 0) if stats.get('last_read') else -1
           log('preparation: Drive reads: %.1f MB in %.0f s (%.2f MB/s), last read %s ago%s'%((got-seen['bytes'])/1048576.0,now-seen['at'],
               (got-seen['bytes'])/1048576.0/max(1,now-seen['at']),'%.0f s'%since if since>=0 else 'never',
               '; problem: '+str(stats.get('read_error')) if stats.get('read_error') else ''))
          seen.update(at=now,bytes=got)
        except Exception as error:diagnostics.log_exception(xbmc,'library_check',error)
        try:
         if q.busy and prepare_downloads.check_requested(profile) and not getattr(q,'inspection_pending',False):
          q.scan(lambda:not monitor.abortRequested(),force=True,beside=True)
        except driveupload.Stop:pass
        except Exception as error:diagnostics.log_exception(xbmc,'library_check',error)
      threading.Thread(target=check_beside,args=(preparation,),daemon=True).start()
      # F2 (PR #24 roadmap; build-356 log: 27 jobs waited behind one re-package reading Drive at 3-7 MB/s): known
      # re-packages run in up to REPACK_LANES extra lanes while the main lane works. They only move bytes (the picture
      # is copied), so the line, not the phone, is their limit. Never while a video or AirPlay plays (the main lane goes
      # on slowed), never while the owner paused converting, never beside an AI Upscale copy.
      def repack_lane(q,lane):
       while not monitor.waitForAbort(5):
        try:
         if not (q.busy and xbmcaddon.Addon().getSettingBool('prepare_downloads') and not transfer_control.paused(profile,'conv')
                 and not prepare_downloads.interrupts(profile) and not slowdown.reason() and not getattr(q,'upscaling',False)):continue
         go=lambda:(not monitor.abortRequested() and not transfer_control.paused(profile,'conv') and not slowdown.reason()
                    and not prepare_downloads.interrupts(profile))
         while go() and q.process_lane(lane,go):pass
        except driveupload.Stop:pass
        except Exception as error:diagnostics.log_exception(xbmc,'preparation_lane',error)
      for lane in range(2,2+prepare_downloads.REPACK_LANES):
       threading.Thread(target=repack_lane,args=(preparation,str(lane)),daemon=True).start()
     can_prepare=lambda:idle() and xbmcaddon.Addon().getSettingBool('prepare_downloads')
     import preparation_runtime
     # Consume explicit starts before the saved-pause gate, including requests written by older builds.
     preparation.apply_requests()
     schedule=preparation_runtime.schedule(preparation.state,transfer_control.paused(profile,'conv'))
     if schedule!=last_schedule:
      diagnostics.event(log,'preparation','scheduler',**schedule);last_schedule=schedule
     with preparation_runtime.Lease(profile,stats=preparation.stream.stats if preparation.stream else lambda:{}) as runtime:
      preparation.runtime=runtime
      # Build-356 log 7249de4d: three videos already on Drive waited 12.5 min after the app opened for the first check.
      # Owner log (build 368): Refresh's inspection of every video held the converter while jobs waited. Waiting jobs go
      # first; the explicit inspection (its request stays) runs once none is ready to start.
      if not preparation.inspection_deferred():
       preparation.scan(can_prepare,force=bool(count) or not getattr(preparation,'checked_at_start',False))
      elif preparation.marker_time()!=getattr(preparation,'listed_for',None):
       # ISSUE-234: a Refresh lists Drive at once (once per request); its inspection waits for the queue.
       preparation.listed_for=preparation.marker_time()
       preparation.scan(can_prepare,force=True,listing_only=True)
      preparation.checked_at_start=True
      # Build 169 made preparation wait for AllDebrid copies; with copies at 6-8 MB/s (build-169 log) both run at once
      # again, so conversion never sits paused behind an hour-long download.
      # A check no longer stops it (build-170 log: each stop restarted Inception from 0%); it runs when this one ends.
      # Build 193: the owner's Pause makes converting() false too, so the converter reaches its hold loop and says
      # "Paused by you" (it used to stop silently at a full upload queue, with old words on every page).
      converting=lambda:can_prepare() and not prepare_downloads.interrupts(profile) and not transfer_control.paused(profile,'conv')
      # Long press › Pause converting (build 186) holds the conversion where it is, for as long as the owner wants.
      # Closing Kodi, Start converting now / Keep as it is and turning preparation off still stop it.
      # Build 193: only the owner's Pause holds it; a video or AirPlay playing slows it (slowdown.py), never pauses it.
      preparation.paused=lambda:(not monitor.abortRequested() and transfer_control.paused(profile,'conv') and
                                 xbmcaddon.Addon().getSettingBool('prepare_downloads') and not prepare_downloads.interrupts(profile))
      # The upload pieces and the Drive read-ahead wait too while paused by the owner.
      if preparation.stream:preparation.stream.hold=lambda:preparation.paused() or slowdown.preparation_holding()   # build 208 held while Kodi played; now only while it buffers
      # DEC-039 measurement build: an AI Upscale test asked for in Settings runs here, between conversions, with the
      # queue's own converter and Drive stream (one AI engine at a time). Counted only, nothing uploaded.
      import upscale_measure
      measure=upscale_measure.pending(profile)
      if measure:
       upscale_measure.clear(profile)   # once, even if it fails: a crash must not repeat it on every pass
       preparation.busy=True
       try:upscale_measure.run(preparation,measure,log,notify=lambda kind,title,text:notices.add(profile,kind,title,text),keep_going=can_prepare)
       except Exception as error:
        diagnostics.log_exception(xbmc,'upscale_measure',error)
        notices.add(profile,'problem','AI Upscale test stopped',diagnostics.redact(error)[:160])
       finally:preparation.busy=False
      if transfer_control.paused(profile,'conv') and not (prepare_downloads.load(profile).get('current') or {}).get('running'):delay=30
      else:
       preparation.busy=True
       try:
        delay=2 if preparation.process_one(converting) else 20
        # DEC-039/040/042: AI Upscale copies are made only when nothing waits to be converted (one engine at a time).
        # Owner log 20d8a992 (build 360): a failed preparation also returns False, and AI Upscale then ran for 15 min
        # while 23 videos waited. Upscaling starts only when no video waits to be prepared.
        import upscale_cloud
        if delay==20 and not transfer_control.paused(profile,'conv') and (getattr(preparation,'running_slots',None) or upscale_cloud._prep_waiting(preparation)):
         upscale_cloud.hold(profile,'Waits while a video is made ready for Kodi')   # ISSUE-265: the real reason
        if delay==20 and not transfer_control.paused(profile,'conv') and not getattr(preparation,'running_slots',None) and not upscale_cloud._prep_waiting(preparation):
         import upscale_cloud,upscale_queue,drivelibrary
         if not getattr(preparation,'upscale_recovered',False):
          data=upscale_queue.load(profile);upscale_queue.save(profile,upscale_queue.recover(data));preparation.upscale_recovered=True
         try:
          preparation.upscaling=True   # F2: no re-package lane starts beside an AI Upscale copy (it changes converter settings)
          import upscale_queue;upscale_queue.RUNNING[0]=True
          try:
           # ISSUE-227: an owner's Repair / Try Again stops it (its copy starts again later) so the repair is applied at once.
           if upscale_cloud.process_one(preparation,lambda:converting() and not prepare_downloads.wakes_work(profile),media_for=upscale_cloud.media_lookup(profile,drivelibrary.parse)):delay=2
          finally:preparation.upscaling=False;upscale_queue.RUNNING[0]=False
         except Exception as error:
          diagnostics.log_exception(xbmc,'upscale',error)
       finally:preparation.busy=False
     preparation.runtime=None
   if count:notices.add(profile,'drive','Uploaded to Google Drive','%d video%s in Kodi Downloads'%(count,'' if count==1 else 's'))
  except driveupload.Stop as error:
   schedule={'reason':'transfer_lock_busy' if str(error)=='A Drive transfer is already running' else 'stop_requested',
             'conversion_paused':transfer_control.paused(profile,'conv'),'uploads_paused':transfer_control.paused(profile,'up')}
   if schedule!=last_schedule:
    diagnostics.event(log,'preparation','scheduler',**schedule);last_schedule=schedule
  except driveupload.SignedOut as error:
   # Once per refused sign-in, then quiet until the owner signs in again (no new refresh is tried meanwhile).
   if not getattr(drive_uploads,'told_signed_out',False):
    diagnostics.log_exception(xbmc,'drive_upload',error)
    notices.add(profile,'problem','Sign in to Google Drive again',str(error));drive_uploads.told_signed_out=True
   work_state.need('drive_signin')   # build 193: the orange card with Sign in on Library status and Notifications
   delay=max(delay,60)
  except driveupload.RefreshBusy as error:
   xbmc.log('Kodi iOS Drive: %s'%diagnostics.error_text(error),xbmc.LOGINFO);delay=max(delay,60)
   work_state.network('drive',driveupload.HOLD.get('until') or time.time()+60,'Google Drive is busy')
  except Exception as error:
   diagnostics.log_exception(xbmc,'drive_upload',error)
   notices.add(profile,'problem','Google Drive upload paused',diagnostics.redact(error)[:160])
  else:
   drive_uploads.told_signed_out=False
   work_state.need('drive_signin',False);work_state.network('drive')
  # A check or a Library status choice (prepare next, try again, keep) is picked up within seconds.
  if prepare_downloads.check_requested(profile) or prepare_downloads.pending_requests(profile):delay=5
if __name__=='__main__':run()
