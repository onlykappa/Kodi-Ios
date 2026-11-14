"""ISSUE-287: the activity pill and its sheet are removed (owner: "I use Library status or the notification tray").
What it carried for other pages stays: the ring and row textures, Kodi's invisible background progress box, and
Elementum Burst's error lines reaching Notifications."""
import sys,tempfile,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import portrait,skin_textures,background_box


class Textures(unittest.TestCase):
 def test_rings_rows_and_hidden_box_are_still_generated(self):
  files=skin_textures.files(types.SimpleNamespace(**vars(portrait)))
  names={Path(k).name for k in files}
  self.assertTrue({'ring_%02d.png'%k for k in range(21)}<=names)
  self.assertTrue({'sheet_bg.png','row_only.png','row_first.png','row_last.png'}<=names)
  box=files[portrait.FOLDER+'/'+skin_textures.BOX].decode()
  self.assertIn('<visible>false</visible>',box);self.assertIn('id="30"',box);self.assertIn('id="31"',box)
  self.assertIn('1080i/'+skin_textures.BOX,files)

 def test_no_pill_anywhere(self):
  for gone in ('activity.py','activity_skin.py'):self.assertFalse((LIB/gone).exists())
  self.assertFalse((BOOT/'activity_page.py').exists())
  src=(LIB/'portrait.py').read_text()
  self.assertNotIn('activity_skin',src);self.assertNotIn('Custom_1187',src)
  self.assertNotIn('activity_page',(BOOT/'default.py').read_text())
  self.assertNotIn('import activity',(BOOT/'service.py').read_text())
  self.assertIn("('Library status','clapperboard.png'",src)   # More › Library status in place of the pill's sheet
  self.assertNotIn('id="activity"',(BOOT/'resources/settings.xml').read_text())

 def test_write_deletes_the_old_pill_windows(self):
  with tempfile.TemporaryDirectory() as tmp:
   skin=Path(tmp)
   for folder in (portrait.FOLDER,'1080i'):
    (skin/folder).mkdir(parents=True,exist_ok=True)
    for name in skin_textures.OBSOLETE:(skin/folder/name).write_text('<window />')
   changed=portrait.write(skin,{}) or []
   for folder in (portrait.FOLDER,'1080i'):
    for name in skin_textures.OBSOLETE:self.assertFalse((skin/folder/name).exists(),folder+'/'+name)


class BurstErrors(unittest.TestCase):
 def test_a_burst_error_is_reported_once_while_shown(self):
  err=('[B]Elementum Burst[/B] errors','Torrentio: timed out')
  boxes=[None,err,err,err,None,err,('Elementum Burst','12 providers left')]
  seq=iter(boxes);said=[];state={'box':None}
  def wait(_):
   try:state['box']=next(seq);return False
   except StopIteration:return True
  background_box.watch(lambda:state['box'],said.append,wait)
  self.assertEqual(said,['Torrentio: timed out','Torrentio: timed out'])   # once, then again after the box closed
  self.assertEqual(background_box.burst_problem('Elementum Burst errors',''),'Some torrent sites did not answer')
  self.assertEqual(background_box.burst_problem('Elementum Burst','3 providers left'),'')

 def test_service_wires_it(self):
  src=(BOOT/'service.py').read_text()
  self.assertIn('target=background_box.watch',src);self.assertIn("'Elementum Burst'",src)


if __name__=='__main__':unittest.main()
