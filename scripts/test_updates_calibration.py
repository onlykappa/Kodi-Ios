import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/'migration/bundled-bootstrap/resources/lib'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
updates=load('updates');calibration=load('calibration');bootstrap=load('bootstrap')
RES='<settings><resolutions><resolution><description>2622x1206 @ 60.00Hz - Full Screen</description><overscan><left>{l}</left><top>0</top><right>{r}</right><bottom>1206</bottom></overscan></resolution></resolutions></settings>'
class Updates(unittest.TestCase):
 def test_picks_newest_newer_build_with_an_ipa(self):
  rel=[{'tag_name':'build-21','assets':[{'name':'a.ipa'}]},{'tag_name':'build-23','assets':[{'name':'b.ipa'}]},{'tag_name':'build-24','assets':[]},{'tag_name':'v9','assets':[{'name':'c.ipa'}]},{'tag_name':'build-30','draft':True,'assets':[{'name':'d.ipa'}]}]
  self.assertEqual(updates.newest(rel,22)['number'],23);self.assertIsNone(updates.newest(rel,23));self.assertEqual(updates.newest(rel,None)['number'],23)
 def test_token_only_when_set_and_binary_accept(self):
  self.assertNotIn('Authorization',updates.headers(''));self.assertEqual(updates.headers('t',True)['Authorization'],'Bearer t');self.assertEqual(updates.headers('',True)['Accept'],'application/octet-stream')
 def test_saved_where_the_files_app_shows_it(self):
  self.assertEqual(str(updates.updates_folder('/var/x/Documents/.kodi')),'/var/x/Documents/Kodi Updates')
class Calibration(unittest.TestCase):
 def test_detects_only_changed_calibration(self):
  with tempfile.TemporaryDirectory() as t:
   g=Path(t)/'guisettings.xml'
   g.write_text(RES.format(l=0,r=2622));self.assertFalse(calibration.changed(g))
   g.write_text(RES.format(l=0,r=2100));self.assertTrue(calibration.changed(g))
   g.write_text(RES.format(l=12,r=2622));self.assertTrue(calibration.changed(g))
   g.write_text('<settings><resolutions/></settings>');self.assertFalse(calibration.changed(g))
 def test_resets_once_through_kodis_own_dialog_and_saves_by_leaving(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'guisettings.xml').write_text(RES.format(l=0,r=2100));calls=[]
   active=lambda cond:cond=='Window.IsActive(screencalibration)'
   self.assertEqual(calibration.reset_once(p,calls.append,active,lambda s:False),'OFFERED')
   self.assertEqual(calls,['ActivateWindow(screencalibration)','Action(resetcalibration)','Action(Back)'])
   self.assertEqual(calibration.reset_once(p,calls.append,active,lambda s:False),'DONE BEFORE');self.assertEqual(len(calls),3)
class EnsureEnabled(unittest.TestCase):
 def setup(self,t,status):
  p=Path(t);seed=p/'seed';seed.mkdir();(seed/'seed-manifest.json').write_text(json.dumps({'addons':['a','b','c']}))
  state=p/'profile/addon_data/service.kodi.ios.bootstrap';state.mkdir(parents=True);(state/'status.json').write_text(json.dumps({'status':status}));(state/'journal.json').write_text(json.dumps({'files':[],'enabled':['a']}))
  return seed,p/'profile',state
 def api(self,on,calls):
  def call(method,params):
   calls.append((method,params['addonid']))
   if method=='Addons.GetAddonDetails':return {'error':{}} if params['addonid']=='c' else {'result':{'addon':{'enabled':params['addonid'] in on}}}
   return {'result':'OK'}
  return call
 def test_turns_on_new_dependencies_and_records_them_for_recovery(self):
  with tempfile.TemporaryDirectory() as t:
   seed,profile,state=self.setup(t,'COMPLETE');calls=[]
   self.assertEqual(bootstrap.ensure_enabled(seed,profile,self.api({'a'},calls)),['b'])
   self.assertEqual(json.loads((state/'journal.json').read_text())['enabled'],['a','b'])
 def test_leaves_a_recovered_profile_alone(self):
  with tempfile.TemporaryDirectory() as t:
   seed,profile,state=self.setup(t,'RESTORED');calls=[]
   self.assertEqual(bootstrap.ensure_enabled(seed,profile,self.api(set(),calls)),[]);self.assertEqual(calls,[])
