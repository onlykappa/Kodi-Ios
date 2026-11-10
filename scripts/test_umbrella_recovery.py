"""A selected AllDebrid file renews once on expired HTTP links, preserving byte identity and provider headers."""
import ast,concurrent.futures,io,json,sys,tempfile,threading,types,unittest,urllib.error,urllib.request
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib';sys.path[:0]=[str(LIB),str(ROOT/'scripts')]
import umbrella_recovery as recovery,remote_media
from test_remote_media import DATA,Reply

OLD='https://media.example/old.mkv';NEW='https://media.example/new.mkv';LINK='https://alldebrid.com/f/selected'
RECORD={'source':OLD,'link':LINK,'filename':'episode.mkv','size':len(DATA)}
class Home:
 def __init__(self):self.props={}
 def setProperty(self,key,value):self.props[key]=value
 def getProperty(self,key):return self.props.get(key,'')

class Registration(unittest.TestCase):
 def test_only_the_selected_resolved_file_matches_the_in_memory_record(self):
  home=Home();recovery.remember(LINK,dict(link=OLD,filename='episode.mkv',filesize=len(DATA)),home)
  self.assertEqual(recovery.selected(OLD+'|Cookie=a%3Db',home),RECORD)
  self.assertIsNone(recovery.selected(NEW,home));self.assertIsNone(recovery.selected('http://127.0.0.1/drive',home))
 def test_invalid_resolver_answers_do_not_record_a_renewable_source(self):
  home=Home()
  for answer in (None,{},'url',{'link':'file:///movie.mkv'}):recovery.remember(LINK,answer,home)
  self.assertEqual(home.props,{})
 def test_unlock_uses_existing_account_and_the_same_file_without_a_new_torrent(self):
  calls=[]
  def request(method,url,data,headers):
   calls.append((method,url,data,headers));return json.dumps({'status':'success','data':{'link':NEW,'filename':'episode.mkv','filesize':len(DATA)}}).encode()
  self.assertEqual(recovery.renew(RECORD,token='test',request=request),NEW)
  self.assertEqual(len(calls),1);self.assertIn('/v4/link/unlock?',calls[0][1]);self.assertNotIn('magnet',calls[0][1])
  self.assertEqual(calls[0][3]['Authorization'],'Bearer test')
 def test_changed_size_name_or_invalid_link_cannot_replace_the_current_movie(self):
  for change in ({'filename':'wrong.mkv'},{'filesize':len(DATA)+1},{'link':'file:///wrong'}):
   data=dict(link=NEW,filename='episode.mkv',filesize=len(DATA),**{})
   data.update(change)
   with self.assertRaises(RuntimeError):recovery.renew(RECORD,token='test',request=lambda *a:json.dumps({'status':'success','data':data}).encode())

class Hook(unittest.TestCase):
 SOURCE="class AllDebrid:\n\tdef unrestrict_link(self, link, returnAll=False):\n\t\ttry:\n\t\t\turl='link/unlock'\n\t\t\turl_append=link\n\t\t\tresponse = self._get(url, url_append)\n\t\t\tif returnAll: return response\n\t\t\treturn response['link']\n\t\texcept: return None\n"
 def test_hook_preserves_unlock_returns_and_records_selected_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'alldebrid.py';path.write_text(self.SOURCE);self.assertTrue(recovery.hook(path));self.assertFalse(recovery.hook(path))
   code=path.read_text();home=Home();answer=dict(link=OLD,filename='episode.mkv',filesize=len(DATA))
   with patch.dict(sys.modules,{'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:str(LIB)),
                                'xbmcgui':types.SimpleNamespace(Window=lambda n:home)}):
    namespace={};exec(compile(code,str(path),'exec'),namespace);instance=namespace['AllDebrid']();instance._get=lambda *a:answer
    self.assertEqual(instance.unrestrict_link(LINK),OLD);self.assertIs(instance.unrestrict_link(LINK,True),answer)
   self.assertEqual(recovery.selected(OLD,home),RECORD)
 def test_unrecognized_upstream_is_not_rewritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   for source in ('class Unknown: pass\n','invalid python !',self.SOURCE.replace('response = self._get(url, url_append)','response = {}')):
    path=Path(tmp)/'alldebrid.py';path.write_text(source);self.assertFalse(recovery.hook(path));self.assertEqual(path.read_text(),source)

