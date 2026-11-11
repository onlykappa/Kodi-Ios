"""Range-only container checks: codec compatibility does not imply a fast-opening index."""
import io,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import fast_open,driveupload

def box(kind,data=b''):return struct.pack('>I4s',8+len(data),kind)+data
FTYP=box(b'ftyp',b'isom0000')
def fragmented(index=True,offset_delta=0,count=1,version=1):
 moov=box(b'moov',box(b'mvex'));offset=len(FTYP+moov)
 media=box(b'moof')+box(b'mdat',b'movie')
 if not index:return FTYP+moov+media
 width=8 if version else 4
 entry=b'\0'*width+(offset+offset_delta).to_bytes(width,'big')+b'\1\1\1'
 tfra=box(b'tfra',bytes([version,0,0,0])+struct.pack('>III',1,0,count)+entry*count)
 return FTYP+moov+media+box(b'mfra',tfra+box(b'mfro',struct.pack('>II',0,8+len(tfra)+16)))

class Layout(unittest.TestCase):
 def check(self,data,**kwargs):
  self.requests=[]
  def open(request,timeout):
   a,b=map(int,request.get_header('Range')[6:].split('-'));self.requests.append((a,b))
   response=io.BytesIO(data[a:b+1]);response.getcode=lambda:206
   response.headers={'Content-Range':'bytes %d-%d/%d'%(a,b,len(data))};return response
  return fast_open.inspect('http://127.0.0.1/movie',len(data),open_url=open,**kwargs)
 def test_progressive_front_index_skips_preparation(self):
  self.assertTrue(self.check(FTYP+box(b'moov')+box(b'mdat',b'movie'))['fast_open'])
 def test_tail_index_requires_only_layout_repair(self):
  self.assertFalse(self.check(FTYP+box(b'mdat',b'movie')+box(b'moov'))['fast_open'])
 def test_mkv_needs_a_container_even_with_compatible_picture(self):
  self.assertEqual(self.check(b'\x1a\x45\xdf\xa3some matroska')['layout_reason'],'not_mp4')
 def test_fragmented_mp4_needs_an_actual_tail_random_access_index(self):
  self.assertFalse(self.check(fragmented(False))['fast_open'])
  for version in (0,1):self.assertTrue(self.check(fragmented(version=version))['fast_open'])
 def test_empty_or_wrong_fragment_offsets_are_not_ready(self):
  for data in (fragmented(count=0),fragmented(offset_delta=1),fragmented(offset_delta=-1)):
   self.assertFalse(self.check(data)['fast_open'])
 def test_corrupt_box_does_not_loop_or_claim_ready(self):
  for data in (FTYP+struct.pack('>I4s',7,b'moov'),FTYP+box(b'moov')+struct.pack('>I4s',999999,b'mdat')):
   self.assertFalse(self.check(data)['fast_open'])
 def test_extended_size_boxes(self):
  data=FTYP+struct.pack('>I4sQ',1,b'moov',16)+box(b'mdat',b'movie')
  self.assertTrue(self.check(data)['fast_open'])
 def test_only_headers_are_requested_never_media_payload(self):
  data=FTYP+box(b'moov')+box(b'mdat',b'x'*1000000)
  self.assertTrue(self.check(data)['fast_open'])
  self.assertLess(sum(b-a+1 for a,b in self.requests),128)
 def test_cancel_is_preserved(self):
  with self.assertRaises(driveupload.Stop):self.check(FTYP,keep_going=lambda:False)
 def test_non_range_response_is_rejected(self):
  response=io.BytesIO(b'12345678');response.getcode=lambda:200
  with self.assertRaises(OSError):fast_open.inspect('http://127.0.0.1/movie',8,open_url=lambda *a,**k:response)

if __name__=='__main__':unittest.main()
