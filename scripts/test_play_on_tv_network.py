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
 def exercise(self,profile,received=None,cancel=None,legacy=False,failed=False,startup=0,choosing=0,raise_log=False,error_message='',roku=False,copy_api=True):
  window=Window();clock=[1000.0];paused=[False];closed=[];messages=[];logs=[];notes=[];plays=[];progress_words=[]
  def wait(seconds):clock[0]+=seconds;return False
  progress=types.SimpleNamespace(create=lambda *a:progress_words.append(a[-1]),update=lambda *a:progress_words.append(a[-1]) if len(a)>1 else None,close=lambda:closed.append('progress'),
                                 iscanceled=lambda:cancel is not None and clock[0]-1000>=cancel)
  player=types.SimpleNamespace(pause=lambda:paused.__setitem__(0,not paused[0]))
  xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda m,*a:logs.append(m),getCondVisibility=lambda c:paused[0],Monitor=lambda:types.SimpleNamespace(waitForAbort=wait,abortRequested=lambda:False))
  gui=types.SimpleNamespace(Window=lambda n:window,DialogProgress=lambda:progress)
  vfs=types.SimpleNamespace(translatePath=lambda p:profile)
  def native_log(buffer,size):
   if raise_log:raise RuntimeError('fixture log failure')
   lines=[]
   if not plays:return 0
   if clock[0]-1000>=startup and not getattr(native_log,'prepared',False):lines.append('prepared: source-resolution MP4 byte ranges');native_log.prepared=True
   if received is not None and clock[0]-1000>=received and not getattr(native_log,'tv',False):
    if roku:lines.extend([
     'source: video codec=hevc profile=2 pixel_format=yuv420p10le bit_depth=10 raw_bit_depth=0 dimensions=3840x2160 level=153',
     'network: TV receiver peer=192.168.1.20 agent=AirPlay/2.0 MFi_AirPlay_Device (MFiModelGroup/TCL Roku TV)',
     'compat: converting video stream 0 to H.264 1920x1080'])
    else:lines.append('client: AirPlay/1 (Apple TV; fixture)')
    native_log.tv=True
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
  if roku and copy_api:lib.kodi_airplay_serve_copy=lambda *a:2
  dialog=types.SimpleNamespace(ok=lambda *a:messages.append(a))
  def get(url,timeout):
   return b'<apps><app id="782875">Media Assistant</app></apps>' if url.endswith('/apps') else b'<device-info><supports-4k>true</supports-4k></device-info>'
  with patch.object(controller,'send') as fallback,patch.object(cast,'http_get',side_effect=get),\
       patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui,'xbmcvfs':vfs}),patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'send_subtitles',return_value=None),patch.object(controller.notices,'note',side_effect=lambda *a:notes.append(a)),\
       patch.object(airplay.time,'time',side_effect=lambda:clock[0]):
   if raise_log:
    with self.assertRaisesRegex(RuntimeError,'fixture log failure'):
     controller.send_airplay(xbmc,dialog,player,'fixture','http://192.0.2.10/file.mp4','Fixture','http://127.0.0.1/file.mp4')
   else:controller.send_airplay(xbmc,dialog,player,'fixture','http://192.0.2.10/file.mp4','Fixture','http://127.0.0.1/file.mp4')
  return types.SimpleNamespace(elapsed=clock[0]-1000,window=window,paused=paused[0],closed=closed,messages=messages,logs=logs,notes=notes,plays=plays,progress_words=progress_words,fallback=fallback)

 def test_converting_roku_switches_same_tv_to_original_picture_route(self):
  with tempfile.TemporaryDirectory() as profile:
   out=self.exercise(profile,received=3,roku=True)
  out.fallback.assert_called_once()
  self.assertEqual(out.fallback.call_args.args[4]['host'],'192.168.1.20')
  self.assertEqual(out.fallback.call_args.kwargs,{'preserve_picture':True,'restore_on_failure':True})
  self.assertIn('native',out.closed);self.assertLess(out.elapsed,10)
 def test_old_framework_and_cancel_do_not_switch_routes(self):
  with tempfile.TemporaryDirectory() as profile:
   self.exercise(profile,received=3,roku=True,copy_api=False).fallback.assert_not_called()
   self.exercise(profile,received=3,roku=True,cancel=2).fallback.assert_not_called()
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
    self.assertEqual(out.elapsed,6+45);self.assertNotIn('native',out.closed);self.assertTrue(out.paused)   # r38: + Kodi watching 45 s after "playing"
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
 def test_new_native_budget_leaves_room_for_real_buffering_and_reports_legacy_limit(self):
  self.assertEqual(airplay.startup_budget(types.SimpleNamespace()),60)
  self.assertEqual(airplay.startup_budget(types.SimpleNamespace(kodi_airplay_startup_budget=lambda:100)),105)
  self.assertEqual(airplay.startup_budget(types.SimpleNamespace(kodi_airplay_startup_budget=lambda:999999)),60)
  elapsed=[0.0]
  def wait(seconds):elapsed[0]+=seconds;return False
  def network():return {'expected':True,'phase':'opening' if elapsed[0]<80 else 'playing','start_age_s':elapsed[0],
                        'tv_requests':int(elapsed[0]>=80),'tv_video':int(elapsed[0]>=80)}
  result=cast.airplay_outcome(lambda:int(elapsed[0]>=80),wait,network=network,startup_limit=105)
  self.assertEqual((result,elapsed[0]),('playing',80))
 def test_startup_progress_logs_preserve_pause_state_and_controller_budget(self):
  with tempfile.TemporaryDirectory() as profile:
   import transfer_control
   transfer_control.set_paused(profile,'up',True)
   out=self.exercise(profile,startup=4,received=6)
  events=[json.loads(s.split('Kodi iOS diagnostic ',1)[1]) for s in out.logs if '"event":"startup_progress"' in s]
  self.assertTrue(events);self.assertEqual(events[0]['controller_budget_s'],60)
  self.assertTrue(events[0]['background_paused']['up']);self.assertIn('phase',events[0]['native'])

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
   self.assertEqual(out.elapsed,82+45);self.assertNotIn('native',out.closed);self.assertTrue(out.paused)   # r38: + Kodi watching 45 s after "playing"
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
   self.assertEqual(out.elapsed,2+2);self.assertEqual(len(out.plays),1)   # r38: + 2 s reading the close's log lines
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
  self.assertRegex(json.loads((ROOT/'migration/airplay-ios/source-lock.json').read_text())['framework_release']['tag'],r'^kodi-airplay-r\d+$')

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
  self.assertIn("__block BOOL warned = NO, compatTried = kr_remux_compat() != 0, restarting = NO, everExternal = NO, slowNoted = NO;",build)
  self.assertIn("if (!preparedLink && wasOn && !external",build)
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertIn('if(!compat && !segmented && kr_prepare_ready(prepared)',remux)
 def test_the_old_items_failure_does_not_cancel_the_restart(self):
  # Build 200 log: the r36 restart began, but routeWatch reported the old item's failure in the same tick, so Kodi
  # showed "AirPlay couldn't play this" and closed the player ("start result -1: AirPlay canceled").
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('static atomic_int compatBusy;',build)
  self.assertIn('compatTried = YES; restarting = YES; atomic_store(&compatBusy,1);',build)
  self.assertIn('restarting = NO; atomic_store(&compatBusy,0);',build)
  self.assertIn('failedSeen=failed && !atomic_load(&compatBusy) ? failedSeen+1 : 0;',build)
  self.assertIn('if(failedSeen>=3){if(playbackStateFor(generation,-1,0))atomic_store(&healthReason,2);}',build)
  self.assertIn('openFailedSeen = openFailed && !atomic_load(&compatBusy) ? openFailedSeen + 1 : 0;',build)
  self.assertIn('} else if (openFailedSeen >= 3) {',build)
  self.assertIn('if(atomic_load(&compatBusy))return;   // r37',build)
  self.assertNotIn('if(item.status==AVPlayerItemStatusFailed || player.status==AVPlayerStatusFailed)playbackStateFor(generation,-1,0);',build)

