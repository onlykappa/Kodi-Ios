import json,os,sys,time,threading
_IMPORT_STARTED=time.monotonic()
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
from bootstrap import initialize,restore,ensure_enabled,install_players,elementum_defaults,elementum_upload_cap,install_payload,umbrella_defaults,media_folders,elementum_library,umbrella_streaming_only,phone_housekeeping
from navigation import upgrade,sync_skin_preferences,update_nodes,phone_defaults,REVISION
from startup import generate,failure,LOCK,FUSE
import airplay,notices,updates,threading,diagnostics,transfer_control
class _Late:
 """A module imported on first use (performance 1E.4: 1.74 s of imports before the service ran; portrait.py alone is
 147 KB). Each of these is first used in a worker thread or well after start-up, so the import leaves the main path."""
 def __init__(self,name):self._name=name;self._module=None
 def __getattr__(self,attribute):
  if self._module is None:
   import importlib;self._module=importlib.import_module(self._name)
  return getattr(self._module,attribute)
activity,signin_server,background,calibration,driveupload,portrait,umbrella_ready=[_Late(n) for n in ('activity','signin_server','background','calibration','driveupload','portrait','umbrella_ready')]
_IMPORT_SECONDS=time.monotonic()-_IMPORT_STARTED

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 begun=time.monotonic()
 xbmc.log('Kodi iOS startup: bootstrap entered (imports %.3fs)'%_IMPORT_SECONDS,xbmc.LOGINFO)
 monitor=xbmc.Monitor()
 root=Path(__file__).resolve().parent;profile=Path(xbmcvfs.translatePath('special://profile/')).resolve()
 diagnostics.configure(root,profile)
 diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'startup','installed_build',
  kodi=xbmc.getInfoLabel('System.BuildVersion'),os=xbmc.getInfoLabel('System.OSVersion'),python=sys.version.split()[0])
 window=xbmcgui.Window(10000);state={'stage':'prepare'};generated=False
 keys={'changed':False}   # roadmap 3.6: Kodi reads the keymaps at launch; they are reloaded only when a file changed
 # Settings shows it beside Kodi's version: "Kodi 21.3 (build 157)" (owner request).
 window.setProperty('KodiIOS.Build',updates.installed_build(root))
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
  portrait_thread=threading.Thread(target=portrait.run_service,args=(xbmc,xbmcvfs,monitor,profile,invoke),kwargs={'ready':setup_done,'native_ui_started':_EARLY_UI_STARTED},daemon=True);portrait_thread.start()
 # Owner build-136 log: the tab bar answered ~8 s after launch, 2 s of it this fixed wait. Only setup waits now.
 if monitor.waitForAbort(2):return
 def slow_start(after=3.0):
  """Board 13 (owner-approved, docs/design/fuse-windows-mockups.html; roadmap U.13): no startup box over Home. Only
  when the skin's own setup (first start, or after an update) is still running `after` seconds later, the activity
  pill says so ("Getting things ready · Preparing your library"), through Kodi's background box that the pill reads
  (activity.classify), until setup is over."""
  import activity
  if monitor.waitForAbort(after) or setup_done.is_set():return
  box=xbmcgui.DialogProgressBG()
  try:
   box.create(activity.STARTUP_TITLE,activity.STARTUP_TEXT)
   while not setup_done.is_set():
    if monitor.waitForAbort(0.5):break
  finally:box.close()
 def prepare_generated(sync=True):
  nonlocal generated
  stage('skin_preferences')
  if sync:sync_skin_preferences(root/'seed',api,invoke,lambda id,is_bool:xbmc.getCondVisibility('Skin.HasSetting('+id+')') if is_bool else xbmc.getInfoLabel('Skin.String('+id+')'))
  # Before generation, so the rebuilt menus include Drive/recovery in the gear menu.
  stage('phone_menus');update_nodes(profile);phone_defaults(lambda id:xbmc.getInfoLabel('Skin.String('+id+')'),invoke)
  skin=Path(xbmcvfs.translatePath('special://skin/')).resolve()
  if skin.name!=FUSE or not skin.is_relative_to(home):raise RuntimeError('Writable Fuse path not selected')
  threading.Thread(target=slow_start,daemon=True).start()
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
 slowdown.configure(lambda:'airplay' if airplay.playback_active(playback_lib,xbmcgui.Window(10000),time.time()) else ('buffering' if xbmc.getCondVisibility('Player.Caching') else 'video' if xbmc.getCondVisibility('Player.HasVideo') else ''))
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
  return transfer_history.activity(torrents,debrid_drive.load(profile).get('current'),prepare_downloads.load(profile).get('current'))
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
     server,port=drive_proxy.start(drive.token,hold=lambda:airplay.starting(home_window),   # roadmap 1G.3
                                   state_dir=profile/'addon_data/service.kodi.ios.bootstrap',log=lambda text:xbmc.log(text,xbmc.LOGINFO))   # 1A.3
     home_window.setProperty(drive_proxy.PROPERTY,str(port))
     xbmc.log('Kodi iOS Drive proxy: streaming Drive copies on port %d'%port,xbmc.LOGINFO)
     monitor.waitForAbort()
     home_window.clearProperty(drive_proxy.PROPERTY);server.shutdown();return
   except Exception as error:xbmc.log('Kodi iOS Drive proxy: not started (%s)'%type(error).__name__,xbmc.LOGWARNING)
   if monitor.waitForAbort(60):return
 threading.Thread(target=drive_proxy_loop,daemon=True).start()
 # Roadmap 1C.1: "open timing" log line per video (tap to picture).
 import open_timing
 import cache_tune   # roadmap 1B.3: Kodi's cache read factor follows Wi-Fi / cellular, set as a video is about to open
 threading.Thread(target=open_timing.watch,args=(xbmcgui.Window(10000),lambda:xbmc.getCondVisibility('Player.HasVideo + Player.Playing'),
                  lambda text:xbmc.log(text,xbmc.LOGINFO),monitor.waitForAbort),
                  kwargs={'on_open':lambda:cache_tune.apply(xbmc,str(profile),lambda text:xbmc.log(text,xbmc.LOGINFO)),
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
 # Roadmap 3.5: one performance line a minute (list runs, opens, Drive proxy requests and seeks), only when something happened.
 import perf_summary,drive_proxy
 threading.Thread(target=perf_summary.watch,args=(xbmcgui.Window(10000),open_timing.take,
                  lambda:drive_proxy.CURRENT[0].stats.take() if drive_proxy.CURRENT else {},
                  lambda text:xbmc.log(text,xbmc.LOGINFO),monitor.waitForAbort),daemon=True).start()
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
  phone=[u for u in notices.uploads(profile) if u.get('source')=='phone']
  prep=prepare_downloads.load(profile);flags=work_state.flags(profile)
  need=prepare_downloads.problem_need(prep)   # board E3: videos that can't be made ready, with Review
  if need:flags=dict(flags,needs=list(flags['needs'])+[need])
  return {'prep':prep,'runtime':preparation_runtime.read(profile),'debrid':debrid_drive.load(profile),
          'phone':phone,'torrents':notices.downloads(),
          'paused':{k:transfer_control.paused(profile,k) for k in transfer_control.KINDS},'slow':slowdown.reason(),
          **flags}
 threading.Thread(target=work_state.publish,args=(profile,work_inputs,monitor.waitForAbort),
                  kwargs={'set_property':window.setProperty,'log':lambda text:xbmc.log('Kodi iOS '+text,xbmc.LOGWARNING)},daemon=True).start()
 # A torrent whose real name turns out to be another film (owner, build 156: Fall 2022 → Fall.2.Deadpoint.2026) is
 # stopped once Elementum knows its name, and explained in Notifications.
 import source_guard
 threading.Thread(target=source_guard.run,args=(window,notices.torrent_list,driveupload.remove_torrent,
  lambda title,text:notices.add(profile,'problem',title,text),monitor.waitForAbort),daemon=True).start()
 import library_watch
 threading.Thread(target=library_watch.run,args=(xbmc,xbmcaddon,xbmcvfs,monitor,profile),daemon=True).start()
 # Umbrella's getting-ready-to-play screen: its source text, split into the badges the portrait page shows.
 threading.Thread(target=umbrella_ready.watch,args=(lambda:xbmc.getCondVisibility('Window.IsVisible(%s)'%umbrella_ready.WINDOW),
  lambda:xbmc.getInfoLabel('Control.GetLabel(2001)'),window.setProperty,window.clearProperty,monitor.waitForAbort),daemon=True).start()
 # The activity pill: Kodi's background progress box (never drawn) read and rewritten, plus Elementum and Drive.
 def activity_setting(key,default):
  try:
   value=xbmcaddon.Addon().getSetting(key)
   return default if value=='' else value.lower()=='true'
  except Exception:return default
 # The pill shows the poster of what is downloading (TMDb, with TMDb Helper's key, as the Library does).
 try:
  import drivelibrary,urllib.request
  key=drivelibrary.tmdb_key(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path')))
  def get(url):
   with urllib.request.urlopen(url,timeout=8) as response:return response.read(1024*1024)
  posters=activity.Posters(activity.poster_lookup(key,get)) if key else None
 except Exception:posters=None
 threading.Thread(target=activity.watch,args=(lambda:activity.read_box(xbmc,xbmcgui),notices.downloads,lambda:notices.uploads(profile),
  activity_setting,lambda:xbmc.Player().isPlayingVideo(),lambda props:[window.setProperty(k,v) for k,v in props.items()],
  lambda text:notices.add(profile,'problem','Elementum Burst',text),monitor.waitForAbort),kwargs={'posters':posters},daemon=True).start()
 # Kept Elementum videos go to Google Drive in the background, never during playback.
 try:
  if xbmcaddon.Addon().getSettingBool('drive_upload') or xbmcaddon.Addon().getSettingBool('prepare_downloads'):
   threading.Thread(target=drive_uploads,args=(monitor,home,profile),daemon=True).start()
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
   threading.Thread(target=airplay_diagnostics.watch,args=(lib,profile,xbmcgui.Window(10000),lambda m:xbmc.log(m,xbmc.LOGINFO),monitor.waitForAbort),daemon=True).start()
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
 slowdown.configure(lambda:'airplay' if airplay_busy() else ('buffering' if xbmc.getCondVisibility('Player.Caching') else 'video' if xbmc.getCondVisibility('Player.HasVideo') else ''))
 if not xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)'):return
 common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
 if common not in sys.path:sys.path.append(common)
 from clouddrive.common.account import AccountManager
 from clouddrive.common.remote.request import tls_context
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
 try:remote_media.start(monitor,xbmcgui.Window(10000),context=tls_context(),open_url=native_reader)
 except Exception as error:diagnostics.log_exception(xbmc,'media_source_bridge',error)
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
    except Exception as error:xbmc.log('Kodi iOS AllDebrid to Drive: Elementum list unavailable (%s)'%type(error).__name__,xbmc.LOGWARNING);diagnostics.log_exception(xbmc,'service',error)
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
     driveupload.invalidate_library(str(profile/'addon_data/service.kodi.ios.bootstrap'))
     prepare_downloads.request_check(profile)   # preparation for Kodi and AirPlay picks it up from Drive
    def ready_copy(with_link,name,size,parent,going,progress,key):
     # F1 (PR #24): made ready while it copies, with the preparation queue's converter and Drive stream. None: plain copy.
     try:q=preparation
     except NameError:return None
     addon=xbmcaddon.Addon()
     if q is None or not addon.getSettingBool('prepare_downloads') or not addon.getSettingBool('prepare_while_copying'):return None
     import debrid_ready,slowdown
     return debrid_ready.copy(q,profile,with_link,name,size,parent,going,progress,key,
                              log=lambda text:xbmc.log('Kodi iOS AllDebrid: '+diagnostics.redact(text),xbmc.LOGINFO),hold=slowdown.holding)
    delay=debrid_drive.step(profile,alldebrid.AllDebrid(token),drive,lambda kind,title,text:notices.add(profile,kind,title,text),ready_copy=ready_copy,
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
 def library_lists():
  import drivelibrary
  state_dir=str(profile/'addon_data/service.kodi.ios.bootstrap')
  while not monitor.waitForAbort(10):
   try:
    if not accounts.get_accounts():continue
    done=drivelibrary.refresh_stale(state_dir)
    if done:log('Library lists refreshed from Google Drive: %s'%', '.join(done))
   except (driveupload.SignedOut,driveupload.RefreshBusy):monitor.waitForAbort(60)   # the uploads loop tells the owner
   except Exception as error:diagnostics.log_exception(xbmc,'library_lists',error)
 threading.Thread(target=library_lists,daemon=True).start()
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
