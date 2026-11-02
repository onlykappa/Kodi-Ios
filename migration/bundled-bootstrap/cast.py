"""Video controls › Play on TV: send what's playing to a TV on the same Wi-Fi (Roku, smart TV, Chromecast,
Apple TV / AirPlay TV).

The picker is one AirPlay-style sheet over the video (1080i/IOSPlayOnTV.xml, written by pages.py): This iPhone
first, then the TVs as the search finds them, with a spinner while it keeps looking. If that page cannot be
loaded (an older skin copy), the previous progress box and list are used instead."""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import airplay,cast,notices

KINDS={'roku':'Roku','dlna':'Smart TV','chromecast':'Chromecast','airplay':'AirPlay'}
ICONS={'phone':'mobile-screen-button.png','roku':'tv.png','dlna':'tv.png','chromecast':'tv.png','airplay':'tv.png'}
ROWS=6          # pages.TV_ROWS
ROW_BASE=9600   # row n is button 9600+n
CLOSE=(9500,9099)
BACK=(9,10,92,110)
SEARCHING='Looking for more TVs on this Wi-Fi…'
NONE_FOUND=('No other TV answered on this Wi-Fi. Check the TV is on the same network. On a Roku: Settings › System › '
            'Advanced system settings › Control by mobile apps › Network access: Default.')

def ordered(tvs,last):
 """The TV used last time first, the rest as found."""
 key=lambda t:t['kind']+'|'+t['host']
 return sorted(tvs,key=lambda t:0 if key(t)==last else 1)

def rows(tvs):
 """[{name, kind, icon, on}] for the sheet: This iPhone, then up to ROWS-1 TVs."""
 out=[{'name':'This iPhone','kind':'Playing here','icon':ICONS['phone'],'on':'true'}]
 for t in tvs[:ROWS-1]:
  out.append({'name':t['name'],'kind':KINDS[t['kind']],
              'icon':ICONS.get(t['kind'],'tv.png'),'on':''})
 return out

def properties(tvs,searching,subtitle,note):
 props={'subtitle':subtitle,'note':note,'searching':SEARCHING if searching else ('' if tvs else NONE_FOUND),
        'spin':'true' if searching else ''}
 shown=rows(tvs)
 # The sheet's height follows what it shows: one background per row count (pages.play_on_tv).
 props['count']=str(len(shown)+(1 if props['searching'] else 0))
 for n in range(1,ROWS+1):
  r=shown[n-1] if n<=len(shown) else {}
  for key in ('name','kind','icon','on'):props['tv.%d.%s'%(n,key)]=r.get(key,'')
 return props

def run():
 import threading,time,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 xbmc.log('Kodi iOS Play on TV: opened',xbmc.LOGINFO)
 dialog=xbmcgui.Dialog();addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');player=xbmc.Player()
 if not player.isPlayingVideo():dialog.ok('Play on TV','Start a video first.');return
 phone=cast.phone_address()
 url,needs_phone=cast.stream_url(player.getPlayingFile(),phone)
 if not url:dialog.ok('Play on TV','This video is not a web stream, so a TV cannot open it by itself.');return
 title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or xbmc.getInfoLabel('VideoPlayer.Title')
 library=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
 extra=[]
 note='Plays from where you are now. '
 if library:
  extra=[{'kind':'airplay','host':'','name':'Apple TV / AirPlay TV'}]
  note+=('AirPlay may not play MKV files; other TVs use their own player.' if cast.media_type(url)=='video/x-matroska'
         else 'AirPlay sends MP4 and HLS; other TVs use their own player.')
 last=addon.getSettingString('last_tv')
 found={};done=threading.Event()
 def search():
  try:found['tvs']=cast.find_tvs(phone,cast.http_get)
  except Exception as error:xbmc.log('Kodi iOS Play on TV search failed: %s'%type(error).__name__,xbmc.LOGWARNING)
  finally:done.set()
 threading.Thread(target=search,daemon=True).start()
 tv=pick_sheet(xbmc,xbmcgui,os.path.dirname(os.path.abspath(__file__)),title,note,extra,found,done,last)
 if tv=='fallback':tv=pick_dialogs(xbmc,xbmcgui,dialog,extra,found,done,last)
 if not tv:return
 addon.setSettingString('last_tv',tv['kind']+'|'+tv['host'])
 send(xbmc,dialog,player,library,tv,url,title,needs_phone)

def pick_sheet(xbmc,xbmcgui,home,title,note,extra,found,done,last):
 """The TV picked in the sheet, None when closed (or This iPhone), 'fallback' when the sheet cannot load."""
 import threading
 chosen={}
 class Sheet(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.tvs=[];self.stop=threading.Event();self.show(searching=True)
   threading.Thread(target=self.wait_search,daemon=True).start()
  def show(self,searching):
   self.tvs=ordered(extra+(found.get('tvs') or []),last)
   for key,value in properties(self.tvs,searching,title or 'What is playing',note).items():self.setProperty(key,value)
  def wait_search(self):
   while not done.wait(0.25):
    if self.stop.is_set():return
   if not self.stop.is_set():self.show(searching=False)
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def finish(self):
   self.stop.set();self.close()
  def onClick(self,control):
   if control in CLOSE or control==ROW_BASE+1:self.finish()
   elif ROW_BASE+1<control<=ROW_BASE+ROWS:
    n=control-ROW_BASE-2
    if n<len(self.tvs):chosen['tv']=self.tvs[n];self.finish()
 try:sheet=Sheet('IOSPlayOnTV.xml',home,'Default','1080i')
 except Exception as error:
  xbmc.log('Kodi iOS Play on TV: sheet unavailable (%s), using the list'%type(error).__name__,xbmc.LOGWARNING);return 'fallback'
 sheet.doModal();sheet.stop.set() if hasattr(sheet,'stop') else None
 del sheet
 return chosen.get('tv')

def pick_dialogs(xbmc,xbmcgui,dialog,extra,found,done,last):
 """The previous picker: a progress box while searching, then a list."""
 import time
 progress=xbmcgui.DialogProgress();progress.create('Play on TV','Looking for TVs on this Wi-Fi...')
 start=time.monotonic()
 try:
  while not done.is_set():
   if progress.iscanceled() or xbmc.Monitor().waitForAbort(0.2):return None
   progress.update(min(95,int((time.monotonic()-start)*12)))
 finally:progress.close()
 tvs=ordered((found.get('tvs') or [])+extra,last)
 if not tvs:dialog.ok('Play on TV',NONE_FOUND.replace('No other TV','No TV'));return None
 pick=dialog.select('Play on which TV?',[t['name']+'  ·  '+KINDS[t['kind']] for t in tvs])
 return tvs[pick] if pick>=0 else None

def send(xbmc,dialog,player,library,tv,url,title,needs_phone):
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

if __name__=='__main__':run()
