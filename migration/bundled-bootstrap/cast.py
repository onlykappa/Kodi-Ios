"""Video controls › Play on TV: send what's playing to a TV on the same Wi-Fi (Roku, smart TV, Chromecast,
Apple TV / AirPlay TV).

The picker is one AirPlay-style sheet over the video (1080i/IOSPlayOnTV.xml, written by pages.py): This iPhone
first, then the TVs as the search finds them, with a spinner while it keeps looking. If that page cannot be
loaded (an older skin copy), the previous progress box and list are used instead."""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
import airplay,cast,notices,diagnostics

KINDS={'roku':'Roku','dlna':'Smart TV','chromecast':'Chromecast','airplay':'AirPlay'}
ICONS={'phone':'mobile-screen-button.png','roku':'tv.png','dlna':'tv.png','chromecast':'tv.png','airplay':'tv.png'}
ROWS=6          # pages.TV_ROWS
ROW_BASE=9600   # row n is button 9600+n
CLOSE=(9500,9099)
LAST=9501       # Last time: the AirPlay check
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
 import time,xbmc,xbmcgui,xbmcvfs
 home=xbmcgui.Window(10000)
 with cast.session_lock(xbmcvfs.translatePath('special://profile/')) as owned:
  if not owned:
   xbmc.log('Kodi iOS Play on TV: already starting; second press ignored',xbmc.LOGINFO)
   xbmcgui.Dialog().notification('Play on TV','Still connecting to the TV…',xbmcgui.NOTIFICATION_INFO,3000);return
  home.setProperty(cast.BUSY,str(time.time()))
  try:run_owned()
  finally:home.clearProperty(cast.BUSY)

def run_owned():
 import threading,time,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 xbmc.log('Kodi iOS Play on TV: opened',xbmc.LOGINFO)
 dialog=xbmcgui.Dialog();addon=xbmcaddon.Addon('service.kodi.ios.bootstrap');player=xbmc.Player()
 if not player.isPlayingVideo():dialog.ok('Play on TV','Start a video first.');return
 phone=cast.phone_address()
 url,needs_phone=cast.stream_url(player.getPlayingFile(),phone)
 if not url:dialog.ok('Play on TV','This video is not a web stream, so a TV cannot open it by itself.');return
 title=xbmc.getInfoLabel('VideoPlayer.TVShowTitle') or xbmc.getInfoLabel('VideoPlayer.Title')
 library=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
 playing=player.getPlayingFile()
 extra=[]
 note='Plays from where you are now. '
 if library:
  # ISSUE-079: Apple's player opens MP4/MOV/HLS only; ISSUE-083: KodiAirPlay r5 converts MKV/AVI/WebM/TS on the
  # phone; the rest go to Screen Mirroring (Kodi keeps playing).
  try:converting=airplay.converts(airplay.load(library))
  except OSError:converting=False
  direct=cast.apple_playable(url,playing)
  apple=direct or cast.apple_playable(url,playing,converts=converting)
  extra=[{'kind':'airplay','host':'','name':'Apple TV / AirPlay TV'+('' if apple else '  (Screen Mirroring)')}]
  note+=('AirPlay sends MP4 and HLS; other TVs use their own player.' if direct
         else 'AirPlay converts this %s video on the phone: keep Kodi open. Other TVs use their own player.'%cast.format_name(url,playing) if apple
         else 'AirPlay shows this %s video through Screen Mirroring; other TVs use their own player.'%cast.format_name(url,playing))
 last=addon.getSettingString('last_tv')
 found={};done=threading.Event()
 diagnostics.attach(os.path.dirname(os.path.abspath(__file__)),xbmcvfs.translatePath('special://profile/'))
 def search():
  try:found['tvs']=cast.find_tvs(phone,cast.http_get)
  except Exception as error:diagnostics.log_exception(xbmc,'tv_discovery',error)
  finally:done.set()
 threading.Thread(target=search,daemon=True).start()
 tv=pick_sheet(xbmc,xbmcgui,os.path.dirname(os.path.abspath(__file__)),title,note,extra,found,done,last)
 if tv=='fallback':tv=pick_dialogs(xbmc,xbmcgui,dialog,extra,found,done,last)
 if not tv:return
 addon.setSettingString('last_tv',tv['kind']+'|'+tv['host'])
 send(xbmc,dialog,player,library,tv,url,title,needs_phone,playing)

