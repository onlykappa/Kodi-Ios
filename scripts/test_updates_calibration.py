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
   def get(url):return client if url==lock['plugin_release']['client_zip_url'] else framework if url.endswith('/t/a.zip') else burst
   def modules(spec,dest):(dest/'script.module.kodi-six').mkdir(parents=True)
   out=Path(t)/'ok';self.assertTrue(f.run(out,pinned,get,modules)['elementum'])
   self.assertEqual((out/'framework.zip').read_bytes(),framework);self.assertEqual((out/'burst.zip').read_bytes(),burst)
   with self.assertRaises(AssertionError):f.run(Path(t)/'bad',pinned,lambda url:b'tampered',modules)
if __name__=='__main__':unittest.main()
