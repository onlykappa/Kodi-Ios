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
CHUNK=16*1024*1024  # a multiple of 256 KiB, as Drive requires
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

def checksum(path,keep_going=lambda:True):
 digest=hashlib.md5()
 with open(path,'rb') as source:
  while True:
   if not keep_going():raise Stop('Scan stopped; phone files kept')
   chunk=source.read(1024*1024)
   if not chunk:break
   digest.update(chunk)
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
 def upload(self,path,parent,sessions,save,keep_going=lambda:True,progress=lambda done,total:None):
  """Resumable upload; sessions[path] survives a restart. Returns the Drive file's metadata."""
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
                              json.dumps({'name':os.path.basename(path),'parents':[parent]}).encode(),
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
 def _done(self,path,sessions,save,body):
  sessions.pop(path,None);save()
  return json.loads(body or b'{}')

def _next_offset(headers):
 value=headers.get('Range') or headers.get('range') or ''
 return int(value.rsplit('-',1)[1])+1 if '-' in value else 0

def run_once(root,drive,state_path,log,keep_going=lambda:True,delete_after=True,on_uploaded=lambda:None,seeding=(),drop=None):
 """Uploads every finished video once; returns the number uploaded. `seeding` adds finished torrents still in
 Elementum's folder ((path, folders, torrent id)); once all of a torrent's videos are on Drive and verified, `drop`
 removes the torrent and its files through Elementum."""
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
  if tid is not None and known and known.get('fp')==list(before):
   # Already on Drive and verified (its torrent could not be dropped yet, or a sibling failed): never upload twice.
   torrent_ok.setdefault(tid,set()).add(path)
   if torrent_ok[tid]>=torrent_files.get(tid,set()) and drop:
    try:drop(tid);log('Removed the finished torrent from the phone (Google Drive has it)')
    except Exception as error:log('Elementum could not remove the finished torrent: %s'%type(error).__name__)
   continue
  # What is uploading now, for the notification center's Uploading card (notices.uploads).
  def progress(done,total,name=os.path.basename(path),folder=' › '.join(['Drive']+list(parts))):
   state['current']={'name':name,'folder':folder,'sent':done,'total':total};save()
  try:meta=drive.upload(path,drive.folder(parts),sessions,save,keep_going,progress)
  finally:
   if state.pop('current',None) is not None:save()
  if int(meta.get('size',-1))!=os.path.getsize(path):
   log('Drive upload size differs for %s; the phone copy is kept'%os.path.basename(path));continue
  count+=1;log('Uploaded %s to Google Drive › %s'%(os.path.basename(path),' › '.join(parts)))
  on_uploaded()  # each file, even when a later transfer fails or is interrupted
  if delete_after:
   digest=checksum(path,keep_going)
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
   while os.path.basename(folder) not in ('Movies','TV Shows') and not os.listdir(folder):os.rmdir(folder);folder=os.path.dirname(folder)
 return count

def sender(context,timeout=120):
 """HTTP for Drive with the given TLS context; returns (status, headers, body) without following redirects."""
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context))
 def send(method,url,body,headers):
  request=urllib.request.Request(url,data=body,headers=dict(headers,**{'User-Agent':'Kodi iOS Drive upload'}),method=method)
  try:
   with opener.open(request,timeout=timeout) as r:return r.status,dict(r.headers),r.read()
  except urllib.error.HTTPError as e:return e.code,dict(e.headers or {}),e.read()
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
