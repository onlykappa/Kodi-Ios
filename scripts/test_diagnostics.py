"""Build identity, useful failure evidence and credential-safe exported support logs."""
import importlib.util,json,os,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0,str(ROOT/'scripts'))
import diagnostics as diag
import driveupload,drive_stream,debrid_drive

class Diagnostics(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.profile=self.root/'profile';self.profile.mkdir()
  (self.root/'build.json').write_text(json.dumps(dict(build=167,commit='abc123def456',frameworks={'airplay':{'tag':'kodi-airplay-r17','sha256':'a'*64},'glassbar':{'tag':'kodi-glassbar-r6'}})))
  diag.configure(self.root,self.profile,clock=lambda:100)
  self.logs=[]
 def record(self):return json.loads(self.logs[-1].split('Kodi iOS diagnostic ',1)[1])
 def test_installed_build_banner_and_every_event_share_provenance(self):
  diag.event(self.logs.append,'startup','installed_build',kodi='21.3')
  first=self.record()
  self.assertEqual(first['build'],'167');self.assertEqual(first['frameworks']['airplay']['tag'],'kodi-airplay-r17')
  diag.event(self.logs.append,'preparation','started')
  self.assertEqual(self.record()['session'],first['session']);self.assertEqual(self.record()['commit'],'abc123def456')
 def test_missing_or_bad_build_remains_explicitly_unknown(self):
  for data in ('[]','{"build":"bad"}','{"build":0}'):
   (self.root/'build.json').write_text(data);self.assertEqual(diag.build_info(self.root)['build'],'unknown')
  (self.root/'build.json').unlink();self.assertEqual(diag.build_info(self.root)['build'],'unknown')
 def test_ui_scripts_attach_to_service_session_without_replacing_it(self):
  original=diag._read(self.profile/'addon_data/service.kodi.ios.bootstrap/diagnostic-session.json')
  diag.configure(self.root)
  self.assertNotEqual(diag._context['session'],original['session'])
  diag.attach(self.root,self.profile)
  self.assertEqual(diag._context['session'],original['session'])
  self.assertEqual(diag._read(self.profile/'addon_data/service.kodi.ios.bootstrap/diagnostic-session.json'),original)
 def test_exception_has_stack_cause_errno_and_no_connection_credentials(self):
  try:
   try:raise ConnectionRefusedError(61,'socket refused https://drive.example/source?token=SECRET')
   except ConnectionRefusedError as cause:raise urllib.error.URLError(cause)
  except Exception as error:diag.exception(self.logs.append,'preparation',error,phase='Inspecting',attempt=2)
  item=self.record();self.assertEqual(item['errors'][1]['errno'],61)
  self.assertEqual(item['errors'][0]['type'],'URLError');self.assertEqual(item['phase'],'Inspecting')
  self.assertTrue(item['errors'][1]['frames']);self.assertNotIn('SECRET',self.logs[-1])
  self.assertEqual(item['errors'][1]['frames'][-1]['file'],'test_diagnostics.py')
 def test_http_error_keeps_status_but_drops_signed_url(self):
  error=urllib.error.HTTPError('https://example/file?key=secret',503,'retry',None,None)
  diag.exception(self.logs.append,'drive',error)
  self.assertEqual(self.record()['errors'][0]['code'],503);self.assertNotIn('secret',self.logs[-1])
 def test_redaction_covers_auth_json_urls_and_kodi_headers(self):
  samples=['Cookie: a=ok; b=SECRET; Path=/','Authorization: Bearer SECRET','{"refresh_token":"SECRET"}',"password='SECRET'",'GET https://host/file?key=SECRET|Authorization=SECRET',
           'magnet:?xt=urn:btih:SECRET','Basic U0VDUkVU']
  for sample in samples:
   with self.subTest(sample=sample):
    result=diag.redact(sample);self.assertNotIn('SECRET',result);self.assertNotIn('U0VDUkVU',result)
  self.assertEqual(diag.safe({'access_token':'SECRET','nested':{'session_url':'SECRET'}}),{'access_token':'[redacted]','nested':{'session_url':'[redacted]'}})
 def test_repeated_redaction_preserves_long_structured_failure_records(self):
  diag.event(self.logs.append,'preparation','failure',reason='Cookie: a=ok; b=SECRET',frames=['frame']*100,details='x'*1900)
  text='2026-11-06 info '+self.logs[0]+'\n'
  redacted=diag.redact(diag.redact(text))
  item=json.loads(redacted.split('Kodi iOS diagnostic ',1)[1])
  self.assertEqual(item['build'],'167');self.assertEqual(len(item['details']),1900);self.assertNotIn('SECRET',redacted)
 def test_snapshot_reports_queue_stage_and_byte_progress_without_raw_jobs(self):
  folder=self.profile/'addon_data/service.kodi.ios.bootstrap'
  (folder/debrid_drive.FILE).write_text(json.dumps({'jobs':[{'status':'uploading','source_url':'SECRET','hash':'SECRET'}],'current':{'stage':'Upload','sent':1024,'total':4096,'source_url':'SECRET'}}))
  (folder/'airplay-preparation.json').write_text(json.dumps({'jobs':{'private_id':{'status':'failed','source':{'id':'SECRET'}}},'staging_cleanup':['SECRET'],'current':{'stage':'Inspecting','progress':0,'indeterminate':True,'updated':80}}))
  (folder/'preparation-runtime.json').write_text(json.dumps(dict(phase='Inspecting',known=False,updated=99,read_bytes=2048,last_read=99,read_error='',url='SECRET')))
  (folder/'drive-uploads.json').write_text(json.dumps({'sessions':{'SECRET':{'url':'SECRET'}},'verified':{'SECRET':{}},'current':{'sent':333,'total':999,'name':'SECRET'}}))
  result=diag.snapshot(self.profile,clock=lambda:100)
  self.assertEqual(result['uploads']['resumable_sessions'],1);self.assertEqual(result['uploads']['current']['sent'],333)
  self.assertEqual(result['debrid']['current']['sent'],1024);self.assertEqual(result['preparation']['current']['age_s'],20)
  self.assertEqual(result['worker']['heartbeat_age_s'],1);self.assertEqual(result['worker']['read_bytes'],2048)
  self.assertNotIn('SECRET',json.dumps(result));self.assertEqual(result['preparation']['statuses'],{'failed':1})
 def test_export_contains_build_header_previous_current_and_summary(self):
  log=self.root/'logs';log.mkdir()
  (log/'kodi.old.log').write_text('old launch\nAuthorization: Bearer OLDSECRET\n')
  (log/'kodi.log').write_text('current launch\nHTTP https://drive.example/file?token=NEWSECRET\n{"refresh_token":"JSONSECRET"}\n')
  path=diag.export(self.root,self.profile,log,self.root/'exports',clock=lambda:100)
  self.assertEqual(path.name,'Kodi-build-167-19700101T000140Z.log')
  text=path.read_text();self.assertIn('Installed build: 167',text);self.assertIn('kodi-airplay-r17',text)
  self.assertLess(text.index('old launch'),text.index('current launch'));self.assertIn('Current queue summary',text)
  self.assertNotIn('SECRET',text);self.assertIn('NEWSECRET',(log/'kodi.log').read_text(),'original log remains unchanged')
 def test_network_summary_says_link_lanes_and_speeds(self):
  # ISSUE-198 (owner logs, build 350): no way to tell Wi-Fi from cellular or which pipe was starved.
  import tempfile,json as _j
  from pathlib import Path as _P
  with tempfile.TemporaryDirectory() as d:
   folder=_P(d)
   # ISSUE-271: a lane that has not reported for 90 s is quiet, not still copying at its last speed.
   (folder/'debrid-drive.json').write_text(_j.dumps({'lanes':{'0':{'stage':'copying','rate_own':2*1048576,'updated':95},'1':{'stage':'copying','rate_own':1048576,'updated':99},
     '2':{'stage':'copying','rate_own':5*1048576,'updated':1}},
     'jobs':[{'status':'copying','net_tries':2},{'status':'done','net_tries':1}]}))
   diag._NET.clear()
   first=diag.network(folder,{'read_bytes':0},lambda:100,link='wifi')
   self.assertEqual((first['link'],first['copy_lanes'],first['copy_mb_s'],first['copies_waiting_for_network']),('wifi',3,3.0,1))
   self.assertEqual(first['quiet_lanes'],1)
   second=diag.network(folder,{'read_bytes':60*1048576},lambda:160,link='cellular')
   self.assertEqual((second['prep_read_mb_s'],second['link_changed_from']),(1.0,'wifi'))
 def test_watch_emits_initial_and_periodic_snapshot_with_build(self):
  waits=[]
  diag.watch(self.profile,self.logs.append,lambda seconds:waits.append(seconds) or len(waits)>=2,settings=lambda:dict(background_transfers=True))
  self.assertEqual(waits,[60,60]);self.assertEqual(len(self.logs),2)
  self.assertEqual(self.record()['build'],'167');self.assertTrue(self.record()['settings']['background_transfers'])
 def test_generated_ipa_identity_has_build_workflow_and_framework_versions(self):
  from build_customized_ipa import build_identity
  with patch.dict(os.environ,{'GITHUB_RUN_NUMBER':'167','GITHUB_SHA':'b'*40,'GITHUB_RUN_ID':'12345','GITHUB_RUN_ATTEMPT':'2','GITHUB_REF_NAME':'fix/branch'},clear=True):identity=build_identity()
  self.assertEqual(identity['build'],167);self.assertEqual(identity['commit'],'b'*40);self.assertEqual(identity['workflow_run'],'12345')
  self.assertIn('airplay',identity['frameworks']);self.assertIn('glassbar',identity['frameworks']);self.assertIn('ios-portrait',identity['frameworks'])

class Network(unittest.TestCase):
 def setUp(self):self.logs=[]
 def response(self):
  r=Mock();r.status=200;r.headers={};r.read.return_value=b'ok';r.__enter__=Mock(return_value=r);r.__exit__=Mock(return_value=False);return r
 def test_retry_records_transport_details_without_headers_or_url_path(self):
  opener=Mock();opener.open.side_effect=[urllib.error.URLError(TimeoutError('read https://upload.example/SECRET timed out')),self.response()]
  with patch('driveupload.urllib.request.build_opener',return_value=opener),patch('driveupload.time.sleep'):
   send=driveupload.sender(None,log=self.logs.append)
   self.assertEqual(send('GET','https://upload.example/SECRET?token=SECRET',None,{'Authorization':'Bearer SECRET'})[0],200)
  self.assertEqual(opener.open.call_count,2);self.assertNotIn('SECRET',''.join(self.logs))
  item=json.loads(self.logs[0].split('Kodi iOS diagnostic ',1)[1]);self.assertEqual(item['host'],'upload.example');self.assertTrue(item['retry'])
 def test_failed_mutating_request_is_logged_without_unsafe_replay(self):
  opener=Mock();opener.open.side_effect=urllib.error.URLError(TimeoutError())
  with patch('driveupload.urllib.request.build_opener',return_value=opener):
   send=driveupload.sender(None,log=self.logs.append)
   with self.assertRaises(urllib.error.URLError):send('POST','https://upload.example/file',b'secret body',{'Authorization':'Bearer SECRET'})
  self.assertEqual(opener.open.call_count,1)
  item=json.loads(self.logs[0].split('Kodi iOS diagnostic ',1)[1]);self.assertFalse(item['retry']);self.assertEqual(item['request_bytes'],11)
 def test_upload_timing_records_bounded_chunk_evidence(self):
  opener=Mock();opener.open.return_value=self.response()
  with patch('driveupload.urllib.request.build_opener',return_value=opener):
   driveupload.sender(None,log=self.logs.append)('PUT','https://upload.example/private-session',b'x'*(256*1024),{})
  item=json.loads(self.logs[0].split('Kodi iOS diagnostic ',1)[1]);self.assertEqual(item['request_bytes'],256*1024);self.assertEqual(item['response_bytes'],2)
  self.assertIn('elapsed_s',item);self.assertNotIn('private-session',self.logs[0])
if __name__=='__main__':unittest.main()
