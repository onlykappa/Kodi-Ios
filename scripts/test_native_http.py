"""ISSUE-167: Drive upload pieces go through the system's networking (KodiAirPlay kodi_http_send) when present."""
import ctypes,sys,types,unittest
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
 def test_status_headers_body_and_errors(self):
  seen=[];send=native_http.sender(fake_lib(308,seen=seen))
  status,headers,body=send('PUT','https://upload/x',b'a'*10,{'Content-Range':'bytes 0-9/20'},60)
  self.assertEqual((status,headers['Range'],body),(308,'bytes=0-1048575',b''))
  self.assertEqual(seen[0][:2],(b'PUT',b'https://upload/x'));self.assertIn(b'Content-Range: bytes 0-9/20\n',seen[0][2]);self.assertEqual(seen[0][3],10)
  done=native_http.sender(fake_lib(200,body=b'{"id":"d"}'))('PUT','u',b'x',{},5);self.assertEqual(done[2],b'{"id":"d"}')
  with self.assertRaisesRegex(ConnectionError,'offline'):native_http.sender(fake_lib(-1))('PUT','u',b'x',{},5)
  self.assertIsNone(native_http.sender(None));self.assertIsNone(native_http.sender(types.SimpleNamespace()))
 def test_only_upload_pieces_go_native(self):
  calls=[]
  def native(method,url,body,headers,timeout):calls.append((method,len(body),headers.get('User-Agent')));return 308,{'Range':'bytes=0-9'},b''
  send=driveupload.sender(None,native=native)
  self.assertEqual(send('PUT','https://upload/x',b'z'*(256*1024),{'Content-Range':'bytes 0-262143/9'})[0],308)
  self.assertEqual(calls,[('PUT',256*1024,'Kodi iOS Drive upload')])
 def test_service_wires_it(self):
  src=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('native=native_http.sender(airplay.load(path))',src);self.assertIn(',native=native)',src)
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('int kodi_http_send(',build);self.assertIn('_kodi_http_send\\n',build)

if __name__=='__main__':unittest.main()
