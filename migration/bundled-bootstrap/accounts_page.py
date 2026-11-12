"""Accounts page (the profile card at the top of Settings): Elementum, Umbrella, Google Drive, Trakt and TMDb Helper
with their sign-in state. Tapping a signed-in service opens its settings; otherwise it starts that add-on's sign-in.
The layout is portrait/IOSAccounts.xml, written by portrait.py (settings_page.py); this fills it."""
import os,sys,threading
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import accounts,page_wait

BACK=(9,10,92,110)   # parent dir, previous menu, nav back, back
ROW_BASE=9600        # service n is button 9600+n
LINK_BASE=9610       # accounts.LINKS[i] is button 9611+i

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 home=os.path.dirname(os.path.abspath(__file__))

 def installed(addon):return xbmc.getCondVisibility('System.HasAddon(%s)'%addon)
 def reader(addon):
  try:a=xbmcaddon.Addon(addon)
  except Exception:return lambda key:''
  def get(key):
   try:return a.getSetting(key)
   except Exception:return ''
  return get
 def drive_accounts():
  try:
   common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
   if common not in sys.path:sys.path.append(common)
   from clouddrive.common.account import AccountManager
   store=AccountManager(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.googledrive').getAddonInfo('profile')))
   return list((store.get_accounts() or {}).values())
  except Exception as error:
   xbmc.log('Kodi iOS accounts: Google Drive accounts unreadable: '+type(error).__name__,xbmc.LOGWARNING);return []
 def states():
  out=[]
  for s in accounts.SERVICES:
   ok=installed(s['addon'])
   out.append(accounts.status(s,ok,reader(s['addon']) if ok else (lambda key:''),drive_accounts() if ok and s.get('drive') else ()))
  return out

 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.stop=threading.Event();self.states=[];self.refresh()
   threading.Thread(target=self.loop,daemon=True).start()
  def refresh(self):
   self.states=states()
   props=accounts.properties(self.states,xbmc.getInfoLabel('System.ProfileName'),xbmc.getInfoLabel('System.ProfileThumb'))
   for key,value in props.items():self.setProperty(key,value)
  def loop(self):
   # Sign-ins finish in other windows (the add-on's settings, a code on trakt.tv); pick them up when they do.
   monitor=xbmc.Monitor()
   while not page_wait.idle(self.stop,monitor,2):
    if self.stop.is_set():break
    try:self.refresh()
    except Exception as error:_quiet('accounts_page:54',error)
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def finish(self):
   self.stop.set();self.close()
  def onClick(self,control):
   if control==9001:self.finish()
   elif ROW_BASE<control<=ROW_BASE+len(accounts.SERVICES):
    n=control-ROW_BASE
    if n<=len(self.states):xbmc.executebuiltin(self.states[n-1]['action'])
   elif LINK_BASE<control<=LINK_BASE+len(accounts.LINKS):
    xbmc.executebuiltin(accounts.LINKS[control-LINK_BASE-1][3])

 page=Page('IOSAccounts.xml',home,'Default','1080i')
 page.doModal()
 if hasattr(page,'stop'):page.stop.set()
 del page

if __name__=='__main__':run()

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass
