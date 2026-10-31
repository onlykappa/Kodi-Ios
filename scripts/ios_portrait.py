"""r11 portrait mode, applied to the staged Kodi.app by build_customized_ipa.py.

- Info.plist: allow portrait (upside down stays off, as on Face ID iPhones).
- Fuse: add the generated `portrait` skin folder (migration/bundled-bootstrap/resources/lib/portrait.py).
- Optionally swap in the Kodi executable built by .github/workflows/kodi-ios-portrait.yml from the same 21.3 tag
  with migration/ios-portrait/kodi-21.3-portrait.patch; without it the app keeps the official, landscape-only one.
"""
import hashlib,importlib.util,plistlib
from pathlib import Path
from inspect_ios_foundation import macho
ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location('ipa_portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
portrait=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(portrait)
PORTRAIT='UIInterfaceOrientationPortrait'
def sha(data):return hashlib.sha256(data).hexdigest()

def allow_portrait(app):
 path=Path(app)/'Info.plist';info=plistlib.loads(path.read_bytes())
 orientations=info.setdefault('UISupportedInterfaceOrientations',[])
 if PORTRAIT not in orientations:orientations.insert(0,PORTRAIT)
 path.write_bytes(plistlib.dumps(info,fmt=plistlib.FMT_BINARY))
 return orientations

def swap_executable(app,executable,expected_sha256=None):
 app=Path(app);name=plistlib.loads((app/'Info.plist').read_bytes())['CFBundleExecutable'];target=app/name
 new=Path(executable).read_bytes();old=target.read_bytes()
 if expected_sha256:assert sha(new)==expected_sha256,'Portrait Kodi executable hash mismatch'
 # Same tag, same bundle: the rebuilt executable must load exactly the libraries the official one does.
 assert sorted(macho(new)['dylib_loads'])==sorted(macho(old)['dylib_loads']),'Portrait executable links different libraries'
 target.write_bytes(new)
 return {'path':name,'official_sha256':sha(old),'portrait_sha256':sha(new)}

def apply(app,skin,profile,executable=None,expected_sha256=None):
 """Returns {'orientations','skin_files','changed','executable'}; 'changed' lists existing skin files it edited."""
 addon=Path(skin)/'addon.xml';before=addon.read_bytes()
 files=portrait.build(skin,profile)
 changed=[{'path':'addons/'+Path(skin).name+'/addon.xml','before_sha256':sha(before),'after_sha256':sha(addon.read_bytes())}]
 return {'revision':portrait.REVISION,'orientations':allow_portrait(app),'skin_files':len(files),'changed':changed,
         'executable':swap_executable(app,executable,expected_sha256) if executable else None}
