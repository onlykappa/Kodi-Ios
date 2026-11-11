"""Settings › Add-on Updates (RunScript(service.kodi.ios.bootstrap,addon_updates)), owner-approved mockup board 12.
portrait/IOSAddonUpdates.xml. With add-ons to update it lists them: tapping one opens Kodi's add-on list
(addons://outdated/), where it is updated. With none it says everything is up to date, when the check last ran, and
offers Check Now, which runs Kodi's UpdateAddonRepos and then reads the list again.

The list is Kodi's own addons://outdated/ directory, read with JSON-RPC Files.GetDirectory (the new version is not in
that listing, so rows say "Update available"). Pure logic: resources/lib/addon_outdated.py."""
import json,os,sys,threading,time
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import addon_outdated,settings_page

OPEN_LIST='ActivateWindow(addonbrowser,addons://outdated/,return)'
ROW_BASE=settings_page.UPDATE_ROW;CHECK=settings_page.UPDATE_CHECK;BACK=9001
BACK_KEYS=(9,10,92,110)
REFRESH_WAIT=5   # seconds given to Kodi's repository check before the list is read again (no completion callback exists)
STAMP_DIR='special://profile/addon_data/service.kodi.ios.bootstrap/'
STAMP=STAMP_DIR+'addon_updates.json'

def rpc(xbmc,method,params):
 """JSON-RPC result, or None when Kodi answers with an error."""
 answer=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 return None if 'error' in answer else answer.get('result') or {}

def outdated(xbmc):
 """[{'id','name','icon'}] of the outdated add-ons, or None when Kodi's list cannot be read."""
 result=rpc(xbmc,'Files.GetDirectory',{'directory':addon_outdated.LISTING,'media':'files','properties':['thumbnail']})
 return None if result is None else addon_outdated.updates(result.get('files'))

def read_stamp(xbmcvfs):
 try:
  with xbmcvfs.File(STAMP) as f:return addon_outdated.parse_stamp(f.read())
 except Exception:return None

def write_stamp(xbmc,xbmcvfs,now):
 try:
  xbmcvfs.mkdirs(STAMP_DIR)
  f=xbmcvfs.File(STAMP,'w')
  try:f.write(addon_outdated.stamp_text(now))
  finally:f.close()
 except Exception as error:xbmc.log('Kodi iOS Add-on Updates: check time not saved: '+type(error).__name__,xbmc.LOGWARNING)

def run():
 import xbmc,xbmcgui,xbmcvfs

 class Updates(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.then=None;self.checking=False;self.closed=threading.Event()
   self.setProperty('button','Check Now')
   self.show(stamp=read_stamp(xbmcvfs))
  def show(self,stamp):
   found=outdated(xbmc);rows=found or []
   self.setProperty('rows',str(min(len(rows),settings_page.UPDATE_ROWS)))
   for n in range(1,settings_page.UPDATE_ROWS+1):
    row=rows[n-1] if n<=len(rows) else {}
    self.setProperty('upd.%d.name'%n,row.get('name',''));self.setProperty('upd.%d.icon'%n,row.get('icon',''))
   self.setProperty('heading','Add-on List Unavailable' if found is None else 'Everything Is Up to Date')
   self.setProperty('checked',addon_outdated.status(stamp,time.time(),len(rows),failed=found is None))
  def check(self):
   if self.checking:return
   self.checking=True;self.setProperty('button','Checking…')
   threading.Thread(target=self.check_and_show,daemon=True).start()
  def check_and_show(self):
   xbmc.executebuiltin('UpdateAddonRepos')
   self.closed.wait(REFRESH_WAIT)
   now=time.time();write_stamp(xbmc,xbmcvfs,now)
   try:
    if not self.closed.is_set():self.show(stamp=now)
    if not self.closed.is_set():self.setProperty('button','Check Now')
   except Exception as error:xbmc.log('Kodi iOS Add-on Updates: page closed during the check: '+type(error).__name__,xbmc.LOGINFO)
   self.checking=False
  def onClick(self,control):
   if control in CHECK:self.check()
   elif ROW_BASE<control<=ROW_BASE+settings_page.UPDATE_ROWS:self.then=OPEN_LIST;self.finish()
   elif control==BACK:self.finish()
  def onAction(self,action):
   if action.getId() in BACK_KEYS:self.finish()
  def finish(self):
   self.closed.set();self.close()

 page=Updates('IOSAddonUpdates.xml',HERE,'Default','1080i')
 try:page.doModal()
 finally:page.closed.set()
 then=getattr(page,'then',None);del page
 if then:xbmc.executebuiltin(then)

if __name__=='__main__':run()