class SlowSource(unittest.TestCase):
 """r38 (owner's build-201 log and photos): the TV took the H.264 stream, the phone needed 20.7 s to read one segment
 from Drive, the TV stopped 13 s after connecting and Apple's bare "AirPlay stopped" alert showed. Kodi now keeps
 watching after "playing" and shows the slow-internet card; uploads are not paused (owner)."""
 LOG=['GET /audio/1/seg0.m4s 200 291200 B 4184 ms','compat: segment 0 stopped after 21817 ms, source I/O 20689 ms',
      'request: converted video segment 0 waited 17876 ms, production 0 ms, result -1']
 def test_the_build_201_log_reads_as_a_slow_source(self):
  self.assertTrue(cast.slow_source(self.LOG))
  self.assertFalse(cast.slow_source(['GET /prepared.mp4 bytes=0-1 -206 0 B 8950 ms']))
 def test_build213_queue_waits_and_teardown_are_not_upstream_measurements(self):
  for line in ('request: video segment -1 waited 45345 ms, production 0 ms, result 0',
               'GET /video/init.mp4 500 0 B 12157 ms: session stopped',
               'GET /video/init.mp4 200 3222 B 45345 ms'):
   self.assertFalse(cast.slow_source([line]),line)
 def test_playlist_and_audio_do_not_claim_video_playback(self):
  net={'expected':1,'tv_requests':3,'tv_media':1,'tv_video':0,'phase':'connecting'}
  self.assertEqual(cast.airplay_outcome(lambda:1,lambda _:False,timeout=2,network=lambda:net),'failed')
  self.assertEqual(cast.receiver_outcome(lambda:net,lambda _:False,timeout=2),'failed')
  net['tv_video']=1
  self.assertEqual(cast.airplay_outcome(lambda:1,lambda _:False,network=lambda:net),'playing')
  self.assertEqual(cast.receiver_outcome(lambda:net,lambda _:False),'playing')
 def test_roku_never_waits_forever_for_a_disconnected_tv(self):
  self.assertEqual(cast.receiver_outcome(lambda:{'tv_requests':0},lambda _:False),'unreachable')
  self.assertEqual(cast.receiver_outcome(lambda:{},lambda _:True),'aborted')
 def test_receiver_feedback_distinguishes_delivery_from_playback(self):
  net={'tv_requests':5,'tv_video':1,'receiver_state':'buffering'}
  self.assertEqual(cast.receiver_outcome(lambda:net,lambda _:False,timeout=1),'failed')
  net['receiver_state']='play'
  self.assertEqual(cast.receiver_outcome(lambda:net,lambda _:False),'playing')
  net['receiver_error']=True
  self.assertEqual(cast.receiver_outcome(lambda:net,lambda _:False),'failed')