class Players(unittest.TestCase):
 def test_umbrella_player_installed_only_when_umbrella_is_on_the_phone(self):
  with tempfile.TemporaryDirectory() as t:
   root=ROOT/'migration/bundled-bootstrap';profile=Path(t)
   self.assertEqual(bootstrap.install_players(root,profile,lambda a:False),[])
   self.assertEqual(bootstrap.install_players(root,profile,lambda a:a=='plugin.video.umbrella'),['ios.umbrella.json'])
   dest=profile/'addon_data/plugin.video.themoviedb.helper/players/ios.umbrella.json'
   self.assertEqual(json.loads(dest.read_text())['plugin'],'plugin.video.umbrella')
   dest.write_text('{"plugin":"plugin.video.umbrella","owner":"edited"}')
   self.assertEqual(bootstrap.install_players(root,profile,lambda a:True),['ios.elementum.json']);self.assertIn('edited',dest.read_text())
class PlayOnTV(unittest.TestCase):
 def test_web_links_go_straight_to_the_tv_and_phone_links_use_its_wifi_address(self):
  cast=load('cast')
  self.assertEqual(cast.stream_url('https://cdn.example/v/a.mkv|User-Agent=Kodi','10.0.0.5'),('https://cdn.example/v/a.mkv',False))
  self.assertEqual(cast.stream_url('http://127.0.0.1:65220/files/a.mkv','192.168.1.11'),('http://192.168.1.11:65220/files/a.mkv',True))
  self.assertEqual(cast.stream_url('http://127.0.0.1:65220/files/a.mkv',None),(None,True))
  self.assertEqual(cast.stream_url('plugin://plugin.video.x/?a=1','1.2.3.4'),(None,False))
  self.assertEqual(cast.stream_url('/private/var/a.mkv','1.2.3.4'),(None,False))
 def test_roku_launch_request(self):
  cast=load('cast');url=cast.launch_url('192.168.1.20','https://cdn.example/v/My Show.mkv?x=1&y=2','You')
  self.assertTrue(url.startswith('http://192.168.1.20:8060/input/15985?t=v&u=https%3A%2F%2Fcdn.example%2Fv%2FMy%20Show.mkv%3Fx%3D1%26y%3D2'))
  self.assertIn('videoName=You',url);self.assertIn('videoFormat=mkv',url);self.assertIn('k=%28null%29',url)
 def test_roku_tries_both_ways_in_and_explains_a_refusal(self):
  import urllib.error
  cast=load('cast');sent=[]
  def refuse(code):
   def post(url):sent.append(url.split('/')[3]);raise urllib.error.HTTPError(url,code,'no',{},None)
   return post
  with self.assertRaises(cast.TVRefused) as ctx:cast.roku_play('192.168.1.20','https://cdn.example/a.mp4','A',refuse(403))
  self.assertEqual(sent,['input','launch']);self.assertIn('Permissive',str(ctx.exception))
  with self.assertRaises(cast.TVRefused) as ctx:cast.roku_play('192.168.1.20','https://cdn.example/a.mp4','A',refuse(404))
  self.assertIn('AirPlay',str(ctx.exception))
  def flaky(url):
   if '/input/' in url:raise urllib.error.HTTPError(url,404,'no',{},None)
   return 200
  self.assertEqual(cast.roku_play('192.168.1.20','https://cdn.example/a.mp4','A',flaky),'launch')
  def down(url):raise TimeoutError()
  with self.assertRaises(cast.TVRefused) as ctx:cast.roku_play('192.168.1.20','https://cdn.example/a.mp4','A',down)
  self.assertIn('did not answer',str(ctx.exception))
 def test_setup_service_keeps_its_home_window(self):
  # Build 86/87: the Umbrella hook reused "window" for a file path, so setup crashed at window.clearProperty and
  # the portrait refresh (video controls, source page) never ran.
  import ast
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/service.py').read_text())
  run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
  assigned=[t.id for n in ast.walk(run) if isinstance(n,(ast.Assign,ast.AnnAssign)) for t in (n.targets if isinstance(n,ast.Assign) else [n.target]) for t in ast.walk(t) if isinstance(t,ast.Name)]
  self.assertEqual(assigned.count('window'),1)
 def test_download_ids_from_tmdb_helper_items(self):
  dl=load('elementum_download')
  self.assertEqual(dl.ids('movie','plugin://plugin.video.themoviedb.helper/?info=details&tmdb_id=155&tmdb_type=movie',{}),('155',None,None))
  self.assertEqual(dl.ids('movie','',{'tmdb':'155'}),('155',None,None))
  self.assertEqual(dl.ids('movie','plugin://x/?tmdb_id=99&tmdb_type=tv',{}),(None,None,None))
  self.assertEqual(dl.ids('season','plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_id=224372&season=2&tmdb_type=tv',{}),('224372','2',None))
  self.assertEqual(dl.ids('episode','',{'tvshow.tmdb_id':'1399','season':'1','episode':'3','tmdb':'63056'}),('1399','1','3'))
  self.assertEqual(dl.ids('tvshow','',{'tmdb':'1399'}),('1399',None,None))
  self.assertEqual(dl.plugin_url('movie','155'),'plugin://plugin.video.elementum/movie/155/download')
  self.assertEqual(dl.plugin_url('season','1399','2'),'plugin://plugin.video.elementum/show/1399/season/2/download')
  self.assertEqual(dl.plugin_url('episode','1399','2','5'),'plugin://plugin.video.elementum/show/1399/season/2/episode/5/download')
 def test_season_pack_switches_to_download_all(self):
  dl=load('elementum_download');calls=[];lists=iter([[{'id':'old'}],[{'id':'old'}],[{'id':'old'},{'id':'pack'}]])
  def get(url):
   calls.append(url)
   return json.dumps(next(lists)).encode() if url.endswith('/torrents/list') else b''
  self.assertEqual(dl.download_all_when_added({'old'},lambda:False,get),'pack')
  self.assertEqual(calls[-1],'http://127.0.0.1:65220/torrents/downloadall/pack')
  self.assertIsNone(dl.download_all_when_added({'old'},lambda:True,lambda u:b'[]'))
 def test_choose_episodes(self):
  dl=load('elementum_download')
  files=[{'filetype':'file','episode':2,'title':'Trust Fall'},{'filetype':'file','episode':1,'title':'Pilot'},
         {'filetype':'directory','episode':0,'label':'..'},{'filetype':'file','episode':0,'title':'Special'}]
  self.assertEqual(dl.episode_choices(files),[(1,'1. Pilot'),(2,'2. Trust Fall')])
  self.assertEqual(dl.season_path('224372','1'),'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_id=224372&season=1&tmdb_type=tv')
  # One at a time: the next starts once the previous torrent shows up; a cancelled one times out.
  state={'ids':[]};started=[]
  def start(n):
   started.append(n)
   if n!=2:state['ids'].append('t%d'%n)
  get=lambda url:json.dumps([{'id':i} for i in state['ids']]).encode()
  self.assertEqual(dl.download_each([1,2,3],start,lambda:False,get,per_episode=3),[1,3]);self.assertEqual(started,[1,2,3])
 def test_retry_restarts_elementum_until_the_engine_answers(self):
  eng=load('elementum_engine');calls=[];answers=iter([False,False,True])
  self.assertTrue(eng.restart(lambda m,p:calls.append(p['enabled']),lambda:False,lambda:next(answers)))
  self.assertEqual(calls,[False,True])
  self.assertFalse(eng.restart(lambda m,p:None,lambda:True,lambda:False))
  import urllib.error
  def refused(url,timeout):raise urllib.error.URLError('refused')
  def http404(url,timeout):raise urllib.error.HTTPError(url,404,'x',{},None)
  self.assertFalse(eng.running(open_url=refused));self.assertTrue(eng.running(open_url=http404))
 def test_finds_rokus_on_the_phones_network(self):
  cast=load('cast')
  def get(url,timeout):
   if url.startswith('http://192.168.1.20:'):return b'<device-info><user-device-name>Living Room</user-device-name></device-info>'
   if url.startswith('http://192.168.1.31:'):return b'<device-info><model-name>Roku Express</model-name></device-info>'
   raise OSError('refused')
  self.assertEqual(cast.find_rokus('192.168.1.11',get,workers=8),[('192.168.1.20','Living Room'),('192.168.1.31','Roku Express')])
  self.assertEqual(cast.find_rokus(None,get),[])
