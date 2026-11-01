"""Video controls › Play on TV: send what's playing to a TV on the same Wi-Fi (Roku, smart TV, Chromecast,
Apple TV / AirPlay TV)."""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import airplay,cast,notices

KINDS={'roku':'Roku','dlna':'Smart TV','chromecast':'Chromecast','airplay':'AirPlay'}

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 xbmc.log('Kodi iOS Play on TV: opened',xbmc.LOGINFO)
 dialog=xbmcgui.Dialog();addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');player=xbmc.Player()
 if not player.isPlayingVideo():dialog.ok('Play on TV','Start a video first.');return
 phone=cast.phone_address()
 url,needs_phone=cast.stream_url(player.getPlayingFile(),phone)
 if not url:dialog.ok('Play on TV','This video is not a web stream, so a TV cannot open it by itself.');return
 title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or xbmc.getInfoLabel('VideoPlayer.Title')
 progress=xbmcgui.DialogProgress();progress.create('Play on TV','Looking for TVs on this Wi-Fi...')
 # The search runs beside the dialog, so Cancel ends it at once (it used to wait for every address to answer).
 import threading,time
 found={}
 search=threading.Thread(target=lambda:found.update(tvs=cast.find_tvs(phone,cast.http_get)),daemon=True);search.start()
 start=time.monotonic()
 try:
  while search.is_alive():
   if progress.iscanceled() or xbmc.Monitor().waitForAbort(0.2):return
   progress.update(min(95,int((time.monotonic()-start)*12)))
 finally:progress.close()
 tvs=found.get('tvs') or []
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
  if tv['kind']=='roku':xbmc.log('Kodi iOS Play on TV: Roku took the link via '+cast.roku_play(tv['host'],url,title,cast.http_post),xbmc.LOGINFO)
  elif tv['kind']=='dlna':cast.dlna_play(tv['control'],url,title,cast.http_post_body)
  elif tv['kind']=='chromecast':cast.chromecast_play(tv['host'],url,title)
  else:
   player.stop();xbmc.sleep(500)
   airplay.load(library).kodi_airplay_play(url.encode('utf-8'),(title or '').encode('utf-8'));return
 except cast.TVRefused as error:
  xbmc.log('Kodi iOS Play on TV refused (%s): %s'%(tv['kind'],error),xbmc.LOGWARNING)
  notices.note('problem',"Play on TV couldn't start",tv['name']+': '+str(error))
  dialog.ok('Play on TV',tv['name']+': '+str(error));return
 except Exception as error:
  xbmc.log('Kodi iOS Play on TV failed (%s): %s: %s'%(tv['kind'],type(error).__name__,error),xbmc.LOGWARNING)
  notices.note('problem',"Play on TV couldn't start",tv['name']+' did not accept the video. Make sure the TV is on.')
  dialog.ok('Play on TV',tv['name']+' did not accept the video. Make sure the TV is on, then try again.');return
 player.stop();notices.note('info','Playing on '+tv['name'],title or '')
 if needs_phone:dialog.ok('Play on TV','Playing on '+tv['name']+'. This stream comes from Elementum on the phone: keep Kodi open and on Wi-Fi.')
 else:dialog.notification('Play on TV','Playing on '+tv['name'],xbmcgui.NOTIFICATION_INFO,5000)

if __name__=='__main__':run()
