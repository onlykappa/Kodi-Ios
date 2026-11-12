"""Keep only a validated MP4 mfra index, bound to live Drive metadata. No movie payload or credentials on disk."""
import base64,hashlib,json,os,re,struct,tempfile,threading,time
from pathlib import Path

MAX_INDEX=2*1024*1024
MAX_TOTAL=8*1024*1024
MAX_ENTRIES=64
MAX_JSON=12*1024*1024
FILE='drive-fragment-indices.json'

def identity(item,file_id):
 try:
  size=int(item.get('size') or 0);md5=str(item.get('md5Checksum') or '').lower()
  if item.get('id')!=file_id or size<40 or not re.fullmatch(r'[0-9a-f]{32}',md5):return None
  meta={key:str(item.get(key) or '') for key in ('id','md5Checksum','version','modifiedTime','mimeType')}
  meta.update(size=size,md5Checksum=md5)
  key=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()
  return key,meta
 except (AttributeError,TypeError,ValueError):return None

def bounds(rng,size):
 match=re.fullmatch(r'bytes=(\d*)-(\d*)',rng or '')
 if not match or not any(match.groups()):return None
 try:
  first,last=match.groups()
  if first:
   start=int(first);end=min(int(last),size-1) if last else size-1
  else:start=max(0,size-int(last));end=size-1
  return (start,end) if 0<=start<=end<size else None
 except ValueError:return None

def valid(data,size):
 """Bounded complete mfra/mfro and tfra table checks; never persist adjacent video bytes."""
 if not 40<=len(data)<=MAX_INDEX or len(data)>=size:return False
 if data[:8]!=struct.pack('>I4s',len(data),b'mfra'):return False
 if data[-16:]!=struct.pack('>I4sII',16,b'mfro',0,len(data)):return False
 at=8;found=False;end=len(data)-16
 while at<end:
  if at+8>end:return False
  length,kind=struct.unpack_from('>I4s',data,at)
  if length<8 or at+length>end:return False
  if kind==b'tfra':
   if length<24:return False
   version=data[at+8];track,flags,count=struct.unpack_from('>III',data,at+12)
   if version not in (0,1) or not track or not count:return False
   width=8 if version else 4;stride=2*width+sum(((flags>>shift)&3)+1 for shift in (4,2,0))
   if 24+count*stride!=length:return False
   previous_time=previous_offset=-1
   for n in range(count):
    pos=at+24+n*stride;t=int.from_bytes(data[pos:pos+width],'big');offset=int.from_bytes(data[pos+width:pos+2*width],'big')
    if t<previous_time or offset<previous_offset or not 0<offset<size-len(data):return False
    previous_time,previous_offset=t,offset
   found=True
  at+=length
 return found and at==end

