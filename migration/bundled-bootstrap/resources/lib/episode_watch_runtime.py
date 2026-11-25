"""Kodi adapters for opening-only episode checks; no account, network or GUI work on import."""
import json,time,urllib.parse,urllib.request,uuid
import episode_watch as watch

def pass_once(profile,window,keep_going,log,auto_allowed=True):
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 import debrid_drive,drivelibrary,library_scan,source_match,elementum_cloud,elementum_download,transfer_control
 if watch.batch_active(window):watch.sweep.last={'deferred':True,'unresolved':0,'checked':0};return 0   # a season batch is running: look again soon
 if not watch.load(profile)['shows']:return 0
 key=source_match.tmdb_key()
 if not key:raise RuntimeError('Episode metadata is unavailable')
 def get(path):
  if not keep_going():raise RuntimeError('Episode check deferred')
  url=drivelibrary.TMDB+path+'?'+urllib.parse.urlencode({'api_key':key})
  with urllib.request.urlopen(url,timeout=8) as response:return json.loads(response.read(2*1024*1024))
 inventory=None;details={}
 def show(ident):
  data=get('/tv/'+ident);details[ident]=data;return data
 def existing(show,episode):
  nonlocal inventory
  s,e=episode['season_number'],episode['episode_number'];failed=False
  for job in debrid_drive.load(profile).get('jobs',[]):
   if job.get('show_tmdb')!=show['tmdb'] or str(job.get('season'))!=str(s):continue
   if str(job.get('episode'))==str(e):
    if job.get('status')!='failed' or 'cancel' in str(job.get('error','')).lower():return True
    failed=True
   if job.get('kind')=='season':
    if not job.get('files') and job.get('status') not in ('done','failed'):
     raise RuntimeError('Season contents are still being checked')
    for file in job.get('files') or []:
     info=drivelibrary.parse(file.get('drive_name') or file.get('path',''))
     if (info.get('season'),info.get('episode'))==(str(s),str(e)) and (file.get('done') or job.get('status')!='failed'):return True
  if inventory is None:
   drive,drive_id=drivelibrary.client()
   if not drive or not drive_id:raise RuntimeError('Drive ownership check unavailable')
   inventory=library_scan.remote_files(drive,keep_going)
  data=details.get(show['tmdb']) or {}
  names=[n for n in (show['title'],data.get('name'),data.get('original_name')) if n]
  year=str(data.get('first_air_date') or '')[:4]
  for item in inventory:
   name=item.get('name','');folder=item.get('folderName','')
   media=drivelibrary.media_key(name,folder)
   if not media or media[0]!='episode' or tuple(map(str,media[-2:]))!=(str(s),str(e)):continue
   if drivelibrary.same_year(year,drivelibrary.media_year(name,folder)) and any(
      media[1]==drivelibrary.show_key(n) for n in names):return True
  # Phone downloads from older installations are checked too; a failed check defers the search.
  import sys,os
  lib=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path'))
  lib=os.path.join(lib,'resources','lib')
  if lib not in sys.path:sys.path.append(lib)
  import ios_downloaded
  if ios_downloaded.completed_copy('episode',show['title'],'',s,e,cloud=False):return True
  return 'failed' if failed else False
 def download(show,episode):
  if not keep_going() or watch.active_request(window) or watch.batch_active(window):return False
  # Do not launch a source search only to discover a missing account in a dialog.
  if not xbmcaddon.Addon('plugin.video.umbrella').getSetting('alldebridtoken'):return False
  import elementum_engine
  if not elementum_engine.ensure_here():return False   # started on demand, not at launch
  ident=uuid.uuid4().hex;target={'tmdb':show['tmdb'],'season':episode['season_number'],'episode':episode['episode_number']}
  request={'request_id':ident,'target':target,'profile':show['preference'],'mode':0,'until':time.time()+600}
  # ISSUE-236 / ISSUE-244: failed versions are never picked again; ones found lower only when nothing else exists.
  request['excluded_names'],request['lower_names']=debrid_drive.avoid_names(debrid_drive.load(profile),show['tmdb'],target['season'],target['episode'])
  try:
   import quality_choice   # DEC-049 board C
   request['prefer_names']=[n for n in (quality_choice.preferred(profile,show['tmdb'],target['season']),) if n]
   request['season_names']=debrid_drive.season_names(debrid_drive.load(profile),show['tmdb'],target['season'])   # ISSUE-274
  except Exception:pass
  window.clearProperty(watch.RESULT);window.clearProperty('KodiIOS.AutoPick.Queued')
  window.setProperty(watch.AUTO,json.dumps(request))
  queued=False
  try:
   url=elementum_download.plugin_url('episode',show['tmdb'],target['season'],target['episode'])
   try:elementum_download.follow(url,timeout=120,route=lambda url:elementum_cloud.route(url,quiet=True,request_id=ident) if allowed() else True,gate=elementum_download.background_gate)
   except elementum_download.Canceled:
    if not allowed():raise   # interrupted (a video started, the app left)
    return False             # AllDebrid did not take it (a new episode is often not cached yet): this episode is not found yet, the others are still checked
   result=json.loads(window.getProperty('KodiIOS.AutoPick.Queued') or '{}')
   queued=result.get('request_id')==ident and result.get('queued') is True
   return queued
  finally:
   if not queued:watch.cancel_request(window,request)
   try:current=json.loads(window.getProperty(watch.AUTO) or '{}')
   except ValueError:current={}
   if current.get('request_id')==ident:window.clearProperty(watch.AUTO)
 def allowed():
  return keep_going() and not watch.batch_active(window) and not any(transfer_control.paused(profile,k) for k in transfer_control.KINDS)
 def notify(show,episode):
  # The bell's Alert switch: a message in Notifications and a toast. Only a message that was posted counts as sent.
  import anticipated,notices
  title,text=anticipated.alert_text(show,episode)
  notices.add(profile,'info',title,text)
  try:xbmcgui.Dialog().notification(title,text,xbmcgui.NOTIFICATION_INFO,6000)
  except Exception:pass
  return True
 return watch.sweep(profile,show,lambda ident,n:get('/tv/%s/season/%d'%(ident,n)),existing,download,keep_going=allowed,log=log,
                    notify=notify,auto_allowed=auto_allowed)

