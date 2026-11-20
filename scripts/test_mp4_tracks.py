"""The subtitle tracks of an MP4 are read from its moov so a log says what kind they are."""
import struct,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import mp4_tracks as mt

def box(kind,payload=b''):return struct.pack('>I4s',8+len(payload),kind)+payload
def lang(code):
    a,b,c=[ord(x)-0x60 for x in code];return (a<<10)|(b<<5)|c
def trak(track_id,handler,fourcc,code='eng'):
    tkhd=box(b'tkhd',struct.pack('>I',0)+struct.pack('>II',0,0)+struct.pack('>I',track_id)+bytes(60))
    mdhd=box(b'mdhd',struct.pack('>I',0)+struct.pack('>IIII',0,0,1000,0)+struct.pack('>HH',lang(code),0))
    hdlr=box(b'hdlr',struct.pack('>I',0)+struct.pack('>I',0)+handler+bytes(12)+b'x\0')
    entry=struct.pack('>I4s',8+8,fourcc)+bytes(8)
    stsd=box(b'stsd',struct.pack('>II',0,1)+entry)
    return box(b'trak',tkhd+box(b'mdia',mdhd+hdlr+box(b'minf',box(b'stbl',stsd))))
def mp4(*traks):return box(b'ftyp',b'isom'+bytes(8))+box(b'moov',b''.join(traks))

class Tracks(unittest.TestCase):
    def test_subtitle_tracks_are_listed_with_their_kind_and_video_and_audio_are_not(self):
        data=mp4(trak(1,b'vide',b'hvc1'),trak(2,b'soun',b'mp4a'),trak(3,b'sbtl',b'tx3g','eng'),trak(4,b'clcp',b'c608','eng'),trak(5,b'subt',b'wvtt','spa'))
        found=mt.subtitle_tracks(data)
        self.assertEqual([(t['id'],t['handler'],t['codec'],t['language']) for t in found],[(3,'sbtl','tx3g','eng'),(4,'clcp','c608','eng'),(5,'subt','wvtt','spa')])
        self.assertEqual(mt.describe(found),'#3 eng tx3g (sbtl); #4 eng c608 (clcp); #5 spa wvtt (subt)')
    def test_a_file_without_a_moov_or_without_subtitles_says_so(self):
        self.assertEqual(mt.subtitle_tracks(box(b'ftyp',b'isom'+bytes(8))),[])
        self.assertEqual(mt.subtitle_tracks(mp4(trak(1,b'vide',b'hvc1'))),[])
        self.assertIn('no subtitle track',mt.describe([]))
    def test_a_moov_cut_off_by_the_end_of_what_was_read_still_yields_its_early_tracks(self):
        data=mp4(trak(1,b'vide',b'hvc1'),trak(2,b'sbtl',b'tx3g'),trak(3,b'sbtl',b'tx3g'))
        cut=data[:len(data)-30]   # the last track is cut
        self.assertEqual([t['id'] for t in mt.subtitle_tracks(cut)][:1],[2])
    def test_garbage_is_not_fatal(self):
        self.assertEqual(mt.subtitle_tracks(b''),[]);self.assertEqual(mt.subtitle_tracks(bytes(range(256))*4),[])
if __name__=='__main__':unittest.main()
