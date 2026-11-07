"""Uploads the Elementum videos the owner chose to keep (Documents/Kodi Downloads/Movies and TV Shows) to Google
Drive › Kodi Downloads › Movies / TV Shows, resuming interrupted uploads, then removes the phone copy once Drive
reports the same size and checksum. Uses the Google Drive add-on's sign-in, which needs the drive.file permission (the sign-in
server deployed by .github/workflows/signin-server.yml); drive.file only reaches files this app created."""
import contextlib,fcntl,hashlib,json,os,re,time,urllib.error,urllib.parse,urllib.request
API='https://www.googleapis.com/drive/v3/files'
UPLOAD='https://www.googleapis.com/upload/drive/v3/files'
FOLDER='application/vnd.google-apps.folder'
VIDEO=('.mkv','.mp4','.m4v','.avi','.mov','.webm','.ts','.m2ts','.mts','.wmv','.mpg','.mpeg','.srt')
PARTIAL=re.compile(r'(?:^|[._ -])(?:sample|partial|incomplete|downloading)(?:[._ -]|$)|\.(?:part|tmp|download)(?:\.|$)',re.I)
CHUNK=32*1024*1024  # a multiple of 256 KiB, as Drive requires (build 181: 32 MB, less time lost between pieces)
TOP='Kodi Downloads'

class Stop(Exception):pass

@contextlib.contextmanager
def transfer_lock(state_dir):
 """The automatic uploader and manual scan must not upload/delete the same phone file concurrently."""
 os.makedirs(state_dir,exist_ok=True)
 with open(os.path.join(state_dir,'drive-transfer.lock'),'a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise Stop('A Drive transfer is already running')
  try:yield
  finally:fcntl.flock(lock,fcntl.LOCK_UN)

def fingerprint(path):
 stat=os.stat(path,follow_symlinks=False)
 return (stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)

def checksum(path,keep_going=lambda:True,pace=0,clock=time.monotonic,sleep=time.sleep):
 """MD5 of a file. pace>0 rests pace x the time each megabyte took (pace 1: half of one core at most). The
 background uploader paces: iOS ended Kodi for 91% CPU over 53 s in the background (owner report, build 142), and
 a 9.5 GB 2160p file takes many seconds to read."""
 digest=hashlib.md5()
 with open(path,'rb') as source:
  while True:
   if not keep_going():raise Stop('Scan stopped; phone files kept')
   started=clock()
   chunk=source.read(1024*1024)
   if not chunk:break
   digest.update(chunk)
   if pace:sleep(max(0.0,clock()-started)*pace)
 return digest.hexdigest()

def confirmed(drive,item_id,size,digest):
 if not item_id:return False
 status,_,body=drive.call('GET',API+'/'+urllib.parse.quote(str(item_id),safe='')+'?fields=id,size,md5Checksum,trashed')
 if status!=200:raise RuntimeError('Drive verification: HTTP %s'%status)
 meta=json.loads(body)
 return not meta.get('trashed',False) and int(meta.get('size',-1))==size and meta.get('md5Checksum','').lower()==digest.lower()

def invalidate_library(state_dir):
 try:os.remove(os.path.join(state_dir,'drive-library.json'))
 except FileNotFoundError:pass
 # Both automatic and manual uploads ask the idle preparation worker for a fresh scan.
 os.makedirs(state_dir,exist_ok=True)
 with open(os.path.join(state_dir,'airplay-preparation-rescan'),'a'):pass

def pending(root,settle=120,now=None):
 """(path, folders on Drive) for finished videos: untouched for `settle` seconds (Elementum moves them whole)."""
 now=now or time.time();found=[]
 for section in ('Movies','TV Shows'):
  base=os.path.join(root,section)
  if os.path.islink(base):continue
  for folder,dirs,files in os.walk(base):
   dirs[:]=[d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(folder,d))]
   for name in sorted(files):
    path=os.path.join(folder,name)
    if not name.lower().endswith(VIDEO) or name.startswith('.') or PARTIAL.search(name) or os.path.islink(path):continue
    try:info=os.stat(path)
    except OSError:continue
    if info.st_size and now-info.st_mtime>=settle:
     relative=os.path.relpath(folder,base)
     found.append((path,[TOP,section]+([] if relative=='.' else relative.split(os.sep))))
 return found

