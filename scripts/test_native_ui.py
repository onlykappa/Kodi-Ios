"""The bottom bar must request display without waiting for setup, feed add-ons or the first polling interval."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import native_ui

class Lib:
 def __init__(self):self.calls=[]
 def kodi_glassbar_show(self,v):self.calls.append(('show',v))
 def kodi_glassbar_select(self,i):self.calls.append(('select',i))
 def kodi_glassbar_take_tap(self):return -1

class Kodi:
 LOGINFO=1;LOGWARNING=2
 def __init__(self,portrait=True):self.logs=[];self.commands=[];self.portrait=portrait
 def log(self,s,level):self.logs.append(s)
 def getSkinDir(self):return 'skin.arctic.fuse.3'
 def getInfoLabel(self,key):return str(2000 if key.endswith('Height') and self.portrait else 1000)
 def getCondVisibility(self,key):return key.startswith('Window.IsActive(home)')
 def executebuiltin(self,command):self.commands.append(command)

class NativeUI(unittest.TestCase):
 def run_ui(self,kodi,lib,path='/app/framework'):
  class VFS:
   @staticmethod
   def translatePath(path):return '/app/'
  test=self
  class Monitor:
   def waitForAbort(self,seconds):
    if kodi.portrait and path:test.assertIn(('show',1),lib.calls,'bar waited for the polling sleep')
    return True
  # In the early path no provider or GUI module is available; an older framework has no native search field.
  with patch.object(native_ui.glassbar,'library_path',return_value=path),patch.object(native_ui.glassbar,'load',return_value=lib),patch.dict(sys.modules,{'xbmcaddon':None,'xbmcgui':None}):
   native_ui.run(kodi,VFS(),Monitor())
 def test_show_requested_before_first_wait_without_provider_or_gui_modules(self):
  kodi=Kodi();lib=Lib();self.run_ui(kodi,lib)
  self.assertEqual(lib.calls,[('select',0),('show',1),('show',0)])
  self.assertTrue(any('show requested' in s for s in kodi.logs))
 def test_landscape_does_not_show_the_menu_bar(self):
  kodi=Kodi(False);lib=Lib();self.run_ui(kodi,lib)
  self.assertNotIn(('show',1),lib.calls)
 def test_missing_framework_restores_the_skin_bar(self):
  kodi=Kodi();kodi.getCondVisibility=lambda key:True
  lib=Lib();self.run_ui(kodi,lib,path=None)
  self.assertIn('Skin.Reset(Portrait.NativeTabBar)',kodi.commands);self.assertEqual(lib.calls,[])
 def test_failed_framework_load_restores_the_skin_bar(self):
  kodi=Kodi()
  with patch.object(native_ui.glassbar,'library_path',return_value='/app/framework'),patch.object(native_ui.glassbar,'load',side_effect=OSError('cannot load')):
   native_ui.run(kodi,type('VFS',(),{'translatePath':staticmethod(lambda path:'/app/')}),None)
  self.assertIn('Skin.Reset(Portrait.NativeTabBar)',kodi.commands)
 def test_early_entrypoint_excludes_recovery_and_runs_before_heavy_imports(self):
  service=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  start=service.index('target=native_ui.run')
  self.assertIn("__name__=='__main__'",service[:start]);self.assertIn("sys.argv[1]=='--recover'",service[:start])
  self.assertLess(start,service.index('from bootstrap import'))
  self.assertIn("'native_ui_started':_EARLY_UI_STARTED",service)

if __name__=='__main__':unittest.main()