class AlreadyDownloaded(unittest.TestCase):
 """Owner (build 152): check for duplicates before downloading."""
 def test_wording_and_marks(self):
  dl=load('elementum_download')
  self.assertEqual(dl.where({'source':'local','path':'x'}),'on this iPhone');self.assertEqual(dl.where({'source':'drive'}),'on Google Drive')
  self.assertEqual(dl.mark_owned(['1. Pilot','2. Two'],[True,False]),['1. Pilot  ·  Downloaded','2. Two'])
  self.assertIsNone(dl.season_question('1',0,10))
  self.assertIn('All 10 episodes',dl.season_question('1',10,10)[1]);self.assertIn('3 of 10',dl.season_question('1',3,10)[1])
 def test_download_script_checks_before_starting(self):
  source=(ROOT/'migration/bundled-bootstrap/download.py').read_text()
  for kind in ("check('movie')","check('episode',season,episode)","dl.mark_owned(","dl.season_question("):self.assertIn(kind,source)
  # every check happens before Elementum is asked: the first start() call comes after the movie/episode checks
  self.assertLess(source.index("check('movie')"),source.index("start('season')"))
  self.assertIn('return None',source.split('def owned_copy',1)[1].split('\ndef ',1)[0])   # a failed check never blocks

class DownloadFolders(unittest.TestCase):
 def test_movies_and_shows_folders_for_elementum_and_umbrella_unless_owner_chose(self):
  with tempfile.TemporaryDirectory() as t:
   folders=bootstrap.media_folders(Path(t)/'Documents/Kodi Downloads')
   self.assertTrue((Path(t)/'Documents/Kodi Downloads/Movies').is_dir());self.assertTrue(folders['shows'].endswith('/TV Shows/'))
   e={};self.assertTrue(bootstrap.elementum_library(folders,lambda k:e.get(k,''),e.__setitem__))
   self.assertEqual((e['download_storage'],e['completed_move'],e['completed_movies_path']),('0','true',folders['movies']))
   self.assertEqual((e['keep_downloading'],e['keep_files_playing'],e['keep_files_finished']),('1','1','1'))
   e2={'completed_shows_path':'/mine/'};self.assertFalse(bootstrap.elementum_library(folders,lambda k:e2.get(k,''),e2.__setitem__));self.assertEqual(e2,{'completed_shows_path':'/mine/'})
   u={};self.assertFalse(bootstrap.umbrella_streaming_only(folders,lambda k:u.get(k,''),u.__setitem__));self.assertEqual(u,{})
   u={'downloads':'true','movie.download.path':folders['movies'],'tv.download.path':folders['shows']}
   self.assertTrue(bootstrap.umbrella_streaming_only(folders,lambda k:u.get(k,''),u.__setitem__))
   self.assertEqual(u,{'downloads':'false','movie.download.path':'','tv.download.path':''})
   u2={'downloads':'true','movie.download.path':'/mine/','tv.download.path':'/mine/'};self.assertFalse(bootstrap.umbrella_streaming_only(folders,lambda k:u2.get(k,''),u2.__setitem__))
