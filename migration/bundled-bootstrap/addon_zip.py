"""Install from zip file (RunScript(service.kodi.ios.bootstrap,addon_zip[,path])): the add-ons page's zip route, owner-approved
docs/design/addon-install-mockups.html frames 1 to 3, 6 and 7. A sheet lists the zips Kodi can see (and "Choose from Files"
when the app has the iPhone Files picker), the chosen one is read and confirmed, then unpacked into the add-ons folder, Kodi
installs what it still needs, and the add-on is switched on. The logic is resources/lib/zip_install.py. With a path argument
the chooser is skipped (rig tests)."""
import os,sys,time
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import zip_install

PICK_WAIT=600     # seconds the Files picker may stay open
DEP_WAIT=180      # seconds each dependency may take
TITLE='Install from zip file'

def roots(xbmcvfs):
 from pathlib import Path
 home=Path(xbmcvfs.translatePath('special://home/'))
 docs=next((p for p in (home,*home.parents) if p.name=='Documents'),home.parent)
 return [(str(docs/'Inbox'),'Shared with Kodi'),(str(docs),'Kodi folder')]

def picker():
 """The framework's iPhone Files picker (kodi_pick_zip / kodi_pick_take) when this build has it, else None."""
 import ctypes,xbmcvfs
 try:
  import glassbar
  path=glassbar.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=glassbar.load(path) if path else None
 except Exception:return None
 if lib is None or not (hasattr(lib,'kodi_pick_zip') and hasattr(lib,'kodi_pick_take')):return None
 lib.kodi_pick_zip.argtypes=[];lib.kodi_pick_zip.restype=None
 lib.kodi_pick_take.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_pick_take.restype=ctypes.c_int
 return lib

def pick_from_files(lib,xbmc):
 """Opens the Files picker and waits for a zip: its path, or '' when cancelled. The picker hands back a copy the app owns."""
 import ctypes
 lib.kodi_pick_zip();buffer=ctypes.create_string_buffer(2048);monitor=xbmc.Monitor();end=time.monotonic()+PICK_WAIT
 while time.monotonic()<end and not monitor.waitForAbort(0.3):
  state=lib.kodi_pick_take(buffer,len(buffer))
  if state==1:return buffer.value.decode('utf-8','replace')
  if state in (2,-1):return ''
 return ''

def rpc(xbmc,method,params):
 import json
 answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 return None if 'error' in answer else (answer.get('result') or {})

def installed_ids(xbmc):
 result=rpc(xbmc,'Addons.GetAddons',{'installed':True}) or {}
 return {a.get('addonid') for a in result.get('addons',[])}

def choose_file(xbmc,xbmcgui,xbmcvfs,lib):
 """The zip to install ('' when the person backs out)."""
 import choice_sheet
 found=zip_install.find_zips(roots(xbmcvfs));rows=[];targets=[]
 if lib is not None:
  rows.append({'label':'Choose from Files','detail':'Downloads, iCloud Drive and other apps','tint':'FF0A84FF','glyph':'folder-open-regular.png'});targets.append(None)
 for item in found:
  # The add-on's own name and version when the zip is one (a file name has no spaces, so it cannot wrap and would be cut short).
  info=zip_install.inspect(item['path'])
  label=info['name'] if info['ok'] else item['name'][:-4].replace('.',' ').replace('_',' ').replace('-',' ')
  facts=[info['version']] if info['ok'] and info['version'] else []
  facts+=[zip_install.size_text(item['size']),zip_install.when_text(item['mtime']),item['where']]
  rows.append({'label':label,'detail':' · '.join(facts),'tint':'FFFF9F0A','glyph':'file-zipper.png'});targets.append(item['path'])
 if not rows:
  xbmcgui.Dialog().ok(TITLE,'No zip files yet. Send one to Kodi with Share or AirDrop, or copy it into the Kodi folder with the Files app.')
  return ''
 spec={'heading':TITLE,'sub':'Pick the file to install','rows':rows,
       'foot':'Zips sent with Share or AirDrop and ones copied into the Kodi folder are listed, newest first.'}
 index=choice_sheet.choose(spec,xbmcgui=xbmcgui,xbmc=xbmc)
 if not 0<=index<len(rows):return ''
 return pick_from_files(lib,xbmc) if targets[index] is None else targets[index]