def pick_sheet(xbmc,xbmcgui,home,title,note,extra,found,done,last):
 """The TV picked in the sheet, None when closed (or This iPhone), 'fallback' when the sheet cannot load."""
 import threading
 chosen={}
 class Sheet(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.tvs=[];self.stop=threading.Event();self.show(searching=True)
   # Last time: how the last Play on TV over AirPlay went (tool_windows.open_airplay), once there has been one.
   try:
    import library_tools,xbmcvfs
    self.setProperty('last','true' if library_tools.load_airplay(xbmcvfs.translatePath('special://profile/')) else '')
   except Exception:self.setProperty('last','')
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
   elif control==LAST:
    import tool_windows;tool_windows.open_airplay()
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

def send_airplay(xbmc,dialog,player,library,url,title,playing):
 """ISSUE-079: Apple's player for MP4/HLS (Kodi waits paused and carries on if it cannot open the stream);
 ISSUE-083: KodiAirPlay r5 converts MKV/AVI/WebM/TS on the phone first. Screen Mirroring steps for the rest, with
 Kodi still playing."""
 lib=airplay.load(library)
 converting=airplay.converts(lib)
 if not cast.apple_playable(url,playing,converts=converting):
  xbmc.log('Kodi iOS Play on TV: %s cannot go through Apple\'s player; Screen Mirroring steps shown'%cast.format_name(url,playing),xbmc.LOGINFO)
  dialog.ok('Play on TV',cast.MIRRORING%cast.format_name(url,playing));return
 if not hasattr(lib,'kodi_airplay_state'):
  player.stop();xbmc.sleep(500);lib.kodi_airplay_play(url.encode('utf-8'),(title or '').encode('utf-8'));return
 if not xbmc.getCondVisibility('Player.Paused'):player.pause()
 # Converting reads the video on the phone itself, so it uses the link Kodi plays (Drive's and Elementum's helpers
 # answer on 127.0.0.1 only: owner build-132 log, "Connection refused" on the Wi-Fi address).
 source=cast.airplay_source(playing,url,converting)
 import urllib.parse
 diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'airplay','start',format=cast.format_name(playing,url),converts=converting,loopback=urllib.parse.urlsplit(source.split('|',1)[0]).hostname in ('127.0.0.1','localhost','::1'))
 # r10: the subtitle Kodi shows goes to the TV burned into the converted picture (TVs' AirPlay ignores WebVTT).
 try:
  import time,xbmcvfs
  subs=airplay.send_subtitles(lib,xbmc,xbmcvfs,time.time())
  if subs is not None:xbmc.log('Kodi iOS Play on TV: subtitles for AirPlay %s'%('off' if subs[0]==-1 else 'external file' if subs[1] and subs[0]==-2 else 'stream %d%s'%(subs[0],' (+ external file)' if subs[1] else '')),xbmc.LOGINFO)
 except Exception as error:diagnostics.log_exception(xbmc,'airplay_subtitles',error)
 # The AirPlay check (Play on TV › Last time) starts a new record for this Play on TV.
 try:
  import library_tools,xbmcvfs
  profile=xbmcvfs.translatePath('special://profile/');library_tools.begin_airplay(profile,title)
 except Exception:profile=None
 import time,xbmcgui
 # Build 186 (owner: "airplay stops out of nowhere"): the copies, uploads and conversion step aside from now on.
 home=xbmcgui.Window(10000);airplay.mark_busy(home,time.time())
 # Something on screen at once while the TV connects (it can take a while), with Cancel.
 progress=xbmcgui.DialogProgress();progress.create('Play on TV',cast.AIRPLAY_WORDS['opening' if converting else 'connecting'])
 # Reset evidence before starting; the service may drain native log lines before this script sees them.
 for key in (airplay.STARTED,airplay.LISTENING,airplay.TV_REQUEST):home.clearProperty(key)
 if converting and cast.format_name(source)!='M3U8':home.setProperty(airplay.STARTED,str(time.time()))
 started=[0.0];monitor=xbmc.Monitor()
 lines=[];endpoint=None
 def network():
  nonlocal endpoint
  new=[airplay.log_text(line) for line in airplay.log_lines(lib)]
  lines.extend(new)
  for line in new:xbmc.log('Kodi iOS AirPlay: '+line,xbmc.LOGINFO)
  airplay.activity(new,home,time.time())
  if profile and new:
   try:library_tools.note_airplay(profile,new)
   except Exception as error:diagnostics.log_exception(xbmc,'airplay_record',error)
  net=airplay.network(lib,home) if converting else None
  if net and net.get('host') and net.get('port') and endpoint!=(net['host'],net['port']):
   endpoint=(net['host'],net['port'])
   diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'airplay','endpoint',host=endpoint[0],port=endpoint[1])
  return net
 def wait(seconds):
  started[0]+=seconds;airplay.mark_busy(home,time.time());progress.update(0)
  return progress.iscanceled() or monitor.waitForAbort(seconds)
 def stage(phase,words):
  progress.update(0,words)
  diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'airplay','phase',phase=phase)
 try:
  lib.kodi_airplay_play(source.encode('utf-8'),(title or '').encode('utf-8'))
  outcome=cast.airplay_outcome(lib.kodi_airplay_state,wait,60 if converting else 25,network=network,stage=stage)
  why=airplay.message(lib)
  net=network()
  if profile and outcome=='failed':
   # The service can have consumed the player's failure line first.
   for line in library_tools.load_airplay(profile).get('lines') or []:
    if line not in lines:lines.append(line)
  connecting=net and (net.get('phase') in ('connecting','playing') or (not net.get('phase') and net.get('listen_age_s',-1)>=0))
  if outcome=='failed' and connecting and net.get('expected') and not net.get('tv_requests') and cast.player_problem(lines)=='the TV could not connect to the phone':outcome='unreachable'
  if profile and net and net.get('tv_requests'):
   import work_state;work_state.need('airplay_network',False,profile)
 except Exception:
  # A logging/controller exception must not strand the native source or Kodi's paused video.
  lib.kodi_airplay_close();airplay.clear_busy(home)
  if xbmc.getCondVisibility('Player.Paused'):player.pause()
  raise
 finally:progress.close()
 # r6: the stream's variant line (CODECS), the receiver's requests and Apple's player events so far; the service
 # keeps relaying the rest while it plays (airplay.relay).
 remaining=[airplay.log_text(line) for line in airplay.log_lines(lib)]
 lines.extend(remaining)
 for line in remaining:xbmc.log('Kodi iOS AirPlay: '+line,xbmc.LOGINFO)
 if profile:
  try:library_tools.note_airplay(profile,remaining)
  except Exception:pass
 diagnostics.event(lambda message:xbmc.log(message,xbmc.LOGINFO),'airplay','outcome',outcome=outcome,elapsed_s=round(started[0],2),reason=why)
 if outcome=='playing':
  # Owner build-136 log: stopping Kodi's video here (7 ms after "playing") turned the app back to portrait under
  # Apple's player; the TV then hung up on the video and audio segments and AirPlay switched off 4 s later. Kodi's
  # video stays paused in landscape while AirPlay plays; closing Apple's player returns to it.
  if not xbmc.getCondVisibility('Player.Paused'):player.pause()
  if profile:
   import work_state;work_state.need('airplay_network',False,profile)
  notices.note('info','Playing with AirPlay',title or '');return
 lib.kodi_airplay_close();airplay.clear_busy(home)
 if xbmc.getCondVisibility('Player.Paused'):player.pause()   # Kodi carries on (also after Cancel)
 if outcome=='aborted':return
 if outcome=='startup_timeout':
  text='The video took too long to open for AirPlay. Try again.'
  notices.note('problem',"AirPlay didn't start",text);dialog.ok('Play on TV',text);return
 if outcome=='selection_timeout':
  dialog.ok('Play on TV','No TV was selected. Open Play on TV and choose a TV from the AirPlay list.');return
 if outcome=='unreachable':
  import work_state
  if profile:work_state.need('airplay_network',True,profile)
  text=work_state.NEEDS_TEXT['airplay_network']['text']
  notices.note('problem',"Your TV couldn't reach this iPhone",text);dialog.ok('Play on TV',text);return
 if why:notices.note('problem',"AirPlay couldn't play this",why);dialog.ok('Play on TV',cast.CONVERT_FAILED%why)
 elif converting:
  # The format was fine (this framework plays or converts it): Apple's player or the TV did not start.
  problem=cast.player_problem(lines) or 'the TV did not answer'
  notices.note('problem',"AirPlay didn't start",problem);dialog.ok('Play on TV',cast.NOT_STARTED%problem)
 else:dialog.ok('Play on TV',cast.MIRRORING%cast.format_name(url,playing))

