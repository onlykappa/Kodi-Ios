"""Host regression tests; these do not establish iPhone runtime success."""
import json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
from startup import generate,failure,FUSE
from navigation import patch_window
class Startup(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.skin=Path(self.tmp.name)
  (self.skin/'shortcuts').mkdir();(self.skin/'1080i').mkdir();self.calls=[]
  for name in ['skinvariables-splash.json','skinvariables-build-templates.json','skinviewtypes.json']:(self.skin/'shortcuts'/name).write_text('{}')
  (self.skin/'shortcuts/skinvariables-generator.json').write_text(json.dumps({'folder':'1080i','output':'script-skinvariables-generator-includes-{skinuser}.xml'}))
 def invoke(self,command):
  self.calls.append(command)
  if 'buildviews' in command:
   (self.skin/'1080i/script-skinviewtypes-includes.xml').write_text('<includes><expression name="ready">true</expression></includes>')
  else:
   (self.skin/'1080i/script-skinvariables-generator-includes-.xml').write_text('<includes>'+''.join('<include name="'+n+'"/>' for n in ['skinvariables-homewidgets-standard','skinvariables-homewidgets-standard-onunload','skinvariables-homewidgets-combined-info'])+'</includes>')
 def test_order_no_reload(self):
  result=generate(self.skin,lambda:FUSE,self.invoke,lambda _:False)
  self.assertTrue(result['shortcuts_verified']);self.assertFalse(result['phone_navigation_verified'])
  self.assertIn('buildviews',self.calls[0]);self.assertIn('buildtemplate',self.calls[1]);self.assertTrue(all('no_reload=true' in c for c in self.calls))
 def test_wrong_skin_refused(self):
  with self.assertRaises(RuntimeError):generate(self.skin,lambda:'skin.estuary',self.invoke,lambda _:False)
  self.assertEqual([],self.calls)
 def test_skin_change_aborts(self):
  def invoke(c):self.invoke(c);self.current='skin.estuary'
  self.current=FUSE
  with self.assertRaises(RuntimeError):generate(self.skin,lambda:self.current,invoke,lambda _:False)
  self.assertEqual(1,len(self.calls))
 def test_bad_json_before_invocation(self):
  (self.skin/'shortcuts/skinvariables-splash.json').write_text('')
  with self.assertRaises(ValueError):generate(self.skin,lambda:FUSE,self.invoke,lambda _:False)
  self.assertEqual([],self.calls)
 def test_stale_valid_xml_does_not_pass(self):
  self.invoke('buildviews');self.calls=[]
  with self.assertRaises(RuntimeError):generate(self.skin,lambda:FUSE,lambda c:self.calls.append(c),lambda _:False,timeout=.5)
  self.assertEqual(1,len(self.calls))
 def test_partial_output_waits(self):
  def invoke(c):(self.skin/'1080i/script-skinviewtypes-includes.xml').write_text('<includes>')
  with self.assertRaises(RuntimeError):generate(self.skin,lambda:FUSE,invoke,lambda _:False,timeout=.5)
 def test_cancel(self):
  with self.assertRaises(RuntimeError):generate(self.skin,lambda:FUSE,lambda c:None,lambda _:True)
 def test_upgrade_guards_helpers_and_remains_idempotent(self):
  source=b'<window><onload>RunScript(script.skinvariables)</onload><onload>AlarmClock(x,ReloadSkin(),00:00,silent)</onload><include>Action_BuildViews</include><controls/></window>'
  first=patch_window(source,'Home.xml');self.assertEqual(first,patch_window(first,'Home.xml'))
  root=ET.fromstring(first)
  for n in list(root.findall('onload'))[:2]+root.findall('include'):self.assertIn('KodiIOS.Activating',n.get('condition',''))
  old=first.replace(b'ios-touch-navigation-r8',b'ios-touch-navigation-r7');new=patch_window(old,'Home.xml')
  self.assertEqual(1,len(ET.fromstring(new).findall("controls/control[@id='98200']")));self.assertEqual(new,first)
 def test_error_evidence_does_not_leak_message(self):
  try:raise RuntimeError('https://private.invalid token=SECRET account@example.com')
  except RuntimeError as e:receipt=failure(e,'build_views')
  self.assertNotIn('SECRET',json.dumps(receipt));self.assertEqual('RuntimeError',receipt['error_type']);self.assertTrue(receipt['frames'])
if __name__=='__main__':unittest.main()
