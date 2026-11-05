"""r11 portrait mode, applied to the staged Kodi.app by build_customized_ipa.py.

- Info.plist: launch in portrait; landscape stays listed for fullscreen video only (no upside down).
- Fuse: add the generated `portrait` skin folder (migration/bundled-bootstrap/resources/lib/portrait.py).
- Optionally swap in the Kodi executable built by .github/workflows/kodi-ios-portrait.yml from the same 21.3 tag
  with migration/ios-portrait/kodi-21.3-portrait.patch; without it the app keeps the official, landscape-only one.
- Optionally add KodiGlassBar.framework (migration/glassbar-ios): the native Liquid Glass tab bar.
- No logo -> splash -> menu sequence at launch: the launch screen's Kodi logo becomes black (black_launch_screen) and
  Kodi's own "KODI 21.3 OMEGA" splash is turned off for every install (disable_splash, run by build_customized_ipa).
All optional inputs come from one directory written by `ios_portrait.py --fetch DIR` (pinned releases only).
"""
import argparse,hashlib,importlib.util,io,json,plistlib,shutil,struct,sys,zipfile,zlib
import xml.etree.ElementTree as ET
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

def black_png(width,height):
 """An all-black RGB PNG of the given size (zero rows compress to a few KB)."""
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 raw=(b'\x00'+b'\x00'*3*width)*height
 return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
         chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))

def png_size(data):
 """(width, height) from IHDR; Xcode's PNG compression may put Apple's CgBI chunk in front of it."""
 assert data[:8]==b'\x89PNG\r\n\x1a\n','Not a PNG'
 at=8
 while at+8<=len(data):
  length,kind=struct.unpack('>I4s',data[at:at+8])
  if kind==b'IHDR':return struct.unpack('>II',data[at+8:at+16])
  at+=12+length
 raise AssertionError('PNG without IHDR')

def black_launch_screen(app):
 """Kodi's LaunchScreen storyboard (xbmc/platform/darwin/ios/LaunchScreen.storyboard, compiled in the official
 package) is a black view with one image view showing applaunch_screen.png, the Kodi logo. The same picture in black,
 same size, makes the launch screen plain black like the first frames Kodi draws, without a new storyboard (that
 needs Xcode's ibtool). iOS may keep its cached launch snapshot until the app is updated or the phone restarts."""
 changed=[]
 for path in sorted(Path(app).glob('applaunch_screen*.png')):
  data=path.read_bytes();black=black_png(*png_size(data))
  if data!=black:path.write_bytes(black)
  changed.append({'path':path.name,'before_sha256':sha(data),'after_sha256':sha(black)})
 return changed

SPLASH_OFF='<splash>false</splash>'
def disable_splash(system):
 """special://xbmc/system/advancedsettings.xml inside the app: Kodi reads it before the profile's own
 advancedsettings.xml (CAdvancedSettings::Load), so it applies to new and existing installs alike, and an owner's own
 file can still override it. <splash>false</splash> makes CRenderSystemBase::ShowSplash skip the picture (messages
 such as a database upgrade still show)."""
 path=Path(system)/'advancedsettings.xml'
 if path.exists():
  root=ET.fromstring(path.read_bytes());assert root.tag=='advancedsettings','Unexpected system advancedsettings.xml'
  splash=root.find('splash')
  if splash is None:splash=ET.SubElement(root,'splash')
  splash.text='false';data=ET.tostring(root,encoding='utf-8')+b'\n'
 else:
  data=('<advancedsettings version="1.0">\n  <!-- Kodi-iOS: no "KODI 21.3 OMEGA" splash between the launch screen and Home -->\n'
        '  %s\n</advancedsettings>\n'%SPLASH_OFF).encode()
 path.write_bytes(data)
 return {'path':path.name,'sha256':sha(data)}

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
 skin=Path(skin);addon=skin/'addon.xml'
 # Existing skin files the build overwrites (addon.xml, and in 1080i the video controls and seek bar).
 before={str(p.relative_to(skin)):sha(p.read_bytes()) for p in skin.rglob('*') if p.is_file()}
 files=portrait.build(skin,profile)
 changed=[{'path':'addons/'+skin.name+'/'+rel,'before_sha256':before[rel],'after_sha256':sha((skin/rel).read_bytes())}
          for rel in sorted(set(files)|{'addon.xml'}) if rel in before and before[rel]!=sha((skin/rel).read_bytes())]
 inputs=Path(inputs) if inputs else None
 exe=inputs/'Kodi' if inputs and (inputs/'Kodi').is_file() else None
 bar=inputs/'KodiGlassBar.framework.zip' if inputs and (inputs/'KodiGlassBar.framework.zip').is_file() else None
 return {'revision':portrait.REVISION,'orientations':allow_portrait(app),'skin_files':len(files),'changed':changed,
         'executable':swap_executable(app,exe,(inputs/'Kodi.sha256').read_text().split()[0]) if exe else None,
         'glassbar':add_glassbar(app,bar) if bar else None,'launch_screen':black_launch_screen(app)}

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
