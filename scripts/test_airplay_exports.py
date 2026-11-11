"""ISSUE-161: every native AirPlay function the Python side calls must be in the framework's exported-symbols list.
Build 224 shipped kodi_airplay_startup_budget unexported, so cast.py fell back to 60 s and cancelled Umbrella
AirPlay while the native side still had its 100 s startup window."""
import glob,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def exports(sh):
 lists=re.findall(r"printf '([^']*)' >>? \"\$WORK/exports\"",sh)
 return set(re.findall(r'_(kodi_\w+)\\n',''.join(lists)))

class Exports(unittest.TestCase):
 def setUp(self):
  self.sh=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text();self.exp=exports(self.sh)
 def test_every_public_native_function_is_exported(self):
  defined=set(re.findall(r'visibility\("default"\)\)\)\s+[\w\s\*]+?\b(kodi_(?:airplay|background)_\w+)\s*\(',self.sh))
  self.assertTrue(defined);self.assertEqual(sorted(defined-self.exp),[])
 def test_every_airplay_function_python_calls_is_exported(self):
  used=set()
  for f in glob.glob(str(ROOT/'migration/bundled-bootstrap/**/*.py'),recursive=True):
   used|=set(re.findall(r'lib\.(kodi_(?:airplay|background)_\w+)',Path(f).read_text(encoding='utf-8')))
  self.assertIn('kodi_airplay_startup_budget',used);self.assertEqual(sorted(used-self.exp),[])

if __name__=='__main__':unittest.main()
