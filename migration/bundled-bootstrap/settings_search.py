"""Search Settings (the field at the top of portrait Settings, RunScript(service.kodi.ios.bootstrap,settings_search)):
Kodi's keyboard asks what to find, the matching settings show in a list, and picking one opens it.
The index and matching are resources/lib/settings_search.py."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import settings_page,settings_search

def legacy():
 import xbmc,xbmcgui,xbmcvfs
 dialog=xbmcgui.Dialog()
 entries=settings_search.page_entries(settings_page)
 try:
  with xbmcvfs.File(settings_search.KODI_SETTINGS) as f:xml=f.read()
  entries+=settings_search.kodi_entries(xml,xbmc.getLocalizedString)
 except Exception as error:
  xbmc.log('Kodi iOS settings search: Kodi settings unreadable: '+type(error).__name__,xbmc.LOGWARNING)
 query=''
 while True:
  query=dialog.input('Search Settings',query)
  if not query:return
  found=settings_search.search(entries,query)
  if found:break
  dialog.notification('Search Settings','No settings match "%s"'%query,xbmcgui.NOTIFICATION_INFO,2500)
 items=[]
 for label,where,_ in found:
  item=xbmcgui.ListItem(label,where);items.append(item)
 choice=dialog.select('Settings matching "%s"'%query,items,useDetails=True)
 if choice<0:return
 for action in found[choice][2].split('\x00'):xbmc.executebuiltin(action)

def run():
 import time,threading,xbmc,xbmcgui,xbmcvfs
 import glassbar,searchbar
 path=glassbar.library_path(xbmcvfs.translatePath('special://xbmc/'))
 try:lib=glassbar.load(path) if path else None
 except OSError:lib=None
 if lib is None or not hasattr(lib,'kodi_search_context'):return legacy()
 home=xbmcgui.Window(10000)
 entries=settings_search.page_entries(settings_page)
 try:
  with xbmcvfs.File(settings_search.KODI_SETTINGS) as f:entries+=settings_search.kodi_entries(f.read(),xbmc.getLocalizedString)
 except Exception as error:xbmc.log('Kodi iOS Settings search index: '+type(error).__name__,xbmc.LOGWARNING)
 class Search(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.stop=threading.Event();self.query=None;self.found=[];self.chosen=None
   home.clearProperty('Settings.Search.Query');home.clearProperty('Settings.Search.Close')
   home.setProperty('Settings.Search.Active','1')
   threading.Thread(target=self.poll,daemon=True).start()
   try:self.setFocusId(9160)
   except Exception:pass
  def poll(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(.1):
    if home.getProperty('Settings.Search.Close')=='1':self.finish();break
    query=home.getProperty('Settings.Search.Query')
    if query==self.query:continue
    # Nothing typed yet: Settings' own rows, so the page is never blank and a tap still goes somewhere.
    self.query=query;self.found=settings_search.search(entries,query) if query else [e for e in entries if e[1]=='Settings']
    self.setProperty('empty','true' if query and not self.found else '')
    self.setProperty('query',query)
    control=self.getControl(9160);control.reset()
    for label,where,actions in self.found:
     item=xbmcgui.ListItem(label,where);control.addItem(item)
  def onClick(self,control):
   if control==9001:self.finish()
   elif control==9160:
    index=self.getControl(9160).getSelectedPosition()
    if 0<=index<len(self.found):self.chosen=self.found[index][2];self.finish()
  def onAction(self,action):
   if action.getId() in (9,10,92,110):self.finish()
  def finish(self):
   self.stop.set();self.close()
 page=Search('IOSSettingsSearch.xml',os.path.dirname(os.path.abspath(__file__)),'Default','1080i')
 try:page.doModal()
 finally:
  if hasattr(page,'stop'):page.stop.set()
  home.clearProperty('Settings.Search.Active');home.clearProperty('Settings.Search.Query');home.clearProperty('Settings.Search.Close')
  lib.kodi_search_focus(0);lib.kodi_search_show(0)
 chosen=getattr(page,'chosen',None);del page
 if chosen:
  for action in chosen.split('\x00'):xbmc.executebuiltin(action)

if __name__=='__main__':run()