def drive_folders(path,root):
 """Drive › Kodi Downloads › Movies, or › TV Shows › <show> for an episode (SxxEyy / 1x02 in the name)."""
 name=os.path.basename(path)
 m=re.search(r'(?i)\bS(\d{1,2})[ ._-]?E(\d{1,3})\b',name) or re.search(r'\b(\d{1,2})x(\d{2,3})\b',name)
 if not m:return [TOP,'Movies']
 show=re.split(r'(?i)[ ._-]+(?:S\d{1,2}[ ._-]?E\d|\d{1,2}x\d{2}|season[ ._-]*\d)',name)[0]
 if not show.strip(' ._-'):  # "S01E02.mkv" inside a show folder
  parts=os.path.relpath(os.path.dirname(path),root).split(os.sep)
  show=parts[0] if parts and parts[0]!='.' else ''
  show=re.split(r'(?i)[ ._-]+(?:S\d{1,2}|season)',show)[0]
 show=re.sub(r'[._]+',' ',show).strip() or 'Episodes'
 return [TOP,'TV Shows',show]

def seeding_pending(root,torrents):
 """[(path, Drive folders, torrent id)] for videos of torrents Elementum reports 100% done that are still in its
 download folder. Owner (PR 8): Elementum moves a download to Kodi Downloads only after it stops seeding (up to a day
 or a 200% ratio), so season packs and many movies stayed on the phone and never reached Drive."""
 found=[]
 for torrent in torrents or []:
  try:done=float(torrent.get('progress') or 0)>=99.9
  except (TypeError,ValueError):done=False
  name=str(torrent.get('name') or '');tid=str(torrent.get('id') or '')
  if not done or not name or not tid or '/' in name or name in ('.','..'):continue
  base=os.path.join(root,name)
  if os.path.islink(base):continue
  if os.path.isfile(base):candidates=[base]
  else:
   candidates=[]
   for folder,dirs,files in os.walk(base):
    dirs[:]=[d for d in dirs if not d.startswith('.') and not os.path.islink(os.path.join(folder,d))]
    candidates+=[os.path.join(folder,f) for f in sorted(files)]
  for path in candidates:
   name_only=os.path.basename(path)
   if not name_only.lower().endswith(VIDEO) or name_only.startswith('.') or PARTIAL.search(name_only) or os.path.islink(path):continue
   try:
    if os.path.getsize(path)<=0:continue
   except OSError:continue
   parts=drive_folders(path,root)
   pack=re.match(r'(?i)(.+?)[ ._-]+(?:S\d{1,2}(?![ ._-]?E\d)|season[ ._-]*\d|complete)\b',name)
   if parts[1]=='Movies' and pack:  # season pack whose files have no SxxEyy ("01 - Pilot.mkv")
    parts=[TOP,'TV Shows',re.sub(r'[._]+',' ',pack.group(1)).strip()]
   found.append((path,parts,tid))
 return found

def remove_torrent(tid,get=None,engine='http://127.0.0.1:65220'):
 """Elementum drops the torrent and its files (it stops seeding a copy Drive now has)."""
 get=get or (lambda url:urllib.request.urlopen(url,timeout=15).read())
 get('%s/torrents/delete/%s?torrent=true&files=true&confirmation=true'%(engine,urllib.parse.quote(tid,safe='')))

