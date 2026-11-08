"""Build-194 log: no receiver request, -1004, and two overlapping Play on TV pickers."""
import importlib.util,json,subprocess,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import airplay,cast,work_state as ws

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

controller=load('cast_controller_network',BOOT/'cast.py')

class Window:
 def __init__(self):self.props={}
 def getProperty(self,key):return self.props.get(key,'')
 def setProperty(self,key,value):self.props[key]=value
 def clearProperty(self,key):self.props.pop(key,None)

class ConnectionTests(unittest.TestCase):
 def exercise(self,profile,received=None,cancel=None,legacy=False,failed=False,startup=0,choosing=0,raise_log=False,error_message=''):
  window=Window();clock=[1000.0];paused=[False];closed=[];messages=[];logs=[];notes=[];plays=[];progress_words=[]
  def wait(seconds):clock[0]+=seconds;return False
  progress=types.SimpleNamespace(create=lambda *a:progress_words.append(a[-1]),update=lambda *a:progress_words.append(a[-1]) if len(a)>1 else None,close=lambda:closed.append('progress'),
                                 iscanceled=lambda:cancel is not None and clock[0]-1000>=cancel)
  player=types.SimpleNamespace(pause=lambda:paused.__setitem__(0,not paused[0]))
  xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda m,*a:logs.append(m),getCondVisibility=lambda c:paused[0],Monitor=lambda:types.SimpleNamespace(waitForAbort=wait))
  gui=types.SimpleNamespace(Window=lambda n:window,DialogProgress=lambda:progress)
  vfs=types.SimpleNamespace(translatePath=lambda p:profile)
  def native_log(buffer,size):
   if raise_log:raise RuntimeError('fixture log failure')
   lines=[]
   if not plays:return 0
   if clock[0]-1000>=startup and not getattr(native_log,'prepared',False):lines.append('prepared: source-resolution MP4 byte ranges');native_log.prepared=True
   if received is not None and clock[0]-1000>=received and not getattr(native_log,'tv',False):
    lines.append('client: AirPlay/1 (Apple TV; fixture)');native_log.tv=True
   if failed and clock[0]-1000>=2:lines.append('player: could not open the stream: Code=-1004 "Could not connect to the server"')
   buffer.value='\n'.join(lines).encode();return len(buffer.value)
  def network(buffer,size):
   elapsed=clock[0]-1000;ready=elapsed>=startup;selected=elapsed>=startup+choosing
   reached=received is not None and elapsed>=received
   phase='opening' if not ready else 'waiting_tv' if not selected else 'playing' if reached else 'connecting'
   buffer.value=json.dumps({'expected':True,'phase':phase,'host':'192.0.2.10' if ready else '', 'port':12345 if ready else 0,
                            'start_age_s':elapsed,'listen_age_s':elapsed-startup if ready else -1,
                            'player_age_s':elapsed-startup if ready else -1,'connect_age_s':elapsed-startup-choosing if selected else -1,
                            'tv_requests':int(reached)}).encode();return len(buffer.value)
  def message(buffer,size):buffer.value=error_message.encode();return len(buffer.value)
  lib=types.SimpleNamespace(kodi_airplay_play=lambda *a:plays.append(a),kodi_airplay_close=lambda:closed.append('native'),
                            kodi_airplay_state=lambda:-1 if failed and clock[0]-1000>=2 else int(clock[0]-1000>=startup),
                            kodi_airplay_message=message,kodi_airplay_log=native_log)
  if not legacy:lib.kodi_airplay_network=network
  dialog=types.SimpleNamespace(ok=lambda *a:messages.append(a))
  with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui,'xbmcvfs':vfs}),patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'send_subtitles',return_value=None),patch.object(controller.notices,'note',side_effect=lambda *a:notes.append(a)),\
       patch.object(airplay.time,'time',side_effect=lambda:clock[0]):
   if raise_log:
    with self.assertRaisesRegex(RuntimeError,'fixture log failure'):
     controller.send_airplay(xbmc,dialog,player,'fixture','http://192.0.2.10/file.mp4','Fixture','http://127.0.0.1/file.mp4')
   else:controller.send_airplay(xbmc,dialog,player,'fixture','http://192.0.2.10/file.mp4','Fixture','http://127.0.0.1/file.mp4')
  return types.SimpleNamespace(elapsed=clock[0]-1000,window=window,paused=paused[0],closed=closed,messages=messages,logs=logs,notes=notes,plays=plays,progress_words=progress_words)

 def test_no_tv_request_stops_at_15_seconds_even_if_the_phone_is_ready(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile)
   self.assertEqual(out.elapsed,15);self.assertEqual(len(out.plays),1)
   self.assertEqual(out.closed,['progress','native']);self.assertFalse(out.paused)
   self.assertEqual(out.messages[-1][1],ws.NEEDS_TEXT['airplay_network']['text'])
   fresh=load('fresh_work_state',LIB/'work_state.py')  # another Kodi interpreter reads the marker
   state=fresh.build(fresh.flags(profile),1015)
   self.assertEqual(state['mode'],'needs_you');self.assertEqual(state['needs'][0]['button'],'Open Settings')
   self.assertEqual(state['needs'][0]['action'],'RunScript(service.kodi.ios.bootstrap,airplay_settings)')
   self.assertEqual(fresh.bell_properties(state)['Notices.Needs'],'1')
   self.assertTrue(any('192.0.2.10' in l and '12345' in l for l in out.logs))
   ws.need('airplay_network',False,profile)

 def test_r33_log_evidence_also_times_out_and_is_shared_with_the_service(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,legacy=True)
   self.assertEqual(out.elapsed,15);self.assertIn('native',out.closed)
   ws.need('airplay_network',False,profile)
  window=Window();airplay.activity(['prepared: source-resolution MP4'],window,1000)
  self.assertEqual(airplay.network(object(),window,1015)['listen_age_s'],15)
  airplay.activity(['client: AirPlay (Apple TV; fixture)'],window,1010)
  self.assertEqual(airplay.network(object(),window,1015)['tv_requests'],1)

 def test_request_before_deadline_keeps_playing_and_clears_recovery(self):
  for legacy in (False,True):
   with self.subTest(legacy=legacy),tempfile.TemporaryDirectory() as profile:
    ws.need('airplay_network',True,profile)
    out=self.exercise(profile,received=6,legacy=legacy)
    self.assertEqual(out.elapsed,6);self.assertNotIn('native',out.closed);self.assertTrue(out.paused)
    self.assertEqual(out.messages,[]);self.assertEqual(ws.flags(profile)['needs'],[])

 def test_cancel_resumes_kodi_without_creating_a_permission_warning(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,cancel=3)
   self.assertLessEqual(out.elapsed,3.5);self.assertIn('native',out.closed);self.assertFalse(out.paused)
   self.assertFalse(out.messages);self.assertFalse(ws.flags(profile)['needs'])

 def test_early_connect_error_gets_the_same_recovery_without_retry(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,failed=True)
   self.assertEqual(out.elapsed,2);self.assertEqual(len(out.plays),1)
   self.assertEqual(out.messages[-1][1],ws.NEEDS_TEXT['airplay_network']['text'])
   ws.need('airplay_network',False,profile)

 def test_start_deadline_reports_startup_instead_of_unreachable(self):
  elapsed=[0.0]
  def wait(seconds):elapsed[0]+=seconds;return False
  outcome=cast.airplay_outcome(lambda:0,wait,60,network=lambda:{'expected':True,'start_age_s':elapsed[0],'listen_age_s':-1,'tv_requests':0})
  self.assertEqual((outcome,elapsed[0]),('startup_timeout',60))
  window=Window();window.setProperty(airplay.STARTED,'1000')
  def snapshot(buffer,size):buffer.value=b'{"expected":1,"start_age_s":0,"tv_requests":0}';return len(buffer.value)
  net=airplay.network(types.SimpleNamespace(kodi_airplay_network=snapshot),window,1015)
  self.assertEqual(net['start_age_s'],15)  # a queued/restarted native probe cannot reset the caller's deadline

 def test_build196_slow_source_is_never_described_as_a_lan_permission_failure(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,startup=129)
   self.assertEqual(out.elapsed,60);self.assertEqual(len(out.plays),1)
   # Owner-approved board 5 (2026-11-08): what happened, never a network or permission problem.
   self.assertIn('took too long to open',out.messages[-1][1]);self.assertNotIn('Local Network',out.messages[-1][1])
   self.assertFalse(ws.flags(profile)['needs']);self.assertFalse(out.paused)
   self.assertIn('native',out.closed)

 def test_file_opening_and_tv_selection_do_not_spend_the_connection_deadline(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,startup=40,choosing=35,received=82)
   self.assertEqual(out.elapsed,82);self.assertNotIn('native',out.closed);self.assertTrue(out.paused)
   self.assertEqual(out.progress_words[:3],[cast.AIRPLAY_WORDS['opening'],cast.AIRPLAY_WORDS['opening'],cast.AIRPLAY_WORDS['waiting_tv']])
   self.assertIn(cast.AIRPLAY_WORDS['connecting'],out.progress_words)
   self.assertFalse(out.messages);self.assertFalse(ws.flags(profile)['needs'])

 def test_no_request_after_actual_selection_gets_15_seconds_of_connection_time(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,startup=20,choosing=35)
   self.assertEqual(out.elapsed,70)
   self.assertEqual(out.messages[-1][1],ws.NEEDS_TEXT['airplay_network']['text'])
   ws.need('airplay_network',False,profile)

 def test_no_tv_selected_gets_its_own_bounded_quiet_recovery(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,startup=5,choosing=200)
   self.assertEqual(out.elapsed,125)
   self.assertIn('No TV was chosen',out.messages[-1][1])   # owner-approved Play on TV wording (2026-11-08)
   self.assertFalse(ws.flags(profile)['needs']);self.assertFalse(out.paused)

 def test_source_connection_error_before_listener_is_not_a_tv_connection_error(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,startup=40,failed=True,error_message='The video source timed out.')
   self.assertEqual(out.elapsed,2);self.assertEqual(len(out.plays),1)
   self.assertNotIn('Local Network',out.messages[-1][1]);self.assertFalse(ws.flags(profile)['needs'])

 def test_controller_errors_also_close_native_and_resume_kodi(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,raise_log=True)
   self.assertEqual(out.closed,['native','progress']);self.assertFalse(out.paused)

 def test_direct_hls_uses_the_player_without_a_local_server_deadline(self):
  self.assertEqual(cast.airplay_outcome(lambda:1,lambda s:False,network=lambda:{'expected':False}),'playing')
  window=Window();window.setProperty(airplay.STARTED,'1000')
  airplay.activity(['start result 3:'],window,1001)
  self.assertFalse(airplay.network(object(),window,1002)['expected'])

 def test_modern_hls_keeps_the_guard_while_the_owner_chooses_a_tv(self):
  elapsed=[0.0]
  def wait(seconds):elapsed[0]+=seconds;return False
  def network():
   return {'expected':False,'phase':'waiting_tv' if elapsed[0]<35 else 'playing',
           'player_age_s':elapsed[0],'connect_age_s':-1 if elapsed[0]<35 else elapsed[0]-35}
  self.assertEqual(cast.airplay_outcome(lambda:1,wait,25,network=network),'playing')
  self.assertEqual(elapsed[0],35)

