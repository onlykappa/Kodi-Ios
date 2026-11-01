"""Uploads the Elementum videos the owner chose to keep (Documents/Kodi Downloads/Movies and TV Shows) to Google
Drive › Kodi Downloads › Movies / TV Shows, resuming interrupted uploads, then removes the phone copy once Drive
reports the same size. Uses the Google Drive add-on's sign-in, which needs the drive.file permission (the sign-in
server deployed by .github/workflows/signin-server.yml); drive.file only reaches files this app created."""
import json,os,time,urllib.error,urllib.parse,urllib.request
API='https://www.googleapis.com/drive/v3/files'
UPLOAD='https://www.googleapis.com/upload/drive/v3/files'
FOLDER='application/vnd.google-apps.folder'
VIDEO=('.mkv','.mp4','.m4v','.avi','.mov','.webm','.ts','.srt')
CHUNK=16*1024*1024  # a multiple of 256 KiB, as Drive requires
TOP='Kodi Downloads'

class Stop(Exception):pass

def pending(root,settle=120,now=None):
 """(path, folders on Drive) for finished videos: untouched for `settle` seconds (Elementum moves them whole)."""
 now=now or time.time();found=[]
 for section in ('Movies','TV Shows'):
  base=os.path.join(root,section)
  for folder,_,files in os.walk(base):
   for name in sorted(files):
    path=os.path.join(folder,name)
    if not name.lower().endswith(VIDEO) or name.startswith('.'):continue
    try:info=os.stat(path)
    except OSError:continue
    if info.st_size and now-info.st_mtime>=settle:
     relative=os.path.relpath(folder,base)
     found.append((path,[TOP,section]+([] if relative=='.' else relative.split(os.sep))))
 return found

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
    found=json.loads(body).get('files',[]) if status==200 else []
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

def run_once(root,drive,state_path,log,keep_going=lambda:True,delete_after=True):
 """Uploads every finished video once; returns the number uploaded."""
 try:state=json.load(open(state_path))
 except Exception:state={}
 sessions=state.setdefault('sessions',{})
 def save():
  temp=state_path+'.tmp'
  with open(temp,'w') as f:json.dump(state,f)
  os.replace(temp,state_path)
 count=0
 for path,parts in pending(root):
  if not keep_going():break
  # What is uploading now, for the notification center's Uploading card (notices.uploads).
  def progress(done,total,name=os.path.basename(path),folder=' › '.join(['Drive']+list(parts))):
   state['current']={'name':name,'folder':folder,'sent':done,'total':total};save()
  try:meta=drive.upload(path,drive.folder(parts),sessions,save,keep_going,progress)
  finally:
   if state.pop('current',None) is not None:save()
  if int(meta.get('size',-1))!=os.path.getsize(path):
   log('Drive upload size differs for %s; the phone copy is kept'%os.path.basename(path));continue
  count+=1;log('Uploaded %s to Google Drive › %s'%(os.path.basename(path),' › '.join(parts)))
  if delete_after:
   os.remove(path);folder=os.path.dirname(path)
   while os.path.basename(folder) not in ('Movies','TV Shows') and not os.listdir(folder):os.rmdir(folder);folder=os.path.dirname(folder)
 return count

def sender(context):
 """HTTP for Drive with the given TLS context; returns (status, headers, body) without following redirects."""
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context))
 def send(method,url,body,headers):
  request=urllib.request.Request(url,data=body,headers=dict(headers,**{'User-Agent':'Kodi iOS Drive upload'}),method=method)
  try:
   with opener.open(request,timeout=120) as r:return r.status,dict(r.headers),r.read()
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