class UniversalPlayOnTV(unittest.TestCase):
 DESC=b'''<root xmlns="urn:schemas-upnp-org:device-1-0"><device><friendlyName>[TV] Samsung</friendlyName><serviceList>
  <service><serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType><controlURL>/rc</controlURL></service>
  <service><serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType><controlURL>/upnp/control/AVTransport1</controlURL></service>
  </serviceList></device></root>'''
 def test_dlna_renderer_and_play_commands(self):
  cast=load('cast')
  self.assertEqual(cast.renderer('http://192.168.1.40:9197/dmr',lambda u,t:self.DESC),('[TV] Samsung','http://192.168.1.40:9197/upnp/control/AVTransport1'))
  self.assertIsNone(cast.renderer('http://x/',lambda u,t:b'<root/>'))
  calls=[];cast.dlna_play('http://tv/ctl','https://cdn/a b.mkv?x=1&y=2','Show & Co',lambda u,b,h:calls.append((h['SOAPAction'],b.decode())))
  self.assertEqual([c[0].split('#')[1].strip('"') for c in calls],['Stop','SetAVTransportURI','Play'])
  body=calls[1][1];self.assertIn('<CurrentURI>https://cdn/a b.mkv?x=1&amp;y=2</CurrentURI>',body);self.assertIn('video/x-matroska',body);self.assertIn('Show &amp;amp; Co',body)
  import xml.etree.ElementTree as ET;ET.fromstring(body)
 def test_unicast_ssdp_collects_locations(self):
  cast=load('cast');sent=[]
  class Sock:
   replies=[(b'HTTP/1.1 200 OK\r\nLOCATION: http://192.168.1.40:9197/dmr\r\n\r\n',('192.168.1.40',1900))]
   def settimeout(self,t):pass
   def sendto(self,data,addr):sent.append(addr)
   def recvfrom(self,n):
    if self.replies:return self.replies.pop()
    raise OSError
   def close(self):pass
  self.assertEqual(cast.ssdp_locations(['192.168.1.40','192.168.1.41'],wait=0.3,make_socket=Sock),{'192.168.1.40':'http://192.168.1.40:9197/dmr'})
  self.assertEqual(sent,[('192.168.1.40',1900),('192.168.1.41',1900)])
 def test_cast_messages_round_trip_and_chromecast_load(self):
  cast=load('cast');import struct,json as j
  frame=cast.cast_frame('sender-0','receiver-0','urn:x-cast:test',{'type':'PING'})
  self.assertEqual(cast.cast_parse(frame[4:]),('urn:x-cast:test',{'type':'PING'}))
  class Sock:
   def __init__(s):s.out=[];s.inbox=b''
   def sendall(s,data):
    ns,payload=cast.cast_parse(data[4:]);s.out.append((ns,payload))
    reply=None
    if payload.get('type')=='LAUNCH':reply={'type':'RECEIVER_STATUS','status':{'applications':[{'appId':'CC1AD845','transportId':'web-7'}]}}
    if payload.get('type')=='LOAD':reply={'type':'MEDIA_STATUS','status':[{}]}
    if reply:s.inbox+=cast.cast_frame('receiver-0','sender-0','urn:x-cast:x',reply)
   def recv(s,n):d,s.inbox=s.inbox[:n],s.inbox[n:];return d
   def close(s):pass
  sock=Sock();cast.chromecast_play('192.168.1.50','https://cdn/a.mkv','You',connect=lambda h:sock,timeout=5)
  load_msg=[p for ns,p in sock.out if p.get('type')=='LOAD'][0]
  self.assertEqual(load_msg['media']['contentId'],'https://cdn/a.mkv');self.assertEqual(load_msg['media']['contentType'],'video/mp4')
  self.assertIn(('urn:x-cast:com.google.cast.tp.connection',{'type':'CONNECT'}),sock.out)
 def test_finds_every_kind_of_tv(self):
  cast=load('cast')
  def get(url,timeout):
   if url.startswith('http://192.168.1.20:8060/'):return b'<device-info><user-device-name>Living Room</user-device-name></device-info>'
   if url.startswith('http://192.168.1.50:8008/'):return b'{"name":"Kitchen"}'
   if url=='http://192.168.1.40:9197/dmr':return self.DESC
   raise OSError
  tvs=cast.find_tvs('192.168.1.11',get,workers=8,locations={'192.168.1.40':'http://192.168.1.40:9197/dmr','192.168.1.20':'http://192.168.1.20:8060/'})
  self.assertEqual([(t['kind'],t['name']) for t in tvs],[('roku','Living Room'),('chromecast','Kitchen'),('dlna','[TV] Samsung')])
