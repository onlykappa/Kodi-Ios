"""Owner (build-187 log: Fall 2 at ~0.1 MB/s): Python's socket timeout limits the whole upload request, so a 32 MB
piece had to finish in 45 s; on a ~0.43 MB/s line 399 of 649 big pieces were cut off and sent again. The limit grows
with the piece; small and read-only requests keep their short limits."""
import sys,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import driveupload

class Timeout(unittest.TestCase):
 def test_scales_with_the_piece(self):
  t=driveupload.request_timeout(45,b'x'*(32*1024*1024))
  self.assertEqual(t,45+256);self.assertGreater(32*1024*1024/t,0.1*1024*1024)   # 0.43 MB/s lines finish easily
  self.assertEqual(driveupload.request_timeout(45,b''),45);self.assertEqual(driveupload.request_timeout(45,None),45)
 def test_sender_uses_it(self):
  seen=[]
  class Answer:
   status=200;headers={}
   def read(self):return b'{}'
   def __enter__(self):return self
   def __exit__(self,*a):return False
  class Opener:
   def open(self,request,timeout):seen.append((request.get_method(),timeout));return Answer()
  with mock.patch('urllib.request.build_opener',return_value=Opener()):
   send=driveupload.sender(None)
   send('PUT','https://upload.example/s',b'x'*(8*1024*1024),{})
   send('GET','https://www.googleapis.com/drive/v3/files/x',None,{})
  self.assertEqual(seen,[('PUT',45+64),('GET',30)])

if __name__=='__main__':unittest.main()
