"""Owner (build 191): asking for a new source for Inception failed at once with "AllDebrid gave an answer this app
cannot read", and its details page showed Kodi's "Control 9201 … has been asked to focus" instead of the cause.
Now a reply that is not AllDebrid's JSON (a busy page, an empty reply, no connection) is tried again later and
says what came back, in the job and in kodi.log; focus chatter is never a message's "What happened"."""
import io,sys,tempfile,unittest,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path[:0]=[str(LIB),str(Path(__file__).resolve().parent)]
import alldebrid,debrid_drive,notices
from test_debrid_drive import FakeDrive,H

def api(reply):
 return alldebrid.AllDebrid('t',request=reply)

class Replies(unittest.TestCase):
 def test_web_page_is_busy_and_described(self):
  with self.assertRaises(alldebrid.Busy) as ctx:api(lambda *a:b'<!DOCTYPE html><html><title>502 Bad Gateway</title></html>').add(H)
  self.assertIn('a web page: "502 Bad Gateway"',str(ctx.exception));self.assertIn('/v4/magnet/upload',str(ctx.exception))
  self.assertNotIsInstance(ctx.exception,alldebrid.Problem)
 def test_empty_and_http_errors_and_no_connection(self):
  with self.assertRaises(alldebrid.Busy) as ctx:api(lambda *a:b'').add(H)
  self.assertIn('an empty reply',str(ctx.exception))
  def http(*a):raise urllib.error.HTTPError('u',503,'x',{},io.BytesIO(b'Service Unavailable'))
  with self.assertRaises(alldebrid.Busy) as ctx:api(http).add(H)
  self.assertIn('HTTP 503, text: "Service Unavailable"',str(ctx.exception))
  def down(*a):raise OSError('no route')
  with self.assertRaises(alldebrid.Busy):api(down).add(H)
  with self.assertRaises(alldebrid.Busy):api(lambda *a:b'[1,2]').add(H)
 def test_a_real_no_is_still_a_problem(self):
  with self.assertRaises(alldebrid.Problem) as ctx:api(lambda *a:b'{"status":"error","error":{"code":"AUTH_BAD_APIKEY"}}').add(H)
  self.assertIn('did not accept the key',str(ctx.exception))

class Job(unittest.TestCase):
 def test_busy_retries_and_logs(self):
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.queue(p,{'id':H,'name':'Inception.2010.2160p'},'movie','Inception (2010)')
   lines=[];notes=[]
   delay=debrid_drive.step(p,api(lambda *a:b'<html>maintenance</html>'),FakeDrive(),lambda k,t,x:notes.append(t),log=lines.append)
   job=debrid_drive.load(p)['jobs'][0]
   self.assertEqual((delay,job['status'],job['tries']),(30,'new',1));self.assertEqual(notes,[])
   self.assertIn('Inception (2010): try 1, again in 30 s: Busy: AllDebrid gave an answer this app cannot read (a web page: "maintenance"',lines[0])

class Notices(unittest.TestCase):
 def test_focus_chatter_is_never_what_happened(self):
  text=('2026-11-07 12:23:27.000 T:1    error <general>: Control 9201 in window 13001 has been asked to focus, but it can\'t\n'
        '2026-11-07 12:23:30.000 T:1  warning <general>: Kodi iOS AllDebrid: Inception (2010): try 1, again in 30 s: Busy: x failed\n')
  records=notices.parse_log(text);when=records[-1]['time']+1
  self.assertEqual([r['text'] for r in notices.excerpt(records,when,'Inception')],['Kodi iOS AllDebrid: Inception (2010): try 1, again in 30 s: Busy: x failed'])

if __name__=='__main__':unittest.main()
