"""Roadmap 1G.8: Play on TV offers Prepare first for a download whose picture still needs converting."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import cast_ready as cr

class CastReady(unittest.TestCase):
    def test_drive_file_id_from_both_kinds_of_link(self):
        self.assertEqual(cr.item_id('plugin://plugin.googledrive/?action=play&driveid=D&item_driveid=D&item_id=F1'),'F1')
        self.assertEqual(cr.item_id('http://127.0.0.1:63092/download/D/D/F2/Movie%20(2010).mp4|User-Agent=x'),'F2')
        self.assertEqual(cr.item_id('https://debrid.example/stream.mkv'),'')
    def test_only_unprepared_pictures_that_need_converting_ask(self):
        view={'rows':{'waiting':[{'id':'A','probe':{'copy_video':False}},{'id':'B'},{'id':'C','probe':{'copy_video':True}}],
                      'preparing':[{'id':'D','probe':{'copy_video':False}}],'ready':[{'id':'E'}]}}
        self.assertEqual([cr.not_ready(view,i) for i in 'ABCDEX'],[True,True,False,True,False,False])
        self.assertFalse(cr.not_ready(view,''))
    def test_it_says_prepare_first_and_offers_no_live_conversion(self):
        self.assertEqual(cr.MESSAGE[0],'Preparing first')
        self.assertFalse(hasattr(cr,'SHEET'))

if __name__=='__main__':unittest.main()
