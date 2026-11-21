"""The subtitle tracks of an MP4 are read from its moov so a log says what kind they are."""
import struct,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import mp4_tracks as mt

def box(kind,payload=b''):return struct.pack('>I4s',8+len(payload),kind)+payload
def lang(code):
    a,b,c=[ord(x)-0x60 for x in code];return (a<<10)|(b<<5)|c
def trak(track_id,handler,fourcc,code='eng',samples=None):
    tkhd=box(b'tkhd',struct.pack('>I',0)+struct.pack('>II',0,0)+struct.pack('>I',track_id)+bytes(60))
    mdhd=box(b'mdhd',struct.pack('>I',0)+struct.pack('>IIII',0,0,1000,0)+struct.pack('>HH',lang(code),0))
    hdlr=box(b'hdlr',struct.pack('>I',0)+struct.pack('>I',0)+handler+bytes(12)+b'x\0')
    entry=struct.pack('>I4s',8+8,fourcc)+bytes(8)
    stsd=box(b'stsd',struct.pack('>II',0,1)+entry)
    stsz=box(b'stsz',struct.pack('>III',0,0,samples)) if samples is not None else b''
    return box(b'trak',tkhd+box(b'mdia',mdhd+hdlr+box(b'minf',box(b'stbl',stsd+stsz))))
def mp4(*traks,fragmented=False):return box(b'ftyp',b'isom'+bytes(8))+box(b'moov',b''.join(traks)+(box(b'mvex',box(b'trex',bytes(24))) if fragmented else b''))

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
    def test_the_number_of_subtitle_samples_is_read(self):
        found=mt.subtitle_tracks(mp4(trak(3,b'sbtl',b'tx3g','eng',samples=812),trak(4,b'sbtl',b'tx3g','eng',samples=0)))
        self.assertEqual([t['samples'] for t in found],[812,0]);self.assertIn('812 samples',mt.describe(found))
    def test_a_fragmented_file_does_not_claim_its_tracks_are_empty(self):
        # Build 618 log: every track of a fragmented Drive copy said "0 samples" (they live in moof boxes) and would have been hidden as empty.
        found=mt.subtitle_tracks(mp4(trak(3,b'sbtl',b'tx3g','eng',samples=0),fragmented=True))
        self.assertIsNone(found[0]['samples']);self.assertNotIn('samples',mt.describe(found))

def mfra(tracks):
    """A real-layout mfra: tracks = {track id: [(time, moof offset)]} (version 1 tfra, 1-byte traf/trun/sample numbers)."""
    boxes=b''
    for track,rows in tracks.items():
        entries=b''.join(struct.pack('>QQBBB',t,o,1,1,1) for t,o in rows)
        boxes+=struct.pack('>I4sIIII',24+len(entries),b'tfra',1<<24,track,0,len(rows))+entries
    length=8+len(boxes)+16
    return struct.pack('>I4s',length,b'mfra')+boxes+struct.pack('>I4sII',16,b'mfro',0,length)

class Fragmented(unittest.TestCase):
    """Build 622 (owner log ac85bba1): a fragmented file counts no samples in its moov, so an empty embedded subtitle track looked like a full one."""
    def test_fragments_per_track_are_counted_from_the_index(self):
        data=mfra({1:[(n*1000,n*50) for n in range(40)],2:[(n*1000,n*50+5) for n in range(40)],3:[(n*1000,n) for n in range(30)],4:[(0,9)]})
        self.assertEqual(mt.fragment_counts(data),{1:40,2:40,3:30,4:1})
        self.assertEqual(mt.fragment_counts(b'junk'),{});self.assertEqual(mt.fragment_counts(b''),{})
    def test_a_track_in_one_fragment_of_a_long_video_is_empty_and_the_menu_rule_sees_it(self):
        found=mt.subtitle_tracks(mp4(trak(1,b'vide',b'hvc1'),trak(3,b'sbtl',b'tx3g','eng'),trak(4,b'sbtl',b'tx3g','eng'),trak(5,b'sbtl',b'tx3g','und'),fragmented=True))
        self.assertTrue(all(t['samples'] is None for t in found))
        mt.with_fragment_counts(found,{1:60,3:41,4:1})
        self.assertEqual([(t['id'],t['samples']) for t in found],[(3,41),(4,1),(5,0)])   # track 5 is in no fragment at all
        self.assertEqual(mt.describe(found),'#3 eng tx3g (sbtl), 41 fragments hold it; #4 eng tx3g (sbtl), 1 fragments hold it; #5 und tx3g (sbtl), 0 fragments hold it')
    def test_a_short_video_is_left_alone(self):
        found=mt.subtitle_tracks(mp4(trak(3,b'sbtl',b'tx3g','eng'),fragmented=True));mt.with_fragment_counts(found,{1:4,3:1})
        self.assertIsNone(found[0]['samples'])
    def test_the_menu_logs_what_kodi_says_after_a_track_is_switched_on(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn("'properties': ['subtitleenabled', 'currentsubtitle']",text);self.assertIn("log('Kodi says subtitles enabled=%s",text)
    def test_the_track_menu_reads_it(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn('mp4_tracks.with_fragment_counts(self.file_tracks, mp4_tracks.fragment_counts(get(total - size, total - 1)))',text)
        self.assertIn("any(t.get('samples') is not None and t['samples'] <= 1 for t in self.file_tracks)",text)   # the existing drop of an empty track

if __name__=='__main__':unittest.main()