class AirPlay(unittest.TestCase):
 def test_framework_found_inside_the_app_only(self):
  airplay=load('airplay')
  with tempfile.TemporaryDirectory() as t:
   home=Path(t)/'Kodi.app/AppData/AppHome';home.mkdir(parents=True)
   self.assertIsNone(airplay.library_path(str(home)+'/'))
   fw=Path(t)/'Kodi.app/Frameworks/KodiAirPlay.framework';fw.mkdir(parents=True);(fw/'KodiAirPlay').write_bytes(b'x')
   self.assertEqual(airplay.library_path(str(home)+'/'),str(fw/'KodiAirPlay'))
   self.assertIsNone(airplay.library_path(t))
 def test_button_follows_playback_and_hides_on_exit(self):
  airplay=load('airplay');calls=[];states=iter([False,True,True,False,True])
  lib=type('L',(),{'kodi_airplay_show':staticmethod(calls.append)})()
  ticks=iter([False,False,False,False,True])
  airplay.watch(lib,lambda:next(states),lambda s:next(ticks))
  self.assertEqual(calls,[0,1,0,1,0])
class DownloadModes(unittest.TestCase):
 def test_download_only_or_download_and_watch(self):
  dl=load('elementum_download')
  self.assertEqual(dl.mode_labels('movie'),['Download only','Download and watch'])
  self.assertEqual(dl.mode_labels('season',[5,3,4]),['Download only','Download and watch episode 3'])
  self.assertEqual(dl.mode_labels('season'),['Download only','Download and watch episode 1'])
 def test_watching_plays_from_the_downloading_torrent(self):
  dl=load('elementum_download')
  self.assertEqual(dl.watch_url('movie','155','abc123'),'plugin://plugin.video.elementum/play?resume=abc123&tmdb=155&type=movie')
  # silent=1: Elementum plays the episode's file from the torrent already on the phone without asking.
  self.assertEqual(dl.watch_url('episode','1399',None,'2','3'),'plugin://plugin.video.elementum/show/1399/season/2/episode/3/play?silent=1')
 def test_added_finds_the_new_torrent_or_gives_up(self):
  dl=load('elementum_download');lists=iter([b'[{"id":"old"}]',b'[{"id":"old"},{"id":"new"}]'])
  self.assertEqual(dl.added({'old'},lambda:False,lambda u:next(lists)),'new')
  self.assertIsNone(dl.added({'old'},lambda:False,lambda u:b'[{"id":"old"}]',attempts=3))
  self.assertIsNone(dl.added({'old'},lambda:True,lambda u:b'[]'))
