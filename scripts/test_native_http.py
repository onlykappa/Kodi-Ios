"""ISSUE-167: Drive upload pieces go through the system's networking (KodiAirPlay kodi_http_send) when present."""
import ctypes,sys,types,unittest,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import native_http,driveupload

def fake_lib(status,headers='Range: bytes=0-1048575\nX-GUploader: y\n',body=b'',seen=None):
 def fn(method,url,lines,data,length,timeout,out_h,hl,out_b,bl,used):
  if seen is not None:seen.append((method,url,lines,length,timeout))
  h=headers.encode();ctypes.memmove(out_h,h,len(h))
  if status<0:ctypes.memmove(out_b,b'offline',7);return status
  ctypes.memmove(out_b,body,len(body));used._obj.value=len(body);return status
 return types.SimpleNamespace(kodi_http_send=fn)

class Native(unittest.TestCase):
 def test_native_copy_passes_only_offsets_and_receipts_to_python(self):
  seen=[]
  def fn(source,source_headers,target,target_headers,offset,count,total,timeout,out_h,hl,out_b,bl,used,read_status):
   seen.append((source,target,offset,count,total));read_status._obj.value=206
   body=b'{"id":"saved","size":"100"}';ctypes.memmove(out_b,body,len(body));used._obj.value=len(body);return 200
  copy=native_http.copier(types.SimpleNamespace(kodi_http_copy=fn))
  result=copy('https://source/file',{},'https://upload/session',{'Authorization':'Bearer test'},0,100,100)
  self.assertEqual(result[0],200);self.assertEqual(result[2],b'{"id":"saved","size":"100"}')
  self.assertEqual(seen,[(b'https://source/file',b'https://upload/session',0,100,100)])
  self.assertIsNone(native_http.copier(None))
  with self.assertRaises(ValueError):copy('s',{},'d',{},10,100,100)
 def test_r50_copies_32_mb_pieces_and_older_frameworks_keep_8(self):
  # Owner log 31996cd8 (182/101 Mbps line, ~2.8 MB/s): 8 MB pieces each waited for AllDebrid and Drive.
  seen=[]
  def fn(source,source_headers,target,target_headers,offset,count,total,timeout,*rest):
   seen.append((count,timeout));rest[-1]._obj.value=206;return 308
  big=32*1024*1024
  new=native_http.copier(types.SimpleNamespace(kodi_http_copy=fn,kodi_http_copy_max=lambda:big))
  self.assertEqual(new.max,big)
  new('s',{},'d',{},0,big,10*big)
  self.assertEqual(seen[-1],(big,32.0))                        # a 32 MB piece gets 32 s, not 20
  old=native_http.copier(types.SimpleNamespace(kodi_http_copy=fn))
  self.assertEqual(old.max,8*1024*1024)
  self.assertFalse(old.streams)
  streamed=native_http.copier(types.SimpleNamespace(kodi_http_copy=fn,kodi_http_copy_max=lambda:256*1024*1024,kodi_http_copy_streams=lambda:1))
  self.assertEqual((streamed.max,streamed.streams),(256*1024*1024,True))   # r53 (ISSUE-201)
  with self.assertRaises(ValueError):old('s',{},'d',{},0,big,10*big)
  chunks=driveupload.StreamChunks(big,cap=big);chunks.current=chunks.minimum
  for _ in range(15):chunks.observe(chunks.current,2.0,0)   # three fast pieces per doubling: 1 to 32 MB
  self.assertEqual(chunks.current,big)                         # fast pieces grow to 32 MB
  self.assertEqual(driveupload.StreamChunks(big).limit,8*1024*1024)   # without the cap: 8 MB as before
 def test_native_copy_exposes_source_expiry_for_existing_link_renewal(self):
  def fn(*args):args[-1]._obj.value=403;return -1
  copy=native_http.copier(types.SimpleNamespace(kodi_http_copy=fn))
  with self.assertRaises(urllib.error.HTTPError) as error:copy('https://source/file',{},'https://upload/session',{},0,10,100)
  self.assertEqual(error.exception.code,403)
 def test_status_headers_body_and_errors(self):
  seen=[];send=native_http.sender(fake_lib(308,seen=seen))
  status,headers,body=send('PUT','https://upload/x',b'a'*10,{'Content-Range':'bytes 0-9/20'},60)
  self.assertEqual((status,headers['Range'],body),(308,'bytes=0-1048575',b''))
  self.assertEqual(seen[0][:2],(b'PUT',b'https://upload/x'));self.assertIn(b'Content-Range: bytes 0-9/20\n',seen[0][2]);self.assertEqual(seen[0][3],10)
  done=native_http.sender(fake_lib(200,body=b'{"id":"d"}'))('PUT','u',b'x',{},5);self.assertEqual(done[2],b'{"id":"d"}')
  with self.assertRaisesRegex(ConnectionError,'offline'):native_http.sender(fake_lib(-1))('PUT','u',b'x',{},5)
  self.assertIsNone(native_http.sender(None));self.assertIsNone(native_http.sender(types.SimpleNamespace()))
 def test_bounded_media_reader_and_expiry_status(self):
  lib=fake_lib(206,headers='Content-Range: bytes 10-12/20\nContent-Length: 3\n',body=b'abc');lib.kodi_http_reads=lambda:1
  open_url=native_http.opener(lib)
  with open_url(urllib.request.Request('https://media/x',headers={'Range':'bytes=10-12'}),5) as response:
   self.assertEqual(response.getcode(),206);self.assertEqual(response.headers.get('content-range'),'bytes 10-12/20')
   self.assertEqual(response.read(),b'abc')
  bad=fake_lib(403);bad.kodi_http_reads=lambda:1
  with self.assertRaises(urllib.error.HTTPError) as caught:native_http.opener(bad)(urllib.request.Request('https://media/x'),5)
  self.assertEqual(caught.exception.code,403)
  self.assertIsNone(native_http.opener(fake_lib(200)))
 def test_native_redirect_does_not_forward_credentials_to_another_host(self):
  seen=[];answers=iter([(302,{'Location':'https://other.example/file'},b''),(206,{},b'x')])
  def send(method,url,body,headers,timeout):seen.append((url,headers));return next(answers)
  from unittest.mock import patch
  with patch.object(native_http,'sender',return_value=send):
   op=native_http.opener(types.SimpleNamespace(kodi_http_reads=lambda:1))
   with op(urllib.request.Request('https://source.example/file',headers={'Authorization':'Bearer test','Cookie':'test','Range':'bytes=1-1'})) as r:self.assertEqual(r.read(),b'x')
  self.assertNotIn('Authorization',seen[1][1]);self.assertNotIn('Cookie',seen[1][1]);self.assertEqual(seen[1][1]['Range'],'bytes=1-1')
 def test_headers_and_native_lengths_are_validated(self):
  send=native_http.sender(fake_lib(200))
  with self.assertRaises(ValueError):send('GET','https://media/x',None,{'Cookie':'a\rb'},1)
  lib=fake_lib(200)
  def invalid(*args):args[-1]._obj.value=-1;return 200
  lib.kodi_http_send=invalid
  with self.assertRaises(ConnectionError):native_http.sender(lib)('GET','https://media/x',None,{},1)
 def test_drive_range_reader_refreshes_rejected_credentials_and_checks_actual_range(self):
  import drive_stream
  token=['old'];renewed=[]
  def refresh(rejected):renewed.append(rejected);token[0]='new'
  def open_url(request,timeout):
   if request.get_header('Authorization')=='Bearer old':
    raise urllib.error.HTTPError(request.full_url,401,'expired',{},None)
   return native_http.Response(206,{'Content-Range':'bytes 0-2/3'},b'abc')
  stream=drive_stream.DriveStream(lambda:token[0],open_url=open_url,refresh_token=refresh);self.addCleanup(stream.close)
  self.assertEqual(stream._fetch('synthetic',0,2),(b'abc',3));self.assertEqual(renewed,['old'])
  stream.open_url=lambda *args:native_http.Response(206,{'Content-Range':'bytes 1-3/4'},b'abc')
  with self.assertRaisesRegex(ConnectionError,'wrong byte range'):stream._fetch('synthetic',0,2)
 def test_only_upload_pieces_go_native(self):
  calls=[]
  def native(method,url,body,headers,timeout):calls.append((method,len(body),headers.get('User-Agent')));return 308,{'Range':'bytes=0-9'},b''
  send=driveupload.sender(None,native=native)
  self.assertEqual(send('PUT','https://upload/x',b'z'*(256*1024),{'Content-Range':'bytes 0-262143/9'})[0],308)
  self.assertEqual(calls,[('PUT',256*1024,'Kodi iOS Drive upload')])
 def test_service_wires_it(self):
  src=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('native=native_http.sender(native_lib)',src);self.assertIn(',native=native)',src)
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('int kodi_http_send(',build);self.assertIn('_kodi_http_send\\n',build)

if __name__=='__main__':unittest.main()
