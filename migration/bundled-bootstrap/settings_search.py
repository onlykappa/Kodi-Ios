"""Search Settings (the field at the top of portrait Settings, RunScript(service.kodi.ios.bootstrap,settings_search)),
owner-approved mockup board 11. On the iPhone the field is the native search field (glassbar, kodi_search_context: the
real iOS keyboard, results update as you type, ISSUE-162); without the glassbar a Kodi edit control stands in. The page shows the matching settings as a grouped list that updates as you type, and "No settings match" when none does.
Picking a result runs its action once the page has closed: a Settings row's own action, or Kodi's settings window at the
setting's category. The index is resources/lib/settings_search.py; matching and bold are resources/lib/settings_find.py."""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import page_wait,settings_page,settings_search,settings_find

FIELD=settings_page.SEARCH_FIELD;LIST=settings_page.SEARCH_LIST;BACK=9001
BACK_KEYS=(9,10,92,110)
POLL=0.3   # seconds between reads of the field

def native_field():
 """The glassbar library when it can host Settings' search (kodi_search_context), else None."""
 import xbmcvfs
 try:
  import glassbar
  path=glassbar.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=glassbar.load(path) if path else None
 except Exception:return None
 return lib if lib is not None and hasattr(lib,'kodi_search_context') else None

def run():
 import threading,xbmc,xbmcgui,xbmcvfs
 lib=native_field();home=xbmcgui.Window(10000)
 entries=settings_search.page_entries(settings_page)
 try:
  with xbmcvfs.File(settings_search.KODI_SETTINGS) as f:entries+=settings_search.kodi_entries(f.read(),xbmc.getLocalizedString)
 except Exception as error:xbmc.log('Kodi iOS Settings search index: '+type(error).__name__,xbmc.LOGWARNING)

 class Search(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.stop=threading.Event();self.query=None;self.found=[];self.chosen=None
   self.setProperty('rows','0');self.setProperty('empty','')
   self.refresh('')   # nothing typed yet: Settings' own rows, so the page is never blank and a tap still goes somewhere
   if lib is not None:
    # searchbar.py (the service) shows the native field in Settings' place and writes what is typed to Home.
    self.setProperty('native','1')
    home.clearProperty('Settings.Search.Query');home.clearProperty('Settings.Search.Close')
    home.setProperty('Settings.Search.Active','1')
    try:self.setFocusId(LIST)
    except Exception:pass
   else:
    try:self.setFocusId(FIELD)
    except Exception:pass
   threading.Thread(target=self.poll,daemon=True).start()
  def typed(self):
   if lib is None:return self.getControl(FIELD).getText()
   if home.getProperty('Settings.Search.Close')=='1':self.finish();return None
   return home.getProperty('Settings.Search.Query')
  def poll(self):
   monitor=xbmc.Monitor();raised=lib is None
   while not page_wait.idle(self.stop,monitor,POLL):
    if not raised:lib.kodi_search_focus(1);raised=True   # the mockup opens with the keyboard up
    try:query=self.typed()
    except Exception:break
    if query is None:break
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
  if lib is not None:
   for key in ('Active','Query','Close'):home.clearProperty('Settings.Search.'+key)
   lib.kodi_search_focus(0);lib.kodi_search_show(0)
 chosen=getattr(page,'chosen',None);del page
 if chosen:
  for action in chosen.split('\x00'):xbmc.executebuiltin(action)

if __name__=='__main__':run()
