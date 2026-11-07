import importlib.util,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
accounts=load('accounts',BOOT/'resources/lib/accounts.py')
portrait=load('portrait_s',BOOT/'resources/lib/portrait.py')
page=load('accounts_page',BOOT/'accounts_page.py')
SVC={s['key']:s for s in accounts.SERVICES}
def reader(values):return lambda key:values.get(key,'')

class AccountStatus(unittest.TestCase):
 def test_missing_addon_offers_install(self):
  s=accounts.status(SVC['trakt'],False,reader({}))
  self.assertEqual((s['signed'],s['button'],s['action']),(False,'Install','InstallAddon(script.trakt)'))
 def test_single_login_shows_user(self):
  s=accounts.status(SVC['trakt'],True,reader({'user':'kappa','authorization':'{"token":1}'}))
  self.assertTrue(s['signed']);self.assertEqual(s['text'],'Signed in as kappa');self.assertEqual(s['action'],'Addon.OpenSettings(script.trakt)')
 def test_signed_out_starts_the_addon_sign_in(self):
  s=accounts.status(SVC['trakt'],True,reader({}))
  self.assertEqual((s['signed'],s['button'],s['action']),(False,'Sign In','RunScript(script.trakt,action=auth_info)'))
  e=accounts.status(SVC['elementum'],True,reader({}))
  self.assertEqual(e['text'],'Trakt not linked');self.assertIn('tracker/authorize?tracker=trakt',e['action'])
 def test_umbrella_lists_each_linked_service(self):
  s=accounts.status(SVC['umbrella'],True,reader({'alldebridtoken':'t','trakt.user.token':'t','trakt.user.name':'k'}))
  self.assertEqual(s['text'],'Signed in · Trakt, AllDebrid')
 def test_tmdb_token_only_and_prefix(self):
  self.assertEqual(accounts.status(SVC['tmdb'],True,reader({'trakt_token':'x'}))['text'],'Home rows · Signed in')
  self.assertEqual(accounts.status(SVC['tmdb'],True,reader({}))['text'],'Home rows · Not signed in')
 def test_drive_uses_saved_accounts(self):
  self.assertEqual(accounts.status(SVC['drive'],True,reader({}),[{'name':'me@gmail.com'}])['text'],'me@gmail.com')
  out=accounts.status(SVC['drive'],True,reader({}),[])
  self.assertEqual((out['signed'],out['action']),(False,accounts.DRIVE))
 def test_summary_initials_and_properties(self):
  states=[accounts.status(s,s['key']!='tmdb',reader({'user':'k'})) for s in accounts.SERVICES]
  self.assertEqual(accounts.summary(states),'1 of 4 services signed in')
  self.assertEqual(accounts.initials('Master user'),'MU');self.assertEqual(accounts.initials(''),'?')
  props=accounts.properties(states,'Kodi')
  self.assertEqual(props['acct.4.signed'],'true');self.assertEqual(props['acct.5.button'],'Install');self.assertEqual(props['initials'],'K')
 def test_every_service_has_an_icon_tint_and_actions(self):
  for s in accounts.SERVICES:
   self.assertTrue(s['icon'].endswith('.png') and len(s['tint'])==8 and s['sign_in'] and s['manage'],s['key'])

