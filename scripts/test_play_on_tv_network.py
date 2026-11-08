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
 def exercise(self,profile,received=None,cancel=None,legacy=False,failed=False):
  window=Window();clock=[1000.0];paused=[False];closed=[];messages=[];logs=[];notes=[];plays=[]
  def wait(seconds):clock[0]+=seconds;return False
  progress=types.SimpleNamespace(create=lambda *a:None,update=lambda *a:None,close=lambda:closed.append('progress'),
                                 iscanceled=lambda:cancel is not None and clock[0]-1000>=cancel)
  player=types.SimpleNamespace(pause=lambda:paused.__setitem__(0,not paused[0]))
  xbmc=types.SimpleNamespace(LOGINFO=1,log=lambda m,*a:logs.append(m),getCondVisibility=lambda c:paused[0],Monitor=lambda:types.SimpleNamespace(waitForAbort=wait))
  gui=types.SimpleNamespace(Window=lambda n:window,DialogProgress=lambda:progress)
  vfs=types.SimpleNamespace(translatePath=lambda p:profile)
  def native_log(buffer,size):
   lines=[]
   if not plays:return 0
   if not getattr(native_log,'prepared',False):lines.append('prepared: source-resolution MP4 byte ranges');native_log.prepared=True
   if received is not None and clock[0]-1000>=received and not getattr(native_log,'tv',False):
    lines.append('client: AirPlay/1 (Apple TV; fixture)');native_log.tv=True
   if failed and clock[0]-1000>=2:lines.append('player: could not open the stream: Code=-1004 "Could not connect to the server"')
   buffer.value='\n'.join(lines).encode();return len(buffer.value)
  def network(buffer,size):
   buffer.value=json.dumps({'expected':True,'host':'192.0.2.10','port':12345,'listen_age_s':clock[0]-1000,
                            'tv_requests':int(received is not None and clock[0]-1000>=received)}).encode();return len(buffer.value)
  lib=types.SimpleNamespace(kodi_airplay_play=lambda *a:plays.append(a),kodi_airplay_close=lambda:closed.append('native'),
                            kodi_airplay_state=lambda:-1 if failed and clock[0]-1000>=2 else 1,
                            kodi_airplay_message=lambda b,n:0,kodi_airplay_log=native_log)
  if not legacy:lib.kodi_airplay_network=network
  dialog=types.SimpleNamespace(ok=lambda *a:messages.append(a))
  with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui,'xbmcvfs':vfs}),patch.object(airplay,'load',return_value=lib),\
       patch.object(airplay,'send_subtitles',return_value=None),patch.object(controller.notices,'note',side_effect=lambda *a:notes.append(a)),\
       patch.object(airplay.time,'time',side_effect=lambda:clock[0]):
   controller.send_airplay(xbmc,dialog,player,'fixture','http://192.0.2.10/file.mp4','Fixture','http://127.0.0.1/file.mp4')
  return types.SimpleNamespace(elapsed=clock[0]-1000,window=window,paused=paused[0],closed=closed,messages=messages,logs=logs,notes=notes,plays=plays)

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

 def test_start_deadline_does_not_wait_for_source_probing_or_a_listen_log(self):
  elapsed=[0.0]
  def wait(seconds):elapsed[0]+=seconds;return False
  outcome=cast.airplay_outcome(lambda:0,wait,60,network=lambda:{'expected':True,'start_age_s':elapsed[0],'listen_age_s':-1,'tv_requests':0})
  self.assertEqual((outcome,elapsed[0]),('unreachable',15))
  window=Window();window.setProperty(airplay.STARTED,'1000')
  def snapshot(buffer,size):buffer.value=b'{"expected":1,"start_age_s":0,"tv_requests":0}';return len(buffer.value)
  net=airplay.network(types.SimpleNamespace(kodi_airplay_network=snapshot),window,1015)
  self.assertEqual(net['start_age_s'],15)  # a queued/restarted native probe cannot reset the caller's deadline

 def test_direct_hls_uses_the_player_without_a_local_server_deadline(self):
  self.assertEqual(cast.airplay_outcome(lambda:1,lambda s:False,network=lambda:{'expected':False}),'playing')
  window=Window();window.setProperty(airplay.STARTED,'1000')
  airplay.activity(['start result 3:'],window,1001)
  self.assertFalse(airplay.network(object(),window,1002)['expected'])

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
  self.assertEqual(json.loads((ROOT/'migration/airplay-ios/source-lock.json').read_text())['framework_release']['tag'],'kodi-airplay-r34')

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

if __name__=='__main__':unittest.main()
