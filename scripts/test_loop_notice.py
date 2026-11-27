"""The Loop's notice window as a portrait sheet (loop_notice.py): only the exact pinned file is replaced, and the control ids the
add-on drives stay (ISSUE-497)."""
import hashlib,os,sys,tempfile,unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','migration','bundled-bootstrap','resources','lib'))
import loop_notice

STAND_IN=b'<window><controls><control type="textbox" id="300"/></controls></window>'

class LoopNotice(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.dir=self.tmp.name
  os.makedirs(os.path.join(self.dir,os.path.dirname(loop_notice.RELATIVE)))
  self.path=os.path.join(self.dir,loop_notice.RELATIVE)
  self.write(STAND_IN);self.addon_xml('8.4')
  self.sha=loop_notice.ORIGINAL_SHA256;loop_notice.ORIGINAL_SHA256=hashlib.sha256(STAND_IN).hexdigest()
 def tearDown(self):loop_notice.ORIGINAL_SHA256=self.sha;self.tmp.cleanup()
 def write(self,data):
  with open(self.path,'wb') as f:f.write(data)
 def addon_xml(self,version):
  with open(os.path.join(self.dir,'addon.xml'),'w') as f:f.write('<?xml version="1.0"?>\n<addon id="plugin.video.the-loop" name="The Loop" version="%s">'%version)
 def read(self):
  with open(self.path,'rb') as f:return f.read()
 def test_replaces_the_pinned_file_once(self):
  self.assertTrue(loop_notice.hook(self.dir));self.assertIn(loop_notice.MARK.encode(),self.read())
  self.assertFalse(loop_notice.hook(self.dir),'second time: nothing to do')
 def test_keeps_the_ids_the_addon_drives(self):
  root=ET.fromstring(loop_notice.xml().split('\n',1)[1])   # without the XML declaration
  ids={c.get('id'):c.get('type') for c in root.iter('control') if c.get('id')}
  self.assertEqual(ids,{'300':'textbox','301':'scrollbar','302':'button'})
  self.assertEqual(root.findtext('defaultcontrol'),'302')
 def test_text_is_not_inside_the_zoom(self):
  # Kodi draws a font at one uniform size: inside a zoom that is not uniform it came out squashed (desktop rig).
  root=ET.fromstring(loop_notice.xml().split('\n',1)[1]);group=root.find('controls/control[@type="group"]')
  self.assertEqual([c.get('type') for c in group.iter('control') if c.get('type') in ('textbox','label','button')],[])
 def test_other_version_other_file_or_missing_is_left_alone(self):
  self.addon_xml('8.5');self.assertFalse(loop_notice.hook(self.dir));self.assertEqual(self.read(),STAND_IN)
  self.addon_xml('8.4');self.write(b'<window>changed by someone else</window>')
  self.assertFalse(loop_notice.hook(self.dir));self.assertEqual(self.read(),b'<window>changed by someone else</window>')
  self.assertFalse(loop_notice.hook(os.path.join(self.dir,'missing')))
 def test_watch_applies_when_the_addon_appears_later(self):
  folders=iter(['',self.dir]);logs=[];waits=[]
  def wait(seconds):
   waits.append(seconds);return len(waits)>=2
  loop_notice.watch(lambda:next(folders),wait,logs.append)
  self.assertEqual(logs,['loop: notice window restyled']);self.assertIn(loop_notice.MARK.encode(),self.read())

if __name__=='__main__':unittest.main()