class LockTests(unittest.TestCase):
 def test_lock_is_shared_by_processes_and_does_not_expire_during_a_slow_picker(self):
  with tempfile.TemporaryDirectory() as profile:
   code='import cast,sys\nwith cast.session_lock(sys.argv[1]) as owned: print(int(owned))'
   def other():
    return subprocess.check_output([sys.executable,'-B','-c','import sys;sys.path.insert(0,sys.argv.pop(1));'+code,str(LIB),profile],text=True).strip()
   with cast.session_lock(profile) as owned:
    self.assertTrue(owned);self.assertEqual(other(),'0')
   self.assertEqual(other(),'1')

 def test_duplicate_press_during_picker_cannot_enter_or_clear_the_owners_guard(self):
  with tempfile.TemporaryDirectory() as profile:
   window=Window();notes=[];entered=[]
   xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda *a:None)
   gui=types.SimpleNamespace(Window=lambda n:window,NOTIFICATION_INFO=0,
                             Dialog=lambda:types.SimpleNamespace(notification=lambda *a:notes.append(a)))
   def picker():
    entered.append(True);before=window.getProperty(cast.BUSY)
    controller.run()  # a second Kodi invocation while the first picker is still open
    self.assertEqual(window.getProperty(cast.BUSY),before)
   with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui,'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:profile)}),\
        patch.object(controller,'run_owned',side_effect=picker):controller.run()
   self.assertEqual(entered,[True]);self.assertEqual(len(notes),1);self.assertEqual(window.getProperty(cast.BUSY),'')
   with cast.session_lock(profile) as owned:self.assertTrue(owned)

 def test_errors_release_the_guard(self):
  with tempfile.TemporaryDirectory() as profile:
   with self.assertRaises(RuntimeError):
    with cast.session_lock(profile):raise RuntimeError('fixture')
   with cast.session_lock(profile) as owned:self.assertTrue(owned)

