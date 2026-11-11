"""Kodi adapters for opening-only episode checks; no account, network or GUI work on import."""
import json,time,urllib.parse,urllib.request,uuid
import episode_watch as watch

def pass_once(profile,window,keep_going,log):
 import xbmc,xbmcaddon,xbmcvfs
 import debrid_drive,drivelibrary,library_scan,source_match,elementum_cloud,elementum_download,transfer_control
 if watch.batch_active(window):return 0
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
  if not elementum_engine.running():return False
  ident=uuid.uuid4().hex;target={'tmdb':show['tmdb'],'season':episode['season_number'],'episode':episode['episode_number']}
  request={'request_id':ident,'target':target,'profile':show['preference'],'mode':0,'until':time.time()+600}
  request['excluded_names']=[j['name'] for j in debrid_drive.load(profile).get('jobs',[])
   if j.get('show_tmdb')==show['tmdb'] and str(j.get('season'))==str(target['season']) and str(j.get('episode'))==str(target['episode'])
   and j.get('status')=='failed' and 'cancel' not in str(j.get('error','')).lower()][-20:]
  window.clearProperty(watch.RESULT);window.clearProperty('KodiIOS.AutoPick.Queued')
  window.setProperty(watch.AUTO,json.dumps(request))
  queued=False
  try:
   url=elementum_download.plugin_url('episode',show['tmdb'],target['season'],target['episode'])
   elementum_download.follow(url,timeout=120,route=lambda url:elementum_cloud.route(url,quiet=True,request_id=ident) if allowed() else True)
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
 return watch.sweep(profile,show,lambda ident,n:get('/tv/%s/season/%d'%(ident,n)),existing,download,keep_going=allowed,log=log)

def run(monitor,profile,ready):
 import xbmc,xbmcaddon,xbmcgui,app_state,diagnostics
 window=xbmcgui.Window(10000)
 log=lambda event,**fields:diagnostics.event(lambda text:xbmc.log(text,xbmc.LOGINFO),'episode_watch',event,**fields)
 def check():
  try:log('opening_check',queued=pass_once(profile,window,
       lambda:not monitor.abortRequested() and app_state.foreground() and not xbmc.getCondVisibility('Player.HasMedia')
              and xbmcaddon.Addon().getSetting('follow_episodes')!='false',log))
  except Exception as error:log('opening_deferred',error=type(error).__name__)
 watch.run_open_checks(monitor,ready,app_state.foreground,
  lambda:xbmc.getCondVisibility('Player.HasMedia | Window.IsVisible(yesnodialog) | Window.IsVisible(selectdialog) | Window.IsVisible(virtualkeyboard)') or bool(watch.active_request(window)) or watch.batch_active(window),
  lambda:xbmcaddon.Addon().getSetting('follow_episodes')!='false',check)