class RokuFeedback(unittest.TestCase):
 def test_unknown_capability_never_silently_forces_a_downgrade(self):
  self.assertFalse(cast.roku_needs_compatibility({}))
  self.assertFalse(cast.roku_needs_compatibility({'supports-4k':'true'}))
  self.assertTrue(cast.roku_needs_compatibility({'supports-4k':'false'}))
  self.assertTrue(cast.roku_needs_compatibility({'max-resolution':'1920x1080'}))
 def test_player_snapshot_and_privacy(self):
  sample=b'<player error="false" state="play"><plugin id="782875" name="private title"/><format audio="aac" video="hevc" video_res="3840x2160" captions="webvtt"/><position>6916 ms</position><url>private-url</url></player>'
  status=cast.roku_player('tv',lambda url,timeout:sample)
  self.assertEqual(status,{'state':'play','error':False,'player_id':'782875','position_ms':6916,'audio':'aac','video':'hevc','video_res':'3840x2160','captions':'webvtt'})
  self.assertEqual(cast.roku_player('tv',lambda *a:b'<player'),{})
  self.assertEqual(cast.roku_player('tv',lambda *a:b'x'*40000),{})
 def test_unavailable_feedback_is_optional_and_model_has_no_device_ids(self):
  def blocked(*a):raise OSError('unavailable')
  self.assertEqual(cast.roku_player('tv',blocked),{})
  status=cast.roku_model('tv',lambda *a:b'<device-info><model-number>4800X</model-number><serial-number>private-serial</serial-number><wifi-mac>private-mac</wifi-mac></device-info>')
  self.assertEqual(status['model-number'],'4800X');self.assertNotIn('private',str(status))
 def test_normal_reads_are_not_slow(self):
  for line in ('GET /prepared.mp4 bytes=73859072-7098056596 -206 1703936 B 6984 ms','request: audio segment 0 waited 3771 ms, production 0 ms, result 0',
               'GET /audio/1/seg0.m4s 200 291200 B 4184 ms','startup: source opened after 8371 ms (attempt 2)'):
   self.assertFalse(cast.slow_source([line]),line)
 def test_settle_reports_a_stop_and_lets_a_good_start_go(self):
  t=[0.0]
  def wait(s):t[0]+=s;return False
  self.assertEqual(cast.airplay_settle(lambda:-1 if t[0]>=13 else 1,wait,seconds=45),'failed');self.assertEqual(t[0],13)
  t[0]=0.0;self.assertEqual(cast.airplay_settle(lambda:1,wait,seconds=45),'playing');self.assertEqual(t[0],45)
  self.assertEqual(cast.airplay_settle(lambda:1,lambda s:True,seconds=45),'playing')
 def test_the_card_has_no_pause_button(self):
  import airplay_flow
  v=airplay_flow.problem_view('slow_source','Movie',busy='Interstellar is uploading to Google Drive at 0.2 MB/s')
  self.assertEqual(v['title'],'The movie took too long to load');self.assertEqual(v['icon'],'wifi.png')
  self.assertNotIn('downloaded movie',v['text']);self.assertNotIn('internet is too slow',v['text'])
  self.assertIn('Interstellar is uploading to Google Drive at 0.2 MB/s at the same time.',v['text'])
  self.assertEqual((v['b1.action'],v['b2.action'],v['link.action']),('retry','','watch'))
  self.assertNotIn('pause',json.dumps(v).lower())
 def test_play_on_tv_watches_after_playing(self):
  text=(BOOT/'cast.py').read_text()
  self.assertIn("settled=cast.airplay_settle(lib.kodi_airplay_state,lambda s:monitor.waitForAbort(s),network)",text)
  self.assertIn("if settled=='playing':return True",text)
  self.assertIn("if cast.slow_source(lines):outcome='slow_source'",text)
  self.assertIn("props=airplay_flow.problem_view('slow_source',title,busy=busy)",text)
  self.assertLess(text.index("elif outcome=='slow_source'"),text.index(' elif why:'))
 def test_native_leaves_problems_to_kodi_while_it_watches(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('atomic_store(&kodiPolledAt, NSProcessInfo.processInfo.systemUptime);',build)
  problem=build[build.index('static void showProblem('):build.index('UIAlertController *alert',build.index('static void showProblem('))]
  self.assertIn('if (NSProcessInfo.processInfo.systemUptime - atomic_load(&kodiPolledAt) < 2.0) {',problem)
  self.assertIn('playbackStateFor(atomic_load(&playGeneration), -1, 0);',problem)
 def test_converting_text_sits_at_the_top_clear_of_the_buttons(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  conv=build[build.index('static void showConverting('):build.index('static NSString *sizeText(')]
  self.assertIn('[pill.topAnchor constraintEqualToAnchor:safe.topAnchor constant:12]',conv)
  self.assertNotIn('centerYAnchor',conv)
  self.assertIn('pill.userInteractionEnabled = NO;',conv)

class PreparedAsHls(unittest.TestCase):
 """r38 (owner's build-201 Apple TV log: black screen, the Apple TV never asked for anything): Apple's player walked the
 prepared MP4 fragment by fragment; it now gets HLS byte ranges over the same file from the file's fragment index."""
 def test_the_log_keeps_the_new_routes(self):
  self.assertEqual(airplay.log_text('server: endpoint http://10.0.0.247:50516/abc123/prepared.m3u8'),'server: endpoint 10.0.0.247:50516/[token]/prepared.m3u8')
  self.assertEqual(airplay.log_text('GET http://10.0.0.247:1/abc/prepared-media.m3u8'),'GET 10.0.0.247:1/[token]/prepared-media.m3u8')
 def test_native_serves_playlists_from_the_fragment_index(self):
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertIn('static int prepared_playlists(int align_plan) {',remux)
  self.assertIn('#EXT-X-MAP:URI=\\"%s/prepared.mp4\\",BYTERANGE=\\"%lld@0\\"',remux)
  self.assertIn('#EXT-X-BYTERANGE:%lld@%lld',remux)
  self.assertIn('snprintf(out,(size_t)outlen,"%s/prepared.%s",S.base,S.prepared_master?"m3u8":"mp4");',remux)
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('[link hasSuffix:@"/prepared.m3u8"]',build)

class AfterAirPlay(unittest.TestCase):
 """r39 (owner, build 202: "if i stop airplay it restarts the movie ... And subtitles didnt work"): the TV starts
 where Kodi was, Kodi continues where the TV was, and the file's text subtitles go as WebVTT renditions."""
 def test_closed_at_is_read_from_the_player_line(self):
  self.assertEqual(airplay.closed_at(['player: 120s: at 210.4 s','player: closed at 246.9 s']),246.9)
  self.assertIsNone(airplay.closed_at(['player: stopped: x']))
 def test_kodi_seeks_to_where_the_tv_was(self):
  seen=[]
  class Player:
   def isPlayingVideo(self):return True
   def seekTime(self,t):seen.append(t)
  self.assertTrue(airplay.back_to_kodi(246.9,Player(),log=lambda m:None));self.assertEqual(seen,[246.9])
  self.assertFalse(airplay.back_to_kodi(0.0,Player(),log=lambda m:None));self.assertEqual(seen,[246.9])
  class Idle(Player):
   def isPlayingVideo(self):return False
  self.assertFalse(airplay.back_to_kodi(300,Idle(),log=lambda m:None))
 def test_the_tv_starts_where_kodi_is(self):
  text=(BOOT/'cast.py').read_text()
  self.assertLess(text.index('lib.kodi_airplay_start_at(float(player.getTime()))'),text.index("lib.kodi_airplay_play(source.encode('utf-8')"))
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('void kodi_airplay_start_at(double seconds)',build);self.assertIn('_kodi_airplay_start_at\\n',build)
  self.assertIn('const double startAt = atomic_exchange(&pendingStart, 0.0);',build)
  self.assertIn('[item selectMediaOption:legible.defaultOption inMediaSelectionGroup:legible];',build)
 def test_prepared_playlists_offer_text_subtitles(self):
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertIn('if(strncmp(path,"/subs/",6)){fail(fd,404,"Not Found");return;}',remux)
  self.assertIn('#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID=\\"subs\\"',remux)

class AnyTv(unittest.TestCase):
 """r40 (owner, build 203: "work on any tv thats connected to the same wifi"): Roku (Media Assistant), Chromecast and
 DLNA TVs get the phone's own server, not Kodi's link (Drive and Elementum answer on 127.0.0.1 only)."""
 def lib(self,result,link):
  calls=[]
  def serve(source,compat,out,size):calls.append((source,compat));out.value=link.encode();return result
  return calls,types.SimpleNamespace(kodi_airplay_serve=serve,kodi_airplay_close=lambda:calls.append('close'),
                                     kodi_airplay_log=lambda b,n:0,kodi_airplay_message=lambda b,n:0)
 def run_link(self,result,link,kind):
  controller=load('cast_controller',BOOT/'cast.py')
  calls,lib=self.lib(result,link);logs=[]
  xbmc=types.SimpleNamespace(log=lambda m,l=0:logs.append(m),executebuiltin=lambda c:None,LOGINFO=1,LOGWARNING=2)
  with patch.object(controller.airplay,'load',return_value=lib):
   out=controller.tv_link(xbmc,'lib','http://192.168.1.24:1234/drive','http://127.0.0.1:1234/drive',kind)
  return out,calls
 def test_copy_only_route_uses_dedicated_api_and_passes_resume_position(self):
  calls,lib=self.lib(2,'unused')
  def copy(source,out,size):calls.append(('copy',source));out.value=b'http://192.168.1.24:5000/t/master.m3u8';return 2
  lib.kodi_airplay_serve_copy=copy;lib.kodi_airplay_start_at=lambda at:calls.append(('start',at))
  xbmc=types.SimpleNamespace(log=lambda *a:None,executebuiltin=lambda c:None,LOGINFO=1,LOGWARNING=2)
  with patch.object(airplay,'load',return_value=lib):
   result=controller.tv_link(xbmc,'lib','http://192.168.1.24/drive','http://127.0.0.1/drive','roku',preserve_picture=True,start=720)
  self.assertTrue(result[1]);self.assertIn(('start',720.0),calls);self.assertIn(('copy',b'http://127.0.0.1/drive'),calls)
  self.assertFalse(any(isinstance(c,tuple) and len(c)==2 and isinstance(c[0],bytes) for c in calls))
 def test_roku_gets_the_phones_playlist(self):
  (link,served),calls=self.run_link(2,'http://192.168.1.24:5000/t/prepared.m3u8','roku')
  self.assertEqual((link,served),('http://192.168.1.24:5000/t/prepared.m3u8',True))
  self.assertEqual(calls,['close',(b'http://127.0.0.1:1234/drive',0)])   # the phone reads Kodi's own link
 def test_dlna_gets_the_prepared_mp4(self):
  (link,served),_=self.run_link(2,'http://192.168.1.24:5000/t/prepared.m3u8','dlna')
  self.assertEqual(link,'http://192.168.1.24:5000/t/prepared.mp4')
 def test_hls_sources_and_failures_keep_kodis_link(self):
  self.assertEqual(self.run_link(3,'','chromecast')[0],('http://192.168.1.24:1234/drive',False))
  self.assertEqual(self.run_link(-1,'','roku')[0],('http://192.168.1.24:1234/drive',None))
 def test_native_serve_export(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('int kodi_airplay_serve(const char *url, int compat, char *out, int outlen)',build)
  self.assertIn('compat == KR_COMPAT_ROKU_SAFE ? KR_COMPAT_ROKU_SAFE',build)
  self.assertIn('_kodi_airplay_serve\\n',build);self.assertRegex(build,r"== (29|[3-9][0-9]) \]\]")   # r54 added an export (30)

class RokuHandoff(unittest.TestCase):
 def setUp(self):
  for name in ('roku_model','roku_player'):
   mock=patch.object(cast,name,return_value={});mock.start();self.addCleanup(mock.stop)
 def phone(self,paused=False):
  state=[paused];events=[]
  def pause():state[0]=not state[0];events.append('pause' if state[0] else 'resume')
  player=types.SimpleNamespace(getTime=lambda:0,pause=pause,stop=lambda:events.append('stop'))
  xbmc=types.SimpleNamespace(getCondVisibility=lambda _:state[0],log=lambda *a:None,LOGINFO=1,LOGWARNING=2,
                           Monitor=lambda:types.SimpleNamespace(waitForAbort=lambda _:False))
  return state,events,player,xbmc
 def test_failed_preparation_restores_phone_and_never_launches_roku(self):
  for was_paused in (False,True):
   state,events,player,xbmc=self.phone(was_paused)
   def prepare(*args,**kwargs):
    self.assertTrue(state[0]);events.append('buffer');return ('source',None)
   lib=types.SimpleNamespace(kodi_airplay_close=lambda:events.append('close'))
   dialog=types.SimpleNamespace(ok=lambda *a:events.append('problem'))
   gui=types.SimpleNamespace(Window=lambda _:Window())
   with patch.object(controller,'tv_link',side_effect=prepare),patch.object(airplay,'load',return_value=lib),\
        patch.object(airplay,'message',return_value='Read timed out'),patch.object(controller.notices,'note'),\
        patch.object(cast,'roku_play') as launch,patch.dict(sys.modules,{'xbmcgui':gui}):
    controller.send(xbmc,dialog,player,'lib',{'kind':'roku','host':'tv','name':'Roku'},'source','Movie',True)
   launch.assert_not_called();self.assertEqual(state[0],was_paused)
   self.assertEqual(events,['buffer','close','problem'] if was_paused else ['pause','buffer','close','resume','problem'])
 def test_preserve_picture_failure_restores_phone_without_h264_or_airplay_retry(self):
  state,events,player,xbmc=self.phone(True)
  lib=types.SimpleNamespace(kodi_airplay_close=lambda:events.append('close'))
  gui=types.SimpleNamespace(Window=lambda _:Window())
  ui=types.SimpleNamespace(show=lambda *a:None,canceled=lambda:False,close=lambda:None,ask=lambda *a:'watch')
  dialog=types.SimpleNamespace(ok=lambda *a:events.append('problem'))
  with patch.object(controller,'tv_link',return_value=('tv-link',True)) as link,patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'message',return_value=''),patch.object(cast,'roku_model',return_value={'supports-4k':'true'}),\
       patch.object(cast,'http_post') as launch,patch.object(cast,'roku_play') as old_launch,\
       patch.object(cast,'receiver_outcome',return_value='failed'),patch.object(controller,'FlowUI',return_value=ui),\
       patch.object(controller,'send_airplay') as again,patch.object(controller.notices,'note'),\
       patch.dict(sys.modules,{'xbmcgui':gui}):
   controller.send(xbmc,dialog,player,'lib',{'kind':'roku','host':'tv','name':'Roku'},'source','Movie',True,
                   preserve_picture=True,restore_on_failure=True)
  link.assert_called_once();self.assertTrue(link.call_args.kwargs['preserve_picture'])
  launch.assert_called_once();self.assertIn('/launch/782875?',launch.call_args.args[0])
  old_launch.assert_not_called();again.assert_not_called();self.assertFalse(state[0])
 def test_cancel_before_video_returns_to_phone(self):
  state,events,player,xbmc=self.phone()
  lib=types.SimpleNamespace(kodi_airplay_close=lambda:events.append('close'))
  gui=types.SimpleNamespace(Window=lambda _:Window())
  ui=types.SimpleNamespace(show=lambda *a:None,canceled=lambda:True,close=lambda:None)
  with patch.object(controller,'tv_link',return_value=('tv-link',True)),patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'message',return_value=''),patch.object(airplay,'log_lines',return_value=[]),\
       patch.object(airplay,'network',return_value={'tv_requests':2,'tv_video':0}),\
       patch.object(controller,'FlowUI',return_value=ui),patch.object(cast,'roku_play',return_value='Media Assistant'),\
       patch.object(controller.notices,'note'),patch.dict(sys.modules,{'xbmcgui':gui}):
   controller.send(xbmc,object(),player,'lib',{'kind':'roku','host':'tv','name':'Roku'},'source','Movie',True)
  self.assertFalse(state[0]);self.assertEqual(events,['pause','close','resume'])
 def test_connected_receiver_failure_tries_compatibility_only_once(self):
  state,events,player,xbmc=self.phone();links=[]
  def link(*args,**kwargs):links.append(kwargs.get('safe',False));return 'tv-link',True
  lib=types.SimpleNamespace(kodi_airplay_close=lambda:events.append('close'))
  gui=types.SimpleNamespace(Window=lambda _:Window(),Dialog=lambda:types.SimpleNamespace(notification=lambda *a:None),NOTIFICATION_INFO=1)
  ui=types.SimpleNamespace(show=lambda *a:None,canceled=lambda:False,close=lambda:None)
  with patch.object(controller,'tv_link',side_effect=link),patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'log_lines',return_value=[]),patch.object(airplay,'network',return_value={'tv_requests':4,'tv_video':0,'phase':'failed'}),\
       patch.object(controller,'FlowUI',return_value=ui),patch.object(cast,'roku_play',return_value='Media Assistant'),\
       patch.object(controller.notices,'note'),patch.dict(sys.modules,{'xbmcgui':gui}):
   count=[0]
   def outcome(network,wait):count[0]+=1;network();return 'failed' if count[0]==1 else 'playing'
   with patch.object(cast,'receiver_outcome',side_effect=outcome):controller.send(xbmc,object(),player,'lib',{'kind':'roku','host':'tv','name':'Roku'},'source','Movie',True)
  self.assertEqual(links,[False,True]);self.assertEqual(count[0],2);self.assertEqual(events,['pause','close','stop'])

 def test_compatibility_retry_failure_cancel_and_capability_preserve_phone(self):
  cases=[({},4,'failed',False,[False,True]),({},4,'aborted',False,[False,True]),
         ({},4,'failed',True,[False,True]),({},0,'failed',False,[False]),
         ({'supports-4k':'false'},4,'failed',False,[True]),({},4,'raise',False,[False,True])]
  for model,requests,final,paused,expected in cases:
   with self.subTest(model=model,requests=requests,final=final,paused=paused):
    state,events,player,xbmc=self.phone(paused);links=[]
    def link(*args,**kwargs):
     links.append(kwargs.get('safe',False))
     if final=='raise' and len(links)==2:raise RuntimeError('preparation interrupted')
     return 'tv-link',True
    lib=types.SimpleNamespace(kodi_airplay_close=lambda:events.append('close'))
    gui=types.SimpleNamespace(Window=lambda _:Window())
    ui=types.SimpleNamespace(show=lambda *a:None,canceled=lambda:False,close=lambda:None,ask=lambda *a:'phone')
    def outcome(network,wait):network();return final if len(links)==2 else 'failed'
    with patch.object(controller,'tv_link',side_effect=link),patch.object(airplay,'load',return_value=lib),\
         patch.object(airplay,'message',return_value=''),patch.object(airplay,'log_lines',return_value=[]),\
         patch.object(airplay,'network',return_value={'tv_requests':requests,'tv_video':0,'phase':'failed'}),\
         patch.object(controller,'FlowUI',return_value=ui),patch.object(cast,'roku_play',return_value='Media Assistant'),\
         patch.object(cast,'receiver_outcome',side_effect=outcome),patch.object(cast,'roku_model',return_value=model),\
         patch.object(controller.notices,'note'),patch.dict(sys.modules,{'xbmcgui':gui}):
     controller.send(xbmc,object(),player,'lib',{'kind':'roku','host':'tv','name':'Roku'},'source','Movie',True)
    self.assertEqual(links,expected);self.assertEqual(state[0],paused);self.assertNotIn('stop',events)

