"""Refresh a visible Library when completed phone or Drive entries change. No startup/network work off-page."""
import json,os,time

def art_titles(params,local,cloud):
 """Exactly the artwork identities used by the displayed local/Drive rows, once per title."""
 kind='tv' if params.get('type')=='tv' else 'movie';seen=set()
 # A show page (phone, Drive or both) takes its header art from the show (ios_library.episode_rows).
 if kind=='tv' and params.get('show') and (params.get('folder') or params.get('local')=='1' or params.get('merge')=='1'):
  seen.add((kind,params['show'],''));yield (kind,params['show'],'')
 for source,entries in (('local',local),('drive',cloud)):
  for entry in entries:
   title=entry.get('title','');year=entry.get('year','')
   if source=='local' and (params.get('local')=='1' or params.get('merge')=='1'):
    if params.get('merge')=='1':continue  # the show identity above is the one the page shows
    if title.casefold()!=params.get('show','').casefold() or year!=params.get('year',''):continue
   if source=='drive' and params.get('folder'):
    if params.get('loose')=='1' and (title.casefold()!=params.get('show','').casefold() or year!=params.get('year','')):continue
    title=params.get('show') or title;year=''
   identity=(kind,title,year)
   if title and identity not in seen:seen.add(identity);yield identity

def hydrate_artwork(params,local,cloud,drive,state_dir,key,get,active,clock=time.monotonic,budget=4,max_titles=6):
 """Fill a small missing-art batch while the Library is idle and visible; never run inside its listing."""
 if not key or not active():return False
 path=os.path.join(state_dir,'drive-library-art.json');cache=drive.load_json(path,{})
 before=dict(cache);deadline=clock()+budget;attempted=0
 def request(url):
  remaining=deadline-clock()
  if remaining<=0 or not active():raise TimeoutError('Library artwork yielded')
  return get(url,min(2,remaining))
 for kind,title,year in art_titles(params,local,cloud):
  if attempted>=max_titles or clock()>=deadline or not active():break
  if '%s:%s:%s'%(kind,title.lower(),year) in cache:continue
  attempted+=1;drive.artwork(kind,title,year,key,cache,request)
 # Episode names, plots and stills for the seasons on a show page.
 show=params.get('show')
 if params.get('type')=='tv' and show and (params.get('folder') or params.get('local')=='1' or params.get('merge')=='1'):
  tmdb=(cache.get('tv:%s:'%show.lower()) or {}).get('tmdb_id')
  if tmdb and 'show:%s'%tmdb not in cache and attempted<max_titles and clock()<deadline and active():
   attempted+=1;drive.show_details(tmdb,key,cache,request)
  for number in sorted({int(e.get('season') or 0) for e in list(local)+list(cloud) if e.get('season')}):
   if not tmdb or attempted>=max_titles or clock()>=deadline or not active():break
   if 'season:%s:%s'%(tmdb,number) in cache:continue
   attempted+=1;drive.season(tmdb,number,key,cache,request)
 updates={k:v for k,v in cache.items() if k not in before or before[k]!=v}
 if not updates:return False
 # Preserve any results written while these requests were in flight.
 latest=drive.load_json(path,{});latest.update(updates);drive.save_json(path,latest)
 return True

def progress_stamp(path):
 """Cheap revision of the local Continue Watching store, checked only on an idle visible show page."""
 try:
  stat=os.stat(path);return (stat.st_mtime_ns,stat.st_size)
 except FileNotFoundError:return None

