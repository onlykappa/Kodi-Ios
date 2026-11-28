"""The Crew's version window as a portrait sheet (crew_notice.py): only the exact pinned files are replaced; the ids and window
properties The Crew uses stay (ISSUE-497)."""
import hashlib,os,sys,tempfile,unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','migration','bundled-bootstrap','resources','lib'))
import crew_notice as c

STAND_IN=b'<window><controls><control type="button" id="103"/></controls></window>'

class CrewNotice(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=self.tmp.name
  self.saved=dict(c.ORIGINAL_SHA256)
  for skin in c.SKINS:
   path=os.path.join(self.d,c.RELATIVE%skin);os.makedirs(os.path.dirname(path));open(path,'wb').write(STAND_IN)
   c.ORIGINAL_SHA256[skin]=hashlib.sha256(STAND_IN).hexdigest()
  self.addon('3.2.0')
 def tearDown(self):c.ORIGINAL_SHA256.update(self.saved);self.tmp.cleanup()
 def addon(self,version):
  with open(os.path.join(self.d,'addon.xml'),'w') as f:f.write('<?xml version="1.0"?>\n<addon id="script.thecrew.artwork" version="%s">'%version)
 def read(self,skin):
  with open(os.path.join(self.d,c.RELATIVE%skin),'rb') as f:return f.read()
 def test_replaces_every_skin_once(self):
  self.assertEqual(c.hook(self.d),list(c.SKINS))
  for skin in c.SKINS:self.assertIn(c.MARK.encode(),self.read(skin))
  self.assertEqual(c.hook(self.d),[],'second time: nothing to do')
 def test_keeps_the_ids_and_properties_the_crew_uses(self):
  text=c.xml();root=ET.fromstring(text.split('\n',1)[1])
  self.assertEqual({k.get('id') for k in root.iter('control') if k.get('id')},{'101','102','103'})
  self.assertEqual(root.findtext('defaultcontrol'),'103')
  for prop in ('version','announcement_type','highlight1','highlight2','highlight3','show_alpha_warning'):self.assertIn('Property(%s)'%prop,text)
  self.assertNotIn('qr',text.lower())
 def test_text_and_buttons_are_not_inside_the_zoom(self):
  root=ET.fromstring(c.xml().split('\n',1)[1]);group=root.find('controls/control[@type="group"]')
  self.assertEqual([k.get('type') for k in group.iter('control') if k.get('type') in ('textbox','label','button')],[])
 def test_other_version_or_a_changed_file_is_left_alone(self):
  self.addon('3.3.0');self.assertEqual(c.hook(self.d),[]);self.addon('3.2.0')
  with open(os.path.join(self.d,c.RELATIVE%'thecrew'),'wb') as f:f.write(b'<window>changed</window>')
  self.assertEqual(c.hook(self.d),['stylish','modern']);self.assertEqual(self.read('thecrew'),b'<window>changed</window>')
  self.assertEqual(c.hook(os.path.join(self.d,'missing')),[])
 def test_real_hashes_are_pinned(self):
  self.assertEqual(set(self.saved),set(c.SKINS));self.assertTrue(all(len(v)==64 for v in self.saved.values()))

if __name__=='__main__':unittest.main()
