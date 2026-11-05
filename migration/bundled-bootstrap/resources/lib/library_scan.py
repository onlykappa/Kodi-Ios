"""Reconcile completed phone videos with Drive; only remove an unchanged, checksum-verified phone duplicate.

The scan is explicit, restricted to selected accessible folders, and shares the uploader's process lock. No
credential, release URL or absolute source path is written into user-visible errors or logs.
"""
import json,os,re,stat,time
import driveupload,drivelibrary

PARTIAL=re.compile(r'(?:^|[._ -])(?:sample|partial|incomplete|downloading)(?:[._ -]|$)|\.(?:part|tmp|download)(?:\.|$)',re.I)
IGNORE={'userdata','addons','packages','temp','cache','thumbnails'}

def within(path,root):
 try:return os.path.commonpath([os.path.realpath(path),os.path.realpath(root)])==os.path.realpath(root)
 except ValueError:return False

def discover(roots,excluded=(),now=time.time,settle=120,keep_going=lambda:True):
 """Walk selected local folders, never active downloads, app data, symlinks or files still being written."""
 found=set();excluded=[os.path.abspath(p) for p in excluded if p]
 for base in roots:
  if not keep_going():raise driveupload.Stop()
  base=os.path.abspath(base)
  if os.path.islink(base) or not os.path.isdir(base) or any(within(base,p) for p in excluded):continue
  def onerror(error):raise error
  for folder,dirs,files in os.walk(base,followlinks=False,onerror=onerror):
   if not keep_going():raise driveupload.Stop()
   dirs[:]=[name for name in dirs if not name.startswith('.') and name.casefold() not in IGNORE
            and not os.path.islink(os.path.join(folder,name)) and not any(within(os.path.join(folder,name),p) for p in excluded)]
   for name in files:
    if not keep_going():raise driveupload.Stop()
    path=os.path.join(folder,name)
    if name.startswith('.') or PARTIAL.search(name) or not drivelibrary.is_video(name) or os.path.islink(path):continue
    try:info=os.stat(path,follow_symlinks=False)
    except FileNotFoundError:continue
    if stat.S_ISREG(info.st_mode) and info.st_size>0 and now()-info.st_mtime>=settle:found.add(path)
 return sorted(found)

def remote_files(drive,keep_going=lambda:True):
 """Exhaustively index app-created Kodi Downloads movies and episodes; do not assume one release-folder shape."""
 out=[];seen=set();stack=[]
 for section in ('Movies','TV Shows'):
  if not keep_going():raise driveupload.Stop()
  stack.extend(drivelibrary.find_folders(drive,[drivelibrary.TOP,section],strict=True))
 while stack:
  if not keep_going():raise driveupload.Stop()
  folder=stack.pop()
  if folder in seen:continue
  seen.add(folder)
  for item in drivelibrary.children(drive,folder):
   if item.get('mimeType')==drivelibrary.FOLDER:stack.append(item['id'])
   elif drivelibrary.is_video(item.get('name','')) and int(item.get('size') or 0)>0:out.append(item)
 return out

def destination(path):
 info=drivelibrary.parse(os.path.basename(path))
 if info['season']:
  title=info['title']
  if title.casefold()=='episode' or re.match(r'^(?:s\d+[ ._-]*e\d+|\d+x\d+)',title,re.I):
   for parent in reversed(os.path.dirname(path).split(os.sep)):
    if not parent or parent in ('TV Shows','Kodi Downloads'):break
    if re.match(r'^(?:season\b|s\d+\b)',parent,re.I):continue
    title=drivelibrary.parse(parent)['title'];break
  return [drivelibrary.TOP,'TV Shows',title or 'Episodes']
 return [drivelibrary.TOP,'Movies']

