"""Accounts › AllDebrid: sign in with a code (or sign out). The sheet is the app's choice sheet; the logic is resources/lib/debrid_signin_ui.py."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))

def run(argv=()):
 import xbmc,xbmcgui
 import choice_sheet,debrid_signin_ui,notices
 here=os.path.dirname(os.path.abspath(__file__))
 choose=lambda spec:choice_sheet.choose(spec,xbmcgui=xbmcgui,xbmc=xbmc,path=here)
 profile=None
 try:
  import xbmcvfs;profile=xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')
 except Exception:pass
 import debrid_account
 result=debrid_signin_ui.run(choose,lambda:xbmc.executebuiltin('Dialog.Close(all,true)'),notices.note,manage='manage' in argv,profile=profile,health=debrid_account.shared_health())
 xbmc.log('Kodi iOS AllDebrid sign-in: %s'%result,xbmc.LOGINFO)

if __name__=='__main__':run(sys.argv[1:])
