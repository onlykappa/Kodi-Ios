"""Local rig for the r11 portrait layout: desktop Kodi 21.3 (built from source) under Xvfb at the iPhone 16 Pro's
portrait safe area (402x778 pt at 1.5x = 603x1167), with the IPA's Fuse patches and portrait folder applied.

Rig only: iOS-only conditions are forced on, and add-ons Kodi's mirror would provide are stubbed so Fuse's
dependencies resolve. No touch gestures, safe areas or rotation; mouse clicks stand in for taps.
usage: portrait_rig.py --kodi-build DIR --addons DIR --fuse DIR --home DIR [--size 603x1167]
"""
import argparse,importlib.util,json,os,re,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
def module(name):
 spec=importlib.util.spec_from_file_location('rig_'+name,LIB/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
FUSE='skin.arctic.fuse.3'
TMDB_POPULAR={'home':'plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie',
 '1101':'plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&sort_by=popularity.desc',
 '1102':'plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&sort_by=popularity.desc'}

def prepare(addons,fuse,home):
 nav,portrait=module('navigation'),module('portrait')
 # Keep the profile (add-on database, Kodi's own guisettings) between runs: Kodi asks before enabling add-ons
 # it finds on disk, which a headless rig cannot answer on a fresh profile. Enable them once over JSON-RPC.
 kodi=home/'.kodi';shutil.rmtree(kodi/'addons',ignore_errors=True)
 (kodi/'addons').mkdir(parents=True);profile=kodi/'userdata'
 for src in Path(addons).iterdir():shutil.copytree(src,kodi/'addons'/src.name,symlinks=True)
 skin=kodi/'addons'/FUSE;shutil.copytree(fuse,skin)
 snap=ROOT/'snapshot/userdata'
 for rel in ['addon_data/script.skinvariables','addon_data/skin.arctic.fuse.3/settings.xml']:
  (profile/rel).parent.mkdir(parents=True,exist_ok=True)
  if (snap/rel).is_dir():shutil.copytree(snap/rel,profile/rel,dirs_exist_ok=True)
  else:shutil.copy2(snap/rel,profile/rel)
 nav.update_nodes(profile)
 # As on the phone: library spotlights become TMDb lists (navigation.phone_defaults does this at runtime).
 settings=profile/'addon_data/skin.arctic.fuse.3/settings.xml';text=settings.read_text()
 for hub,path in TMDB_POPULAR.items():
  text=re.sub(r'<setting id="HomeSwitcher\.%s\.Spotlight\.Path" type="string"\s*(/>|>[^<]*</setting>)'%re.escape(hub),'',text,flags=re.I)
  text=text.replace('</settings>','    <setting id="HomeSwitcher.%s.Spotlight.Path" type="string">%s</setting>\n</settings>'%(hub,path.replace('&','&amp;')))
 settings.write_text(text)
 nav.patch_skin(skin)
 portrait.build(skin,profile)
 for path in skin.rglob('*.xml'):
  data=path.read_text(errors='replace')
  if 'System.Platform.IOS' in data:path.write_text(data.replace('System.Platform.IOS','true'))
 gui=profile/'guisettings.xml'
 if gui.exists():
  text=re.sub(r'<setting id="lookandfeel.skin"[^>]*>[^<]*</setting>','<setting id="lookandfeel.skin">%s</setting>'%FUSE,gui.read_text())
  # As portrait.run_service sets once on the phone.
  text=re.sub(r'<setting id="filelists.showparentdiritems"[^>]*>[^<]*</setting>','<setting id="filelists.showparentdiritems">false</setting>',text)
  gui.write_text(text)
 else:gui.write_text('<settings version="2">\n<setting id="lookandfeel.skin">%s</setting>\n'
  '<setting id="addons.unknownsources">true</setting>\n<setting id="services.webserver">true</setting>\n'
  '<setting id="services.webserverauthentication">false</setting>\n<setting id="services.webserverport">8089</setting>\n</settings>\n'%FUSE)
 (profile/'advancedsettings.xml').write_text('<advancedsettings><loglevel>1</loglevel></advancedsettings>\n')
 return kodi

def launch(build,home,size,display=':5'):
 xvfb=subprocess.Popen(['Xvfb',display,'-screen','0',size+'x24','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 time.sleep(1.5)
 env=dict(os.environ,DISPLAY=display,HOME=str(home),KODI_HOME=str(build),LIBGL_ALWAYS_SOFTWARE='1')
 kodi=subprocess.Popen([str(Path(build)/'kodi-x11'),'--standalone','-fs'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 return xvfb,kodi

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['--kodi-build','--addons','--fuse','--home']:p.add_argument(name,type=Path,required=True)
 p.add_argument('--size',default='603x1167');p.add_argument('--prepare-only',action='store_true')
 a=p.parse_args();prepare(a.addons,a.fuse,a.home)
 if not a.prepare_only:
  xvfb,kodi=launch(a.kodi_build,a.home,a.size);print(json.dumps({'xvfb':xvfb.pid,'kodi':kodi.pid}))