class PlaybackLifetimeTests(unittest.TestCase):
 def test_native_playback_ownership_survives_expired_log_lease(self):
  window=Window();window.setProperty(airplay.BUSY,'1000')
  lib=types.SimpleNamespace(kodi_airplay_active=lambda:1)
  self.assertTrue(airplay.playback_active(lib,window,100000))
  window.setProperty(airplay.BUSY,'100000')
  lib.kodi_airplay_active=lambda:0
  self.assertFalse(airplay.playback_active(lib,window,100001))  # stopped playback beats a fresh old log
  self.assertTrue(airplay.playback_active(object(),window,100001))
  self.assertFalse(airplay.playback_active(object(),window,100100))

 def test_service_keeps_airplay_alive_with_downloads_disabled_and_screen_locked(self):
  import ast
  tree=ast.parse((BOOT/'service.py').read_text())
  why=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='why')
  active=[1];window=Window();window.setProperty(airplay.BUSY,'1000')
  lib=types.SimpleNamespace(kodi_airplay_active=lambda:active[0])
  env={'airplay':airplay,'lib':lib,'time':types.SimpleNamespace(time=lambda:100000),
       'xbmcgui':types.SimpleNamespace(Window=lambda n:window),
       'xbmcaddon':types.SimpleNamespace(Addon=lambda:types.SimpleNamespace(getSettingBool=lambda k:False)),
       'xbmc':types.SimpleNamespace(Player=lambda:types.SimpleNamespace(isPlayingAudio=lambda:True))}
  exec(compile(ast.Module(body=[why],type_ignores=[]),'service-background-why','exec'),env)
  self.assertEqual(env['why'](),'AirPlay')
  active[0]=0
  self.assertEqual(env['why'](),'')
  import background
  calls=[];ticks=[]
  def wait(seconds):
   ticks.append(seconds)
   if len(ticks)==2:active[0]=0
   return len(ticks)>=3
  active[0]=1
  background.watch(calls.append,env['why'],wait)
  self.assertEqual(calls,[1,1,0])

 def test_service_pollers_reuse_one_native_handle(self):
  lib=types.SimpleNamespace(kodi_airplay_active=lambda:1)
  with patch.dict(airplay._libraries,clear=True),patch.object(airplay,'load',return_value=lib) as loader:
   self.assertIs(airplay.cached_load('fixture'),lib)
   for _ in range(5):self.assertTrue(airplay.playback_active(airplay.cached_load('fixture')))
   loader.assert_called_once_with('fixture')
  with patch.dict(airplay._libraries,clear=True),patch.object(airplay,'load',side_effect=OSError('fixture')) as loader:
   self.assertIsNone(airplay.cached_load('missing'));self.assertIsNone(airplay.cached_load('missing'))
   loader.assert_called_once_with('missing')

