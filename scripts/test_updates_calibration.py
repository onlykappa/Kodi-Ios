import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'migration/bundled-bootstrap/resources/lib'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
updates=load('updates');calibration=load('calibration')
RES='<settings><resolutions><resolution><description>2622x1206 @ 60.00Hz - Full Screen</description><overscan><left>{l}</left><top>0</top><right>{r}</right><bottom>1206</bottom></overscan></resolution></resolutions></settings>'
class Updates(unittest.TestCase):
 def test_picks_newest_newer_build_with_an_ipa(self):
  rel=[{'tag_name':'build-21','assets':[{'name':'a.ipa'}]},{'tag_name':'build-23','assets':[{'name':'b.ipa'}]},{'tag_name':'build-24','assets':[]},{'tag_name':'v9','assets':[{'name':'c.ipa'}]},{'tag_name':'build-30','draft':True,'assets':[{'name':'d.ipa'}]}]
  self.assertEqual(updates.newest(rel,22)['number'],23);self.assertIsNone(updates.newest(rel,23));self.assertEqual(updates.newest(rel,None)['number'],23)
 def test_token_only_when_set_and_binary_accept(self):
  self.assertNotIn('Authorization',updates.headers(''));self.assertEqual(updates.headers('t',True)['Authorization'],'Bearer t');self.assertEqual(updates.headers('',True)['Accept'],'application/octet-stream')
 def test_saved_where_the_files_app_shows_it(self):
  self.assertEqual(str(updates.updates_folder('/var/x/Documents/.kodi')),'/var/x/Documents/Kodi Updates')
class Calibration(unittest.TestCase):
 def test_detects_only_changed_calibration(self):
  with tempfile.TemporaryDirectory() as t:
   g=Path(t)/'guisettings.xml'
   g.write_text(RES.format(l=0,r=2622));self.assertFalse(calibration.changed(g))
   g.write_text(RES.format(l=0,r=2100));self.assertTrue(calibration.changed(g))
   g.write_text(RES.format(l=12,r=2622));self.assertTrue(calibration.changed(g))
   g.write_text('<settings><resolutions/></settings>');self.assertFalse(calibration.changed(g))
 def test_resets_once_through_kodis_own_dialog_and_saves_by_leaving(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'guisettings.xml').write_text(RES.format(l=0,r=2100));calls=[]
   active=lambda cond:cond=='Window.IsActive(screencalibration)'
   self.assertEqual(calibration.reset_once(p,calls.append,active,lambda s:False),'OFFERED')
   self.assertEqual(calls,['ActivateWindow(screencalibration)','Action(resetcalibration)','Action(Back)'])
   self.assertEqual(calibration.reset_once(p,calls.append,active,lambda s:False),'DONE BEFORE');self.assertEqual(len(calls),3)
if __name__=='__main__':unittest.main()
