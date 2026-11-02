"""Performance budgets from the 2026-11-02 performance pass. Each test names the regression it prevents; the measured
numbers behind them are in docs/PERFORMANCE.md (scripts/perf_rig_bench.py repeats them in the desktop rig)."""
import importlib.util,re,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
import portrait,glassbar,notices
SERVICE=(ROOT/'migration/bundled-bootstrap/service.py').read_text()

WIDGETS=['plugin://plugin.video.themoviedb.helper/?info=row%d'%n for n in range(12)]

class StartupLoad(unittest.TestCase):
 def home(self):
  hubs=[(tab,(tab.title(),[{'label':'Row %d'%n,'path':p} for n,p in enumerate(WIDGETS)],tab,spot,'all'))
        for tab,spot in (('home','home'),('movies','1102'),('tv','1101'))]
  variables={};xml=portrait.hubs_window('<window id="0"/>',hubs,variables)
  return ET.fromstring(xml),variables

 def test_home_open_loads_at_most_the_hero_and_first_rows(self):
  # Was: all three hubs' rows (36+ add-on runs) at every start; the hero waited behind them on "Loading...".
  root,variables=self.home()
  lists=[c for c in root.iter('control') if c.get('type')=='list' and (c.findtext('content') or '').strip()]
  immediate=[c for c in lists if not c.findtext('content').startswith('$VAR[')]
  self.assertLessEqual(len(immediate),1+portrait.EAGER_ROWS)
  self.assertGreaterEqual(len(variables),len(lists)-len(immediate))

 def test_movies_and_tv_wait_for_their_first_visit(self):
  _,variables=self.home()
  for name,xml in variables.items():
   if '_movies' in name or '_tv' in name:self.assertIn('Portrait.Load.%s)'%name.split('_')[2],xml)

 def test_no_fuse_scripts_on_home_open_and_no_startup_wait(self):
  fuse_home=('<window><onload>RunScript(script.skinvariables,run_executebuiltin=special://skin/shortcuts/skinvariables-splash.json)</onload>'
             '<onload>$VAR[Action_RatingsMonitor]</onload><onload>Skin.SetString(TMDbHelper.Corner.Radius,20)</onload></window>')
  root=ET.fromstring(portrait.strip_fuse_onloads(fuse_home))
  self.assertFalse([o for o in root.iter('onload') if 'RunScript' in (o.text or '') or 'VAR[Action' in (o.text or '')])
  self.assertTrue(all(o.get('condition') for o in root.iter('onload')),'a skin setting written at every Home open')
  startup=ET.fromstring(portrait.STARTUP.decode().split('\n',2)[2])
  first=[o for o in startup.iter('onload') if o.get('condition')=='Skin.HasSetting(Portrait.FuseStartupDone)']
  self.assertIn('ReplaceWindow(Home)',[o.text for o in first])

class ServiceLoad(unittest.TestCase):
 def test_tab_bar_and_portrait_service_do_not_wait_for_the_update_check(self):
  # Was: a fixed ten-second wait (calibration, update check) before the tab bar and Continue Watching started.
  wait=SERVICE.index('monitor.waitForAbort(10)')
  self.assertLess(SERVICE.rindex('def later():',0,wait),wait)
  self.assertIn('threading.Thread(target=later,daemon=True).start()',SERVICE)

 def test_elementum_folders_are_not_fixed_twice(self):
  self.assertNotIn('follow_container(',SERVICE)

 def test_engine_list_shared_between_bell_and_background(self):
  self.assertTrue(hasattr(notices,'torrent_list'))

 def test_focused_item_details_only_on_focus_change(self):
  asked=[];tick=portrait.focused_item_publisher(lambda k:asked.append(k) or 'x',lambda c:'Window' in c,lambda k,v:None)
  tick();n=len(asked);tick();tick()
  self.assertLessEqual((len(asked)-n)/2,2)

class Overlap(unittest.TestCase):
 def test_one_tab_bar(self):
  # Was: the skin's tab bar appeared whenever the native glass bar hid (dialogs, page changes), two bars swapping.
  self.assertIn('!Skin.HasSetting(Portrait.NativeTabBar)',portrait.tabbar('home'))
  self.assertFalse(hasattr(glassbar,'ACTIONS'),'a second copy of the tab actions')

if __name__=='__main__':unittest.main()
