"""Apple's AirPlay button over Kodi, from Kodi.app/Frameworks/KodiAirPlay.framework (migration/airplay-ios)."""
import json,os,re,threading,time
import diagnostics
# Full-screen video or music only: on Fuse's menus the top-right corner holds the clock and the gear.
PLAYING='Player.HasMedia + [Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)]'

def startup_budget(lib):
 """New frameworks own one absolute startup deadline; older installed frameworks keep their existing limit."""
 try:
  seconds=int(lib.kodi_airplay_startup_budget())
  if 60<=seconds<=180:return seconds+5  # let native failure diagnostics arrive before controller cancellation
 except (AttributeError,TypeError,ValueError):pass
 return 60

def library_path(xbmc_home):
 """special://xbmc lies inside Kodi.app; the framework sits in Kodi.app/Frameworks."""
 app=str(xbmc_home).rstrip('/')
 while app and not app.endswith('.app') and os.path.dirname(app)!=app:app=os.path.dirname(app)
 path=os.path.join(app,'Frameworks','KodiAirPlay.framework','KodiAirPlay')
 return path if app.endswith('.app') and os.path.isfile(path) else None

def load(path):
 import ctypes
 lib=ctypes.CDLL(path);lib.kodi_airplay_show.argtypes=[ctypes.c_int];lib.kodi_airplay_show.restype=None
 lib.kodi_airplay_open.argtypes=[];lib.kodi_airplay_open.restype=None
 if hasattr(lib,'kodi_airplay_play'):lib.kodi_airplay_play.argtypes=[ctypes.c_char_p,ctypes.c_char_p];lib.kodi_airplay_play.restype=None
 # r3: whether Apple's player could open the stream (0 idle/loading, 1 playing, -1 failed), closing it, and keeping
 # Kodi awake in the background (background.py).
 if hasattr(lib,'kodi_airplay_state'):lib.kodi_airplay_state.argtypes=[];lib.kodi_airplay_state.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_close'):lib.kodi_airplay_close.argtypes=[];lib.kodi_airplay_close.restype=None
 # r5: MKV/AVI/WebM/TS converted on the phone for AirPlay; why it could not play, for the screen.
 if hasattr(lib,'kodi_airplay_message'):lib.kodi_airplay_message.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_message.restype=ctypes.c_int
 # r6: what the AirPlay stream did (requests, CODECS, Apple's player events), for kodi.log.
 if hasattr(lib,'kodi_airplay_log'):lib.kodi_airplay_log.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_log.restype=ctypes.c_int
 # r34: non-draining network evidence (the service and a script both read it), and the app's Settings link.
 if hasattr(lib,'kodi_airplay_health'):lib.kodi_airplay_health.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_health.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_network'):lib.kodi_airplay_network.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_network.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_settings'):lib.kodi_airplay_settings.argtypes=[];lib.kodi_airplay_settings.restype=None
 if hasattr(lib,'kodi_airplay_active'):lib.kodi_airplay_active.argtypes=[];lib.kodi_airplay_active.restype=ctypes.c_int
 # r10: the subtitles burned into the picture a TV gets converted (Kodi's current choice, set before playing).
 if hasattr(lib,'kodi_airplay_subtitles'):lib.kodi_airplay_subtitles.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p];lib.kodi_airplay_subtitles.restype=None
 # r39: where Kodi was, so the TV starts there (set before playing).
 if hasattr(lib,'kodi_airplay_start_at'):lib.kodi_airplay_start_at.argtypes=[ctypes.c_double];lib.kodi_airplay_start_at.restype=None
 # r40: the phone's server for a TV's own player (Roku, Chromecast, DLNA); blocks while the source opens.
 if hasattr(lib,'kodi_airplay_serve'):lib.kodi_airplay_serve.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_serve.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_serve_segmented'):   # r41: a Roku's own player gets the movie remuxed in 6-s segments
  lib.kodi_airplay_serve_segmented.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_serve_segmented.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_serve_copy'):
  lib.kodi_airplay_serve_copy.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_serve_copy.restype=ctypes.c_int
 if hasattr(lib,'kodi_background_keep'):lib.kodi_background_keep.argtypes=[ctypes.c_int];lib.kodi_background_keep.restype=None
 if hasattr(lib,'kodi_background_state'):lib.kodi_background_state.argtypes=[];lib.kodi_background_state.restype=ctypes.c_int
 return lib

