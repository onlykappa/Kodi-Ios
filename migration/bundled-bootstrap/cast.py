"""Video controls › Play on TV: send what's playing to a Roku on the same Wi-Fi."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import cast

def run():
 import xbmc,xbmcaddon,xbmcgui
 dialog=xbmcgui.Dialog();addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');player=xbmc.Player()
 if not player.isPlayingVideo():dialog.ok('Play on TV','Start a video first.');return
 phone=cast.phone_address()
 url,needs_phone=cast.stream_url(player.getPlayingFile(),phone)
 if not url:
  dialog.ok('Play on TV','This video is not a web stream, so the TV cannot open it by itself.');return
 roku=addon.getSettingString('roku_address').strip()
 name=cast.device_name(roku,cast.http_get) if roku else None
 if not name:
  progress=xbmcgui.DialogProgress();progress.create('Play on TV','Looking for a Roku on this Wi-Fi...')
  try:found=cast.find_rokus(phone,cast.http_get)
  finally:progress.close()
  if not found:
   dialog.ok('Play on TV','No Roku answered on this Wi-Fi. Check that the phone and Roku share a network and that the Roku allows it: Settings › System › Advanced system settings › Control by mobile apps › Network access: Default.');return
  pick=0 if len(found)==1 else dialog.select('Choose your TV',[n+'  ('+h+')' for h,n in found])
  if pick<0:return
  roku,name=found[pick];addon.setSettingString('roku_address',roku)
 title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or xbmc.getInfoLabel('VideoPlayer.Title')
 try:cast.http_post(cast.launch_url(roku,url,title))
 except Exception as error:
  xbmc.log('Kodi iOS Play on TV failed: '+type(error).__name__,xbmc.LOGWARNING)
  dialog.ok('Play on TV',name+' did not accept the video. Try again, or open the Roku Media Player channel once.');return
 player.stop()
 if needs_phone:dialog.ok('Play on TV','Playing on '+name+'. This stream comes from Elementum on the phone: keep Kodi open and on Wi-Fi.')
 else:xbmcgui.Dialog().notification('Play on TV','Playing on '+name,xbmcgui.NOTIFICATION_INFO,5000)

if __name__=='__main__':run()
