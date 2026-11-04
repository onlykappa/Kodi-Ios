import ast,importlib.util,json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.path.insert(0,str(BOOT/'resources/lib'))
import notices,portrait
spec=importlib.util.spec_from_file_location('notifications_page',BOOT/'notifications.py');page=importlib.util.module_from_spec(spec);spec.loader.exec_module(page)

TORRENTS=[{'id':'a','name':'Scary Movie','progress':64,'status':'Downloading','size_bytes':18*1024**3,'download_rate':10240},
          {'id':'b','name':'Paused one','progress':10,'status':'Paused','size_bytes':1024**3,'download_rate':0},
          {'id':'c','name':'Done','progress':100,'status':'Seeding','size_bytes':1024**3,'download_rate':0}]

class NoticeTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.profile=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_store_newest_first_dedupe_and_cap(self):
  notices.add(self.profile,'drive','A',now=100);notices.add(self.profile,'drive','A',now=130);notices.add(self.profile,'nonsense','B',now=200)
  items=notices.load(self.profile);self.assertEqual([i['title'] for i in items],['B','A']);self.assertEqual(items[0]['kind'],'info')
  for n in range(60):notices.add(self.profile,'info','m%d'%n,now=300+n*100)
  self.assertEqual(len(notices.load(self.profile)),notices.MAX)
 def test_unread_and_clear(self):
  notices.add(self.profile,'problem','X',now=1);notices.add(self.profile,'update','Y',now=2)
  self.assertEqual(notices.unread(self.profile),2);notices.mark_all_read(self.profile);self.assertEqual(notices.unread(self.profile),0)
  notices.clear(self.profile);self.assertEqual(notices.load(self.profile),[])
 def test_broken_store_reads_empty(self):
  path=notices.store(self.profile);path.parent.mkdir(parents=True);path.write_text('{nope')
  self.assertEqual(notices.load(self.profile),[])
 def test_downloads_from_engine(self):
  out=notices.downloads(lambda url:json.dumps(TORRENTS))
  self.assertEqual([d['id'] for d in out],['a','b'])
  self.assertEqual(out[0]['line'],'64%  ·  11.5 GB of 18.0 GB');self.assertIn('10.0 MB/s',out[0]['speed']);self.assertEqual(out[1]['speed'],'Paused')
  def down(url):raise OSError('refused')
  self.assertEqual(notices.downloads(down),[])
 def test_engine_actions(self):
  seen=[];notices.engine_action('cancel','a',seen.append);notices.engine_action('pause','a',seen.append)
  self.assertEqual(seen,[notices.ENGINE+'/torrents/delete/a?files=true&torrent=true',notices.ENGINE+'/torrents/pause/a'])
 def test_uploads_and_badge(self):
  self.assertEqual(notices.badge(self.profile,lambda url:'[]'),('',''))
  state=Path(self.profile)/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json'
  state.parent.mkdir(parents=True,exist_ok=True);state.write_text(json.dumps({'current':{'name':'Pilot.mkv','folder':'TV','sent':50,'total':200}}))
  self.assertEqual(notices.uploads(self.profile)[0]['progress'],25.0)
  notices.add(self.profile,'info','x')
  self.assertEqual(notices.badge(self.profile,lambda url:'[]'),('1','true'))
 def test_ingest_kodi_popups(self):
  path=notices.toasts(self.profile);path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text('\n'.join([json.dumps({'time':10,'type':'info','caption':'TMDbHelper','description':'Trakt authorized in 1.665s'}),
   'not json',json.dumps({'time':20,'type':'error','caption':'Umbrella','description':'Scraper failed'}),
   json.dumps({'time':30,'type':'default','caption':'','description':''}),
   json.dumps({'time':40,'type':'default','caption':'','description':'Only text'})])+'\n')
  self.assertEqual(notices.ingest(self.profile),3);self.assertFalse(path.exists())
  items=notices.load(self.profile)
  self.assertEqual([(i['kind'],i['title'],i['text']) for i in items],
   [('general','Kodi','Only text'),('problem','Umbrella','Scraper failed'),('general','TMDbHelper','Trakt authorized in 1.665s')])
  self.assertEqual(items[2]['time'],10.0);self.assertEqual(notices.ingest(self.profile),0)
  props,shown=page.message_properties(items,'general',now=50);self.assertEqual([i['title'] for i in shown],['Kodi','TMDbHelper'])
  props,shown=page.message_properties(items,'problems',now=50);self.assertEqual([i['title'] for i in shown],['Umbrella'])
 def test_ingest_resumes_an_interrupted_take(self):
  path=notices.toasts(self.profile);path.parent.mkdir(parents=True,exist_ok=True)
  path.with_suffix('.taking').write_text(json.dumps({'time':1,'type':'warning','caption':'A','description':'b'})+'\n')
  path.write_text(json.dumps({'time':2,'type':'info','caption':'C','description':'d'})+'\n')
  self.assertEqual(notices.ingest(self.profile),1);self.assertTrue(path.exists())
  self.assertEqual(notices.ingest(self.profile),1);self.assertEqual([i['title'] for i in notices.load(self.profile)],['C','A'])
 def test_ago(self):
  self.assertEqual([notices.ago(0,n) for n in (5,120,7200,200000)],['now','2m','2h','2d'])