def allow_unknown_sources(xbmc,xbmcgui):
 current=rpc(xbmc,'Settings.GetSettingValue',{'setting':'addons.unknownsources'})
 if current is None or current.get('value'):return True
 if not xbmcgui.Dialog().yesno('Allow add-ons from zip files?',"Kodi is set to block add-ons that don't come from a repository. Allow it for this install?",nolabel='Not now',yeslabel='Allow'):
  return False
 rpc(xbmc,'Settings.SetSettingValue',{'setting':'addons.unknownsources','value':True})
 return True

def wait_for(xbmc,condition,seconds,cancelled=lambda:False):
 """True when `condition` holds before the time is up; False on time-out, Cancel or Kodi quitting."""
 monitor=xbmc.Monitor();end=time.monotonic()+seconds
 while time.monotonic()<end:
  if condition():return True
  if cancelled() or monitor.waitForAbort(0.5):return False
 return False

def install(xbmc,xbmcgui,xbmcvfs,path,info):
 """Unpack, let Kodi see it, install what it needs, switch it on. (True, '') or (False, plain-words reason)."""
 import shutil
 progress=xbmcgui.DialogProgress();progress.create('Installing %s'%info['name'],'Unpacking');unpacked=[]
 def undo():
  # A failed install leaves nothing behind: the unpacked folder goes and Kodi looks again.
  for folder in unpacked:shutil.rmtree(folder,ignore_errors=True)
  if unpacked:xbmc.executebuiltin('UpdateLocalAddons')
 try:
  addons=xbmcvfs.translatePath('special://home/addons/')
  unpacked.append(zip_install.unpack(path,info['folder'],addons));progress.update(25,'Adding it to Kodi')
  xbmc.executebuiltin('UpdateLocalAddons')
  if not wait_for(xbmc,lambda:info['id'] in installed_ids(xbmc),15):undo();return False,'Kodi did not pick the add-on up.'
  need=zip_install.missing(info['requires'],installed_ids(xbmc))
  for n,dep in enumerate(need):
   progress.update(40+50*n//max(1,len(need)),'Adding what it needs: %d of %d'%(n+1,len(need)))
   xbmc.executebuiltin('InstallAddon(%s)'%dep)
   if not wait_for(xbmc,lambda:dep in installed_ids(xbmc),DEP_WAIT,progress.iscanceled):
    undo()
    if progress.iscanceled():return None,''
    xbmc.log('Kodi iOS zip install: dependency %s was not installed'%dep,xbmc.LOGWARNING)
    return False,'One of the add-ons it needs could not be installed. Check your connection and try again.'
  progress.update(95,'Switching it on')
  rpc(xbmc,'Addons.SetAddonEnabled',{'addonid':info['id'],'enabled':True})
  return True,''
 except Exception as error:
  xbmc.log('Kodi iOS zip install: %s'%type(error).__name__,xbmc.LOGWARNING);undo()
  return False,'The add-on could not be installed from this file.'
 finally:
  progress.close()

def run(argv=None):
 import xbmc,xbmcgui,xbmcvfs
 argv=argv if argv is not None else sys.argv[1:]
 lib=None if argv else picker()
 path=argv[0] if argv else choose_file(xbmc,xbmcgui,xbmcvfs,lib)
 if not path:return
 while True:
  info=zip_install.inspect(path)
  if not info['ok']:
   xbmcgui.Dialog().ok(TITLE,info['reason']);return
  need=zip_install.missing(info['requires'],installed_ids(xbmc))
  lines=['%s.'%zip_install.describe(info)]
  if need:lines.append('It also needs %d more add-on%s.'%(len(need),'' if len(need)==1 else 's'))
  lines.append('Only install add-ons from people you trust. An add-on can read what you watch and use the internet.')
  if not xbmcgui.Dialog().yesno('Install %s?'%info['name'],'[CR]'.join(lines),nolabel='Cancel',yeslabel='Install'):return
  if not allow_unknown_sources(xbmc,xbmcgui):return
  ok,reason=install(xbmc,xbmcgui,xbmcvfs,path,info)
  if ok is None:return   # cancelled: nothing was changed
  if ok:
   if xbmcgui.Dialog().yesno('Installed %s'%info['name'],'It is installed and switched on.',nolabel='Done',yeslabel='Open'):
    xbmc.executebuiltin('RunAddon(%s)'%info['id'])
   return
  if not xbmcgui.Dialog().yesno('Could not install',reason+'[CR]Nothing was changed.',nolabel='Close',yeslabel='Try again'):return

if __name__=='__main__':run()