class Drive(object):
 def __init__(self,token,send):
  self.token=token;self.send=send;self.folders={}
 def call(self,method,url,body=None,headers=None):
  headers=dict(headers or {});headers['Authorization']='Bearer '+self.token()
  return self.send(method,url,body,headers)
 def folder(self,parts):
  parent='root'
  for depth in range(len(parts)):
   key='/'.join(parts[:depth+1])
   if key not in self.folders:
    name=parts[depth].replace('\\','\\\\').replace("'","\\'")
    q="name='%s' and mimeType='%s' and '%s' in parents and trashed=false"%(name,FOLDER,parent)
    status,_,body=self.call('GET',API+'?'+urllib.parse.urlencode({'q':q,'fields':'files(id)','spaces':'drive'}))
    if status!=200:raise RuntimeError('Drive folder lookup: HTTP %s'%status)
    found=json.loads(body).get('files',[])
    if found:self.folders[key]=found[0]['id']
    else:
     status,_,body=self.call('POST',API+'?fields=id',json.dumps({'name':parts[depth],'mimeType':FOLDER,'parents':[parent]}).encode(),{'Content-Type':'application/json'})
     if status not in (200,201):raise RuntimeError('Drive folder %s: HTTP %s'%(key,status))
     self.folders[key]=json.loads(body)['id']
   parent=self.folders[key]
  return parent
 def upload(self,path,parent,sessions,save,keep_going=lambda:True,progress=lambda done,total:None,name=None):
  """Resumable upload; sessions[path] survives a restart. Returns the Drive file's metadata. name: the Drive file's
  name when it is not the local file's."""
  size=os.path.getsize(path);session=sessions.get(path)
  if session and session.get('size')!=size:session=None
  offset=0
  if session:
   status,headers,_=self.call('PUT',session['url'],b'',{'Content-Range':'bytes */%d'%size})
   if status in (200,201):return self._done(path,sessions,save,self.call('GET',session['url'])[2])
   if status==308:offset=_next_offset(headers)
   else:session=None
  if not session:
   status,headers,_=self.call('POST',UPLOAD+'?uploadType=resumable&fields=id,size',
                              json.dumps({'name':name or os.path.basename(path),'parents':[parent]}).encode(),
                              {'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Length':str(size)})
   location=headers.get('Location') or headers.get('location')
   if status!=200 or not location:raise RuntimeError('Drive upload start: HTTP %s'%status)
   session={'url':location,'size':size};sessions[path]=session;save();offset=0
  with open(path,'rb') as f:
   while offset<size:
    if not keep_going():raise Stop()
    f.seek(offset);chunk=f.read(CHUNK);end=offset+len(chunk)-1
    status,headers,body=self.call('PUT',session['url'],chunk,{'Content-Range':'bytes %d-%d/%d'%(offset,end,size)})
    if status in (200,201):return self._done(path,sessions,save,body)
    if status!=308:raise RuntimeError('Drive upload: HTTP %s'%status)
    offset=_next_offset(headers);progress(offset,size)
  raise RuntimeError('Drive did not confirm the upload')
 def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda done,total:None):
  """Resumable upload of a web file straight into Drive, CHUNK at a time: nothing is written to the phone (owner,
  build 160: AllDebrid straight to Drive). open_at(offset) -> a readable response from that byte on. `session` is a
  dict kept by the caller ({'url','size'}) so a restart carries on where Drive got to. Returns the Drive file."""
  offset=0
  if session.get('url') and session.get('size')==size:
   status,headers,body=self.call('PUT',session['url'],b'',{'Content-Range':'bytes */%d'%size})
   if status in (200,201):return json.loads(body or b'{}')
   if status==308:offset=_next_offset(headers)
   else:session.clear()
  if not session.get('url'):
   status,headers,_=self.call('POST',UPLOAD+'?uploadType=resumable&fields=id,size,md5Checksum',
                              json.dumps({'name':name,'parents':[parent]}).encode(),
                              {'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Length':str(size)})
   location=headers.get('Location') or headers.get('location')
   if status!=200 or not location:raise RuntimeError('Drive upload start: HTTP %s'%status)
   session.clear();session.update(url=location,size=size);save();offset=0
  import concurrent.futures
  source=[open_at(offset)]
  def read(at):
   chunk=b'';began=time.monotonic()
   while len(chunk)<CHUNK and at+len(chunk)<size:
    data=source[0].read(min(CHUNK-len(chunk),1024*1024))
    if not data:break
    chunk+=data
   return chunk,time.monotonic()-began
  # Build 181 (owner: "whatever that will make uploading and downloading quicker"): the next piece downloads from
  # the source while this one goes up to Drive (they used to take turns).
  ahead=concurrent.futures.ThreadPoolExecutor(max_workers=1);coming=None
  try:
   while offset<size:
    if not keep_going():raise Stop()
    if coming is not None:chunk,read_s=coming.result();coming=None
    else:chunk,read_s=read(offset)
    if not chunk:raise RuntimeError('The download stopped before the end; it will carry on')
    end=offset+len(chunk)-1;began=time.monotonic()
    if end+1<size:coming=ahead.submit(read,end+1)
    status,headers,body=self.call('PUT',session['url'],chunk,{'Content-Range':'bytes %d-%d/%d'%(offset,end,size)})
    # Owner (build 168): 0.2 MB/s. Which side is slow, the source (AllDebrid) or Google Drive, for the next log.
    put_s=time.monotonic()-began;mb=len(chunk)/1048576.0
    _note('Drive copy: %.1f MB read in %.1f s (%.2f MB/s from the source), sent in %.1f s (%.2f MB/s to Google Drive), %.1f%% done'%(
     mb,read_s,mb/max(read_s,.001),put_s,mb/max(put_s,.001),100.0*(end+1)/size))
    if status in (200,201):progress(size,size);return json.loads(body or b'{}')
    if status!=308:raise RuntimeError('Drive upload: HTTP %s'%status)
    confirmed=_next_offset(headers)
    if confirmed!=end+1:   # Drive kept less than sent: drop what was read ahead and read again from where it got to
     if coming is not None:
      try:coming.result()
      except Exception:pass
      coming=None
     try:source[0].close()
     except Exception:pass
     source[0]=open_at(confirmed)
    offset=confirmed;save();progress(offset,size)
  finally:
   if coming is not None:
    try:coming.result()
    except Exception:pass
   ahead.shutdown(wait=False)
   try:source[0].close()
   except Exception:pass
  raise RuntimeError('Drive did not confirm the upload')
 def _done(self,path,sessions,save,body):
  sessions.pop(path,None);save()
  return json.loads(body or b'{}')