def converts(lib):
 """r5 frameworks convert MKV, AVI, WebM and MPEG-TS for AirPlay on the phone."""
 return hasattr(lib,'kodi_airplay_message')

_libraries={}
_libraries_lock=threading.Lock()

def cached_load(path):
 """The service's polling callbacks share one loaded handle; a missing framework keeps the legacy fallback."""
 if not path:return None
 with _libraries_lock:
  if path not in _libraries:
   try:_libraries[path]=load(path)
   except OSError:_libraries[path]=None
  return _libraries[path]

def message(lib):
 """The framework's reason AirPlay could not play the last stream ('' when none or an older framework)."""
 if not converts(lib):return ''
 import ctypes
 buffer=ctypes.create_string_buffer(400)
 lib.kodi_airplay_message(buffer,400)
 return buffer.value.decode('utf-8','replace')

SUB_EXTENSIONS=('.srt','.ass','.ssa','.vtt','.sup','.idx')
# Where subtitle add-ons leave the file Kodi loads (a4kSubtitles, Kodi's own subtitle search).
SUB_DIRS=('special://temp/a4ksubtitles','special://profile/addon_data/service.subtitles.a4ksubtitles/temp',
          'special://temp/subtitles','special://temp')
SUB_RECENT=3*3600  # an external file older than this belongs to something else

def subtitle_choice(props,files,now):
 """r10: what to burn in from Kodi's Player.GetProperties (subtitleenabled, currentsubtitle) and recent subtitle
 files [(path, mtime)]: (ordinal, file, language) for kodi_airplay_subtitles. ordinal is Kodi's subtitle number (the
 remuxer maps it to the file's subtitle streams in order; past them it is the external file), -1 off, -2 unknown
 (the file's forced / default). A file whose name matches Kodi's current subtitle is taken as that subtitle (-2 with
 the file); otherwise the newest recent file is passed only as the fallback for an ordinal past the file's own."""
 if not isinstance(props,dict) or 'subtitleenabled' not in props:return (-2,'','')
 if not props.get('subtitleenabled'):return (-1,'','')
 current=props.get('currentsubtitle') or {}
 index=current.get('index',-1);index=index if isinstance(index,int) and index>=0 else -2
 lang=str(current.get('language') or '')[:15]
 name=str(current.get('name') or '').strip().lower()
 recent=sorted([(m,p) for p,m in files if os.path.splitext(p)[1].lower() in SUB_EXTENSIONS and now-m<SUB_RECENT],reverse=True)
 for _,path in recent:
  base=os.path.basename(path).lower()
  if name and len(name)>=4 and (name in base or os.path.splitext(base)[0] in name):return (-2,path,lang)
 return (index,recent[0][1] if recent else '',lang)

def recent_subtitle_files(translate,listdir,mtime):
 """[(path, mtime)] of subtitle files in SUB_DIRS (translate: xbmcvfs.translatePath)."""
 found=[]
 for folder in SUB_DIRS:
  try:
   root=translate(folder)
   entries=listdir(root)
   for entry in entries:
    # VobSub's IDX is the selectable index; its SUB data must remain beside it.
    stem,extension=os.path.splitext(entry)
    if extension.lower()=='.idx' and stem+('.SUB' if extension=='.IDX' else '.sub') not in entries:continue
    if os.path.splitext(entry)[1].lower() in SUB_EXTENSIONS:
     path=os.path.join(root,entry);found.append((path,mtime(path)))
  except Exception:continue
 return found

def send_subtitles(lib,xbmc,xbmcvfs,now):
 """r10: hands Kodi's current subtitle to the framework before kodi_airplay_play; returns the choice (None: older
 framework). Third-party AirPlay TVs ignore the stream's WebVTT subtitles, so the remuxer burns this one in."""
 if not hasattr(lib,'kodi_airplay_subtitles'):return None
 import json
 props={}
 try:
  players=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Player.GetActivePlayers'}))).get('result') or []
  video=[p['playerid'] for p in players if p.get('type')=='video']
  if video:
   props=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Player.GetProperties','params':{
    'playerid':video[0],'properties':['subtitleenabled','currentsubtitle']}}))).get('result') or {}
 except Exception:props={}
 choice=subtitle_choice(props,recent_subtitle_files(xbmcvfs.translatePath,os.listdir,os.path.getmtime),now)
 # Kodi can report names/ISO 639-2 while VobSub uses ISO 639-1. Let Kodi's complete language table normalize it.
 try:
  aliases=[choice[2]] if len(choice[2]) in (2,3) else []
  for fmt in (xbmc.ISO_639_2,xbmc.ISO_639_1):
   normalized=xbmc.convertLanguage(choice[2],fmt)
   if normalized and normalized not in aliases:aliases.append(normalized)
  if aliases:choice=(choice[0],choice[1],'|'.join(aliases)[:15])
 except (AttributeError,TypeError,ValueError):pass
 lib.kodi_airplay_subtitles(choice[0],choice[1].encode('utf-8'),choice[2].encode('utf-8'))
 return choice

