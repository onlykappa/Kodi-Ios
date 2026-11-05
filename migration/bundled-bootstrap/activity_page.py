"""Taps on the activity pill (portrait/Custom_1187_Activity.xml).

 activity_page.py          the Activity sheet (portrait/IOSActivity.xml): every running job with its own bar
 activity_page.py,pause    pause or resume the one Elementum download the pill shows
The bootstrap service (activity.watch) keeps Window(Home).Property(Activity.*) current; this only reads it."""
import os,sys,threading
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import activity,notices

BACK=(9,10,92,110)
PAUSE_BASE=9610   # row n's pause button is 9610+n
BAR_BASE=9620     # row n's progress bar is 9620+n

def toggle(window,prefix):
 """Pause or resume the Elementum download behind `prefix` (Activity. or Activity.<n>.)."""
 torrent=window.getProperty(prefix+('PauseId' if prefix==activity.PREFIX else 'Id'))
 command=window.getProperty(prefix+'Pause')
 if not torrent or command not in ('pause','resume'):return False
 ok=notices.engine_action(command,torrent)
 # Show the new state at once; the service confirms it from the engine within two seconds.
 if ok:window.setProperty(prefix+'Pause','resume' if command=='pause' else 'pause')
 return ok

def run(args):
 import xbmc,xbmcgui
 home=xbmcgui.Window(10000)
 if args[:1]==['pause']:
  if not toggle(home,activity.PREFIX):xbmcgui.Dialog().notification('Elementum','The download engine did not answer',xbmcgui.NOTIFICATION_WARNING,3000)
  return
 here=os.path.dirname(os.path.abspath(__file__))

 class Sheet(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.stop=threading.Event();self.bars()
   threading.Thread(target=self.loop,daemon=True).start()
  def bars(self):
   for n in range(1,activity.ROWS+1):
    pct=home.getProperty('%s%d.Pct'%(activity.PREFIX,n))
    try:self.getControl(BAR_BASE+n).setPercent(float(pct or 0))
    except Exception:pass
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(0.5):
    if self.stop.is_set():break
    self.bars()
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def finish(self):
   self.stop.set();self.close()
  def onClick(self,control):
   if control in (9600,9099):self.finish()
   elif PAUSE_BASE<control<=PAUSE_BASE+activity.ROWS:toggle(home,'%s%d.'%(activity.PREFIX,control-PAUSE_BASE))

 sheet=Sheet('IOSActivity.xml',here,'Default','1080i')
 sheet.doModal()
 if hasattr(sheet,'stop'):sheet.stop.set()
 del sheet

if __name__=='__main__':run(sys.argv[1:])
