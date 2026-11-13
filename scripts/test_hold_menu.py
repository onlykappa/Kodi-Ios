"""Owner (build 186): "if i hold down on the conversation tab in the notifications it like closes the notification it should
give the option to pause or cancel the conversation, download or transfer". A long press on a transfer card opens a menu
(pause / resume, cancel, the speed graph) instead of closing the page; the service obeys the choices."""
import io,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(BOOT),str(Path(__file__).resolve().parent)]
import transfer_control as tc,debrid_drive,prepare_downloads
from test_debrid_drive import FakeAPI,FakeDrive,H

class Control(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_pause_files(self):
  for kind in tc.KINDS:
   self.assertFalse(tc.paused(self.p,kind));tc.set_paused(self.p,kind,True);self.assertTrue(tc.paused(self.p,kind))
   tc.set_paused(self.p,kind,False);tc.set_paused(self.p,kind,False);self.assertFalse(tc.paused(self.p,kind))
  with self.assertRaises(ValueError):tc.set_paused(self.p,'down',True)
 def test_cancel_requests(self):
  tc.cancel_copy(self.p,H.upper());tc.cancel_copy(self.p,'b'*40)
  self.assertEqual(tc.cancelled_copies(self.p),{H,'b'*40})
  tc.clear_cancelled(self.p,H);self.assertEqual(tc.cancelled_copies(self.p),{'b'*40})
  tc.clear_cancelled(self.p,'b'*40);self.assertEqual(tc.cancelled_copies(self.p),set())
 def test_cards(self):
  self.assertEqual([tc.card_of(c) for c in (9432,9433,9436,9439,9440,9501)],[('up',0),('conv',0),('down',0),('down',3),None,None])
  # Owner (build 356): every copy lane has a card on the bell page.
  self.assertEqual([tc.card_of(c) for c in (9441,9445,9446)],[('up',1),('up',5),None])
 def test_menus(self):
  self.assertEqual([a for _,a in tc.menu('down',{'paused':False})],['toggle','cancel','speed'])
  self.assertEqual(tc.menu('down',{'paused':True})[0][0],'Resume download')
  self.assertEqual([a for _,a in tc.menu('up',{'source':'phone'})],['toggle','speed'])
  self.assertEqual([l for l,_ in tc.menu('up',{'source':'debrid','hash':H},up_paused=True)],['Resume uploads','Cancel this download','Show speed'])
  self.assertEqual([l for l,_ in tc.menu('conv',{'id':'d1'})],['Pause converting','Cancel conversion','Show speed'])
  self.assertEqual(tc.menu('conv',{'id':'d1'},conv_paused=True)[0][0],'Resume converting')

class CancelACopy(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_cancelled_job_ends_and_the_request_clears(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  tc.cancel_copy(self.p,H)
  r=debrid_drive.step(self.p,FakeAPI(),FakeDrive(),cancelled=lambda:tc.cancelled_copies(self.p),forget=lambda h:tc.clear_cancelled(self.p,h))
  self.assertIsNone(r);job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual((job['status'],job['error']),('failed','Cancelled'));self.assertEqual(tc.cancelled_copies(self.p),set())
 def test_a_copy_in_flight_stops(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  drive=FakeDrive();api=FakeAPI()
  debrid_drive.step(self.p,api,drive)   # added, ready: copying next
  asks=iter([set()]+[{H}]*9)   # pressed while it copies: the step began before the request
  r=debrid_drive.step(self.p,api,drive,open_url=lambda u,o:io.BytesIO(b'abc'[o:]),cancelled=lambda:next(asks))
  self.assertEqual(r,30);self.assertEqual(drive.data,b'')   # driveupload.Stop before anything was sent
 def test_paused_uploads_stop_the_copy_where_drive_has_it(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  drive=FakeDrive();api=FakeAPI();debrid_drive.step(self.p,api,drive)
  self.assertEqual(debrid_drive.step(self.p,api,drive,open_url=lambda u,o:io.BytesIO(b'abc'[o:]),keep_going=lambda:False),30)
  self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'copying')

class ConversionCard(unittest.TestCase):
 def test_card_has_the_video_and_shows_paused(self):
  with tempfile.TemporaryDirectory() as p:
   state={'jobs':{'d1':{'source':{'id':'d1','name':'Inception.2010.mkv'},'status':'waiting'}},'current':{}}
   prepare_downloads.save(p,state) if hasattr(prepare_downloads,'save') else None
   original=prepare_downloads.snapshot
   prepare_downloads.snapshot=lambda profile,now=None:state
   try:
    card=prepare_downloads.cards(p)[0];self.assertEqual(card['id'],'d1');self.assertFalse(card.get('paused'))
    tc.set_paused(p,'conv',True);card=prepare_downloads.cards(p)[0]
    self.assertTrue(card['paused']);self.assertIn('Paused by you',card['line'])
   finally:prepare_downloads.snapshot=original

class Wiring(unittest.TestCase):
 def test_page_and_service(self):
  page=(BOOT/'notifications.py').read_text();service=(BOOT/'service.py').read_text()
  self.assertIn('LONG=(101,117)',page);self.assertIn('if code in LONG or code==10:',page)
  self.assertIn('xbmcgui.Dialog().contextmenu(',page);self.assertIn("prepare_downloads.request(profile,'keep',item['id'])",page)
  self.assertIn("preparation.paused=lambda:(not monitor.abortRequested() and transfer_control.paused(profile,'conv') and",service)
  self.assertIn("and not transfer_control.paused(profile,'conv')",service.split('converting=lambda:')[1].split('\n')[0])
  self.assertIn("uploading=lambda:idle() and not transfer_control.paused(profile,'up')",service)
  self.assertIn("cancelled=lambda:transfer_control.cancelled_copies(profile)",service)
  self.assertIn('<longpress>RightClick</longpress>',(LIB/'navigation.py').read_text())

if __name__=='__main__':unittest.main()