def _note(message):
 try:
  import xbmc;xbmc.log('Kodi iOS '+message,xbmc.LOGINFO)
 except Exception:pass

def _next_offset(headers):
 value=headers.get('Range') or headers.get('range') or ''
 return int(value.rsplit('-',1)[1])+1 if '-' in value else 0

def run_once(root,drive,state_path,log,keep_going=lambda:True,delete_after=True,on_uploaded=lambda:None,seeding=(),drop=None,
             remote=None,pace=0,notify=lambda title,text:None):
 """Uploads every finished video once; returns the number uploaded. `seeding` adds finished torrents still in
 Elementum's folder ((path, folders, torrent id)); once all of a torrent's videos are on Drive and verified, `drop`
 removes the torrent and its files through Elementum.

 `remote()` lists the videos already in Drive › Kodi Downloads (library_scan.remote_files). A phone video whose exact
 bytes (size + MD5, confirmed with fresh Drive metadata) are already there is not uploaded again; its phone copy is
 removed under the same rules as an upload (owner, build 145: phone duplicates of Drive videos stayed on the phone)."""
 import drivelibrary   # here, not at the top: tests load this module on its own
 index=[None]
 def listing():
  if remote is None:return []
  if index[0] is None:
   try:index[0]=list(remote())
   except Exception as error:
    log('Drive listing for duplicates failed (%s); uploading as usual'%type(error).__name__);index[0]=[]
  return index[0]
 def already_on_drive(size,digest):
  if remote is None:return None
  for item in listing():
   if int(item.get('size') or 0)!=size:continue
   listed=(item.get('md5Checksum') or '').lower()
   if listed and listed!=digest:continue
   if not keep_going():raise Stop()
   if confirmed(drive,item.get('id'),size,digest):return item
  return None
 try:
  with open(state_path,encoding='utf-8') as source:state=json.load(source)
 except Exception:state={}
 sessions=state.setdefault('sessions',{})
 def save():
  temp=state_path+'.tmp'
  with open(temp,'w') as f:json.dump(state,f)
  os.replace(temp,state_path)
 count=0;torrent_files={};torrent_ok={}
 for path,parts,tid in seeding:torrent_files.setdefault(tid,set()).add(path)
 work=[(p,parts,None) for p,parts in pending(root)]+list(seeding)
 done_before=state.setdefault('verified',{})
 for path,parts,tid in work:
  if not keep_going():break
  before=fingerprint(path)
  known=done_before.get(path)
  if tid is None and known and known.get('fp')==list(before):continue  # on Drive already; phone copy kept by setting
  if tid is not None and known and known.get('fp')==list(before):
   # Already on Drive and verified (its torrent could not be dropped yet, or a sibling failed): never upload twice.
   torrent_ok.setdefault(tid,set()).add(path)
   if torrent_ok[tid]>=torrent_files.get(tid,set()) and drop:
    try:drop(tid);log('Removed the finished torrent from the phone (Google Drive has it)')
    except Exception as error:log('Elementum could not remove the finished torrent: %s'%type(error).__name__)
   continue
  digest=None;duplicate=None
  # Another release of the same episode or movie already on Drive, at least as good (owner, build 152: two
  # 'Lanterns' folders each held S1 E1). Checked before any upload; this copy stays where it is.
  better=drivelibrary.better_on_drive(path,listing()) if remote is not None else None
  noted=state.setdefault('same_media',{})
  if better is not None and noted.get(path)==list(before):continue   # already reported; nothing to re-check
  if remote is not None:
   digest=checksum(path,keep_going,pace)
   if fingerprint(path)!=before:continue  # still changing: next pass
   duplicate=already_on_drive(before[2],digest)
  if duplicate is None and better is not None:
   where=better.get('folderName') or 'Kodi Downloads';title=drivelibrary.display_title(os.path.basename(path))
   # The owner's rule: the extra copy is deleted. Only with the remove-phone-copies setting on, and only once the
   # Drive copy is confirmed to still be there with its listed size and checksum.
   if delete_after and better.get('md5Checksum') and confirmed(drive,better.get('id'),int(better.get('size') or 0),better['md5Checksum'].lower()):
    if fingerprint(path)!=before:continue
    log('%s: Google Drive already has it in “%s” (%s); removing this copy'%(os.path.basename(path),where,better.get('name','')))
    if tid is not None:
     # A seeding torrent's files belong to Elementum: count this file as on Drive and drop the torrent once all are.
     done_before[path]={'fp':list(before),'id':better.get('id')};save()
     torrent_ok.setdefault(tid,set()).add(path)
     if torrent_ok[tid]>=torrent_files.get(tid,set()) and drop:
      try:drop(tid);log('Removed the finished torrent from the phone (Google Drive has it)')
      except Exception as error:log('Elementum could not remove the finished torrent: %s'%type(error).__name__)
    else:
     os.remove(path);folder=os.path.dirname(path)
     while os.path.basename(folder) not in ('Movies','TV Shows') and not os.listdir(folder):os.rmdir(folder);folder=os.path.dirname(folder)
    notify('Duplicate removed from the phone','%s is already in “%s” on Google Drive, so this copy was removed.'%(title,where))
    continue
   noted[path]=list(before);save()
   log('%s: Google Drive already has it in “%s” (%s); not uploaded'%(os.path.basename(path),where,better.get('name','')))
   notify('Already on Google Drive','%s is already in “%s”, so this copy was not uploaded. It stays on the phone.'%(title,where))
   continue
  if duplicate is not None:
   meta=dict(duplicate,size=before[2])
   log('%s is already on Google Drive (same size and checksum); not uploaded again'%os.path.basename(path))
  else:
   if remote is not None:parts=drivelibrary.show_folder(drive,parts)   # the show's existing folder, never a second one
   # What is uploading now, for the notification center's Uploading card (notices.uploads).
   def progress(done,total,name=os.path.basename(path),folder=' › '.join(['Drive']+list(parts))):
    state['current']={'name':name,'folder':folder,'sent':done,'total':total};save()
   try:meta=drive.upload(path,drive.folder(parts),sessions,save,keep_going,progress)
   finally:
    if state.pop('current',None) is not None:save()
   if int(meta.get('size',-1))!=os.path.getsize(path):
    log('Drive upload size differs for %s; the phone copy is kept'%os.path.basename(path));continue
   count+=1;log('Uploaded %s to Google Drive › %s'%(os.path.basename(path),' › '.join(parts)))
   if remote is not None and digest and confirmed(drive,meta.get('id'),before[2],digest):
    # This copy is better than what Drive had for the same episode/movie: the old one goes to Drive's Trash.
    gone=drivelibrary.trash_worse(drive,os.path.basename(path),os.path.basename(os.path.dirname(path)),listing(),meta.get('id'))
    if gone:notify('Duplicate removed from Google Drive','%s: uploaded a better copy; moved the older one in %s to Drive’s Trash.'%(
     drivelibrary.display_title(os.path.basename(path)),', '.join('“%s”'%g for g in gone)))
   if index[0] is not None and digest:index[0].append(dict(meta,size=before[2],md5Checksum=digest))
   on_uploaded()  # each file, even when a later transfer fails or is interrupted
  if not delete_after:
   if tid is None:done_before[path]={'fp':list(before),'id':meta.get('id')};save()
   continue
  if delete_after:
   if digest is None or fingerprint(path)!=before:digest=checksum(path,keep_going,pace)
   if fingerprint(path)!=before or not confirmed(drive,meta.get('id'),before[2],digest):
    log('Drive checksum could not be verified; the phone copy is kept');continue
   if tid is not None:
    # A seeding torrent's files belong to Elementum: drop the whole torrent once every video of it is verified.
    done_before[path]={'fp':list(before),'id':meta.get('id')};save()
    torrent_ok.setdefault(tid,set()).add(path)
    if torrent_ok[tid]>=torrent_files.get(tid,set()) and drop:
     try:drop(tid);log('Removed the finished torrent from the phone (Google Drive has it)')
     except Exception as error:log('Elementum could not remove the finished torrent: %s'%type(error).__name__)
    continue
   if not keep_going():raise Stop()
   if fingerprint(path)!=before:continue
   os.remove(path);folder=os.path.dirname(path)
   log('Removed the phone copy of %s (Google Drive has it)'%os.path.basename(path))
   if duplicate is not None:on_uploaded()  # the Library lists it from Drive now
   while os.path.basename(folder) not in ('Movies','TV Shows') and not os.listdir(folder):os.rmdir(folder);folder=os.path.dirname(folder)
 return count

