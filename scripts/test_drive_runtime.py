"""Exercise pinned upstream refresh/resume code with mocked Kodi and synthetic state.
Requires the verified private upstream source cache; makes no network requests.
"""
import argparse,hashlib,json,sys,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-cache',type=Path,required=True);p.add_argument('--report',type=Path);args=p.parse_args()
lock=json.loads((ROOT/'migration/google-drive/source-lock.json').read_text())
for repo in lock['repositories']:
 for f in repo['files']:
  data=(args.source_cache/repo['addon_id']/f['path']).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==f['git_blob_sha']
sys.path.insert(0,str(args.source_cache/'script.module.clouddrive.common/tests'))
import kodistubs
from clouddrive.common.remote.provider import Provider
from clouddrive.common.ui.addon import CloudDriveAddon
from clouddrive.common.ui.utils import KodiUtils
import xbmcgui,xbmcplugin
from urllib.error import HTTPError
from clouddrive.common.remote import oauth2
class RefreshTests(unittest.TestCase):
 def setUp(self):
  self.account={'id':'fixture','access_tokens':{'access_token':'at0','refresh_token':'rt0'}}
  self.manager=mock.Mock(get_by_driveid=mock.Mock(return_value=self.account))
  self.provider=Provider('googledrive');self.provider.configure(self.manager,'fixture')
  self.provider._signin=mock.Mock()
 def test_refresh_preserves_account_and_saves_new_tokens(self):
  self.provider._signin.refresh_tokens.return_value={'access_token':'at1','refresh_token':'rt0'}
  result=self.provider.refresh_access_tokens();self.assertIn('date',result)
  self.provider.persist_access_tokens(result)
  self.provider._signin.refresh_tokens.assert_called_once_with('googledrive','rt0',None)
  self.manager.save_account.assert_called_once_with(self.account)
  self.assertEqual(self.account['access_tokens']['access_token'],'at1')
 def test_expired_request_refreshes_before_authorization(self):
  self.account['access_tokens'].update(date=0,expires_in=3600)
  self.provider._signin.refresh_tokens.return_value={'access_token':'at1','expires_in':3600}
  self.provider._get_api_url=lambda:'https://www.googleapis.com/drive/v3'
  self.provider._get_request_headers=lambda:{}
  with mock.patch.object(oauth2.time,'time',return_value=4000),mock.patch.object(oauth2,'Request') as request:
   self.provider.prepare_request('get','files')
  self.assertEqual(request.call_args.args[2]['authorization'],'Bearer at1')
  self.manager.save_account.assert_called_once()
 def test_unexpired_request_does_not_refresh(self):
  self.account['access_tokens'].update(date=3900,expires_in=3600)
  self.provider._get_api_url=lambda:'https://www.googleapis.com/drive/v3'
  self.provider._get_request_headers=lambda:{}
  with mock.patch.object(oauth2.time,'time',return_value=4000),mock.patch.object(oauth2,'Request') as request:
   self.provider.prepare_request('get','files')
  self.assertEqual(request.call_args.args[2]['authorization'],'Bearer at0')
  self.provider._signin.refresh_tokens.assert_not_called()
 def test_rate_limit_stops_this_request_budget(self):
  request=mock.Mock(tries=4,current_tries=1)
  self.provider._on_exception(request,HTTPError('https://example.invalid',429,'fixture',{},None),None)
  self.assertEqual(request.tries,1)
 def test_service_unavailable_keeps_bounded_retry_budget(self):
  request=mock.Mock(tries=4,current_tries=1)
  self.provider._on_exception(request,HTTPError('https://example.invalid',503,'fixture',{},None),None)
  self.assertEqual(request.tries,4)
 def test_refresh_failure_does_not_destroy_saved_state(self):
  self.provider._signin.refresh_tokens.side_effect=RuntimeError('fixture relay failure')
  with self.assertRaises(RuntimeError):self.provider.refresh_access_tokens()
  self.manager.save_account.assert_not_called();self.assertEqual(self.account['access_tokens']['access_token'],'at0')
class FakeAddon(CloudDriveAddon):
 def __init__(self):pass
 def __del__(self):pass
class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.addon=FakeAddon();self.addon._addon=mock.Mock();self.addon._addon.getSetting.return_value='true'
  self.addon._content_type='video';self.addon._account_manager=mock.Mock();self.addon._addonid='plugin.googledrive';self.addon._common_addon=mock.Mock();self.addon._addon_handle=1
  self.addon._dialog=mock.Mock();self.addon._dialog.contextmenu.return_value=0
  self.provider=mock.Mock();self.provider.get_item.return_value={'name':'Fixture.mp4','mimetype':'video/mp4','video':{'duration':100},'subtitles':[{'name':'Fixture.srt','id':'s1'}]}
  self.addon.get_provider=mock.Mock(return_value=self.provider);self.addon.cancel_operation=lambda:False
  self.addon._get_item_play_url=lambda *a,**kw:'http://127.0.0.1/fixture'
  self.item=mock.Mock()
  self.patches=[mock.patch.object(xbmcgui,'ListItem',return_value=self.item),mock.patch.object(xbmcplugin,'setResolvedUrl'),mock.patch.object(KodiUtils,'get_current_library_info',return_value={'id':1,'type':'movie'}),mock.patch.object(KodiUtils,'get_video_details',return_value={'resume':{'position':30,'total':100},'playcount':0}),mock.patch.object(KodiUtils,'get_addon_setting',return_value='true'),mock.patch.object(KodiUtils,'localize',return_value='Resume %s')]
  self.active=[p.start() for p in self.patches]
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
 def test_playback_start_sets_resume_and_subtitle_urls(self):
  self.addon.play('fixture','fixture','video')
  self.item.setProperty.assert_any_call('resumetime','30');self.item.setProperty.assert_any_call('startoffset','30')
  self.item.setSubtitles.assert_called_once_with(['http://127.0.0.1/fixture'])
  self.active[1].assert_called_once_with(1,True,self.item)
 def test_cancelled_resume_does_not_start_playback(self):
  self.addon._dialog.contextmenu.return_value=-1;self.addon.play('fixture','fixture','video')
  self.active[1].assert_called_once_with(1,False,self.item)
 def test_start_from_beginning_does_not_apply_resume_offset(self):
  self.addon._dialog.contextmenu.return_value=1;self.addon.play('fixture','fixture','video')
  self.assertFalse(any(call.args[0] in {'resumetime','startoffset'} for call in self.item.setProperty.call_args_list))
if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [RefreshTests,ResumeTests]])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'scope':'Pinned source with mocked Kodi/library and synthetic tokens; no real account, network, codec or iPhone test','direct_unindexed_browse_resume_verified':False,'ios_runtime_verified':False}
 if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