class RokuSegmented(unittest.TestCase):
 """ISSUE-138 (owner's build-209/211 logs): a Roku read the prepared playlists and the 3.7 KB init (7.8 s), then
 nothing; Roku's AirPlay read prepared.m3u8 only and Apple's player stopped. Roku's streaming specifications: CMAF HLS
 with audio and video muxed is not supported, 4-6 s chunks recommended; the prepared fragments are muxed, up to 70 s."""
 def lib(self,segmented=True):
  calls=[]
  def serve(source,compat,out,size):calls.append(('serve',source,compat));out.value=b'http://192.168.1.24:5000/t/prepared.m3u8';return 2
  def serve_segmented(source,out,size):calls.append(('segmented',source));out.value=b'http://192.168.1.24:5000/t/master.m3u8';return 2
  ns=types.SimpleNamespace(kodi_airplay_serve=serve,kodi_airplay_close=lambda:None,kodi_airplay_log=lambda b,n:0,kodi_airplay_message=lambda b,n:0)
  if segmented:ns.kodi_airplay_serve_segmented=serve_segmented
  return calls,ns
 def link(self,kind,segmented=True):
  controller=load('cast_controller',BOOT/'cast.py')
  calls,lib=self.lib(segmented)
  xbmc=types.SimpleNamespace(log=lambda m,l=0:None,executebuiltin=lambda c:None,LOGINFO=1,LOGWARNING=2)
  with patch.object(controller.airplay,'load',return_value=lib):
   out=controller.tv_link(xbmc,'lib','http://192.168.1.24:1234/drive','http://127.0.0.1:1234/drive',kind)
  return out,calls
 def test_roku_gets_the_segmented_stream(self):
  (link,served),calls=self.link('roku')
  self.assertEqual((link,served),('http://192.168.1.24:5000/t/master.m3u8',True))
  self.assertEqual(calls,[('segmented',b'http://127.0.0.1:1234/drive')])
  self.assertIn('videoFormat=hls',cast.assistant_url('192.168.1.8',link,'Movie'))
 def test_other_tvs_and_older_frameworks_keep_the_prepared_playlist(self):
  for kind in ('chromecast','dlna'):
   self.assertEqual(self.link(kind)[1],[('serve',b'http://127.0.0.1:1234/drive',0)])
  (link,_),calls=self.link('roku',segmented=False)
  self.assertEqual((link,calls),('http://192.168.1.24:5000/t/prepared.m3u8',[('serve',b'http://127.0.0.1:1234/drive',0)]))
 def test_tv_server_receives_the_current_subtitle_choice(self):
  calls,lib=self.lib();gui=types.SimpleNamespace(Window=lambda _:Window());vfs=types.SimpleNamespace()
  xbmc=types.SimpleNamespace(log=lambda *a:None,executebuiltin=lambda *a:None,LOGINFO=1,LOGWARNING=2)
  with patch.object(controller.airplay,'load',return_value=lib),patch.object(controller.airplay,'send_subtitles',return_value=(0,'','eng')) as choose,patch.dict(sys.modules,{'xbmcvfs':vfs,'xbmcgui':gui}):
   link,served=controller.tv_link(xbmc,'lib','http://tv/source','http://127.0.0.1/source','roku')
  choose.assert_called_once();self.assertTrue(served);self.assertIn('/master.m3u8',link)
 def test_native_segmented_mode(self):
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertIn('enum { KR_COMPAT_SEGMENTED = 2 };',(ROOT/'migration/airplay-ios/remux/src/kr_remux.h').read_text())
  self.assertIn('if(!compat && !segmented && kr_prepare_ready(prepared)',remux)
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('int kodi_airplay_serve_segmented(const char *url, char *out, int outlen)',build)
  self.assertIn('kr_remux_start_for(ticket, url, 1, KR_COMPAT_SEGMENTED, out, outlen)',build)
  self.assertIn('_kodi_airplay_serve_segmented\\n',build);self.assertIn('serve|serve_segmented)',build)
  self.assertIn('lib.kodi_airplay_serve_segmented.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]',(BOOT/'resources/lib/airplay.py').read_text())
 def test_init_read_ahead_and_kept(self):
  remux=(ROOT/'migration/airplay-ios/remux/src/kr_remux.c').read_text()
  self.assertLess(remux.index('        prepared_playlists(0);\n        prepared_warm_start(ticket);'),remux.index('pthread_create(&S.accept_thread,NULL,accept_loop,NULL)'))
  self.assertIn('b->at!=0',(ROOT/'migration/airplay-ios/remux/src/kr_source.c').read_text())  # header block stays resident
  self.assertIn('kr_source_cached_read(S.src,offset,buf,want)',remux)
  self.assertIn('atomic_fetch_sub(&S.active,1);',remux[remux.index('static void *prepared_warm'):])   # teardown waits for it
 def test_airplay_rejection_of_the_prepared_playlist_converts_once(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('if (!compatTried && preparedLink && everExternal && kr_remux_served_external(1) == 0) {',build)
  self.assertIn('if (external) everExternal = YES;',build)
  failed=build.index('preparedLink && everExternal')
  self.assertLess(failed,build.index('showProblem(m && *m ? @(m)',failed))   # before the problem is reported

class PhoneServedTv(unittest.TestCase):
 """Build 211 (log 1430bbc1): after Play on TV handed a Roku the phone's link, "slowdown: full speed" and the TV's
 first 3.7 KB took 7.8 s. A TV fed by the phone's server slows the background like AirPlay, while it asks for video."""
 def test_serve_mark_counts_and_ends(self):
  class W:
   def __init__(self):self.p={}
   def setProperty(self,k,v):self.p[k]=v
   def getProperty(self,k):return self.p.get(k,'')
   def clearProperty(self,k):self.p.pop(k,None)
  class Lib:
   def kodi_airplay_active(self):return 0
  w=W();lib=Lib()
  self.assertFalse(airplay.playback_active(lib,w,1000))
  airplay.mark_serve(w,1000);self.assertTrue(airplay.playback_active(lib,w,1050))
  self.assertFalse(airplay.playback_active(lib,w,1000+airplay.BUSY_FOR+1))     # the TV stopped asking
  airplay.activity(['GET /prepared.mp4 bytes=0-3763 206 3764 B 7816 ms'],w,1200)  # it asks again: kept
  self.assertFalse(airplay.serve_busy(w,1200))                                  # an expired mark stays expired
  airplay.mark_serve(w,1300);airplay.activity(['GET /prepared.mp4 206 65536 B 40 ms'],w,1380)
  self.assertTrue(airplay.playback_active(lib,w,1380+airplay.BUSY_FOR-1))
  self.assertIn('airplay.mark_serve(xbmcgui.Window(10000),time.time())',(BOOT/'cast.py').read_text())

if __name__=='__main__':unittest.main()