def scan(paths,drive,state_dir,keep_going=lambda:True,progress=lambda stage,index,total:None,remote=None):
 """Caller holds transfer_lock. Returns counts, retaining originals on failed or cancelled work.

Duplicate means identical bytes (size + MD5), even if the filename differs. Name/size alone never permits deletion.
"""
 os.makedirs(state_dir,exist_ok=True)
 state_path=os.path.join(state_dir,'library-scan.json');state=drivelibrary.load_json(state_path,{})
 sessions=state.setdefault('sessions',{});digests=state.setdefault('digests',{})
 def save():drivelibrary.save_json(state_path,state)
 candidates=remote_files(drive,keep_going) if remote is None else list(remote)
 result={'uploaded':0,'duplicates':0,'deleted':0,'kept':0,'failed':0,'cancelled':False}
 for index,path in enumerate(paths):
  if not keep_going():result['cancelled']=True;break
  try:
   progress('Checking',index,len(paths))
   if os.path.islink(path) or not stat.S_ISREG(os.stat(path,follow_symlinks=False).st_mode):
    result['kept']+=1;continue
   before=driveupload.fingerprint(path)
   if before[2]<=0:result['kept']+=1;continue
   digest=driveupload.checksum(path,keep_going)
   if driveupload.fingerprint(path)!=before:result['kept']+=1;continue
   item=None
   for candidate in candidates:
    if int(candidate.get('size') or 0)!=before[2]:continue
    # Listing checksums are an optimization; authorization to delete always comes from fresh file metadata.
    listed=candidate.get('md5Checksum','').lower()
    if listed and listed!=digest:continue
    if not keep_going():raise driveupload.Stop()
    if driveupload.confirmed(drive,candidate.get('id'),before[2],digest):item=candidate;break
   if item is None:
    progress('Uploading',index,len(paths))
    if digests.get(path)!=digest:sessions.pop(path,None)
    digests[path]=digest;save()
    item=drive.upload(path,drive.folder(destination(path)),sessions,save,keep_going,
                      lambda done,total:progress('Uploading',index,len(paths)))
    result['uploaded']+=1
   else:result['duplicates']+=1
   # Re-read the source after any lengthy upload and compare current remote metadata before deletion.
   progress('Verifying',index,len(paths))
   if not keep_going():raise driveupload.Stop()
   if os.path.islink(path) or driveupload.fingerprint(path)!=before or driveupload.checksum(path,keep_going)!=digest:
    result['kept']+=1;continue
   if not driveupload.confirmed(drive,item.get('id'),before[2],digest):result['kept']+=1;continue
   if not keep_going():raise driveupload.Stop()
   if os.path.islink(path) or driveupload.fingerprint(path)!=before:result['kept']+=1;continue
   driveupload.invalidate_library(state_dir)
   digests.pop(path,None);sessions.pop(path,None);save()
   os.remove(path);result['deleted']+=1
   candidates.append(dict(item,size=before[2],md5Checksum=digest))
  except driveupload.Stop:
   result['cancelled']=True;break
  except (OSError,RuntimeError,ValueError,KeyError):
   result['failed']+=1;result['kept']+=1
 result['kept']=len(paths)-result['deleted']
 progress('Finished',len(paths),len(paths))
 return result

def run():
 import sys,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 from pathlib import Path
 home=xbmcvfs.translatePath('special://home/')
 documents=next((p for p in (Path(home),*Path(home).parents) if p.name=='Documents'),Path(home).parent)
 choice=xbmcgui.Dialog().select('Scan iPhone files',['Kodi Downloads','Choose another accessible folder'])
 if choice<0:return
 selected=str(documents/'Kodi Downloads')
 if choice==1:
  selected=xbmcgui.Dialog().browseSingle(0,'Folder to scan for movies and shows','files',defaultt=str(documents))
  if not selected:return
  selected=xbmcvfs.translatePath(selected)
  if not os.path.isabs(selected) or '://' in selected:
   xbmcgui.Dialog().ok('Library','Choose a local folder available to Kodi.');return
 monitor=xbmc.Monitor();dialog=xbmcgui.DialogProgress()
 dialog.create('Library scan','Checking completed videos. Verified Drive copies will be removed from this folder.')
 keep=lambda:not monitor.abortRequested() and not dialog.iscanceled() and not xbmc.Player().isPlayingVideo()
 state_dir=xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')
 try:
  addon=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.kodi.ios.watch').getAddonInfo('path'))
  lib=os.path.join(addon,'resources','lib')
  if lib not in sys.path:sys.path.append(lib)
  import ios_downloaded
  configured=ios_downloaded.folders();active=[p for p in configured[2:] if p]
  # An active torrent folder can contain full-sized preallocated media; never treat its bytes as complete.
  # Saved settings may point at an older installation; also exclude this sandbox's active torrent folder.
  excluded=active+[str(documents/'Elementum Downloads')]+([home] if choice==1 else [])
  roots=[selected]
  if choice==0:
   roots=[p for p in configured[:2]+ios_downloaded.default_completed_folder('movie')+ios_downloaded.default_completed_folder('tv') if p]
  with driveupload.transfer_lock(state_dir):
   paths=discover(roots,excluded,keep_going=keep)
   if not keep():return
   drive,_=drivelibrary.client()
   if not drive:
    xbmcgui.Dialog().ok('Library','Sign in to Google Drive from Settings › Accounts, then scan again.');return
   result=scan(paths,drive,state_dir,keep,lambda stage,index,total:dialog.update(int(index*100/max(1,total)),stage+' videos…'))
  status='Scan stopped' if result['cancelled'] else 'Scan finished'
  message='%d uploaded, %d duplicates checked, %d phone copies removed, %d kept.'%(
           result['uploaded'],result['duplicates'],result['deleted'],result['kept'])
  if result['failed']:message+=' %d files could not be checked; their phone copies were kept.'%result['failed']
  dialog.close();xbmcgui.Dialog().ok(status,message)
  if result['deleted'] or result['uploaded']:xbmc.executebuiltin('Container.Refresh')
 except driveupload.Stop:
  stopped=not keep();dialog.close()
  xbmcgui.Dialog().ok('Library','Scan stopped. Unverified phone files were kept.' if stopped else 'Another Drive transfer is running. Try the scan when it finishes.')
 except Exception as error:
  xbmc.log('Kodi iOS Library scan failed: '+type(error).__name__,xbmc.LOGWARNING)
  dialog.close();xbmcgui.Dialog().ok('Library','The scan could not finish. Unverified phone files were kept. Check your Drive connection and try again.')
 finally:dialog.close()
