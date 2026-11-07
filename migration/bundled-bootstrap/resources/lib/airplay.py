"""Apple's AirPlay button over Kodi, from Kodi.app/Frameworks/KodiAirPlay.framework (migration/airplay-ios)."""
import os
import diagnostics
# Full-screen video or music only: on Fuse's menus the top-right corner holds the clock and the gear.
PLAYING='Player.HasMedia + [Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)]'

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
 # r10: the subtitles burned into the picture a TV gets converted (Kodi's current choice, set before playing).
 if hasattr(lib,'kodi_airplay_subtitles'):lib.kodi_airplay_subtitles.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p];lib.kodi_airplay_subtitles.restype=None
 if hasattr(lib,'kodi_background_keep'):lib.kodi_background_keep.argtypes=[ctypes.c_int];lib.kodi_background_keep.restype=None
 if hasattr(lib,'kodi_background_state'):lib.kodi_background_state.argtypes=[];lib.kodi_background_state.restype=ctypes.c_int
 return lib

def converts(lib):
 """r5 frameworks convert MKV, AVI, WebM and MPEG-TS for AirPlay on the phone."""
 return hasattr(lib,'kodi_airplay_message')

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
# holds the time it was last seen working), the copies, the uploads and the conversion wait.
BUSY='KodiIOS.AirPlay'
BUSY_FOR=90   # seconds after its last log line; Apple's player logs its requests and a heartbeat while it plays
ENDED=('player: closed','player: stopped')
def mark_busy(window,now):window.setProperty(BUSY,'%.0f'%now)
def clear_busy(window):window.setProperty(BUSY,'')
def busy(window,now):
 try:return now-float(window.getProperty(BUSY) or 0)<BUSY_FOR
 except (TypeError,ValueError):return False
def activity(lines,window,now):
 """relay's keep: a line from Apple's player keeps AirPlay marked busy; closed / stopped ends it."""
 if not lines:return
 if any(end in line for line in lines for end in ENDED) and not any('start:' in line for line in lines):clear_busy(window)
 else:mark_busy(window,now)

def relay(lib,write,wait,every=5,keep=None):
 """Writes the framework's AirPlay log into kodi.log every few seconds until wait(seconds) reports Kodi is closing.
 keep(lines): also hands them on (library_tools.note_airplay keeps the last Play on TV for the AirPlay check)."""
 if not hasattr(lib,'kodi_airplay_log'):return
 while True:
  lines=[diagnostics.redact(line) for line in log_lines(lib)]
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