class ExpiredLink(unittest.TestCase):
 def source(self,opener,renew=lambda record:NEW):
  source=remote_media.Foreground(OLD+'|User-Agent=Player&Cookie=a%3Db',open_url=opener)
  source.configure_renewal(RECORD,renew);self.addCleanup(source.close);return source
 def reply(self,req):
  a,b=map(int,req.get_header('Range')[6:].split('-'));return Reply(DATA,a,min(b,len(DATA)-1))
 def expired(self,req,code=403):raise urllib.error.HTTPError(req.full_url,code,'expired',{},io.BytesIO())
 def test_each_expiry_status_refreshes_once_and_preserves_range_and_headers(self):
  for code in (401,403,404,410):
   calls=[];renewals=[]
   def open(req,timeout):
    calls.append(req)
    return self.expired(req,code) if req.full_url==OLD else self.reply(req)
   s=self.source(open,lambda r:(renewals.append(r),NEW)[1]);body,total=s._fetch('media',123,999)
   self.assertEqual(body,DATA[123:1000]);self.assertEqual(total,len(DATA));self.assertEqual(len(renewals),1)
   self.assertEqual([r.full_url for r in calls],[OLD,NEW]);self.assertEqual(calls[1].get_header('Range'),'bytes=123-999')
   self.assertEqual(calls[1].get_header('Cookie'),'a=b');self.assertEqual(calls[1].get_header('User-agent'),'Player')
 def test_repeated_expiry_or_failed_renewal_cannot_loop(self):
  for failed in (False,True):
   renewals=[]
   def renew(r):
    renewals.append(1)
    if failed:raise RuntimeError('provider unavailable')
    return NEW
   s=self.source(lambda req,timeout:self.expired(req),renew)
   for _ in range(2):
    with self.assertRaises(urllib.error.HTTPError):s._fetch('media',0,99)
   self.assertEqual(len(renewals),1)
 def test_concurrent_readers_share_one_renewal(self):
  barrier=threading.Barrier(2);renewals=[]
  def open(req,timeout):
   if req.full_url==OLD:barrier.wait(timeout=3);return self.expired(req)
   return self.reply(req)
  s=self.source(open,lambda r:(renewals.append(1),NEW)[1])
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda n:s._fetch('media',n,n+9),[0,100]))
  self.assertEqual(len(renewals),1);self.assertEqual([r[0] for r in results],[DATA[:10],DATA[100:110]])
 def test_transient_server_errors_retry_without_requesting_a_new_source(self):
  calls=[];renewals=[]
  def open(req,timeout):
   calls.append(1)
   if len(calls)==1:return self.expired(req,503)
   return self.reply(req)
  s=self.source(open,lambda r:(renewals.append(1),NEW)[1]);self.assertEqual(s._fetch('media',0,9)[0],DATA[:10]);self.assertEqual(renewals,[])
 def test_unregistered_sources_never_use_account_link_recovery(self):
  s=remote_media.Foreground(OLD,open_url=lambda req,timeout:self.expired(req));self.addCleanup(s.close)
  with self.assertRaises(urllib.error.HTTPError):s._fetch('media',0,9)
  self.assertFalse(s.renewed)
 def test_changed_total_cannot_mix_another_file_with_cached_bytes(self):
  s=self.source(lambda req,timeout:self.reply(req));s.blocks.sizes['media']=len(DATA)+1
  with self.assertRaisesRegex(ConnectionError,'different file'):s._fetch('media',0,9)
 def test_broker_retains_recovery_and_exposes_only_safe_status(self):
  renewals=[]
  def factory(url):
   return remote_media.Foreground(url,open_url=lambda req,timeout:self.expired(req) if req.full_url==OLD else self.reply(req))
  broker=remote_media.Broker(source_factory=factory,renew_link=lambda r:(renewals.append(1),NEW)[1]);self.addCleanup(broker.close)
  home=Home();home.setProperty(remote_media.PROPERTY,broker.url);home.setProperty(recovery.PROPERTY,json.dumps(RECORD))
  url,lease=remote_media.acquire(OLD,home)
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-9'}),timeout=5) as response:self.assertEqual(response.read(),DATA[:10])
  self.assertEqual(lease.status(),{'renewal':'refreshed'});self.assertEqual(renewals,[1]);lease.close()

if __name__=='__main__':unittest.main()