def log_lines(lib,size=16384,rounds=8):
 """The framework's AirPlay log lines since the last call (r6; [] with an older framework). Each call drains them."""
 if not hasattr(lib,'kodi_airplay_log'):return []
 import ctypes
 lines=[]
 for _ in range(rounds):
  buffer=ctypes.create_string_buffer(size)
  if lib.kodi_airplay_log(buffer,size)<=0:break
  lines+=[line for line in buffer.value.decode('utf-8','replace').split('\n') if line]
 return lines

# Owner (build 185 log: "airplay stops out of nowhere"): the TV's first read of the movie took 12 s and the next ones
# 19 s while an AllDebrid copy went up to Drive, so Apple's player timed out. While AirPlay plays (this window property
# holds the time it was last seen working), the copies, the uploads and the conversion wait (build 193: they slow down instead).
BUSY='KodiIOS.AirPlay'   # build 193: work slows down while it is set (slowdown.py); it no longer waits
BUSY_FOR=90   # seconds after its last log line; Apple's player logs its requests and a heartbeat while it plays
LISTENING='KodiIOS.AirPlay.Listening'
TV_REQUEST='KodiIOS.AirPlay.TVRequest'
STARTED='KodiIOS.AirPlay.Started'

def network(lib,window,now=None):
 """r34 is authoritative; r33 falls back to shared log evidence, including when the service drained it."""
 now=time.time() if now is None else now
 try:started=float(window.getProperty(STARTED))
 except (TypeError,ValueError):started=0
 if hasattr(lib,'kodi_airplay_network'):
  import ctypes
  buffer=ctypes.create_string_buffer(1024)
  lib.kodi_airplay_network(buffer,len(buffer))
  try:
   net=json.loads(buffer.value.decode('utf-8'))
   if not isinstance(net,dict):return None
   if net.get('expected') and started:net['start_age_s']=max(net.get('start_age_s',-1),now-started)
   return net
  except (ValueError,UnicodeError):return None
 try:begun=float(window.getProperty(LISTENING))
 except (TypeError,ValueError):begun=0
 return {'expected':bool(begun or started),'start_age_s':now-started if started else -1,'listen_age_s':now-begun if begun else -1,
         'tv_requests':int(bool(window.getProperty(TV_REQUEST))),'legacy':True}

def log_text(line):
 """Keep only the streaming server's authority and public route; never a token or source URL."""
 def stream(match):
  from urllib.parse import urlsplit
  try:
   p=urlsplit(match.group(0));route=p.path.rsplit('/',1)[-1]
   if route in ('prepared.mp4','prepared.m3u8','prepared-media.m3u8','master.m3u8') and p.port:
    return '%s:%d/[token]/%s'%(p.hostname,p.port,route)
  except ValueError:pass
  return '[URL redacted]'
 return diagnostics.redact(re.sub(r'https?://[^\s\"\']+',stream,str(line)))
ENDED=('player: closed','player: stopped')
def mark_busy(window,now):window.setProperty(BUSY,'%.0f'%now)
def clear_busy(window):window.setProperty(BUSY,'')
SERVE='KodiIOS.TvServe'   # build 211: set when Play on TV hands a Roku, Chromecast or DLNA TV the phone's link
def mark_serve(window,now):window.setProperty(SERVE,'%.0f'%now)
def clear_serve(window):window.setProperty(SERVE,'')
def serve_busy(window,now):
 try:return now-float(window.getProperty(SERVE) or 0)<BUSY_FOR
 except (TypeError,ValueError):return False
def busy(window,now):
 try:return now-float(window.getProperty(BUSY) or 0)<BUSY_FOR
 except (TypeError,ValueError):return False

