"""Automatic request ownership and the existing manual download choice must survive HTTP fallback."""
import json,sys,time,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import provider_fallback as f,debrid_drive,elementum_cloud
class Home:
 def __init__(self):self.data={}
 def getProperty(self,k):return self.data.get(k,'')
 def setProperty(self,k,v):self.data[k]=v
 def clearProperty(self,k):self.data.pop(k,None)
class Queue(unittest.TestCase):
 def setUp(self):
  self.home=Home();self.request={'media_type':'episode','title':'Example Show','show_title':'Example Show','tmdb':'1','season':1,'episode':2}
  self.c=f.verified([{'name':'Example.Show.S01E02.1080p.mkv','quality':'1080p','url':'https://fixture.invalid/file.mkv'}],self.request,'pov')[0]
  self.auto={'request_id':'owned','until':time.time()+30,'target':{'tmdb':'1','season':1,'episode':2},'mode':1,'_lane':''}
  self.home.setProperty('KodiIOS.AutoPick',json.dumps(self.auto))
  self.stack=patch.dict(sys.modules,{'xbmcgui':types.SimpleNamespace(Window=lambda n:self.home,Dialog=lambda:object()),'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:'/fixture')});self.stack.start();self.addCleanup(self.stack.stop)
  self.queue=patch.object(debrid_drive,'queue_direct',return_value={'hash':'a'*40});self.native=self.queue.start();self.addCleanup(self.queue.stop)
 def test_matching_owner_queues_and_sets_only_its_receipt(self):
  self.assertTrue(f.queue_download(self.c,self.c['url'],self.request,auto=self.auto))
  self.assertTrue(self.native.call_args.kwargs['watch'])
  self.assertEqual(json.loads(self.home.getProperty('KodiIOS.AutoPick.Queued'))['request_id'],'owned')
 def test_replaced_or_expired_owner_cannot_queue(self):
  for current in [dict(self.auto,request_id='replacement'),dict(self.auto,until=0),dict(self.auto,target={'tmdb':'2','season':1,'episode':2})]:
   self.home.setProperty('KodiIOS.AutoPick',json.dumps(current))
   with self.assertRaises(f.Canceled):f.queue_download(self.c,self.c['url'],self.request,auto=self.auto)
  self.native.assert_not_called()
 def test_tombstoned_request_cannot_queue(self):
  import episode_watch
  episode_watch.cancel_request(self.home,self.auto)
  with self.assertRaises(f.Canceled):f.queue_download(self.c,self.c['url'],self.request,auto=self.auto)
  self.native.assert_not_called()
 def test_manual_prompt_cancel_never_queues(self):
  with patch('transfer_control.paused',return_value=False),patch.object(elementum_cloud,'ask',return_value=-1):
   with self.assertRaises(f.Canceled):f.queue_download(self.c,self.c['url'],self.request)
  self.native.assert_not_called()
 def test_manual_download_and_watch_keeps_existing_mode(self):
  with patch('transfer_control.paused',return_value=False),patch.object(elementum_cloud,'ask',return_value=1):self.assertTrue(f.queue_download(self.c,self.c['url'],self.request))
  self.assertTrue(self.native.call_args.kwargs['watch'])
if __name__=='__main__':unittest.main()