class DiagnosticsTests(unittest.TestCase):
 def test_server_authority_survives_but_tokens_queries_and_source_links_do_not(self):
  token='a'*32
  text=airplay.log_text('stream: http://192.0.2.10:12345/'+token+'/prepared.mp4?credential=fixture')
  self.assertIn('192.0.2.10:12345/[token]/prepared.mp4',text)
  self.assertNotIn(token,text);self.assertNotIn('fixture',text)
  self.assertEqual(airplay.log_text('start: https://fixture.invalid/private/file.mkv?key=value'),'start: [URL redacted]')

 def test_native_request_is_logged_before_serving_and_network_snapshot_is_not_drained(self):
  code=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  connection=code[code.index('static void *connection('):code.index('static void *accept_loop(')]
  self.assertLess(connection.index('request: peer='),connection.index('if (ok) serve('))
  self.assertLess(connection.index('N.tv_requests++'),connection.index('if (ok) serve('))
  self.assertIn('first TV request peer=',connection)
  snapshot=code[code.index('int kr_remux_network('):code.index('void kr_remux_network_begin(')]
  self.assertNotIn('kr_remux_log(',snapshot);self.assertNotIn('S.lock',snapshot)
  self.assertIn('server: listening bind=',code);self.assertIn('accept: peer=',code)
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('_kodi_airplay_network\\n_kodi_airplay_settings\\n',build)
  self.assertIn('generation != atomic_load(&playGeneration)',build)
  self.assertEqual(json.loads((ROOT/'migration/airplay-ios/source-lock.json').read_text())['framework_release']['tag'],'kodi-airplay-r36')

 def test_settings_bridge_and_fallback(self):
  settings=load('airplay_settings_test',BOOT/'airplay_settings.py')
  for available in (True,False):
   with self.subTest(bridge=available):
    opened=[];instructions=[]
    lib=types.SimpleNamespace(**({'kodi_airplay_settings':lambda:opened.append(True)} if available else {}))
    modules={'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:p),
             'xbmcgui':types.SimpleNamespace(Dialog=lambda:types.SimpleNamespace(ok=lambda *a:instructions.append(a)))}
    with patch.dict(sys.modules,modules),patch.object(airplay,'library_path',return_value='fixture'),patch.object(airplay,'load',return_value=lib):settings.run()
    self.assertEqual(bool(opened),available);self.assertEqual(bool(instructions),not available)