class TorrentListTests(unittest.TestCase):
 def test_engine_list_shared_for_two_seconds(self):
  calls=[]
  def fake(url):calls.append(url);return b'[]'
  notices._LIST.update(at=-1e9,data=None)
  real=notices.urllib.request.urlopen
  class R:
   def __init__(self):pass
   def read(self):calls.append(1);return b'[{"id":"a"}]'
  notices.urllib.request.urlopen=lambda url,timeout=3:R()
  try:
   t=[0.0]
   self.assertEqual(notices.torrent_list(clock=lambda:t[0]),[{'id':'a'}]);t[0]=1.5;notices.torrent_list(clock=lambda:t[0])
   self.assertEqual(len(calls),1)
   t[0]=2.5;notices.torrent_list(clock=lambda:t[0]);self.assertEqual(len(calls),2)
   notices.torrent_list(fake);self.assertEqual(calls[-1],notices.ENGINE+'/torrents/list')  # a custom get always asks
  finally:notices.urllib.request.urlopen=real;notices._LIST.update(at=-1e9,data=None)

class PageTests(unittest.TestCase):
 def test_layout_ids_match_controller(self):
  root=ET.fromstring(portrait.notices_page().encode())
  ids={int(c.get('id')) for c in root.iter('control') if c.get('id')}
  need={9001,9002,9101,9102,9103,9300,9430}|{9400+n for n in range(1,page.SLOTS+1)}|{9410+n for n in range(1,page.SLOTS+1)}|{9420+n for n in range(1,page.SLOTS+1)}|{9500+n for n in range(1,page.ROWS+1)}
  self.assertTrue(need<=ids,need-ids)
  self.assertEqual((portrait.NOTICE_SLOTS,portrait.NOTICE_ROWS),(page.SLOTS,page.ROWS))
 def test_card_and_message_properties(self):
  props=page.card_properties(notices.downloads(lambda url:json.dumps(TORRENTS)),[])
  self.assertEqual((props['has.dl'],props['dl.1.pausetext'],props['dl.2.pausetext'],props['dl.3.title'],props['dl.summary']),('true','Pause','Resume','','1 active'))
  items=[{'kind':'problem','title':'P','time':0},{'kind':'drive','title':'D','time':0,'was_read':True}]
  props,shown=page.message_properties(items,'problems',now=60)
  self.assertEqual([i['title'] for i in shown],['P']);self.assertEqual((props['msg.1.icon'],props['msg.1.unread'],props['msg.2.title']),('triangle-exclamation.png','true',''))
  props,shown=page.message_properties(items,'downloads',now=60);self.assertEqual(props['msg.1.title'],'D');self.assertEqual(props['msg.1.unread'],'')
 def test_bell_in_hub_and_page_headers(self):
  for xml in (portrait.page_header('Library'),):
   self.assertIn('id="9207"',xml);self.assertIn('RunScript(service.kodi.ios.bootstrap,notifications)',xml)
  self.assertIn('ring.png',portrait.textures())
 def test_service_starts_publisher(self):
  tree=ast.parse((BOOT/'service.py').read_text(encoding='utf-8'))
  self.assertTrue(any(isinstance(n,ast.Attribute) and n.attr=='publish' for n in ast.walk(tree)))

if __name__=='__main__':unittest.main()
