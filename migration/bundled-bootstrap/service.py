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
from bootstrap import initialize,restore,ensure_enabled,install_players,elementum_defaults,install_payload,umbrella_defaults,media_folders,elementum_library,umbrella_streaming_only,phone_housekeeping
from navigation import upgrade,sync_skin_preferences,update_nodes,phone_defaults,REVISION
from startup import generate,failure,LOCK,FUSE
import activity,signin_server,airplay,background,calibration,driveupload,notices,updates,threading,portrait,umbrella_ready
_IMPORT_SECONDS=time.monotonic()-_IMPORT_STARTED

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 begun=time.monotonic()
 xbmc.log('Kodi iOS startup: bootstrap entered (imports %.3fs)'%_IMPORT_SECONDS,xbmc.LOGINFO)
 monitor=xbmc.Monitor()
 root=Path(__file__).resolve().parent;profile=Path(xbmcvfs.translatePath('special://profile/')).resolve()
 window=xbmcgui.Window(10000);state={'stage':'prepare'};generated=False
 # Settings shows it beside Kodi's version: "Kodi 21.3 (build 157)" (owner request).
 window.setProperty('KodiIOS.Build',updates.installed_build(root))
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
  # Load the guarded XML before a legacy completed profile runs its helpers again.
  if navigation.get('changed_files') and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  stage('initialize')
  result=initialize(root/'seed',profile,api,verify_skin=verify_skin,home=home,refresh=refresh)
  upgrade(home,profile)
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
    import umbrella_picker
    # (Not "window": that name is the Home window, used again when setup finishes.)
    source_window=Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path')))/'resources/lib/windows/source_results.py'
    if umbrella_picker.umbrella_hook(str(source_window)):xbmc.log('Kodi iOS setup added the Deck source page to Umbrella',xbmc.LOGINFO)
    elif source_window.is_file() and umbrella_picker.HOOK_MARK not in source_window.read_text(encoding='utf-8',errors='replace'):
     xbmc.log('Kodi iOS setup: this Umbrella version has a different source window; its own list stays',xbmc.LOGWARNING)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)') and xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)'):
    umbrella=xbmcaddon.Addon('plugin.video.umbrella')
    if umbrella_defaults(umbrella.getSetting,umbrella.setSetting):xbmc.log('Kodi iOS setup set Umbrella to CocoScrapers',xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS scraper setup skipped: '+type(error).__name__,xbmc.LOGWARNING)
  if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)'):
   try:
    engine=xbmcaddon.Addon('plugin.video.elementum')
    folder=elementum_defaults(updates.updates_folder(home).with_name('Elementum Downloads'),engine.getSetting,engine.setSetting)
    if folder:xbmc.log('Kodi iOS setup set Elementum downloads to '+folder,xbmc.LOGINFO)
   except Exception as error:xbmc.log('Kodi iOS Elementum defaults skipped: '+type(error).__name__,xbmc.LOGWARNING)
  # Once per phone: folders the Deck config expects, phone-useless network discovery off (ISSUE-070).
  try:
   engine=xbmcaddon.Addon('plugin.video.elementum') if xbmc.getCondVisibility('System.HasAddon(plugin.video.elementum)') else None
   done=phone_housekeeping(profile,(engine.getSetting,engine.setSetting) if engine else None,api)
   if done:xbmc.log('Kodi iOS setup housekeeping: '+', '.join(done),xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS housekeeping skipped: '+type(error).__name__,xbmc.LOGWARNING)
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
  except Exception as error:xbmc.log('Kodi iOS download folders skipped: '+type(error).__name__,xbmc.LOGWARNING)
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
  receipt=failure(error,state['stage']);dest=profile/'addon_data/service.kodi.ios.bootstrap/startup-error.json'
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(receipt,indent=2)+'\n')
  xbmc.log('Kodi iOS setup failed: '+json.dumps(receipt),xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Kodi setup needs review','Automatic setup failed at '+state['stage']+'. Settings and Recovery remain available. Report startup-error.json; do not share credentials.')
 finally:
  window.clearProperty(LOCK)
  invoke('Action(reloadkeymaps)')
  # Exactly one reload after verified generation, never during Keep Skin confirmation.
  if generated and state['stage']=='complete' and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  setup_done.set()
  # After any reload has settled: the one-time calibration reset, then a quiet check for a newer build. In the
  # background (performance pass): the tab bar, Continue Watching and the rest below used to wait for these ten
  # seconds too (the glass bar appeared ~19 s after launch in the owner's log).
  def later():
   if xbmc.getSkinDir()!=FUSE or monitor.waitForAbort(10):return
   try:calibration.reset_once(profile,lambda command:xbmc.executebuiltin(command),xbmc.getCondVisibility,monitor.waitForAbort)
   except Exception as error:xbmc.log('Kodi iOS calibration reset skipped: '+type(error).__name__,xbmc.LOGWARNING)
   try:
    if xbmcaddon.Addon().getSettingBool('check_on_start'):updates.run(check_only=True)
   except Exception as error:xbmc.log('Kodi iOS update check skipped: '+type(error).__name__,xbmc.LOGWARNING)
  threading.Thread(target=later,daemon=True).start()
 # The bell in the hub headers: unread messages and whether a download or Drive upload runs. Each message also gets
 # its part of kodi.log, shown when it is tapped.
 threading.Thread(target=notices.publish,args=(window,profile,monitor.waitForAbort,lambda:xbmc.Player().isPlayingVideo()),
  kwargs={'log_path':os.path.join(xbmcvfs.translatePath('special://logpath/'),'kodi.log')},daemon=True).start()
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
 except Exception as error:xbmc.log('Kodi iOS Drive upload unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 # Downloads and Drive uploads keep going when Kodi leaves the screen (KodiAirPlay r3 plays silence meanwhile).
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=airplay.load(path) if path else None
  if lib is not None and hasattr(lib,'kodi_background_keep') and xbmcaddon.Addon().getSettingBool('background_transfers'):
   kept=str(updates.updates_folder(home).with_name('Kodi Downloads'))
   def why():
    if xbmc.Player().isPlayingAudio():return ''  # Kodi's own music keeps it running; the silence would make it mixable
    uploading=xbmcaddon.Addon().getSettingBool('drive_upload') and xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)')
    import prepare_downloads
    preparing=any(card.get('running') for card in prepare_downloads.cards(profile))
    return ('video preparation' if preparing else background.reason(notices.downloads(),notices.uploads(profile),uploading and background.videos_waiting(kept)))
   threading.Thread(target=background.watch,args=(lib.kodi_background_keep,why,monitor.waitForAbort,lambda m:xbmc.log(m,xbmc.LOGINFO)),daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS background transfers unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 # r6: the AirPlay stream's requests, CODECS and Apple's player events into kodi.log (owner build-133: sound only).
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=airplay.load(path) if path else None
  if lib is not None and hasattr(lib,'kodi_airplay_log'):
   threading.Thread(target=airplay.relay,args=(lib,lambda m:xbmc.log(m,xbmc.LOGINFO),monitor.waitForAbort),daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS AirPlay log unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 # Stays running for the rest of the session: Apple's AirPlay button in the top-right corner during playback.
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if path and xbmcaddon.Addon().getSettingBool('airplay_button'):
   airplay.watch(airplay.load(path),lambda:xbmc.getCondVisibility(airplay.PLAYING),monitor.waitForAbort)
 except Exception as error:xbmc.log('Kodi iOS AirPlay button unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 while not monitor.waitForAbort(60):pass

def drive_uploads(monitor,home,profile):
 """Idle-only download → upload → one-file preparation. Startup scan and new uploads share one queue/lock."""
 import urllib.parse,urllib.request,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)'):return
 common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
 if common not in sys.path:sys.path.append(common)
 from clouddrive.common.account import AccountManager
 from clouddrive.common.remote.request import tls_context
 drive_addon=xbmcaddon.Addon('plugin.googledrive')
 if signin_server.migrate(drive_addon):xbmc.log('Kodi iOS Drive: sign-in server set to the owner worker',xbmc.LOGINFO)
 accounts=AccountManager(xbmcvfs.translatePath(drive_addon.getAddonInfo('profile')))
 send=driveupload.sender(tls_context())
 def refresh(refresh_token):
  server=signin_server.server(drive_addon.getSetting('sign-in-server'))
  body=urllib.parse.urlencode({'provider':'googledrive','refresh_token':refresh_token}).encode()
  status,_,answer=send('POST',server+'/refresh',body,{'Content-Type':'application/x-www-form-urlencoded'})
  if status!=200:raise RuntimeError('Drive sign-in refresh: HTTP %s'%status)
  return json.loads(answer)
 drive=driveupload.Drive(driveupload.token_source(accounts.get_accounts,accounts.save_account,refresh),send)
 root=str(updates.updates_folder(home).with_name('Kodi Downloads'))
 state=str(profile/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json')
 # Downloads through AllDebrid go straight to Drive (debrid_drive): its own loop, so a long copy never holds up the
 # phone-to-Drive uploads or preparation below, and it runs during playback too (network only, no phone storage).
 def debrid_loop():
  import alldebrid,debrid_drive,prepare_downloads
  delay=10
  while not monitor.waitForAbort(delay):
   delay=20
   try:token=xbmcaddon.Addon('plugin.video.umbrella').getSetting('alldebridtoken')
   except Exception:token=''
   # A version played from the source page keeps downloading onto the phone after playback (Elementum's keep
   # downloading): once nothing plays, AllDebrid takes it to Drive and Elementum drops it (owner, build 160).
   if token and accounts.get_accounts():
    try:
     for tid in debrid_drive.adopt(profile,notices.torrent_list(),xbmc.Player().isPlayingVideo()):
      driveupload.remove_torrent(tid);xbmc.log('Kodi iOS AllDebrid to Drive: took %s from Elementum'%tid,xbmc.LOGINFO)
    except Exception as error:xbmc.log('Kodi iOS AllDebrid to Drive: Elementum list unavailable (%s)'%type(error).__name__,xbmc.LOGWARNING)
   if not debrid_drive.active(profile) or not accounts.get_accounts():continue
   try:
    def done(job):
     driveupload.invalidate_library(str(profile/'addon_data/service.kodi.ios.bootstrap'))
     prepare_downloads.request_check(profile)   # preparation for Kodi and AirPlay picks it up from Drive
    delay=debrid_drive.step(profile,alldebrid.AllDebrid(token),drive,lambda kind,title,text:notices.add(profile,kind,title,text),
                            keep_going=lambda:not monitor.abortRequested(),on_done=done) or 20
   except alldebrid.Problem as problem:
    notices.add(profile,'problem',"Couldn't download to Google Drive",str(problem));delay=300
   except Exception as error:
    xbmc.log('Kodi iOS AllDebrid to Drive paused: %s %s'%(type(error).__name__,error),xbmc.LOGWARNING);delay=60
 threading.Thread(target=debrid_loop,daemon=True).start()
 idle=lambda:not monitor.abortRequested() and not xbmc.Player().isPlayingVideo()
 log=lambda message:xbmc.log('Kodi iOS '+message,xbmc.LOGINFO)
 import library_scan,prepare_downloads
 preparation=None
 def preparation_queue():
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if not path:raise RuntimeError('AirPlay preparation framework is missing')
  native=prepare_downloads.Native(airplay.load(path))
  # KodiAirPlay r14 reads the Drive file through this loopback stream: no downloaded copy on the phone.
  stream=None
  if native.streams:
   import drive_stream
   stream=drive_stream.DriveStream(drive.token,context=tls_context())
   xbmc.log('Kodi iOS preparation: streaming from Google Drive (no downloaded copy)',xbmc.LOGINFO)
  return prepare_downloads.Queue(profile,drive,native,
    download_file=lambda *args:prepare_downloads.download(*args,context=tls_context()),
    notify=lambda kind,title,text:notices.add(profile,kind,title,text),stream=stream)
 # First pass 30 s after start (owner, build 145: the Library was opened, and left, before the old 120 s first pass).
 delay=5
 while not monitor.waitForAbort(delay):
  delay=120
  if not idle() or not accounts.get_accounts():continue
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
     count=driveupload.run_once(root,drive,state,log,idle,xbmcaddon.Addon().getSettingBool('drive_upload_delete'),
                              lambda:driveupload.invalidate_library(state_dir),seeding,driveupload.remove_torrent,
                              remote=lambda:library_scan.remote_files(drive,idle),pace=1,
                              notify=lambda title,text:notices.add(profile,'drive',title,text))
    if xbmcaddon.Addon().getSettingBool('prepare_downloads'):
     if preparation is None:preparation=preparation_queue()
     can_prepare=lambda:idle() and xbmcaddon.Addon().getSettingBool('prepare_downloads')
     preparation.scan(can_prepare,force=bool(count))
     # Settings › Library › Check library for conversion: the current video pauses (it resumes where it was) so
     # the check runs within seconds instead of after a long conversion.
     converting=lambda:can_prepare() and not prepare_downloads.check_requested(profile)
     if preparation.process_one(converting):delay=2
     else:delay=30
   if count:notices.add(profile,'drive','Uploaded to Google Drive','%d video%s in Kodi Downloads'%(count,'' if count==1 else 's'))
  except driveupload.Stop:pass
  except Exception as error:
   xbmc.log('Kodi iOS Drive upload paused: %s %s'%(type(error).__name__,error),xbmc.LOGWARNING)
   notices.add(profile,'problem','Google Drive upload paused',str(error)[:160])
  # A check or a Library status choice (prepare next, try again, keep) is picked up within seconds.
  if prepare_downloads.check_requested(profile) or prepare_downloads.pending_requests(profile):delay=5
if __name__=='__main__':run()