class AirPlayFormats(unittest.TestCase):
 def test_only_apple_containers_go_to_apples_player(self):
  cast=load('cast')
  self.assertTrue(cast.apple_playable('http://192.168.1.4:65220/files/Movie.2000.mp4'))
  self.assertTrue(cast.apple_playable('https://cdn.example/live/index.m3u8|User-Agent=Kodi'))
  self.assertFalse(cast.apple_playable('http://192.168.1.4:65220/files/Scary.Movie.2000.1080p.mkv'))
  # Elementum's link may carry no extension; Kodi's file name then decides.
  self.assertTrue(cast.apple_playable('http://192.168.1.4:65220/play?resume=1','/x/Movie.m4v'))
  self.assertFalse(cast.apple_playable('http://192.168.1.4:65220/play?resume=1',''))
 def test_mirroring_message_names_the_format(self):
  cast=load('cast')
  self.assertEqual(cast.format_name('http://h/files/a.mkv'),'MKV');self.assertEqual(cast.format_name('http://h/play'),'this format')
  self.assertIn('Screen Mirroring',cast.MIRRORING%'MKV');self.assertIn('(MKV)',cast.MIRRORING%'MKV')
 def test_apples_player_outcome(self):
  cast=load('cast')
  states=iter([0,0,1]);self.assertEqual(cast.airplay_outcome(lambda:next(states),lambda s:False),'playing')
  states=iter([0,-1]);self.assertEqual(cast.airplay_outcome(lambda:next(states),lambda s:False),'failed')
  self.assertEqual(cast.airplay_outcome(lambda:0,lambda s:False,timeout=2),'failed')
  self.assertEqual(cast.airplay_outcome(lambda:0,lambda s:True),'aborted')