def send(xbmc,dialog,player,library,tv,url,title,needs_phone,playing=''):
 try:
  if tv['kind']=='roku':xbmc.log('Kodi iOS Play on TV: Roku took the link via '+cast.roku_play(tv['host'],url,title,cast.http_post),xbmc.LOGINFO)
  elif tv['kind']=='dlna':cast.dlna_play(tv['control'],url,title,cast.http_post_body)
  elif tv['kind']=='chromecast':cast.chromecast_play(tv['host'],url,title)
  else:send_airplay(xbmc,dialog,player,library,url,title,playing);return
 except cast.TVRefused as error:
  diagnostics.log_exception(xbmc,'play_on_tv',error,receiver=tv['kind'])
  # Owner (build-138): a Roku TV without "Play on Roku" (404) goes straight to AirPlay (Roku TVs have AirPlay built
  # in) instead of a message; Apple's device sheet then lists that TV.
  if tv['kind']=='roku' and library:
   xbmc.log('Kodi iOS Play on TV: %s -> AirPlay'%tv['name'],xbmc.LOGINFO)
   send_airplay(xbmc,dialog,player,library,url,title,playing);return
  notices.note('problem',"Play on TV couldn't start",tv['name']+': '+str(error))
  dialog.ok('Play on TV',tv['name']+': '+str(error));return
 except Exception as error:
  diagnostics.log_exception(xbmc,'play_on_tv',error,receiver=tv['kind'])
  notices.note('problem',"Play on TV couldn't start",tv['name']+' did not accept the video. Make sure the TV is on.')
  dialog.ok('Play on TV',tv['name']+' did not accept the video. Make sure the TV is on, then try again.');return
 player.stop();notices.note('info','Playing on '+tv['name'],title or '')
 if needs_phone:dialog.ok('Play on TV','Playing on '+tv['name']+'. This stream comes from Elementum on the phone: keep Kodi open and on Wi-Fi.')

if __name__=='__main__':run()