def run(monitor,profile,ready):
 import xbmc,xbmcaddon,xbmcgui,app_state,diagnostics
 window=xbmcgui.Window(10000)
 log=lambda event,**fields:diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'episode_watch',event,**fields)
 def check():
  # The Library setting only switches automatic downloading off; the bell's alerts still run (a stream-only show).
  # Returns when to look again: soon after an interrupted pass, every half hour while an aired episode is still not found.
  watch.sweep.last={}
  try:
   queued=pass_once(profile,window,lambda:not monitor.abortRequested() and app_state.foreground() and not xbmc.getCondVisibility('Player.HasMedia'),log,
                    auto_allowed=xbmcaddon.Addon().getSetting('follow_episodes')!='false')
  except Exception as error:
   log('opening_deferred',error=type(error).__name__);return watch.RETRY_DEFERRED if watch.interrupted(error) else None
  last=getattr(watch.sweep,'last',{}) or {}
  log('opening_check',queued=queued,checked=last.get('checked',0),unresolved=last.get('unresolved',0),deferred=bool(last.get('deferred')))
  if last.get('deferred'):return watch.RETRY_DEFERRED
  return watch.RETRY_UNRESOLVED if last.get('unresolved') else None
 watch.run_open_checks(monitor,ready,app_state.foreground,
  lambda:xbmc.getCondVisibility('Player.HasMedia | Window.IsVisible(yesnodialog) | Window.IsVisible(selectdialog) | Window.IsVisible(virtualkeyboard)') or bool(watch.active_request(window)) or watch.batch_active(window),
  lambda:True,check)