def playback_active(lib,window=None,now=None):
 """Native ownership survives lock/background and does not depend on log-flush timing or download preferences."""
 # Build 211 (log 1430bbc1, Roku via Media Assistant): a TV fed by the phone's server (Roku, Chromecast, DLNA) is
 # not Apple's player, so kodi_airplay_active() was 0 and the background ran at full speed beside it ("slowdown: full
 # speed" at 16:55:46; the TV's first 3.7 KB took 7.8 s). The server's own request lines keep the busy mark (relay).
 now=time.time() if now is None else now
 serving=serve_busy(window,now) if window is not None else False
 if hasattr(lib,'kodi_airplay_active'):return bool(lib.kodi_airplay_active()) or serving
 return (busy(window,now) if window is not None else False) or serving
# Build 193 (build-192 log, 13:10-13:30): the converter writes its own 'prepare: …' lines to the same log; they counted as
# AirPlay playing and held every worker for 90 s ("Paused while a video plays" with nothing playing). Only the AirPlay
# server's and Apple's player's lines count now.
CONVERTER=('prepare:',)
def airplay_lines(lines):return [l for l in lines or () if not str(l).lstrip().startswith(CONVERTER)]
def activity(lines,window,now):
 """relay's keep: a line from Apple's player or the AirPlay server keeps AirPlay marked busy; closed / stopped ends
 it. A slow read of the movie by the TV slows the background work further (slowdown.note_served)."""
 lines=airplay_lines(lines)
 if not lines:return
 if any(l.startswith('start result 3:') for l in lines):  # r33 found an HLS source; no phone server is needed
  window.clearProperty(STARTED);window.clearProperty(LISTENING)
 if any(l.startswith(('prepared:','master:','server: listening')) for l in lines) and not window.getProperty(LISTENING):
  window.setProperty(LISTENING,str(now))
 if any(l.startswith('client:') and any(t in l.lower() for t in ('mfi_airplay_device','apple tv','appletv')) for l in lines):
  window.setProperty(TV_REQUEST,str(now))
 try:
  import slowdown;slowdown.note_served(lines,now)
 except Exception:pass
 if any(end in line for line in lines for end in ENDED) and not any('start:' in line for line in lines):clear_busy(window);clear_serve(window)
 else:
  mark_busy(window,now)
  # A TV fed by the phone's server keeps its mark while it asks for the video (its GET lines).
  if serve_busy(window,now) and any(l.startswith(('GET ','HEAD ')) for l in lines):mark_serve(window,now)
 at=closed_at(lines)
 if at is not None:back_to_kodi(at)

def closed_at(lines):
 """r39: the position Apple's player had when it closed ("player: closed at 246.9 s"), or None."""
 found=None
 for line in lines or ():
  m=re.search(r'player: closed at ([\d.]+) s',line)
  if m:found=float(m.group(1))
 return found

def back_to_kodi(at,player=None,log=None):
 """r39 (owner, build 202: "if i stop airplay it restarts the movie"): Kodi's paused video moves to where the TV
 was. Nothing under 5 s (a start that never played) and nothing when Kodi has no video open."""
 if at<5:return False
 try:
  if player is None or log is None:
   import xbmc
   player=player or xbmc.Player();log=log or (lambda m:xbmc.log(m,xbmc.LOGINFO))
  if not player.isPlayingVideo():return False
  player.seekTime(at)
  log('Kodi iOS Play on TV: Kodi continues at %.1f s, where the TV was'%at)
  return True
 except Exception:return False

def relay(lib,write,wait,every=5,keep=None):
 """Writes the framework's AirPlay log into kodi.log every few seconds until wait(seconds) reports Kodi is closing.
 keep(lines): also hands them on (library_tools.note_airplay keeps the last Play on TV for the AirPlay check)."""
 if not hasattr(lib,'kodi_airplay_log'):return
 while True:
  lines=[log_text(line) for line in log_lines(lib)]
  for line in lines:write('Kodi iOS AirPlay: '+line)
  if lines and keep:
   try:keep(lines)
   except Exception:pass
  if wait(every):break

def watch(lib,playing,wait):
 """Shows the button while playing() is true, until wait(seconds) reports Kodi is closing."""
 shown=None
 while True:
  now=bool(playing())
  if now!=shown:lib.kodi_airplay_show(int(now));shown=now
  if wait(0.5):break
 if shown:lib.kodi_airplay_show(0)


def health(lib):
 """Safe native player snapshot; absent on older frameworks."""
 if lib is None or not hasattr(lib,'kodi_airplay_health'):return {}
 import ctypes
 buffer=ctypes.create_string_buffer(4096);lib.kodi_airplay_health(buffer,len(buffer))
 try:return json.loads(buffer.value.decode('utf-8'))
 except (ValueError,UnicodeError):return {}
