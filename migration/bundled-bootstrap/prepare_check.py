"""Settings › Library › Check library for conversion.

Asks the bootstrap service to check Google Drive › Kodi Downloads for videos that still need preparing for Kodi and
AirPlay (the service pauses a conversion in progress to do it, and resumes it after), waits for that check, then shows
what is ready, waiting or paused, and why."""
import os,sys,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import prepare_downloads

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 profile=xbmcvfs.translatePath('special://profile/');addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');dialog=xbmcgui.Dialog()
 if not addon.getSettingBool('prepare_downloads'):
  if not dialog.yesno('Check library for conversion','Preparing videos for Kodi and AirPlay is turned off. Turn it on and check now?',
                      nolabel='Cancel',yeslabel='Turn on'):return
  addon.setSettingBool('prepare_downloads',True)
 asked=time.time();prepare_downloads.request_check(profile)
 progress=xbmcgui.DialogProgress();progress.create('Check library for conversion','Checking Google Drive › Kodi Downloads…')
 monitor=xbmc.Monitor();checked=False
 # Up to two minutes: a large library takes a while, and nothing happens while a video plays.
 for second in range(120):
  state=prepare_downloads.load(profile)
  if (state.get('library') or {}).get('checked',0)>=asked:checked=True;break
  if progress.iscanceled() or monitor.waitForAbort(1):break
  progress.update(min(95,second),'Checking Google Drive › Kodi Downloads…')
 progress.close()
 text=prepare_downloads.summary(prepare_downloads.load(profile))
 if not checked:text='The check is still running and will finish in the background.\n'+text
 dialog.textviewer('Kodi and AirPlay',text)

if __name__=='__main__':run()
