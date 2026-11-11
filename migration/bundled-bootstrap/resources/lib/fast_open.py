"""Inspect MP4 layout with bounded range reads, without downloading the movie.

A front moov opens a progressive MP4 quickly. Fragmented MP4 also needs a completed
random-access index; otherwise opening can walk every fragment over Drive.
This checks layout, independently of the native codec/copy-safety probe.
"""
import struct,time,urllib.request
import driveupload

def inspect(url,size,keep_going=lambda:True,open_url=urllib.request.urlopen):
 size=int(size);deadline=time.monotonic()+30;reads=[0]
 def read(at,n):
  if not keep_going():raise driveupload.Stop('Library check paused')
  if at<0 or n<0 or at+n>size:raise ValueError('Invalid movie box bounds')
  reads[0]+=1
  if reads[0]>512 or time.monotonic()>=deadline:raise TimeoutError('Movie layout check timed out')
  request=urllib.request.Request(url,headers={'Range':'bytes=%d-%d'%(at,at+n-1)})
  with open_url(request,timeout=max(.1,min(10,deadline-time.monotonic()))) as response:
   if response.getcode()!=206:raise OSError('Movie layout needs byte ranges')
   if response.headers.get('Content-Range','')!='bytes %d-%d/%d'%(at,at+n-1,size):raise OSError('Movie layout range changed')
   data=response.read(n+1)
  if len(data)!=n:raise OSError('Movie layout read was incomplete')
  return data
 def box(at,end):
  if at+8>end:raise ValueError('Incomplete movie box')
  h=read(at,8);n,kind=struct.unpack('>I4s',h);header=8
  if n==1:n=struct.unpack('>Q',read(at+8,8))[0];header=16
  elif n==0:n=end-at
  if n<header or at+n>end:raise ValueError('Invalid movie box size')
  return kind,at+header,at+n
 def boxes(at,end):
  for _ in range(256):
   if at==end:return
   kind,payload,next_at=box(at,end)
   yield kind,payload,next_at
   at=next_at
  if at!=end:raise ValueError('Too many movie boxes')
 def result(ok,reason):return {'fast_open':ok,'layout_reason':reason}
 if size<8:return result(False,'not_mp4')
 # MKV and other containers need a remux for the indexed MP4 layout.
 if read(0,8)[4:] not in (b'ftyp',b'moov',b'free',b'wide',b'mdat',b'skip'):
  return result(False,'not_mp4')
 try:
  front=None;media=None;fragmented=False
  for kind,payload,end in boxes(0,size):
   if kind==b'moov':
    front=payload
    fragmented=any(k==b'mvex' for k,_,_ in boxes(payload,end))
   if kind in (b'mdat',b'moof'):
    media=payload;fragmented=fragmented or kind==b'moof';break
  if front is None or media is None or front>media:return result(False,'index_after_media')
  if not fragmented:return result(True,'front_moov')
  if size<16:return result(False,'missing_fragment_index')
  tail=read(size-16,16)
  if tail[:12]!=struct.pack('>I4sI',16,b'mfro',0):return result(False,'missing_fragment_index')
  length=struct.unpack('>I',tail[12:])[0];start=size-length
  if length<40 or start<media:return result(False,'invalid_fragment_index')
  kind,payload,end=box(start,size)
  if kind!=b'mfra' or end!=size:return result(False,'invalid_fragment_index')
  indexed=False
  for kind,at,end in boxes(payload,size-16):
   if kind!=b'tfra':continue
   if end-at<16:return result(False,'invalid_fragment_index')
   h=read(at,16);version=h[0];flags=struct.unpack('>I',h[8:12])[0];count=struct.unpack('>I',h[12:])[0]
   if version not in (0,1) or not count:return result(False,'empty_fragment_index')
   width=8 if version else 4;stride=2*width+sum(((flags>>shift)&3)+1 for shift in (4,2,0))
   if at+16+count*stride!=end:return result(False,'invalid_fragment_index')
   previous=-1
   for number in sorted({0,count-1}):
    entry=read(at+16+number*stride,2*width)
    offset=int.from_bytes(entry[width:],'big')
    if offset<=previous or offset<front or offset>=start:return result(False,'invalid_fragment_index')
    if box(offset,start)[0]!=b'moof':return result(False,'invalid_fragment_index')
    previous=offset
   indexed=True
  return result(indexed,'fragment_index' if indexed else 'missing_fragment_index')
 except ValueError:return result(False,'invalid_mp4_layout')
