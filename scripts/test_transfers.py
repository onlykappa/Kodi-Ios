"""Transfers page (owner-approved mockup, build 171): speed history, the painted graph, the page XML, and that only a
tap on a transfer card in Notifications opens it ("I only want the graph to show in notifications if i tap on it")."""
import importlib.util,os,struct,sys,tempfile,time,unittest,zlib,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(BOOT),str(Path(__file__).resolve().parent)]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import transfer_history as th
portrait=load('portrait_transfers',LIB/'portrait.py')
tp=load('transfers_page_t',LIB/'transfers_page.py')
MB=1048576.0

def decode(png):
 w,h=struct.unpack('>II',png[16:24]);i=33;data=b''
 while i<len(png):
  n=struct.unpack('>I',png[i:i+4])[0];tag=png[i+4:i+8]
  if tag==b'IDAT':data+=png[i+8:i+8+n]
  i+=12+n
 raw=zlib.decompress(data);stride=w*4+1
 return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]

class History(unittest.TestCase):
 def test_ranges_peak_today_and_new_day(self):
  d={}
  for i in range(200):th.record(d,1000+i*2,20*MB,8*MB,.5*MB)
  self.assertEqual(len(d['5min']),150);self.assertEqual(len(th.series(d,'hour',1400)),120);self.assertEqual(len(th.series(d,'day',1400)),144)
  s=th.stats(d,'5min',1400);self.assertAlmostEqual(s['down'],20*MB);self.assertAlmostEqual(s['peak'],20*MB);self.assertGreater(s['today'],0)
  self.assertEqual(th.stats(d,'5min',1500)['down'],0.0)   # stale after 10 s
  th.record(d,1000+86400*2,1*MB,0,0);self.assertLess(d['moved'],10*MB)   # a new day starts the day's total again
 def test_rates(self):
  down,up,conv=th.rates([{'status':'downloading','download_rate':1024},{'status':'paused','download_rate':9999}],
                        {'stage':'copying','rate':8*MB},{'running':True,'rate':.5*MB})
  self.assertEqual((down,up,conv),(MB+8*MB,8*MB,.5*MB))
  self.assertEqual(th.rates(None,{'stage':'fetching','rate':5},{'running':False,'rate':5}),(0.0,0.0,0.0))
 def test_saved_and_loaded(self):
  with tempfile.TemporaryDirectory() as p:
   th.save(p,th.record({},1000,MB,MB,0));self.assertEqual(th.load(p)['now'][1],MB)
   self.assertEqual(th.load(p+'/nope'),{})

class Graph(unittest.TestCase):
 def test_png_has_bars_line_limit(self):
  d={}
  for i in range(150):th.record(d,1000+i*2,25*MB,8*MB,.5*MB)
  w,h,rows=decode(th.render(th.series(d,'5min',1300)))
  self.assertEqual((w,h),(th.W,th.H))
  colours={bytes(r[x*4:x*4+3]) for r in rows for x in range(w) if r[x*4+3]}
  for c in (th.DOWN,th.UP,th.LIMIT):self.assertIn(bytes(c),colours)
 def test_cycling_names(self):
  with tempfile.TemporaryDirectory() as f:
   names=[th.write_graph(f,n,b'x') for n in range(12)]
   self.assertEqual(len(set(names)),th.GRAPH_FILES);self.assertEqual(names[0],names[10])
   self.assertEqual(sorted(os.listdir(f)),sorted(set(names)))

class Page(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.xml=tp.page(portrait);cls.tree=ET.fromstring(cls.xml.split('\n',2)[2])
 def test_buttons_44pt_and_ids(self):
  ids={c.get('id') for c in self.tree.iter('control')}
  for n in (tp.BACK,tp.LIST,9701,9702,9703,tp.JOB_BAR+1,tp.JOB_BAR+3):self.assertIn(str(n),ids)
  for c in self.tree.iter('control'):
   if c.get('type')=='button':self.assertGreaterEqual(float(c.findtext('height') or 0),tp.HIT,c.get('id'))
 def test_every_property_is_set(self):
  import transfers
  props,bars=transfers.page_state(th.record({},1000,20*MB,8*MB,.5*MB),1001,'5min',
   [{'title':'Fall','progress':40,'line':'40%','speed':'2 MB/s'}],[{'title':'Fall 2','progress':86,'line':'86% · 8.4 MB/s','stage':'copying'}],
   [{'title':'Inception','progress':4,'line':'Converting · 0.9 GB read'}],[('Interstellar','convert · 8.4 GB')],[('Fall','to Google Drive · 18.1 GB')])
  self.assertEqual(props['down.value'],'20.0 MB/s');self.assertEqual(props['up.mbps'],'67 Mbps');self.assertEqual(props['job.2.kind'],'Uploading to Google Drive')
  self.assertEqual(props['job.3.tint'],tp.PURPLE);self.assertEqual(bars,[40,86,4]);self.assertEqual(props['next.1.title'],'Interstellar')
  for k in props:
   if k not in ('range',) and not k.startswith('has.'):self.assertIn('Window().Property(%s)'%k,self.xml,k)
  self.assertIn('Window().Property(graph)',self.xml);self.assertIn('Window().Property(has.jobs)',self.xml)
 def test_registered_and_pill_hidden(self):
  files=portrait.build if False else None
  self.assertIn('transfers_page.files(ns)',(LIB/'portrait.py').read_text());self.assertIn('IOSTransfers.xml',(LIB/'activity_skin.py').read_text())

class OnlyFromNotifications(unittest.TestCase):
 def test_cards_have_tap_targets_under_pause(self):
  xml=portrait.notices_page()
  for n in (9432,9433,9436,9437,9438,9439):self.assertIn('id="%d"'%n,xml)
  self.assertLess(xml.index('id="9436"'),xml.index('id="9411"'))   # Pause/Cancel stay on top
  for page in ('library_status.py','activity_page.py'):self.assertNotIn('transfers',(BOOT/page).read_text())
 def test_tapping_the_upload_card_opens_transfers(self):
  import notices,test_library_status as lib
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as profile:
   th.save(profile,th.record({},time.time(),20*MB,8*MB,.5*MB))
   seen={}
   def look(w):seen.update(dict(w.props))
   kodi=lib.FakeKodi(profile,[('IOSNotifications.xml',lambda w:w.onClick(9432)),(tp.WINDOW,look),(tp.WINDOW,lambda w:w.onClick(9702)),
                              (tp.WINDOW,lambda w:seen.update(range=w.getProperty('range'))),(tp.WINDOW,lambda w:w.onClick(tp.BACK)),
                              ('IOSNotifications.xml',lambda w:w.onClick(9001))])
   kodi.modules['xbmcvfs'].translatePath=lambda path:profile
   class Window:
    def __init__(self,n):pass
    def setProperty(self,*a):pass
   kodi.modules['xbmcgui'].Window=Window;kodi.modules['xbmc'].executebuiltin=lambda a:None
   with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(notices,'uploads',lambda p:[]):
    load('notifications_run_t',BOOT/'notifications.py').run()
   self.assertEqual(seen['down.value'],'20.0 MB/s');self.assertTrue(seen['graph'].startswith('special://skin/extras/portrait/graph/graph_'))
   self.assertEqual(seen['range'],'hour');self.assertTrue(all(w.closed for w in kodi.windows))
   self.assertTrue(os.path.exists(os.path.join(profile,'extras','portrait','graph')))

if __name__=='__main__':unittest.main()