def watch(info,busy,refresh,wait,page,drive,state_dir,clock=time.monotonic,every=5,cloud_every=30,hydrate=None,art_every=15,art_busy=lambda:False,progress_signature=None):
 last_path=None;last=None;cloud_at=-1e9;art_at=-1e9;cloud=[];cache_seen=False;art_pending=False
 while not wait(every):
  path=info();params=page.current_params(path)
  if params is None:
   last_path=None;last=None;continue
  if busy():continue
  if path!=last_path:last=None;cloud_at=-1e9;art_at=-1e9;last_path=path;cloud=[];cache_seen=False;art_pending=False
  kind='tv' if params.get('type')=='tv' else 'movie'
  try:
   local=[] if params.get('folder') and not params.get('show') and params.get('merge')!='1' else page.local_entries(kind,drive)
   if params.get('show'):
    local=[entry for entry in local if (page.show_key(entry.get('title')) if hasattr(page,'show_key') else entry.get('title','').casefold())==
           (page.show_key(params['show']) if hasattr(page,'show_key') else params['show'].casefold())]
   if clock()-cloud_at>=cloud_every or (cache_seen and not os.path.exists(os.path.join(state_dir,'drive-library.json'))):
    cloud_at=clock()
    try:
     if params.get('show') and hasattr(page,'cloud_entries'):cloud=page.cloud_entries(params,drive,state_dir,fresh=True)
     else:cloud=[] if params.get('local')=='1' or (params.get('merge')=='1' and not params.get('folder')) else drive.listing(kind,state_dir,params.get('folder'),strict=True,fresh=True)[0]
    except Exception as error:_quiet('library_watch:51',error)  # offline Drive must not hide a newly completed phone download
    cache_seen=os.path.exists(os.path.join(state_dir,'drive-library.json'))
   # Art is cosmetic; only media membership/paths need to refresh the page.
   progress=progress_signature() if (params.get('show') or kind=='movie') and progress_signature is not None else None
   signature=json.dumps([local,cloud,progress],sort_keys=True)
  except Exception:continue  # preserve the working page during an offline/failed check
  art_changed=False
  if hydrate is not None and clock()-art_at>=art_every and not busy() and not art_busy() and info()==path:
   art_at=clock()
   try:art_changed=hydrate(params,local,cloud)
   except Exception as error:_quiet('library_watch:60',error)  # cosmetic metadata must not interrupt completed-download discovery
  art_pending=art_pending or art_changed
  if signature!=last or (art_pending and not art_busy()):
   # Also refresh on entry: a previous cached empty listing must not remain empty for five minutes.
   if not busy() and info()==path:
    refresh('Container.Refresh');last=signature;art_pending=False

def run(xbmc,xbmcaddon,xbmcvfs,monitor,profile):
 import sys,urllib.request,drivelibrary
 try:
  addon=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path'))
  lib=os.path.join(addon,'resources','lib')
  if lib not in sys.path:sys.path.append(lib)
  import ios_library
  state_dir=str(profile/'addon_data/service.kodi.ios.bootstrap')
  info=lambda:xbmc.getInfoLabel('Container.FolderPath') if xbmc.getCondVisibility('Window.IsActive(videos)') else ''
  busy=lambda:xbmc.Player().isPlayingVideo() or xbmc.getCondVisibility('System.HasActiveModalDialog') or xbmc.getCondVisibility('Container.IsUpdating')
  # Owner (build 145): downloaded movies stayed grey. Notices.Active is 'true' for as long as any Elementum download
  # runs, so posters waited for every download to end. Art is a few small TMDb requests, cached once per title;
  # it now runs during downloads too (still never during playback, a dialog or a page load: busy()).
  art_busy=lambda:False
  try:key=drivelibrary.tmdb_key(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path')))
  except Exception:key=''
  def get(url,timeout):
   with urllib.request.urlopen(url,timeout=timeout) as response:return response.read(1024*1024)
  def hydrate(params,local,cloud):
   active=lambda:not monitor.abortRequested() and not busy() and not art_busy() and ios_library.current_params(info())==params
   return hydrate_artwork(params,local,cloud,drivelibrary,state_dir,key,get,active)
  progress_path=xbmcvfs.translatePath('special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json')
  watch(info,busy,
        xbmc.executebuiltin,monitor.waitForAbort,ios_library,drivelibrary,
        state_dir,hydrate=hydrate,art_busy=art_busy,progress_signature=lambda:progress_stamp(progress_path))
 except Exception as error:xbmc.log('Kodi iOS Library refresh unavailable: '+type(error).__name__,xbmc.LOGWARNING)

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc,diagnostics;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,diagnostics.error_text(error)),xbmc.LOGWARNING)
 except Exception:pass