class Cache:
 def __init__(self,state_dir,log=lambda text:None,clock=time.monotonic):
  self.path=Path(state_dir)/FILE;self.log=log;self.clock=clock;self.lock=threading.RLock()
  self.entries={};self.opened={};self.failed={};self.used=0
  try:
   with self.path.open('rb') as file:raw=file.read(MAX_JSON+1)
   if len(raw)<=MAX_JSON:
    rows=json.loads(raw).get('entries',[])
    for row in rows[:MAX_ENTRIES]:
     meta=row.get('metadata') or {};ident=identity(meta,meta.get('id'))
     encoded=row.get('index','')
     if not ident or not isinstance(encoded,str) or len(encoded)>4*((MAX_INDEX+2)//3):continue
     data=base64.b64decode(encoded,validate=True)
     if valid(data,ident[1]['size']):self.entries[meta['id']]={'key':ident[0],'metadata':ident[1],'data':data,'used':self.used};self.used+=1
  except (OSError,ValueError,TypeError,AttributeError,RecursionError):self.entries={}
  self._trim()
 def _trim(self):
  while len(self.entries)>MAX_ENTRIES or sum(len(row['data']) for row in self.entries.values())>MAX_TOTAL:
   self.entries.pop(min(self.entries,key=lambda key:self.entries[key]['used']))
 def _save(self):
  self._trim();tmp=None
  try:
   self.path.parent.mkdir(parents=True,exist_ok=True)
   rows=[{'metadata':row['metadata'],'index':base64.b64encode(row['data']).decode()} for row in self.entries.values()]
   with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=self.path.parent,prefix='.drive-index-',delete=False) as file:
    tmp=file.name;json.dump({'entries':rows},file)
   os.replace(tmp,self.path);tmp=None
  except OSError:pass  # caching is optional; a read-only/full profile must not break playback
  finally:
   if tmp:
    try:os.unlink(tmp)
    except OSError:pass
 def begin(self,file_id,upstream,head=False,front=False):
  with self.lock:
   now=self.clock();current=self.opened.get(file_id)
   if front and current and current.get('head') and now-current['at']<2:
    current['head']=False;return current['metadata']
   if not head and not front and current and now-current['at']<300:return current['metadata']
   if now<self.failed.get(file_id,0):return None
  # Network waits for one title must not hold the cache lock for every other title.
  item=upstream.metadata(file_id);ident=identity(item,file_id)
  with self.lock:
   if not ident:
    self.opened.pop(file_id,None);self.failed[file_id]=now+30
    if len(self.failed)>MAX_ENTRIES:self.failed.pop(next(iter(self.failed)))
    return None
   key,meta=ident
   old=self.entries.get(file_id)
   if old and old['key']!=key:self.entries.pop(file_id);self._save()
   self.opened[file_id]={'key':key,'metadata':meta,'head':head,'at':now}
   if len(self.opened)>MAX_ENTRIES:self.opened.pop(next(iter(self.opened)))
   if len(self.failed)>MAX_ENTRIES:self.failed.pop(next(iter(self.failed)))
   return meta
 def _read(self,upstream,file_id,start,end,size):
  response=upstream.get(file_id,'bytes=%d-%d'%(start,end))
  try:
   if response.status!=206 or response.getheader('Content-Range')!='bytes %d-%d/%d'%(start,end,size):return None
   data=response.read(end-start+2)
   return data if len(data)==end-start+1 else None
  finally:
   try:response.close()
   finally:upstream.drop()
 def range(self,file_id,rng,upstream,meta):
  if not meta:return None
  span=bounds(rng,meta['size'])
  if not span:return None
  start,end=span
  with self.lock:
   ident=identity(meta,file_id);row=self.entries.get(file_id)
   if row and ident and row['key']==ident[0] and start>=meta['size']-len(row['data']):
    self.used+=1;row['used']=self.used;at=start-(meta['size']-len(row['data']))
    data=row['data'][at:at+end-start+1]
    self.log('Kodi iOS Drive index: served from cache (%d bytes)'%len(data))
    return start,end,meta['size'],data
  if end!=meta['size']-1 or not 16<=end-start+1<=MAX_INDEX:return None
  data=self._read(upstream,file_id,start,end,meta['size'])
  if data is None:return None
  tail=data[-16:]
  if tail[:12]==struct.pack('>I4sI',16,b'mfro',0):
   length=struct.unpack('>I',tail[12:])[0]
   # Capture the player's existing index read. Do not add a second read to its first mfro request.
   if 40<=length<=min(MAX_INDEX,len(data)) and length<meta['size']:
    index=data[-length:]
    if valid(index,meta['size']):
     fresh=identity(upstream.metadata(file_id),file_id)
     with self.lock:
      current=self.opened.get(file_id)
      if fresh and ident and current and fresh[0]==ident[0]==current['key']:
       self.used+=1;self.entries[file_id]={'key':fresh[0],'metadata':fresh[1],'data':index,'used':self.used};self._save()
       self.log('Kodi iOS Drive index: cached validated fragment index (%d bytes)'%length)
  return start,end,meta['size'],data
