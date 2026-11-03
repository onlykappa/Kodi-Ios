"""Search Settings (the field at the top of portrait Settings, RunScript(service.kodi.ios.bootstrap,settings_search)):
Kodi's keyboard asks what to find, the matching settings show in a list, and picking one opens it.
The index and matching are resources/lib/settings_search.py."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import settings_page,settings_search

def run():
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

if __name__=='__main__':run()
