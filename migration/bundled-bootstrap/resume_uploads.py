"""Library status › "Downloads are paused" › Resume: lift the upload pause (transfer_control) and say so."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))

def run():
 import xbmc,xbmcgui,xbmcvfs,transfer_control,work_state
 profile=xbmcvfs.translatePath('special://profile/')
 transfer_control.set_paused(profile,'up',False)
 work_state.need('uploads_paused',False,profile)
 xbmc.log('Kodi iOS transfers: uploads resumed from Library status',xbmc.LOGINFO)
 xbmcgui.Dialog().notification('Downloads resumed','Uploads to Google Drive are running again.',xbmcgui.NOTIFICATION_INFO,3000,False)
 xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_status)')

if __name__=='__main__':run()
