"""A prepared copy with zero-length subtitle cues is re-packed once the converter can fix them, once per framework revision (build 639 log 9f7b4ab2)."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import caption_repair as cr

BAD={'tracks':[{'id':1,'zero_length':False},{'id':2,'zero_length':True}]}
GOOD={'tracks':[{'id':1,'zero_length':False}]}

class Repair(unittest.TestCase):
    def test_the_revision_is_read_from_the_build_file(self):
        d=tempfile.mkdtemp();p=Path(d)/'build.json'
        p.write_text(json.dumps({'frameworks':{'airplay':{'tag':'kodi-airplay-r72'}}}));self.assertEqual(cr.revision(str(p)),72)
        p.write_text(json.dumps({'frameworks':{'airplay':{'tag':'kodi-airplay-r71'}}}));self.assertEqual(cr.revision(str(p)),71)
        p.write_text('{no');self.assertEqual(cr.revision(str(p)),0);self.assertEqual(cr.revision(str(Path(d)/'none.json')),0)
    def test_nothing_happens_before_the_converter_can_fix_it(self):
        tried={};self.assertFalse(cr.due('u','k',tried,installed=71,probe=lambda u:BAD));self.assertEqual(tried,{})
    def test_a_copy_with_zero_length_cues_is_due_once_per_revision(self):
        tried={}
        self.assertTrue(cr.due('u','k',tried,installed=72,probe=lambda u:BAD));self.assertEqual(tried,{'k':72})
        self.assertFalse(cr.due('u','k',tried,installed=72,probe=lambda u:BAD))   # the converter did not fix it: not again at r72
        self.assertTrue(cr.due('u','k',tried,installed=73,probe=lambda u:BAD))   # a newer converter tries once more
    def test_good_unreadable_or_failing_copies_are_left_alone(self):
        tried={}
        for probe in (lambda u:GOOD,lambda u:None,lambda u:{}):self.assertFalse(cr.due('u','k',tried,installed=72,probe=probe))
        def boom(u):raise OSError('gone')
        self.assertFalse(cr.due('u','k',tried,installed=72,probe=boom));self.assertEqual(tried,{})
    def test_the_library_check_asks_only_for_ready_copies_with_a_good_layout(self):
        text=(LIB/'prepare_downloads.py').read_text()
        self.assertIn("elif streamable_video(probe) and probe.get('fast_open') is not False and ready(item):",text)
        self.assertIn("caption_repair.due(source,key(item),self.state.setdefault('captions',{}))",text)
    def test_a_repack_the_caption_check_asked_for_survives_the_second_look(self):
        # ISSUE-486 (owner log 0d8c75c0, Iron Man): the run's own inspection finds due() already answered, so it must keep the ask
        asked={'fast_open':False,'layout_reason':cr.REASON}
        again={'fast_open':True,'codec':'h264'}
        self.assertEqual(cr.carry(asked,dict(again))['fast_open'],False)
        self.assertEqual(cr.carry(asked,dict(again))['layout_reason'],cr.REASON)
        self.assertTrue(cr.carry({'fast_open':False,'layout_reason':'fragment_index'},dict(again))['fast_open'])   # other reasons are re-judged
        self.assertTrue(cr.carry(None,dict(again))['fast_open'])
        self.assertIn("caption_repair.carry(job.get('probe'),q.inspect_source(item,keep_going))",(LIB/'prepare_cloud.py').read_text())
if __name__=='__main__':unittest.main()