class Background(unittest.TestCase):
 def test_awake_only_while_a_transfer_has_work(self):
  bg=load('background')
  self.assertEqual(bg.reason([{'paused':False},{'paused':True}],[],False),'1 Elementum download')
  self.assertEqual(bg.reason([{'paused':True}],[],False),'')
  self.assertEqual(bg.reason([],[{'title':'a'}],False),'Google Drive upload')
  self.assertEqual(bg.reason([],[],True),'videos waiting for Google Drive')
  self.assertEqual(bg.reason([],[],False),'')
 def test_videos_waiting_for_drive(self):
  bg=load('background')
  with tempfile.TemporaryDirectory() as t:
   self.assertFalse(bg.videos_waiting(t))
   (Path(t)/'Movies').mkdir();(Path(t)/'Movies/.partial.mkv').write_bytes(b'');self.assertFalse(bg.videos_waiting(t))
   (Path(t)/'TV Shows/Show/Season 1').mkdir(parents=True);(Path(t)/'TV Shows/Show/Season 1/e1.mkv').write_bytes(b'x')
   self.assertTrue(bg.videos_waiting(t))
 def test_framework_told_on_change_and_released_on_exit(self):
  bg=load('background');calls=[];work=iter(['1 Elementum download','1 Elementum download','',RuntimeError,'x'])
  def why():
   w=next(work)
   if w is RuntimeError:raise w('engine down')
   return w
  ticks=iter([False]*5+[True])
  bg.watch(calls.append,why,lambda s:next(ticks))
  self.assertEqual(calls,[1,1,0,1,0])
class Scrapers(unittest.TestCase):
 def test_payload_copied_once_and_never_over_an_existing_copy(self):
  with tempfile.TemporaryDirectory() as t:
   root,home=Path(t)/'boot',Path(t)/'home';mod=root/'payload/script.module.cocoscrapers';mod.mkdir(parents=True)
   (mod/'addon.xml').write_text('<addon id="script.module.cocoscrapers" version="1.0.45"/>');(mod/'lib').mkdir();(mod/'lib/x.py').write_text('x=1')
   self.assertEqual(bootstrap.install_payload(root,home),['script.module.cocoscrapers'])
   dest=home/'addons/script.module.cocoscrapers';self.assertTrue((dest/'lib/x.py').is_file())
   (dest/'addon.xml').write_text('<addon id="script.module.cocoscrapers" version="1.0.50"/>')
   self.assertEqual(bootstrap.install_payload(root,home),[]);self.assertIn('1.0.50',(dest/'addon.xml').read_text())
   self.assertEqual(bootstrap.install_payload(Path(t)/'none',home),[])
 def test_umbrella_pointed_at_cocoscrapers_unless_owner_chose(self):
  settings={}
  self.assertTrue(bootstrap.umbrella_defaults(lambda k:settings.get(k,''),settings.__setitem__))
  self.assertEqual(settings,{'provider.external.enabled':'true','external_provider.name':'cocoscrapers','external_provider.module':'script.module.cocoscrapers'})
  settings['external_provider.module']='script.module.other'
  self.assertFalse(bootstrap.umbrella_defaults(lambda k:settings.get(k,''),settings.__setitem__));self.assertEqual(settings['external_provider.module'],'script.module.other')
