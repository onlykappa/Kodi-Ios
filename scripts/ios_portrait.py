"""r11 portrait mode, applied to the staged Kodi.app by build_customized_ipa.py.

- Info.plist: launch in portrait; landscape stays listed for fullscreen video only (no upside down).
- Fuse: add the generated `portrait` skin folder (migration/bundled-bootstrap/resources/lib/portrait.py).
- Optionally swap in the Kodi executable built by .github/workflows/kodi-ios-portrait.yml from the same 21.3 tag
  with migration/ios-portrait/kodi-21.3-portrait.patch; without it the app keeps the official, landscape-only one.
- Optionally add KodiGlassBar.framework (migration/glassbar-ios): the native Liquid Glass tab bar.
All optional inputs come from one directory written by `ios_portrait.py --fetch DIR` (pinned releases only).
"""
import argparse,hashlib,importlib.util,io,json,plistlib,shutil,sys,zipfile
from pathlib import Path
from inspect_ios_foundation import macho
ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location('ipa_portrait',ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py')
portrait=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(portrait)
PORTRAIT='UIInterfaceOrientationPortrait'
def sha(data):return hashlib.sha256(data).hexdigest()

def allow_portrait(app):
 """Launch upright: the menus are portrait only. Landscape stays listed only so fullscreen video can turn;
 the patched controller allows it only while video plays (no upside down)."""
 path=Path(app)/'Info.plist';info=plistlib.loads(path.read_bytes())
 info['UISupportedInterfaceOrientations']=[PORTRAIT,'UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']
 info['UIInterfaceOrientation']=PORTRAIT
 path.write_bytes(plistlib.dumps(info,fmt=plistlib.FMT_BINARY))
 return info['UISupportedInterfaceOrientations']

def swap_executable(app,executable,expected_sha256=None):
 app=Path(app);name=plistlib.loads((app/'Info.plist').read_bytes())['CFBundleExecutable'];target=app/name
 new=Path(executable).read_bytes();old=target.read_bytes()
 if expected_sha256:assert sha(new)==expected_sha256,'Portrait Kodi executable hash mismatch'
 # Same tag, same bundle. A different Xcode may link a slightly different set of system libraries, so require
 # what can actually fail at launch: every load is an iOS system library or a framework this app ships.
 names=lambda data:{d['name'] for d in macho(data)['dylib_loads']}
 loads,official=names(new),names(old)
 for lib in sorted(loads-official):
  if lib.startswith(('/System/Library/','/usr/lib/')):continue
  shipped=next((app/'Frameworks'/lib[len(p):] for p in ('@rpath/','@executable_path/Frameworks/') if lib.startswith(p)),None)
  assert shipped and shipped.is_file(),'Portrait executable needs %s, which the app lacks'%lib
 target.write_bytes(new)
 return {'path':name,'official_sha256':sha(old),'portrait_sha256':sha(new),
         'dylibs_added':sorted(loads-official),'dylibs_dropped':sorted(official-loads)}

GLASSBAR=ROOT/'migration/glassbar-ios/source-lock.json'
EXECUTABLE=ROOT/'migration/ios-portrait/source-lock.json'
RELEASES='https://github.com/onlykappa/Kodi-Ios/releases/download/'

def add_glassbar(app,archive):
 """Unpack KodiGlassBar.framework into Kodi.app/Frameworks (never over an existing one)."""
 frameworks=Path(app)/'Frameworks';frameworks.mkdir(exist_ok=True)
 assert not (frameworks/'KodiGlassBar.framework').exists(),'Glass bar framework collision'
 with zipfile.ZipFile(archive) as z:
  names=z.namelist();assert all(n.startswith('KodiGlassBar.framework/') for n in names),'Unexpected glass bar archive'
  z.extractall(frameworks)
 binary=frameworks/'KodiGlassBar.framework/KodiGlassBar'
 return {'framework':'Frameworks/KodiGlassBar.framework','sha256':sha(binary.read_bytes())}

def apply(app,skin,profile,inputs=None):
 """Returns {'orientations','skin_files','changed','executable','glassbar'}; 'changed' lists existing skin files it
 edited. inputs: directory from fetch() (optional Kodi + Kodi.sha256, KodiGlassBar.framework.zip)."""
 addon=Path(skin)/'addon.xml';before=addon.read_bytes()
 files=portrait.build(skin,profile)
 changed=[{'path':'addons/'+Path(skin).name+'/addon.xml','before_sha256':sha(before),'after_sha256':sha(addon.read_bytes())}]
 inputs=Path(inputs) if inputs else None
 exe=inputs/'Kodi' if inputs and (inputs/'Kodi').is_file() else None
 bar=inputs/'KodiGlassBar.framework.zip' if inputs and (inputs/'KodiGlassBar.framework.zip').is_file() else None
 return {'revision':portrait.REVISION,'orientations':allow_portrait(app),'skin_files':len(files),'changed':changed,
         'executable':swap_executable(app,exe,(inputs/'Kodi.sha256').read_text().split()[0]) if exe else None,
         'glassbar':add_glassbar(app,bar) if bar else None}

def fetch(out,get=None):
 """Download the pinned native pieces that are published; skip any not pinned yet (the IPA still builds)."""
 if get is None:
  sys.path.insert(0,str(ROOT/'scripts'));from fetch_elementum_inputs import fetch as get
 out=Path(out);out.mkdir(parents=True,exist_ok=True);got=[]
 bar=json.loads(GLASSBAR.read_text())['framework_release']
 if bar.get('sha256'):
  data=get(RELEASES+bar['tag']+'/'+bar['asset']);assert sha(data)==bar['sha256'],'Glass bar digest mismatch'
  (out/'KodiGlassBar.framework.zip').write_bytes(data);got.append('KodiGlassBar')
 exe=json.loads(EXECUTABLE.read_text()).get('executable_release',{})
 if exe.get('sha256'):
  data=get(RELEASES+exe['tag']+'/'+exe['asset'])
  with zipfile.ZipFile(io.BytesIO(data)) as z:binary=z.read('Kodi')
  assert sha(binary)==exe['sha256'],'Portrait executable digest mismatch'
  (out/'Kodi').write_bytes(binary);(out/'Kodi.sha256').write_text(exe['sha256']+'  Kodi\n');got.append('Kodi')
 return got

if __name__=='__main__':
 p=argparse.ArgumentParser(description='Fetch the pinned portrait inputs for the IPA build.')
 p.add_argument('--fetch',type=Path,required=True);print(json.dumps({'fetched':fetch(p.parse_args().fetch)}))