class SettingsPages(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();skin=Path(cls.tmp.name)/'skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True)
  (skin/'addon.xml').write_text('<addon id="skin.arctic.fuse.3"><extension point="xbmc.gui.skin"><res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" /></extension></addon>')
  for name,data in {'Font.xml':'<fonts><fontset id="Default" /></fonts>','Includes.xml':'<includes />',
                    'Settings.xml':'<window id="10004"><onload>RunScript(script.skinvariables)</onload><controls /></window>',
                    'SettingsCategory.xml':'<window><controls /></window>','DialogAddonSettings.xml':'<window><controls /></window>'}.items():(skin/'1080i'/name).write_text(data)
  profile=Path(cls.tmp.name)/'profile';profile.mkdir()
  cls.files=portrait.build(skin,profile);cls.skin=skin
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def read(self,name):return ET.parse(self.skin/'portrait'/name).getroot()
 def clicks(self,root,id):
  button=[c for c in root.iter('control') if c.get('id')==str(id)][0];return [o.text for o in button.findall('onclick')]

 def test_settings_is_handmade_and_keeps_fuse_window(self):
  root=self.read('Settings.xml')
  self.assertEqual(root.get('id'),'10004');self.assertIn('RunScript(script.skinvariables)',[o.text for o in root.findall('onload')])
  self.assertNotIn('landscape window',ET.tostring(root,encoding='unicode'))
 def test_every_kodi_category_is_a_row(self):
  root=self.read('Settings.xml')
  for id,action in ((9111,'ActivateWindow(skinsettings)'),(9112,'ActivateWindow(interfacesettings)'),(9114,'ActivateWindow(playersettings)'),
                    (9115,'ActivateWindow(mediasettings)'),(9121,'ActivateWindow(pvrsettings)'),(9122,'ActivateWindow(gamesettings)'),
                    (9131,'ActivateWindow(systemsettings)'),(9132,'ActivateWindow(servicesettings)'),(9133,'ActivateWindow(profiles)'),
                    (9141,'ActivateWindow(addonbrowser)'),(9142,'ActivateWindow(filemanager)'),(9143,'ActivateWindow(eventlog)'),
                    (9151,'ActivateWindow(systeminfo)'),(9102,'ActivateWindow(addonbrowser,addons://outdated/,return)')):
   self.assertEqual(self.clicks(root,id),[action])
 def test_profile_card_opens_accounts_script_that_exists(self):
  action=self.clicks(self.read('Settings.xml'),9101)[0]
  self.assertEqual(action,'RunScript(service.kodi.ios.bootstrap,accounts_page)')
  self.assertTrue((BOOT/'accounts_page.py').is_file())
 def test_customisation_page_uses_fuse_actions(self):
  root=self.read('Settings.xml')
  self.assertEqual(self.clicks(root,9113),['SetProperty(Settings.Page,custom,10004)','SetFocus(9401)','RunScript(service.kodi.ios.bootstrap,customise_counts)'])
  self.assertEqual(self.clicks(root,9401),['ActivateWindow(1115)'])
  self.assertEqual(self.clicks(root,9412)[-1],'ActivateWindow(1118)')
  self.assertEqual(self.clicks(root,9411),['SetProperty(Settings.Page,osd,10004)','SetFocus(9531)'])
  self.assertEqual(self.clicks(root,9414),['SetProperty(Settings.Page,badges,10004)','SetFocus(9501)'])
 def test_back_button_leaves_customisation_first(self):
  root=self.read('Settings.xml');button=[c for c in root.iter('control') if c.get('id')=='9001'][0]
  actions=[(o.get('condition'),o.text) for o in button.findall('onclick')]
  self.assertEqual(actions[-1][1],'Action(Back)');self.assertTrue(actions[0][1].startswith('ClearProperty(Settings.Page'))
 def test_library_page_has_scan_refresh_and_fresh_movie_tv_routes(self):
  root=self.read('Settings.xml');settings=portrait.settings_page
  self.assertEqual(self.clicks(root,9116),['SetProperty(Settings.Page,library,10004)','SetFocus(9451)'])
  self.assertEqual(self.clicks(root,9451),['RunScript(service.kodi.ios.bootstrap,library_scan)'])
  self.assertEqual(self.clicks(root,9452),['RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=library_refresh&all=1)'])
  self.assertEqual(self.clicks(root,9453),['ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=movie&fresh=1,return)'])
  self.assertEqual(self.clicks(root,9454),['ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&fresh=1,return)'])
  library=root.find(".//control[@id='9320']")
  self.assertEqual(library.findtext('visible'),settings.ON_LIBRARY)
  text=' '.join(n.text or '' for n in library.iter('label'))
  self.assertIn('size and checksum match Drive',text)
  self.assertIn('folders made available to the app',text)
 def test_library_back_and_header_navigation_return_to_visible_controls(self):
  root=self.read('Settings.xml');settings=portrait.settings_page
  back=root.find(".//control[@id='9001']")
  actions=[(o.get('condition'),o.text) for o in back.findall('onclick')]
  self.assertIn((settings.ON_LIBRARY,'ClearProperty(Settings.Page,10004)'),actions)
  self.assertIn((settings.ON_LIBRARY,'SetFocus(9116)'),actions)
  self.assertIn((settings.ON_LIBRARY,'9451'),[(o.get('condition'),o.text) for o in back.findall('ondown')])
  first=root.find(".//control[@id='9451']")
  self.assertEqual(first.findtext('onup'),'9001')
  self.assertEqual(first.findtext('ondown'),'9452')
  self.assertIn((settings.ON_LIBRARY,'SetFocus(9451)'),[(o.get('condition'),o.text) for o in root.findall('onload')])
 def test_native_addon_settings_expose_the_same_scan_and_refresh_actions(self):
  root=ET.parse(BOOT/'resources/settings.xml').getroot();library=root.find(".//category[@id='library']")
  self.assertIsNotNone(library)
  actions={n.get('id'):n.findtext('data') for n in library.iter('setting')}
  self.assertEqual(actions,{'library_scan':'RunScript(service.kodi.ios.bootstrap,library_scan)',
                            'library_refresh':'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=library_refresh&all=1)'})
  dispatch=load('settings_scan_dispatch',BOOT/'default.py')
  script,argv=dispatch.target(['service.kodi.ios.bootstrap','library_scan'])
  self.assertEqual(Path(script),BOOT/'library_scan.py');self.assertEqual(argv,[script])
 def test_navigation_skips_the_hidden_updates_banner(self):
  root=self.read('Settings.xml');card=[c for c in root.iter('control') if c.get('id')=='9101'][0]
  downs=[(o.get('condition'),o.text) for o in card.findall('ondown')]
  self.assertEqual([t for _,t in downs],['9102','9111']);self.assertTrue(downs[1][0].startswith('!['))
  ids=[c.get('id') for c in root.iter('control') if c.get('id')];self.assertEqual(len(ids),len(set(ids)))
 def back_top(self,root):
  return int([g for g in root.iter('control') if g.get('type')=='group' and any(c.get('id')=='9001' for c in g)][0].findtext('top'))
 def test_search_field_and_header_clear_the_status_bar(self):
  root=self.read('Settings.xml')
  self.assertEqual(self.clicks(root,9100),['RunScript(service.kodi.ios.bootstrap,settings_search)'])
  card=[c for c in root.iter('control') if c.get('id')=='9101'][0];self.assertEqual(card.findtext('onup'),'9100')
  top=self.back_top(root);self.assertGreaterEqual(top,70)
  lists={c.get('id'):int(c.findtext('top')) for c in root.iter('control') if c.get('id') in ('9300','9310')}
  self.assertTrue(all(t>=top+108+40 for t in lists.values()),lists)
  self.assertEqual(self.back_top(self.read('IOSAccounts.xml')),36)   # other pages keep their header
 def test_accounts_page_matches_the_script(self):
  root=self.read('IOSAccounts.xml');ids={c.get('id') for c in root.iter('control')}
  rows={str(page.ROW_BASE+n) for n in range(1,len(accounts.SERVICES)+1)}|{str(page.LINK_BASE+1+i) for i in range(len(accounts.LINKS))}
  self.assertTrue(rows|{'9001','9300'}<=ids)
  xml=(self.skin/'portrait/IOSAccounts.xml').read_text()
  for key in ('acct.1.name','acct.5.text','acct.3.signed','summary','initials'):self.assertIn(key,xml)
 def test_textures_are_written(self):
  for name in ('group.png','tile84.png','tile100.png','avatar.png','avatar_s.png'):
   self.assertTrue((self.skin/'extras/portrait'/name).read_bytes().startswith(b'\x89PNG'))

 def test_kodi_setting_pages_have_every_template(self):
  # GUIDialogSettingsBase copies these: categories 10 -> 3, settings 7/8/9/12/13/14/15/11 -> 5, title 2, help 6.
  for name,kind in (('SettingsCategory.xml','togglebutton'),('DialogAddonSettings.xml','button')):
   root=self.read(name);types={c.get('id'):c.get('type') for c in root.iter('control') if c.get('id')}
   self.assertEqual({k:types.get(k) for k in ('2','3','5','6','7','8','9','10','11','12','13','14','15')},
    {'2':'label','3':'grouplist','5':'grouplist','6':'label','7':'button','8':'radiobutton','9':'spincontrolex','10':kind,
     '11':'image','12':'edit','13':'sliderex','14':'label','15':'colorbutton'},name)
  sheet={c.get('id') for c in self.read('DialogAddonSettings.xml').iter('control')}
  self.assertTrue({'28','29','20','30'}<=sheet)   # OK, Cancel, and the two Fuse keeps hidden
  level=[c for c in self.read('SettingsCategory.xml').iter('control') if c.get('id')=='20'][0]
  self.assertEqual(level.findtext('onclick'),'settingslevelchange')
 def test_conditions_use_kodi_brackets(self):
  # Kodi groups boolean expressions with [ ]; '!(' fails to parse (found in the desktop Kodi rig).
  for name in ('Settings.xml','IOSAccounts.xml','SettingsCategory.xml','DialogAddonSettings.xml'):
   xml=(self.skin/'portrait'/name).read_text();self.assertNotIn('!(',xml,name)
  # Negating a compound condition needs the brackets, or '!' binds to the first term only (profile glyph bug).
  self.assertIn('<visible>![!String.IsEmpty(System.ProfileThumb) + !String.Contains(System.ProfileThumb,DefaultUser)]</visible>',
                (self.skin/'portrait/Settings.xml').read_text())

class BuildNumber(unittest.TestCase):
 """Owner: the build number beside Kodi's version at the bottom of Settings."""
 def test_footer_and_reader(self):
  import tempfile,importlib.util
  spec=importlib.util.spec_from_file_location('updates_bn',BOOT/'resources/lib/updates.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(up.installed_build(d),'')
   Path(d,'build.json').write_text('{"build": 157, "commit": "abc"}');self.assertEqual(up.installed_build(d),'157')
  source=(BOOT/'resources/lib/settings_page.py').read_text()
  self.assertIn("$INFO[Window(Home).Property(KodiIOS.Build), (build ,)]",source)
  self.assertIn("window.setProperty('KodiIOS.Build',updates.installed_build(root))",(BOOT/'service.py').read_text())

if __name__=='__main__':unittest.main()