class Elementum(unittest.TestCase):
 def test_download_folder_set_once_and_never_over_the_owners_choice(self):
  with tempfile.TemporaryDirectory() as t:
   settings={};folder=Path(t)/'Documents/Elementum Downloads'
   self.assertEqual(bootstrap.elementum_defaults(folder,lambda k:settings.get(k,''),settings.__setitem__),str(folder))
   self.assertTrue(folder.is_dir());self.assertEqual(settings['download_path'],str(folder)+'/')
   settings['download_path']='/private/var/old-container/Documents/Elementum Downloads/'
   self.assertEqual(bootstrap.elementum_defaults(folder,lambda k:settings.get(k,''),settings.__setitem__),str(folder));self.assertEqual(settings['download_path'],str(folder)+'/')
   self.assertIsNone(bootstrap.elementum_defaults(folder,lambda k:settings.get(k,''),settings.__setitem__))
   settings['download_path']='/owner/choice/'
   self.assertIsNone(bootstrap.elementum_defaults(folder,lambda k:settings.get(k,''),settings.__setitem__));self.assertEqual(settings['download_path'],'/owner/choice/')
 def test_inputs_are_verified_and_skipped_until_the_framework_is_pinned(self):
  import hashlib,fetch_elementum_inputs as f
  lock=json.loads(f.LOCK.read_text())
  with tempfile.TemporaryDirectory() as t:
   self.assertFalse(f.run(Path(t)/'none',dict(lock,framework_release={'tag':'x','asset':'y','sha256':None}))['elementum'])
   self.assertFalse((Path(t)/'none').exists())
   client,framework,burst=b'client',b'framework',b'burst';sha=lambda b:hashlib.sha256(b).hexdigest()
   pinned=dict(lock,plugin_release=dict(lock['plugin_release'],client_zip_sha256=sha(client)),
               framework_release={'tag':'t','asset':'a.zip','sha256':sha(framework)},burst=dict(lock['burst'],sha256=sha(burst)))
   pinned['extras']={'script.module.a':{'install':'app','url':'u-app','sha256':sha(b'app')},'script.module.b':{'install':'profile','url':'u-profile','sha256':sha(b'profile')}}
   def get(url):return client if url==lock['plugin_release']['client_zip_url'] else framework if url.endswith('/t/a.zip') else {'u-app':b'app','u-profile':b'profile'}.get(url,burst)
   def modules(spec,dest):(dest/'script.module.kodi-six').mkdir(parents=True)
   out=Path(t)/'ok';self.assertTrue(f.run(out,pinned,get,modules,{'tag':'x','asset':'y','sha256':None})['elementum'])
   self.assertFalse((out/'frameworks').exists())
   air=Path(t)/'air';self.assertEqual(f.run(air,pinned,lambda url:b'fw' if url.endswith('/ap/A.zip') else get(url),modules,{'tag':'ap','asset':'A.zip','sha256':sha(b'fw')})['frameworks'],['KodiAirPlay'])
   self.assertEqual((out/'framework.zip').read_bytes(),framework);self.assertEqual((out/'burst.zip').read_bytes(),burst)
   self.assertEqual((out/'extras-app/script.module.a.zip').read_bytes(),b'app');self.assertEqual((out/'extras-profile/script.module.b.zip').read_bytes(),b'profile')
   with self.assertRaises(AssertionError):f.run(Path(t)/'bad',pinned,lambda url:b'tampered',modules,{'tag':'x','asset':'y','sha256':None})
 def test_phone_housekeeping_once(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   profile=Path(tmp);(profile/'sources.xml').write_text('<sources><video><source><name>Local</name><path pathversion="1">special://profile/media/local_media_root_04/</path></source>'
    '<source><name>Bad</name><path pathversion="1">special://profile/media/../escape/</path></source></video></sources>')
   settings={'disable_upnp':'false'};calls=[]
   api=lambda method,params:calls.append((method,params)) or {'result':'OK'}
   done=bootstrap.phone_housekeeping(profile,(lambda k:settings.get(k,''),settings.__setitem__),api)
   self.assertEqual(sorted(done),['elementum_always_ask','elementum_network','media_folders','tmdbhelper_players','versioncheck','wsdiscovery','zeroconf'])
   # Downloads (and every play) show Elementum's version list and wait for an answer.
   self.assertEqual([settings[k] for k in ('use_cache_selection','smart_episode_choose','autoyes_enabled','silent_stream_start')],['false']*4)
   self.assertTrue((profile/'media/local_media_root_04').is_dir());self.assertFalse((profile/'escape').exists())
   self.assertTrue((profile/'addon_data/plugin.video.themoviedb.helper/reconfigured_players').is_dir())
   self.assertEqual([settings[k] for k in ('disable_upnp','disable_natpmp','disable_lsd')],['true']*3)
   self.assertEqual(calls,[('Addons.SetAddonEnabled',{'addonid':'service.xbmc.versioncheck','enabled':False}),('Settings.SetSettingValue',{'setting':'services.zeroconf','value':False}),('Settings.SetSettingValue',{'setting':'services.wsdiscovery','value':False})])
   # Once: the owner turning UPnP back on is left alone.
   settings['disable_upnp']='false';self.assertEqual(bootstrap.phone_housekeeping(profile,(lambda k:settings.get(k,''),settings.__setitem__),api),[])
   self.assertEqual(settings['disable_upnp'],'false');self.assertEqual(len(calls),3)
if __name__=='__main__':unittest.main()
