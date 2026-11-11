"""Search Settings (the field at the top of portrait Settings, RunScript(service.kodi.ios.bootstrap,settings_search)),
owner-approved mockup board 11. portrait/IOSSettingsSearch.xml shows the field (a Kodi edit control, so iOS opens its own
keyboard), the matching settings as a grouped list that updates as you type, and "No settings match" when none does.
Picking a result runs its action once the page has closed: a Settings row's own action, or Kodi's settings window at the
setting's category. The index is resources/lib/settings_search.py; matching and bold are resources/lib/settings_find.py."""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import settings_page,settings_search,settings_find

FIELD=settings_page.SEARCH_FIELD;LIST=settings_page.SEARCH_LIST;BACK=9001
BACK_KEYS=(9,10,92,110)
POLL=0.3   # seconds between reads of the field

def run():
 import threading,xbmc,xbmcgui,xbmcvfs
 entries=settings_search.page_entries(settings_page)
 try:
  with xbmcvfs.File(settings_search.KODI_SETTINGS) as f:entries+=settings_search.kodi_entries(f.read(),xbmc.getLocalizedString)
 except Exception as error:xbmc.log('Kodi iOS Settings search index: '+type(error).__name__,xbmc.LOGWARNING)

 class Search(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.stop=threading.Event();self.query=None;self.found=[];self.chosen=None
   self.setProperty('rows','0');self.setProperty('empty','')
   self.refresh('')   # nothing typed yet: Settings' own rows, so the page is never blank and a tap still goes somewhere
   try:self.setFocusId(FIELD)
   except Exception:pass
   # The mockup opens with the keyboard up: Select on the focused field is what tapping it does.
   xbmc.executebuiltin('Action(Select)')
   threading.Thread(target=self.poll,daemon=True).start()
  def poll(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(POLL):
    try:query=self.getControl(FIELD).getText()
    except Exception:break
    if query!=self.query:self.refresh(query)
  def refresh(self,typed):
   query=' '.join(str(typed or '').split());self.query=typed
   found=settings_find.search(entries,query) if query else [e for e in entries if e[1]=='Settings']
   self.found=found
   control=self.getControl(LIST);control.reset()
   for n,(label,where,_) in enumerate(found):
    item=xbmcgui.ListItem(settings_find.bold(label,query) if query else label,where)
    item.setProperty('first','1' if n==0 else '')
    control.addItem(item)
   self.setProperty('rows',str(min(len(found),settings_page.SEARCH_CARD)))
   self.setProperty('empty','1' if query and not found else '')
  def onClick(self,control):
   if control==BACK:self.finish()
   elif control==LIST:
    index=self.getControl(LIST).getSelectedPosition()
    if 0<=index<len(self.found):self.chosen=self.found[index][2];self.finish()
  def onAction(self,action):
   if action.getId() in BACK_KEYS:self.finish()
  def finish(self):
   self.stop.set();self.close()

 page=Search('IOSSettingsSearch.xml',HERE,'Default','1080i')
 try:page.doModal()
 finally:
  if hasattr(page,'stop'):page.stop.set()
 chosen=getattr(page,'chosen',None);del page
 if chosen:
  for action in chosen.split('\x00'):xbmc.executebuiltin(action)

if __name__=='__main__':run()
