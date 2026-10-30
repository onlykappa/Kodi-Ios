"""In-app updates from this repository's GitHub test builds (prereleases tagged build-N with a raw .ipa).
iOS cannot install an IPA from inside Kodi, so the update is saved where the Files app shows it and the
sideloader installs it from there."""
import json,re
from pathlib import Path
REPO='onlykappa/Kodi-Ios'
API='https://api.github.com/repos/'+REPO+'/releases?per_page=20'

def build_number(tag):
 match=re.fullmatch(r'build-(\d+)',tag or '');return int(match.group(1)) if match else None

def newest(releases,current):
 """The newest build-N release with an .ipa that is newer than the installed build, else None."""
 best=None
 for release in releases:
  number=build_number(release.get('tag_name'))
  assets=[a for a in release.get('assets',[]) if str(a.get('name','')).endswith('.ipa')]
  if number is None or not assets or release.get('draft'):continue
  if number>(current or 0) and (best is None or number>best['number']):
   best={'number':number,'name':release.get('name') or release['tag_name'],'asset':assets[0],'notes':release.get('body') or ''}
 return best

def headers(token,binary=False):
 values={'User-Agent':'Kodi-iOS-updater','Accept':'application/octet-stream' if binary else 'application/vnd.github+json'}
 if token:values['Authorization']='Bearer '+token
 return values

def updates_folder(home):
 """Documents is shared with the Files app on a sideloaded Kodi; fall back next to Kodi's home."""
 home=Path(home)
 for parent in [home,*home.parents]:
  if parent.name=='Documents':return parent/'Kodi Updates'
 return home.parent/'Kodi Updates'

def run(check_only=False):
 import urllib.parse,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');token=addon.getSettingString('github_token').strip()
 build=Path(addon.getAddonInfo('path'))/'build.json'
 current=json.loads(build.read_text()).get('build') if build.exists() else None
 def fetch(url,binary=False,progress=None,dest=None):
  # Kodi's own curl: Python TLS has failed on this device for some hosts.
  url=url+'|'+urllib.parse.urlencode(headers(token,binary))
  if dest is None:
   # readBytes() returns nothing without a Content-Length, which GitHub's API often omits; copy instead.
   temp=Path(xbmcvfs.translatePath('special://temp/'))/'kodi-ios-releases.json'
   try:return temp.read_bytes() if xbmcvfs.copy(url,str(temp)) else b''
   finally:
    if temp.exists():temp.unlink()
  f=xbmcvfs.File(url)
  try:
   size=f.size() or 0;done=0
   with open(dest,'wb') as out:
    while True:
     chunk=bytes(f.readBytes(1<<20))
     if not chunk:break
     out.write(chunk);done+=len(chunk)
     if progress and progress(done,size):return None
   return done
  finally:f.close()
 body=fetch(API)
 try:releases=json.loads(body or b'[]')
 except ValueError:releases=[]
 if not isinstance(releases,list):releases=[]
 if not releases:
  if not check_only:xbmcgui.Dialog().ok('Check for updates','Could not read GitHub releases. A private repository needs a read-only GitHub token in this add-on\'s settings (or make the repository public).')
  return None
 update=newest(releases,current)
 if update is None:
  if not check_only:xbmcgui.Dialog().ok('Check for updates','You have the newest build'+(' (build %d).'%current if current else '.'))
  return None
 if check_only:
  xbmcgui.Dialog().notification('Update available',update['name']+' — gear menu › Check for updates',time=8000);return update
 asset=update['asset'];size=int(asset.get('size') or 0)
 if not xbmcgui.Dialog().yesno('Update available','%s\n%.0f MB. Download it to the Files app now?'%(update['name'],size/1e6)):return None
 folder=updates_folder(xbmcvfs.translatePath('special://home/'));folder.mkdir(parents=True,exist_ok=True)
 dest=folder/asset['name'];temp=dest.with_suffix('.part')
 progress=xbmcgui.DialogProgress();progress.create('Downloading update',update['name'])
 def report(done,total):
  progress.update(int(done*100/(total or size or 1)),'%.0f of %.0f MB'%(done/1e6,(total or size)/1e6));return progress.iscanceled()
 try:
  url=asset['url'] if token else asset['browser_download_url']
  got=fetch(url,binary=True,progress=report,dest=temp)
 finally:progress.close()
 if not got or (size and got!=size):
  if temp.exists():temp.unlink()
  if got is not None:xbmcgui.Dialog().ok('Update not downloaded','The download did not complete. Try again on Wi-Fi.')
  return None
 temp.replace(dest)
 xbmcgui.Dialog().ok('Update downloaded','Saved to Files › On My iPhone › Kodi › Kodi Updates › '+dest.name+'\n\nOpen your sideloader (SideStore/AltStore), tap + and pick that file to install it as an update.')
 return dest