class SoundOnlyRestart(unittest.TestCase):
 """r36 (owner's build-198 log: a TCL Roku TV took the sound of a prepared HEVC movie only): the native player restarts
 with the H.264 picture and opens again; the TV choice and connection deadlines start over instead of expiring."""
 def test_a_restart_gets_fresh_connection_time(self):
  t=[0.0];phases=[]
  def net():
   # 0-4 s opening, 4-10 s connecting with no TV request (sound only), 10-20 s opening again (compat), then
   # connecting from 20 s, and the TV fetches at 32 s: 12 s after the restart's connect, 28 s after the first one.
   at=t[0]
   phase='opening' if at<4 else 'connecting' if at<10 else 'opening' if at<20 else 'connecting'
   return {'expected':True,'phase':phase,'tv_requests':1 if at>=32 else 0}
  def wait(s):t[0]+=s;return False
  outcome=cast.airplay_outcome(lambda:1 if t[0]>=32 else 0,wait,60,network=net,stage=lambda g,w:phases.append(g))
  self.assertEqual(outcome,'playing')
  self.assertEqual(phases,['opening','connecting','opening','connecting'])
 def test_the_card_says_the_picture_is_being_converted(self):
  import airplay_flow
  v=airplay_flow.stage_view('opening','Movie',converting=True)
  self.assertEqual(v['title'],'Converting the picture for your TV');self.assertEqual(v['step0.label'],'Converting the picture to H.264')
 def test_native_restarts_prepared_movies_once_when_the_tv_takes_the_sound_only(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn("soundOnlyTicks = (!external && tvRoute(player)) ? soundOnlyTicks + 1 : 0;",build)
  self.assertIn("__block BOOL warned = NO, compatTried = kr_remux_compat() != 0, restarting = NO;",build)
  self.assertIn("if (!preparedLink && wasOn && !external",build)
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertIn('if(!compat && kr_prepare_ready(prepared)',remux)

if __name__=='__main__':unittest.main()
