"""Video controls › Play on TV: send what's playing to a TV on the same Wi-Fi (Roku, smart TV, Chromecast,
Apple TV / AirPlay TV)."""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import airplay,cast

KINDS={'roku':'Roku','dlna':'Smart TV','chromecast':'Chromecast','airplay':'AirPlay'}

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 dialog=xbmcgui.Dialog();addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');player=xbmc.Player()
 if not player.isPlayingVideo():dialog.ok('Play on TV','Start a video first.');return
 phone=cast.phone_address()
 url,needs_phone=cast.stream_url(player.getPlayingFile(),phone)
 if not url:dialog.ok('Play on TV','This video is not a web stream, so a TV cannot open it by itself.');return
 title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or xbmc.getInfoLabel('VideoPlayer.Title')
 progress=xbmcgui.DialogProgress();progress.create('Play on TV','Looking for TVs on this Wi-Fi...')
 try:tvs=cast.find_tvs(phone,cast.http_get)
 finally:progress.close()
 library=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
 if library:
  note='' if cast.media_type(url)!='video/x-matroska' else '  — MKV may not play over AirPlay'
  tvs.append({'kind':'airplay','host':'','name':'Apple TV / AirPlay TV'+note})
 if not tvs:
  dialog.ok('Play on TV','No TV answered on this Wi-Fi. Check the TV is on the same network. On a Roku: Settings › System › Advanced system settings › Control by mobile apps › Network access: Default.');return
 last=addon.getSettingString('last_tv')
 labels=[t['name']+'  ·  '+KINDS[t['kind']] for t in tvs]
 keys=[t['kind']+'|'+t['host'] for t in tvs]
 pick=dialog.select('Play on which TV?',labels,preselect=keys.index(last) if last in keys else 0)
 if pick<0:return
 tv=tvs[pick];addon.setSettingString('last_tv',keys[pick])
 try:
  if tv['kind']=='roku':cast.http_post(cast.launch_url(tv['host'],url,title))
  elif tv['kind']=='dlna':cast.dlna_play(tv['control'],url,title,cast.http_post_body)
  elif tv['kind']=='chromecast':cast.chromecast_play(tv['host'],url,title)
  else:
   player.stop();xbmc.sleep(500)
   airplay.load(library).kodi_airplay_play(url.encode('utf-8'),(title or '').encode('utf-8'));return
 except Exception as error:
  xbmc.log('Kodi iOS Play on TV failed (%s): %s'%(tv['kind'],type(error).__name__),xbmc.LOGWARNING)
  dialog.ok('Play on TV',tv['name']+' did not accept the video. Make sure the TV is on, then try again.');return
 player.stop()
 if needs_phone:dialog.ok('Play on TV','Playing on '+tv['name']+'. This stream comes from Elementum on the phone: keep Kodi open and on Wi-Fi.')
 else:dialog.notification('Play on TV','Playing on '+tv['name'],xbmcgui.NOTIFICATION_INFO,5000)

if __name__=='__main__':run()