# Build-184 log: a 32 MB piece hung with no progress for 120 s ("The write operation timed out") and only then was
# retried. The socket timeout is per send/receive, so 45 s means 45 s with nothing moving; the piece is then retried
# on a new connection (the resumable session asks Drive what it kept first).
STALL=45
def sender(context,timeout=STALL,log=lambda message:None):
 """HTTP for Drive with the given TLS context; returns (status, headers, body) without following redirects."""
 import diagnostics
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context))
 def send(method,url,body,headers):
  request=urllib.request.Request(url,data=body,headers=dict(headers,**{'User-Agent':'Kodi iOS Drive upload'}),method=method)
  safe=method in ('GET','HEAD','DELETE')
  for attempt in range(3 if safe else 1):
   begun=time.monotonic()
   fields=dict(method=method,host=urllib.parse.urlsplit(url).hostname,attempt=attempt+1,request_bytes=len(body) if body else 0)
   try:
    with opener.open(request,timeout=min(timeout,30) if safe else timeout) as r:
     answer=r.read();elapsed=round(time.monotonic()-begun,3)
     if elapsed>=10 or (body and len(body)>=256*1024):diagnostics.event(log,'drive_http','response',status=r.status,elapsed_s=elapsed,response_bytes=len(answer),**fields)
     return r.status,dict(r.headers),answer
   except urllib.error.HTTPError as e:
    diagnostics.event(log,'drive_http','http_error',status=e.code,elapsed_s=round(time.monotonic()-begun,3),retry=safe and e.code in (429,500,502,503,504) and attempt<2,**fields)
    if not safe or e.code not in (429,500,502,503,504) or attempt==2:return e.code,dict(e.headers or {}),e.read()
    e.close()
   except (urllib.error.URLError,TimeoutError) as e:
    diagnostics.exception(log,'drive_http',e,elapsed_s=round(time.monotonic()-begun,3),retry=safe and attempt<2 and 'CERTIFICATE_VERIFY_FAILED' not in str(e),**fields)
    if not safe or attempt==2 or 'CERTIFICATE_VERIFY_FAILED' in str(e):raise
   time.sleep(.5*2**attempt)
 return send

def token_source(accounts,save_account,refresh,now=time.time):
 """Access token from the Google Drive add-on's first signed-in account, refreshed through the sign-in server."""
 def token():
  account=next(iter(accounts().values()),None)
  if not account:raise RuntimeError('Sign in to Google Drive in Kodi first')
  tokens=account['access_tokens']
  if now()>tokens.get('date',0)+tokens.get('expires_in',0)-600:
   fresh=refresh(tokens['refresh_token']);fresh['date']=now()
   tokens.update(fresh);account['access_tokens']=tokens;save_account(account)
  return tokens['access_token']
 return token
