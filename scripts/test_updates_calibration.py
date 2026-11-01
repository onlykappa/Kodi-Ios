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
 def test_finds_rokus_on_the_phones_network(self):
  cast=load('cast')
  def get(url,timeout):
   if url.startswith('http://192.168.1.20:'):return b'<device-info><user-device-name>Living Room</user-device-name></device-info>'
   if url.startswith('http://192.168.1.31:'):return b'<device-info><model-name>Roku Express</model-name></device-info>'
   raise OSError('refused')
  self.assertEqual(cast.find_rokus('192.168.1.11',get,workers=8),[('192.168.1.20','Living Room'),('192.168.1.31','Roku Express')])
  self.assertEqual(cast.find_rokus(None,get),[])
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
if __name__=='__main__':unittest.main()
