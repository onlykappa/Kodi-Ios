"""Owner (build 160): "a movie im downloading goes onto my phone still … if i do a large movie it wont ever download";
chose AllDebrid straight to Drive. alldebrid (client, pick), driveupload.upload_stream, debrid_drive (queue, step),
and the wiring in download.py, service.py and notices.py."""
import io,json,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import alldebrid,debrid_drive,driveupload,notices
H='a'*40

class Client(unittest.TestCase):
 def api(self,answers):
  self.calls=[]
  def request(method,url,data,headers):
   self.calls.append((method,url,data,headers));return json.dumps(answers.pop(0)).encode()
  return alldebrid.AllDebrid('tok',request)
 def test_add_status_files_unlock(self):
  api=self.api([{'status':'success','data':{'magnets':[{'id':7,'ready':False}]}},
                {'status':'success','data':{'magnets':{'statusCode':1,'size':100,'downloaded':40,'status':'Downloading'}}},
                {'status':'success','data':{'magnets':[{'files':[{'n':'Fall.2022','e':[{'n':'Fall.2022.2160p.mkv','s':9,'l':'L1'},{'n':'sample.mkv','s':1,'l':'L2'}]}]}]}},
                {'status':'success','data':{'link':'https://x.debrid.it/dl/f.mkv','filename':'Fall.2022.2160p.mkv','filesize':9}}])
  self.assertEqual(api.add(H),('7',False))
  self.assertEqual(self.calls[0][3]['Authorization'],'Bearer tok');self.assertIn('agent=KodiIOS',self.calls[0][1])
  self.assertEqual(self.calls[0][2],{'magnets[]':[H]})
  self.assertEqual(api.status('7'),(1,0.4,'Downloading'))
  self.assertEqual(api.files('7'),[('Fall.2022/Fall.2022.2160p.mkv',9,'L1'),('Fall.2022/sample.mkv',1,'L2')])
  self.assertEqual(api.unlock('L1'),('https://x.debrid.it/dl/f.mkv','Fall.2022.2160p.mkv',9))
 def test_errors_in_plain_words(self):
  api=self.api([{'status':'error','error':{'code':'AUTH_BAD_APIKEY','message':'bad'}}])
  with self.assertRaises(alldebrid.Problem) as c:api.add(H)
  self.assertIn('Umbrella › Accounts',str(c.exception))
  with self.assertRaises(alldebrid.Problem):alldebrid.AllDebrid('')
 def test_token_from_umbrella_settings(self):
  self.assertEqual(alldebrid.token_from_settings('<settings><setting id="alldebridtoken">abc123</setting></settings>'),'abc123')
  self.assertEqual(alldebrid.token_from_settings('<setting id="alldebridtoken" value="xyz" />'),'xyz')
  self.assertEqual(alldebrid.token_from_settings(''),'')
 def test_pick(self):
  files=[('F/Movie.2160p.mkv',9,'a'),('F/Sample/sample.mkv',1,'b'),('F/extras.mkv',5,'c'),('F/info.nfo',1,'d')]
  self.assertEqual([f[2] for f in alldebrid.pick(files,'movie')],['a'])
  pack=[('S/Show.S01E02.mkv',2,'e2'),('S/Show.S01E01.mkv',2,'e1'),('S/Show.S01E03.mkv',2,'e3')]
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'episode','1','2')],['e2'])
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'season','1')],['e1','e2','e3'])
  self.assertEqual([f[2] for f in alldebrid.pick(pack,'season','1',episodes=[1,3])],['e1','e3'])

class FakeDrive(driveupload.Drive):
 """Drive's resumable upload: keeps what it got; can lose the last chunk once."""
 def __init__(self,lose_after=None):
  super().__init__(lambda:'t',None);self.data=b'';self.lose_after=lose_after;self.puts=0;self.folders_made=[]
 def call(self,method,url,body=None,headers=None):
  if method=='POST':return 200,{'Location':'https://upload/session'},b''
  cr=headers['Content-Range']
  if cr.startswith('bytes */'):return 308,({'Range':'bytes=0-%d'%(len(self.data)-1)} if self.data else {}),b''
  a,b=cr[6:].split('/')[0].split('-');a=int(a);total=int(cr.split('/')[1])
  self.puts+=1
  if self.lose_after and self.puts==self.lose_after:return 308,{'Range':'bytes=0-%d'%(a-1)} if a else {},b''   # dropped
  self.data=self.data[:a]+body
  if len(self.data)==total:return 200,{},json.dumps({'id':'drive-1','size':str(total)}).encode()
  return 308,{'Range':'bytes=0-%d'%(len(self.data)-1)},b''
 def folder(self,parts):self.folders_made.append(parts);return 'folder-id'

class Stream(unittest.TestCase):
 def test_chunk_policy_shrinks_aligns_and_recovers_cautiously(self):
  policy=driveupload.StreamChunks(8*1024*1024)
  policy.observe(8*1024*1024,1,12);self.assertEqual(policy.current,8*1024*1024)   # 12 s: kept (ISSUE-164)
  policy.observe(8*1024*1024,1,27)          # the owner's 0.3 MB/s: about ten seconds' worth, 256 KiB aligned
  self.assertEqual(policy.current,2816*1024)
  for _ in range(2):policy.observe(policy.current,.5,1)
  self.assertEqual(policy.current,2816*1024)
  policy.observe(policy.current,.5,1);self.assertEqual(policy.current,5632*1024)
  policy.observe(policy.current,120,1);self.assertEqual(policy.current,1024*1024)
 def test_activity_does_not_claim_unconfirmed_download_bytes(self):
  import threading
  thread=threading.get_ident();events=[];drive=FakeDrive()
  def activity(phase,done,total):
   self.assertEqual(threading.get_ident(),thread)
   self.assertLessEqual(done,len(drive.data));events.append(phase)
  drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,activity=activity)
  self.assertIn('reading',events);self.assertIn('uploading',events)
 def setUp(self):
  self.old=driveupload.CHUNK;driveupload.CHUNK=256*1024
  self.blob=bytes(range(256))*4000   # ~1 MB
  self.opened=[]
 def tearDown(self):driveupload.CHUNK=self.old
 def open_at(self,offset):self.opened.append(offset);return io.BytesIO(self.blob[offset:])
 def test_copies_without_a_local_file_and_resumes_from_drive(self):
  drive=FakeDrive(lose_after=2);session={}
  result=drive.upload_stream(self.open_at,len(self.blob),'Fall.mkv','p',session,lambda:None)
  self.assertEqual(drive.data,self.blob);self.assertEqual(result['id'],'drive-1')
  self.assertEqual(self.opened,[0,256*1024])     # Drive dropped the 2nd chunk: read again from where it got to
 def test_a_restart_carries_on(self):
  drive=FakeDrive();drive.data=self.blob[:512*1024];session={'url':'https://upload/session','size':len(self.blob)}
  drive.upload_stream(self.open_at,len(self.blob),'Fall.mkv','p',session,lambda:None)
  self.assertEqual(self.opened,[512*1024]);self.assertEqual(drive.data,self.blob)
 def test_stop_when_asked(self):
  with self.assertRaises(driveupload.Stop):FakeDrive().upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,keep_going=lambda:False)
 def test_confirmed_progress_precedes_throttle_and_completion_does_not_wait(self):
  import slowdown
  drive=FakeDrive();seen=[];calls=[]
  class Gate:
   def after(inner,seconds,nbytes=0,download=False):
    calls.append(len(drive.data))
    self.assertEqual(seen[-1],len(drive.data))
    self.assertLess(len(drive.data),len(self.blob))
  with patch.object(slowdown,'Gate',side_effect=[type('Reader',(),{'after':lambda *a,**k:None})(),Gate()]):
   drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,progress=lambda sent,total:seen.append(sent))
  self.assertEqual(seen[-1],len(self.blob));self.assertEqual(len(calls),drive.puts-1)
 def test_large_stream_reports_eight_megabyte_checkpoints(self):
  driveupload.CHUNK=32*1024*1024;self.blob=b'z'*(17*1024*1024);seen=[];drive=FakeDrive()
  drive.upload_stream(self.open_at,len(self.blob),'x','p',{},lambda:None,progress=lambda sent,total:seen.append(sent))
  self.assertEqual(seen,[8*1024*1024,16*1024*1024,17*1024*1024]);self.assertEqual(drive.data,self.blob)

class FakeAPI:
 def __init__(self,ready=True,status=(4,1.0,'Ready')):self.ready=ready;self.st=status;self.added=[]
 def add(self,h):self.added.append(h);return '9',self.ready
 def status(self,m):return self.st
 def files(self,m):return [('Fall/Fall.2022.2160p.mkv',3,'L')]
 def unlock(self,l):return 'https://x/f','Fall.2022.2160p.mkv',3

class NativeCopies(unittest.TestCase):
 def test_copy_bytes_bypass_python_reader_and_query_uncertain_ack_before_resuming(self):
  blob=b'x'*(20*1024*1024);offsets=[]   # owner log 4beafff6: native pieces start at 8 MB
  class API(FakeAPI):
   def unlock(self,link):return 'https://source/f','Fall.2022.2160p.mkv',len(blob)
  class Drive(FakeDrive):
   def copy_piece(self,source,source_headers,target,headers,offset,count,total,timeout):
    offsets.append(offset)
    result=self.call('PUT',target,blob[offset:offset+count],{'Content-Range':'bytes %d-%d/%d'%(offset,offset+count-1,total)})
    if len(offsets)==1:raise ConnectionError('response lost after Drive accepted the bytes')
    return result
  with tempfile.TemporaryDirectory() as profile:
   debrid_drive.queue(profile,{'id':H,'name':'Fall'},'movie','Fall');drive=Drive();api=API()
   debrid_drive.step(profile,api,drive)
   def forbidden(*args):raise AssertionError('Video bytes passed through Python source reader')
   debrid_drive.step(profile,api,drive,open_url=forbidden)
   self.assertEqual(debrid_drive.load(profile)['jobs'][0]['status'],'done');self.assertEqual(drive.data,blob)
   self.assertEqual(offsets,[0,8*1024*1024,12*1024*1024,16*1024*1024])   # after the lost answer: half-size pieces

class Paced(unittest.TestCase):
 def test_the_deadline_follows_the_confirmed_speed(self):
  # Owner log ec3b0956 (build 325): ~0.1 MB/s a lane; 40 % of pieces hit the fixed 20 s and were partly sent again.
  pace=driveupload.Pace()
  self.assertEqual(pace.deadline(1024*1024),20.0)                          # nothing measured yet
  pace.observe(1024*1024,10)                                               # 0.1 MB/s confirmed
  self.assertAlmostEqual(pace.deadline(1024*1024),30.0)                    # 3 x 10 s
  self.assertEqual(pace.deadline(64*1024*1024),180.0)                      # never past the framework's cap
  pace.observe(0,20)                                                       # a stalled piece does not move it
  self.assertAlmostEqual(pace.deadline(1024*1024),30.0)
  for _ in range(10):pace.observe(8*1024*1024,1)                           # a fast link: back to the floor
  self.assertEqual(pace.deadline(1024*1024),20.0)
 def test_copiers_get_the_deadline(self):
  blob=b'x'*(3*1024*1024);seen=[]
  class Drive(FakeDrive):
   def copy_piece(self,source,source_headers,target,headers,offset,count,total,timeout):
    seen.append(timeout)
    return self.call('PUT',target,blob[offset:offset+count],{'Content-Range':'bytes %d-%d/%d'%(offset,offset+count-1,total)})
  class API(FakeAPI):
   def unlock(self,link):return 'https://source/f','Fall.2022.2160p.mkv',len(blob)
  with tempfile.TemporaryDirectory() as profile:
   debrid_drive.queue(profile,{'id':H,'name':'Fall'},'movie','Fall');drive=Drive();api=API()
   debrid_drive.step(profile,api,drive);debrid_drive.step(profile,api,drive)
   self.assertEqual(debrid_drive.load(profile)['jobs'][0]['status'],'done');self.assertEqual(seen[0],20.0)

class LaneLearning(unittest.TestCase):
 def test_lanes_follow_what_the_link_gives(self):
  # E16: start at three (ISSUE-200); one more while it pays (15 %); else the fastest count measured.
  st={}
  self.assertEqual(debrid_drive.lane_plan(st),3)
  debrid_drive.learn_lanes(st,2,300*1024**2,600)            # 0.5 MB/s with two
  self.assertEqual(debrid_drive.lane_plan(st),3)              # try three
  debrid_drive.learn_lanes(st,3,330*1024**2,600)            # +10 %: not worth it
  self.assertEqual(debrid_drive.lane_plan(st),2)
  fast={}
  debrid_drive.learn_lanes(fast,2,1200*1024**2,600)
  debrid_drive.learn_lanes(fast,3,1700*1024**2,600)         # +42 %
  self.assertEqual(debrid_drive.lane_plan(fast),4)
  debrid_drive.learn_lanes(fast,4,2400*1024**2,600)
  self.assertEqual(debrid_drive.lane_plan(fast),5)            # still paying: one more
  for n,mb in ((5,3000),(6,3600)):debrid_drive.learn_lanes(fast,n,mb*1024**2,600)
  self.assertEqual(debrid_drive.lane_plan(fast),6)            # never more than LANES (6, ISSUE-200)
  # ISSUE-200: a new connection forgets what the old one rewarded.
  moved={'link':'cellular','lane_speeds':{'2':1.0},'lanes_now':2,'jobs':[]}
  debrid_drive.kick_on_new_link(moved,'wifi',lambda:0)
  self.assertNotIn('lane_speeds',moved);self.assertEqual(debrid_drive.lane_plan(moved),3)
  quick={}
  debrid_drive.learn_lanes(quick,2,1024,5)                   # a few seconds say nothing
  self.assertEqual(quick,{})
  src=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/debrid_drive.py').read_text()
  self.assertIn('if not busy and not converting():',src)       # E19: runs beside a conversion are not learned from

class LateBytes(unittest.TestCase):
 def test_drive_keeping_a_timed_out_pieces_bytes_is_not_an_error(self):
  # Owner log 3b94b426 (build 319): after a 20 s timeout Drive confirmed more than the next piece sent; the copy failed
  # with "Invalid Drive confirmed position". Drive's position is the truth up to the file's size.
  blob=bytes(range(256))*(64*1024);size=len(blob);calls=[]
  class Drive(FakeDrive):
   def copy_piece(self,source,source_headers,target,headers,offset,count,total,timeout):
    calls.append((offset,count))
    if len(calls)==1:   # the first piece times out; Drive has only half when asked
     self.data=blob[:count//2];raise TimeoutError('piece took 20 s')
    if len(calls)==2:   # the rest of piece 1 lands late: Drive is past this piece's end
     self.data=blob[:offset+count+1024*1024]
     return 308,{'Range':'bytes=0-%d'%(len(self.data)-1)},b''
    return self.call('PUT',target,blob[offset:offset+count],{'Content-Range':'bytes %d-%d/%d'%(offset,offset+count-1,total)})
  class API(FakeAPI):
   def unlock(self,link):return 'https://source/f','Fall.2022.2160p.mkv',size
  with tempfile.TemporaryDirectory() as profile:
   debrid_drive.queue(profile,{'id':H,'name':'Fall'},'movie','Fall');drive=Drive();api=API()
   debrid_drive.step(profile,api,drive);debrid_drive.step(profile,api,drive)
   self.assertEqual(debrid_drive.load(profile)['jobs'][0]['status'],'done');self.assertEqual(drive.data,blob)
   self.assertEqual(calls[2][0],calls[1][0]+calls[1][1]+1024*1024)   # carried on from where Drive was

class HashNamedJobs(unittest.TestCase):
 def test_names_from_releases_tmdb_and_requeue(self):
  # Owner screenshots (build 325): "3c90db2e05…" and "ee34425d5595…" cards; "Download · S1 E4" in Up next.
  t=debrid_drive.title_from_name
  self.assertEqual(t('Naruto Shippuden Episode 006 Mission to Rescue the Kazekage.mkv'),'Naruto Shippuden')
  self.assertEqual(t('S/[Sub] Naruto.Shippuuden.-.002.[1080p].mkv'),'Naruto Shippuuden')
  self.assertEqual(t('Show.S01E04.1080p.mkv'),'Show')
  self.assertEqual(t('ee34425d5595f37297bc8c94dab3184c02d43daf'),'')
  h='3c90db2e05'+'a'*30
  state={'jobs':[{'hash':h,'name':h,'title':h,'kind':'episode','season':'1','episode':'4','show_tmdb':'31910','status':'new','files':[]},
                 {'hash':'e'*40,'name':'e'*40,'title':'e'*40,'kind':'episode','season':'1','episode':'6','status':'copying',
                  'files':[{'path':'P/Naruto Shippuden Episode 006 Mission.mkv','done':False,'session':{}}]}]}
  asked=[]
  changed=debrid_drive.retitle('/p',state,plans={},lookup=lambda i:asked.append(i) or 'Naruto Shippūden')
  self.assertEqual([j['title'] for j,_ in changed],['Naruto Shippūden','Naruto Shippuden'])
  self.assertEqual((asked,state['jobs'][0]['name']),(['31910'],'Naruto Shippūden S01E04'))
 def test_a_new_request_renames_an_old_hash_job(self):
  with tempfile.TemporaryDirectory() as p:
   h='ee34425d55'+'f'*30
   debrid_drive.queue(p,{'id':h},'episode','',season='1',episode='4',show_tmdb='31910')
   self.assertEqual(debrid_drive.load(p)['jobs'][0]['title'],'')
   job=debrid_drive.queue(p,{'id':h,'name':'Naruto Shippūden S01E04'},'episode','Naruto Shippūden',season='1',episode='4',show_tmdb='31910')
   self.assertEqual((job['title'],len(debrid_drive.load(p)['jobs'])),('Naruto Shippūden',1))

class Duplicates(unittest.TestCase):
 def test_pick_better_versions_plan(self):
  # Owner (build 328): episodes already queued with oversized versions get a better pick; copies under way stay.
  started={'path':'a','done':False,'session':{'url':'u'}}
  state={'jobs':[{'hash':'a'*40,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':'3','status':'copying','files':[started]},
                 {'hash':'a'*40,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':'4','status':'copying','files':[]},
                 {'hash':'b'*40,'title':'Naruto Shippuuden','kind':'episode','season':'1','episode':'5','status':'new','files':[]},
                 {'hash':'c'*40,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':'6','status':'new','files':[]},
                 {'hash':'d'*40,'title':'Lanterns','kind':'episode','season':'1','episode':'1','status':'new','files':[]}]}
  hashes,episodes=debrid_drive.repick_plan(state,'Naruto Shippūden')
  self.assertEqual((hashes,episodes),(['b'*40,'c'*40],[(1,5),(1,6)]))   # E4 shares a torrent with E3, already copying
 def test_a_cancelled_job_never_stands_in_for_the_new_pick(self):
  import transfer_control
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.queue(p,{'id':'1'*40,'name':'Naruto S01E06 huge'},'episode','Naruto',season='1',episode='6',show_tmdb='9')
   transfer_control.cancel_copy(p,'1'*40)
   debrid_drive.queue(p,{'id':'2'*40,'name':'Naruto S01E06 web'},'episode','Naruto',season='1',episode='6',show_tmdb='9')
   self.assertEqual(len(debrid_drive.load(p)['jobs']),2)

 def test_one_title_per_show(self):
  # Owner screenshot (build 327): "Naruto Shippuden" (poster) and "Naruto Shippuuden" (none) as two shows.
  state={'jobs':[{'hash':'1'*40,'title':'Naruto Shippuden','kind':'episode','show_tmdb':'31910','status':'copying','files':[]},
                 {'hash':'2'*40,'title':'Naruto Shippuuden','kind':'episode','status':'done','files':[]},
                 {'hash':'3'*40,'title':'Naruto Shippuuden','kind':'episode','status':'new','files':[]},
                 {'hash':'4'*40,'title':'Lanterns','kind':'episode','status':'new','files':[]}]}
  changed=debrid_drive.one_spelling(state)
  self.assertEqual([(j['hash'][0],old) for j,old in changed],[('2','Naruto Shippuuden'),('3','Naruto Shippuuden')])
  self.assertEqual({j['title'] for j in state['jobs'][:3]},{'Naruto Shippuden'})
  self.assertEqual(state['jobs'][1]['moved_from'],'Naruto Shippuuden')   # its files move out of that folder

 def test_an_episode_already_on_drive_leaves_the_queue(self):
  # Owner screenshot (build 325): "Naruto Shippuuden - 002" on Drive and converting, while S1 E2 waited to be copied.
  import os
  with tempfile.TemporaryDirectory() as p:
   d=os.path.join(p,'addon_data','service.kodi.ios.bootstrap');os.makedirs(d)
   json.dump({'tv:':{'entries':[{'id':'f1','title':'Naruto Shippuuden'}]},
              'tv:f1':{'entries':[{'id':'e2','name':'[Sub] Naruto Shippuuden - 002 [1080p].mkv','show':'Naruto Shippuuden','season':'','episode':''}]}},
             open(os.path.join(d,'drive-library.json'),'w'))
   on=debrid_drive.drive_episodes(p)
   self.assertIn((debrid_drive.show_match('Naruto Shippūden'),1,2),on)
   state={'jobs':[{'hash':'1'*40,'title':'Naruto Shippūden','kind':'episode','season':'1','episode':'2','status':'new','files':[]},
                  {'hash':'2'*40,'title':'Naruto Shippūden','kind':'episode','season':'1','episode':'3','status':'new','files':[]},
                  {'hash':'3'*40,'title':'Naruto Shippuden','kind':'episode','season':'1','episode':'2','status':'copying',
                   'files':[{'path':'x','done':False,'session':{'url':'u'}}]}]}
   dropped=debrid_drive.drop_on_drive(state,on)
   self.assertEqual([j['hash'][0] for j in dropped],['1'])                 # a copy already under way finishes
   self.assertEqual([j['hash'][0] for j in state['jobs']],['2','3'])
 def test_spellings_of_a_show_match(self):
  m=debrid_drive.show_match
  self.assertEqual(m('Naruto Shippūden'),m('Naruto Shippuuden'));self.assertEqual(m('Naruto Shippuden'),m('naruto.shippuden'))
  self.assertNotEqual(m('Naruto'),m('Naruto Shippuden'))

 def test_one_episode_is_queued_once(self):
  # Owner screenshot (build 325): "Naruto Shippuden Episode 006" waited three times, each from another torrent.
  with tempfile.TemporaryDirectory() as p:
   for n in (1,2,3):
    debrid_drive.queue(p,{'id':('%d'%n)*40,'name':'Naruto Episode 006 v%d'%n},'episode','Naruto',season='1',episode='6',show_tmdb='31910')
   debrid_drive.queue(p,{'id':'4'*40,'name':'Naruto Episode 007'},'episode','Naruto',season='1',episode='7',show_tmdb='31910')
   self.assertEqual([j['episode'] for j in debrid_drive.load(p)['jobs']],['6','7'])
 def test_old_duplicates_leave_the_queue_unless_started(self):
  started={'path':'a.mkv','done':False,'session':{'url':'https://upload/a'}}
  state={'jobs':[{'hash':'1'*40,'title':'Naruto','kind':'episode','season':'1','episode':'6','show_tmdb':'9','status':'new','files':[]},
                 {'hash':'2'*40,'title':'Naruto','kind':'episode','season':'1','episode':'6','show_tmdb':'9','status':'copying','files':[started]},
                 {'hash':'3'*40,'title':'Naruto','kind':'episode','season':'1','episode':'6','show_tmdb':'9','status':'new','files':[]},
                 {'hash':'4'*40,'title':'Naruto','kind':'episode','season':'1','episode':'2','show_tmdb':'9','status':'done','files':[]},
                 {'hash':'5'*40,'title':'Naruto','kind':'episode','season':'1','episode':'2','show_tmdb':'9','status':'new','files':[]}]}
  dropped=debrid_drive.drop_duplicates(state)
  self.assertEqual(sorted(j['hash'][0] for j in dropped),['1','3'])        # the one already copying stays
  self.assertEqual([j['hash'][0] for j in state['jobs']],['2','4','5'])    # a done one never counts as waiting

 """Owner screenshot (build 314): Build Season's episodes went into Drive folders named after the torrent hash
 ("3c90db2e052…"), so the Library had no title or poster for them."""
 def test_jobs_take_the_show_title_and_copied_files_move_into_its_folder(self):
  h='3c90db2e05'+'a'*30
  state={'jobs':[{'hash':h,'name':h,'title':h,'kind':'episode','season':'1','episode':'2','show_tmdb':'31910','status':'done',
                  'files':[{'path':'Naruto Shippuuden - 002 [1080p].mkv','drive_name':'Naruto Shippuuden - 002 [1080p].mkv','drive_id':'f1','done':True}]},
                 {'hash':'b'*40,'name':'b'*40,'title':'b'*40,'kind':'episode','season':'1','episode':'3','show_tmdb':'31910','status':'new','files':[]},
                 {'hash':'c'*40,'name':'Fall','title':'Fall','kind':'movie','status':'new','files':[]}]}
  changed=debrid_drive.retitle('/p',state,plans={'31910':{'title':'Naruto Shippūden'}})
  self.assertEqual([j['title'] for j,_ in changed],['Naruto Shippūden','Naruto Shippūden'])
  self.assertEqual((state['jobs'][1]['name'],state['jobs'][2]['title']),('Naruto Shippūden S01E03','Fall'))
  calls=[]
  class Drive:
   def folder(self,parts):return 'id:'+'/'.join(parts[1:])
   def call(self,method,url,body=None,headers=None):
    calls.append((method,url));return (200,{},b'{"files":[]}') if method=='GET' else (200,{},b'{}')
  self.assertEqual(debrid_drive.rehome(Drive(),state['jobs'][0]),1)
  move=calls[0][1]
  self.assertIn('addParents=id%3ATV%20Shows/Naruto%20Shipp%C5%ABden',move.replace('%2F','/'))
  self.assertIn('removeParents=id%3ATV%20Shows/'+h,move.replace('%2F','/'))
  self.assertTrue(any(m=='PATCH' and h in u for m,u in calls[2:]))      # the empty hash folder goes to the Trash
  self.assertNotIn('moved_from',state['jobs'][0])
  self.assertTrue(debrid_drive.is_hash('A'*32) and not debrid_drive.is_hash('Naruto'))
  self.assertEqual(state['jobs'][0]['files'][0]['drive_name'],'Naruto Shippūden S01E02 - Naruto Shippuuden - 002 [1080p].mkv')
  import drivelibrary
  info=drivelibrary.parse(state['jobs'][0]['files'][0]['drive_name'])
  self.assertEqual((info['title'],info['season'],info['episode']),('Naruto Shippūden','1','2'))
  self.assertEqual(debrid_drive.episode_name(state['jobs'][0],'Naruto.S01E02.mkv'),'Naruto.S01E02.mkv')   # already says it

 def test_a_job_with_no_season_plan_takes_its_shows_title_from_another_job(self):
  # Owner (build 319): an "ee34425d5595…" card stayed in Downloaded TV Shows.
  h='ee34425d55'+'f'*30
  state={'jobs':[{'hash':h,'name':h,'title':h,'kind':'episode','season':'1','episode':'4','show_tmdb':'46260','status':'copying','files':[]},
                 {'hash':'d'*40,'name':'Naruto S01E01','title':'Naruto','kind':'episode','season':'1','episode':'1','show_tmdb':'46260','status':'done','files':[]}]}
  changed=debrid_drive.retitle('/p',state,plans={})
  self.assertEqual([(j['title'],j['name'],old) for j,old in changed],[('Naruto','Naruto S01E04',h)])

class NetworkTrouble(unittest.TestCase):
 """ISSUE-198 (owner logs, build 350): 65 of 116 copies ended 'failed' after network trouble (Wi-Fi / cellular
 switches, the phone asleep, Kodi closed); they must wait and carry on, never give up."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_what_counts_as_network_trouble(self):
  import urllib.error
  for e in (ConnectionError('x'),TimeoutError(),OSError('Input/output error'),urllib.error.URLError('offline'),
            urllib.error.HTTPError('u',503,'busy',{},None),RuntimeError('Drive did not confirm the upload'),
            'ConnectionError: Native copy did not finish','RuntimeError: Source read: Input/output error'):
   self.assertTrue(debrid_drive.network_error(e),e)
  for e in (urllib.error.HTTPError('u',404,'gone',{},None),RuntimeError('Google Drive has a different size'),'Problem: torrent has no video',
            'Cancelled'):
   self.assertFalse(debrid_drive.network_error(e),e)
  self.assertEqual([debrid_drive.net_wait(n) for n in (1,2,3,4,5,6,9)],[15,30,60,120,240,300,300])
 def test_fifty_drops_never_fail_a_copy_and_it_finishes_from_where_drive_got_to(self):
  # Wi-Fi switched, phone asleep, app closed and opened again: every step loads the saved state afresh.
  debrid_drive.queue(self.p,{'id':H,'name':'Fall'},'movie','Fall')
  drops={'n':50}
  class Flaky(FakeDrive):
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None,activity=lambda *a:None):
    session.update(url='https://upload/s',size=size);save()
    if drops['n']:
     drops['n']-=1;raise ConnectionError('The network connection was lost')
    return {'id':'d1','size':str(size)}
  clock={'t':0}
  for _ in range(60):
   clock['t']+=400
   if debrid_drive.step(self.p,FakeAPI(),Flaky(),clock=lambda:clock['t']) is None:break
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(job.get('tries',0),0)
 def test_a_new_connection_wakes_waiting_copies(self):
  # Owner: "ensure downloads work if wifi is switched". A copy waiting out network trouble tries again at once.
  state={'link':'wifi','jobs':[{'hash':'a'*40,'status':'copying','net_tries':4,'retry_at':500},{'hash':'b'*40,'status':'copying','retry_at':500}]}
  self.assertIsNone(debrid_drive.kick_on_new_link(state,'wifi',lambda:100))
  self.assertEqual(state['jobs'][0]['retry_at'],500)
  self.assertEqual(debrid_drive.kick_on_new_link(state,'cellular',lambda:100),'wifi')
  self.assertEqual([j['retry_at'] for j in state['jobs']],[0,500])        # only the one waiting for the network
  self.assertEqual(state['link'],'cellular')
 def test_copies_failed_for_network_trouble_come_back_once_and_problems_list_the_rest(self):
  state={'jobs':[{'hash':'a'*40,'name':'A','title':'Naruto','kind':'episode','season':'1','episode':'2','status':'failed','error':'ConnectionError: lost','files':[{'path':'x','done':False,'session':{'url':'u'}}]},
                 {'hash':'b'*40,'name':'B','title':'Fall','kind':'movie','status':'failed','error':'Problem: This torrent has no video file.'},
                 {'hash':'c'*40,'name':'C','title':'Heat','kind':'movie','status':'failed','error':'Cancelled'}]}
  back=debrid_drive.revive(state,lambda:5)
  self.assertEqual([j['title'] for j in back],['Naruto']);self.assertEqual(state['jobs'][0]['status'],'copying')
  self.assertEqual(state['jobs'][0]['files'][0]['session'],{'url':'u'})                 # carries on, not from zero
  self.assertEqual(debrid_drive.revive(state,lambda:6),[])
  kinds=[(p['title'],p['kind']) for p in debrid_drive.problems(state)]
  self.assertEqual(kinds,[('Fall','source'),('Heat','cancelled')])
  debrid_drive.save(self.p,state)
  self.assertEqual(debrid_drive.retry_failed(self.p,('source',)),1)
  self.assertEqual(debrid_drive.clear_failed(self.p),1)
  self.assertEqual([j['status'] for j in debrid_drive.load(self.p)['jobs']],['copying','new'])

class DownloadProblemsPage(unittest.TestCase):
 def test_lines_and_settings_row(self):
  import importlib.util
  root=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
  spec=importlib.util.spec_from_file_location('copy_problems',root/'copy_problems.py');cp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cp)
  found=[{'title':'Fall','reason':'This torrent has no video file.','kind':'source'},{'title':'Heat','reason':'Cancelled','kind':'cancelled'}]
  self.assertEqual(cp.rows(found),[('retry','Retry All (1)'),('clear','Clear All (2)'),('item','Fall · Source: This torrent has no video file.'),
                                    ('item','Heat · Cancelled: Cancelled')])
  self.assertEqual(cp.rows([]),[])
  self.assertIn("R(9459,'Download problems','RunScript(service.kodi.ios.bootstrap,copy_problems)'",(root/'resources/lib/settings_page.py').read_text())
  self.assertIn("'copy_problems'",(root/'default.py').read_text())

class TwoLanes(unittest.TestCase):
 """ISSUE-164 / 1F.4: a season's episodes go up to Drive up to three at a time; a movie is still one upload."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
  # These check the lanes' mechanics at full width; how many the link earns is LaneLearning's.
  self.plan=patch.object(debrid_drive,'lane_plan',lambda state:debrid_drive.LANES);self.plan.start()
 def tearDown(self):self.plan.stop();self.tmp.cleanup()
 def season(self,names):
  class Pack(FakeAPI):
   def files(self,m):return [('S/%s'%n,3,n) for n in names]
   def unlock(self,l):return 'https://x/'+l,l,3
  return Pack()
 def drive(self,fail=None,pause=.3):
  import threading,time
  test=self;lock=threading.Lock();test.now=test.most=0;test.uploaded=[];test.shown=[];p=self.p
  class Lanes(FakeDrive):
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None,activity=lambda *a:None):
    with lock:test.now+=1;test.most=max(test.most,test.now)
    try:
     session.update(url='https://upload/'+name,size=size);save()
     time.sleep(pause);progress(1,size);time.sleep(pause)
     test.shown.append(dict(debrid_drive.load(p).get('current') or {}))
     if name==fail:raise ConnectionError('dropped')
     progress(size,size);test.uploaded.append(name);return {'id':'d-'+name,'size':str(size)}
    finally:
     with lock:test.now-=1
  return Lanes()
 def run_job(self,api,drive):
  for _ in range(6):
   if debrid_drive.step(self.p,api,drive) is None:break
 def test_a_season_uploads_three_episodes_at_once(self):
  # Roadmap 1F.4: three lanes when three or more files remain (build-252 log: ~3.3 MB/s per lane on a 115 Mbps line).
  names=['Show.S01E0%d.mkv'%n for n in (1,2,3)]
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  drive=self.drive();self.run_job(self.season(names),drive)
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(sorted(self.uploaded),names);self.assertEqual(self.most,3)
  self.assertTrue(all(f['done'] and f['drive_id'] for f in job['files']))
  self.assertEqual(len(drive.folders_made),3)
  self.assertTrue(any(c.get('parallel')==3 for c in self.shown))      # the pages show all three lanes' speed
  state=debrid_drive.load(self.p);self.assertNotIn('current',state);self.assertNotIn('current_also',state)
 def test_build_season_episodes_one_job_each_copy_three_at_a_time(self):
  # Owner log 31996cd8 (build 309, 182/101 Mbps line): one job per episode went up one at a time (~2.8 MB/s).
  class Episodes(FakeAPI):
   def files(self,m):return [('S/Show.S01E0%s.mkv'%m[-1],3,'Show.S01E0%s.mkv'%m[-1])]
   def unlock(self,l):return 'https://x/'+l,l,3
   def add(self,h):self.added.append(h);return 'magnet'+h[-1],True
  for n in (1,2,3,4):
   debrid_drive.queue(self.p,{'id':('%d'%n)*40,'name':'Show S01E0%d'%n},'episode','Show',season='1',episode=str(n))
  drive=self.drive();api=Episodes()
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)          # episode 1: added at AllDebrid
  debrid_drive.step(self.p,api,drive)                              # 1, 2 and 3 copy side by side
  self.assertEqual(self.most,4);self.assertEqual(len(self.uploaded),4)
  jobs=debrid_drive.load(self.p)['jobs']
  self.assertEqual([j['status'] for j in jobs],['done']*4)
  self.run_job(api,drive)
  self.assertEqual([j['status'] for j in debrid_drive.load(self.p)['jobs']],['done']*4)
 def test_a_companion_episode_failing_does_not_fail_the_first(self):
  class Episodes(FakeAPI):
   def files(self,m):return [('S/Show.S01E0%s.mkv'%m[-1],3,'Show.S01E0%s.mkv'%m[-1])]
   def unlock(self,l):return 'https://x/'+l,l,3
   def add(self,h):self.added.append(h);return 'magnet'+h[-1],True
  for n in (1,2):
   debrid_drive.queue(self.p,{'id':('%d'%n)*40,'name':'Show S01E0%d'%n},'episode','Show',season='1',episode=str(n))
  drive=self.drive(fail='Show.S01E02.mkv',pause=.05);api=Episodes()
  debrid_drive.step(self.p,api,drive);debrid_drive.step(self.p,api,drive)
  jobs=debrid_drive.load(self.p)['jobs']
  self.assertEqual(jobs[0]['status'],'done')
  # ISSUE-198: a dropped connection is network trouble: it waits and never counts toward giving up.
  self.assertEqual((jobs[1]['status'],jobs[1].get('net_tries'),jobs[1].get('tries',0)),('copying',1,0));self.assertIn('ConnectionError',jobs[1]['error'])
 def test_a_lane_whose_episode_fails_once_tries_it_again_in_the_same_turn(self):
  # Owner log 3b94b426 (build 319): three of four lanes ended at their first error; one copied the season alone for hours.
  import threading,time
  names=['Show.S01E0%d.mkv'%n for n in (1,2,3)];failed=[]
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  test=self;base=self.drive(pause=.05)
  class Once(type(base)):
   def upload_stream(self,open_at,size,name,parent,session,save,*a,**k):
    if name=='Show.S01E02.mkv' and not failed:
     failed.append(name);session.update(url='https://upload/'+name,size=size);save()
     raise RuntimeError('Invalid Drive confirmed position')
    return super().upload_stream(open_at,size,name,parent,session,save,*a,**k)
  api=self.season(names);drive=Once()
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)   # done in this turn, not "again in 30 s"
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(sorted(self.uploaded),names);self.assertFalse(job.get('tries'))
 def test_a_new_turn_clears_an_old_card_and_two_lanes_while_converting(self):
  # Owner screenshot (build 325): "no answer for 23 min" at 0 % from an earlier run's lane; four lanes beside a conversion.
  names=['Show.S01E0%d.mkv'%n for n in range(1,6)]
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  state=debrid_drive.load(self.p);state['current']={'slot':7,'name':'old','updated':1,'stage':'copying'};debrid_drive.save(self.p,state)
  with patch.object(debrid_drive,'conversion_running',lambda profile,now:True):
   self.run_job(self.season(names),self.drive(pause=.1))
  self.assertEqual(self.most,debrid_drive.BUSY_LANES)   # beside a conversion: four (ISSUE-200; was two)
  self.assertFalse(any(c.get('name')=='old' for c in self.shown))
 def test_two_episodes_use_two_lanes_and_five_use_three_at_a_time(self):
  self.assertEqual([debrid_drive.lanes_for(n) for n in (0,1,2,3,4,10)],[1,1,2,3,4,6])   # ISSUE-200: up to six
  for count,most in ((2,2),(5,5)):
   self.tearDown();self.setUp()
   names=['Show.S01E%02d.mkv'%n for n in range(1,count+1)]
   debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
   self.run_job(self.season(names),self.drive(pause=.1))
   self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'done');self.assertEqual(sorted(self.uploaded),names);self.assertEqual(self.most,most)
 def test_a_movie_is_still_one_upload(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  self.run_job(FakeAPI(),self.drive());self.assertEqual(self.most,1)
 def test_one_lane_failing_keeps_the_others_work_and_the_session(self):
  names=['Show.S01E01.mkv','Show.S01E02.mkv']
  debrid_drive.queue(self.p,{'id':H,'name':'Show.S01'},'season','Show',season='1')
  api,drive=self.season(names),self.drive(fail='Show.S01E02.mkv')
  self.assertEqual(debrid_drive.step(self.p,api,drive),1)                 # AllDebrid has it
  self.assertEqual(debrid_drive.step(self.p,api,drive),15)                # copy: one lane dropped (network), again in 15 s
  job=debrid_drive.load(self.p)['jobs'][0];files={f['path']:f for f in job['files']}
  self.assertTrue(files['S/Show.S01E01.mkv']['done']);self.assertFalse(files['S/Show.S01E02.mkv']['done'])
  self.assertEqual(files['S/Show.S01E02.mkv']['session']['url'],'https://upload/Show.S01E02.mkv')   # resumes there
  self.assertEqual((job.get('tries',0),job.get('net_tries')),(0,1))   # ISSUE-198: a dropped connection is not a try

class Queue(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name;self.notes=[];self.done=[]
 def tearDown(self):self.tmp.cleanup()
 def test_expired_source_renews_at_the_same_offset_without_waiting_for_a_job_retry(self):
  api=FakeAPI();unlocks=[];opens=[]
  def unlock(link):
   unlocks.append(link);return 'https://source/'+str(len(unlocks)),'Fall.2022.2160p.mkv',3
  api.unlock=unlock
  def open(url,offset):
   opens.append((url,offset))
   if url.endswith('/1'):raise urllib.error.HTTPError(url,403,'expired',{},io.BytesIO())
   return io.BytesIO(b'abc'[offset:])
  debrid_drive.queue(self.p,{'id':H,'name':'Fall'},'movie','Fall')
  debrid_drive.step(self.p,api,FakeDrive())
  drive=FakeDrive();debrid_drive.step(self.p,api,drive,open_url=open)
  self.assertEqual(drive.data,b'abc');self.assertEqual(opens,[('https://source/1',0),('https://source/2',0)])
  self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'done')
 def run_all(self,api,drive):
  for _ in range(10):
   if debrid_drive.step(self.p,api,drive,lambda k,t,x:self.notes.append((k,t)),open_url=lambda u,o:io.BytesIO(b'abc'[o:]),on_done=self.done.append) is None:break
 def test_movie_end_to_end(self):
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  self.assertEqual(len(debrid_drive.queue(self.p,{'id':H},'movie')['hash']),40);self.assertEqual(len(debrid_drive.load(self.p)['jobs']),1)
  drive=FakeDrive();self.run_all(FakeAPI(),drive)
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual(job['status'],'done');self.assertEqual(drive.data,b'abc');self.assertEqual(drive.folders_made,[['Kodi Downloads','Movies']])
  self.assertIn(('drive','Saved to Google Drive'),self.notes);self.assertEqual(len(self.done),1)
  self.assertFalse(debrid_drive.active(self.p));self.assertEqual(debrid_drive.uploads(self.p),[])
 def test_a_season_download_with_one_episode_says_so(self):
  # Owner (build 205): "i pressed full season" and the Lanterns version picked held S01E01 alone (8.4 GB).
  class One(FakeAPI):
   def files(self,m):return [('Lanterns/Lanterns.S01E01.2160p.mkv',3,'L')]
   def unlock(self,l):return 'https://x/f','Lanterns.S01E01.2160p.mkv',3
  debrid_drive.queue(self.p,{'id':H,'name':'Lanterns.S01E01.2160p'},'season','Lanterns',season='1')
  self.run_all(One(),FakeDrive())
  self.assertIn(('problem','Only one episode was in that download'),self.notes)
  self.assertNotIn(('drive','Saved to Google Drive'),self.notes)
 def test_speed_between_slow_pieces(self):
  # Build 207 (build-206 log): 32 MB pieces 20-30 s apart; the 20 s window held one mark and every page read 0 MB/s.
  t={'now':1000.0};seen=[];p=self.p
  class Slow(FakeDrive):
   def upload_stream(self,open_at,size,name,parent,session,save,keep_going=lambda:True,progress=lambda s,t:None,activity=lambda *a:None):
    for n in range(1,4):
     t['now']+=25;progress(n*32*1048576,size);seen.append(debrid_drive.load(p)['current']['rate'])
    return {'id':'d','size':str(size)}
  class Big(FakeAPI):
   def files(self,m):return [('Fall/Fall.2022.2160p.mkv',10**10,'L')]
   def unlock(self,l):return 'https://x/f','Fall.2022.2160p.mkv',10**10
  debrid_drive.queue(self.p,{'id':H,'name':'Fall.2022.2160p'},'movie','Fall (2022)')
  for _ in range(5):
   if debrid_drive.step(self.p,Big(),Slow(),clock=lambda:t['now']) is None or len(seen)>=3:break
  self.assertEqual(seen[0],0.0)
  self.assertAlmostEqual(seen[1],32*1048576/25.0);self.assertAlmostEqual(seen[2],32*1048576/25.0)
 def test_waits_while_alldebrid_fetches(self):
  debrid_drive.queue(self.p,{'id':H},'movie','Fall (2022)')
  api=FakeAPI(ready=False,status=(1,0.25,'Downloading'))
  self.assertEqual(debrid_drive.step(self.p,api,FakeDrive()),1)
  self.assertEqual(debrid_drive.step(self.p,api,FakeDrive()),15)
  up=notices.uploads(self.p);self.assertEqual(up[0]['line'],'AllDebrid is fetching it · 25%')
 def test_alldebrid_refusal_fails_with_its_words(self):
  debrid_drive.queue(self.p,{'id':H},'movie','Fall (2022)')
  class Bad(FakeAPI):
   def add(self,h):raise alldebrid.Problem('AllDebrid needs a premium subscription for this.')
  debrid_drive.step(self.p,Bad(),FakeDrive(),lambda k,t,x:self.notes.append((k,t,x)))
  self.assertEqual(debrid_drive.load(self.p)['jobs'][0]['status'],'failed');self.assertIn('premium',self.notes[0][2])
 def test_episode_goes_to_its_show(self):
  self.assertEqual(debrid_drive.folders('episode','Lanterns.S01E01.2160p.mkv','Lanterns'),['Kodi Downloads','TV Shows','Lanterns'])
  self.assertEqual(debrid_drive.folders('season','01 - Pilot.mkv','Lanterns'),['Kodi Downloads','TV Shows','Lanterns'])
  self.assertEqual(debrid_drive.info_hash({'id':H.upper()}),H);self.assertEqual(debrid_drive.info_hash({'id':'nothex'}),'')

class SeriesPack(unittest.TestCase):
    """Owner (build 252): seasons 1-3 of Naruto Shippuden from a complete-series pack queued all 500 episodes and the
    films three times."""
    PACK = 'Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio)/'
    def files(self):
        out = []
        for season, first, last in ((1, 1, 32), (2, 33, 53), (3, 54, 71), (4, 72, 88)):
            for n in range(first, last + 1):
                out.append((self.PACK + 'Season %02d (%03d-%03d)/Naruto Shippuden Episode %03d.mkv' % (season, first, last, n), 400, 'L%d' % n))
        out.append((self.PACK + 'Movies/Naruto Shippuden The Movie 02 - Bonds (2008).mkv', 2000, 'M2'))
        return out
    def test_a_season_takes_only_its_folder(self):
        picked = alldebrid.pick(self.files(), 'season', '2')
        self.assertEqual(len(picked), 21)
        self.assertTrue(all('/Season 02 (' in p for p, _, _ in picked))
    def test_sxxeyy_names_win_and_another_season_is_empty(self):
        files = [('Show.S01/Show.S01E%02d.mkv' % n, 300, str(n)) for n in range(1, 11)]
        self.assertEqual(len(alldebrid.pick(files, 'season', '1')), 10)
        self.assertEqual(alldebrid.pick(files, 'season', '3'), [])
    def test_an_unknowable_series_pack_is_refused_not_queued(self):
        files = [('Pack/Episode %03d.mkv' % n, 300, str(n)) for n in range(1, 501)]
        with self.assertRaises(alldebrid.TooMany):
            alldebrid.pick(files, 'season', '1')

class CancelAll(unittest.TestCase):
    def test_every_unfinished_copy_is_cancelled_once(self):
        import transfer_control
        with tempfile.TemporaryDirectory() as tmp:
            debrid_drive.save(tmp, {'jobs': [{'hash': 'AA', 'status': 'copying'}, {'hash': 'bb', 'status': 'new'},
                                             {'hash': 'cc', 'status': 'done'}, {'hash': 'dd', 'status': 'failed'}]})
            self.assertEqual(transfer_control.unfinished_copies(tmp), ['aa', 'bb'])
            self.assertEqual(transfer_control.cancel_all_copies(tmp), 2)
            self.assertEqual(transfer_control.cancelled_copies(tmp), {'aa', 'bb'})
            self.assertEqual(transfer_control.menu('up', {'source': 'debrid', 'hash': 'aa'}, queued=2)[-2],
                             ('Cancel all downloads to Drive (2)', 'cancel_all'))


class RememberShows(unittest.TestCase):
    def test_finished_episode_copies_name_their_show(self):
        seen = []
        jobs = [{'status': 'done', 'kind': 'episode', 'title': 'Phony', 'show_tmdb': '275139',
                 'files': [{'drive_name': 'phony.s01e01.1080p.web.h264-x.mkv'}]},
                {'status': 'copying', 'kind': 'episode', 'title': 'Busy', 'show_tmdb': '1', 'files': []},
                {'status': 'done', 'kind': 'movie', 'title': 'Film', 'show_tmdb': '2', 'files': []},
                {'status': 'done', 'kind': 'season', 'title': 'Old', 'files': []}]
        self.assertTrue(debrid_drive.remember_shows(None, jobs, lambda names, tmdb: seen.append((names, tmdb)) or True))
        self.assertEqual(len(seen), 1)
        names, tmdb = seen[0]
        self.assertEqual(tmdb, '275139')
        self.assertIn('Phony', names)
        self.assertEqual(len(names), 2)


class Wiring(unittest.TestCase):
 def test_download_uses_the_shared_pre_selection_interceptor(self):
  src=(BOOT/'download.py').read_text()
  self.assertIn('dl.follow(url)',src)
  self.assertNotIn('dl.added(',src)
  self.assertNotIn('to_drive(',src)
  hook=(BOOT/'resources/lib/elementum_cloud.py').read_text()
  self.assertIn('watch=mode == 1',hook)
 def test_service_runs_the_queue(self):
  src=(BOOT/'service.py').read_text()
  self.assertIn('debrid_drive.step(profile,alldebrid.AllDebrid(token),drive',src);self.assertIn('threading.Thread(target=debrid_loop,daemon=True).start()',src)
  self.assertIn('prepare_downloads.request_check(profile)',src[src.index('def debrid_loop'):])

class PlayedVersions(unittest.TestCase):
 """Owner (build 160): "Download only or download and watch doesnt appear when i select the source it just starts
 downloading" — a played version kept downloading onto the phone (19.8 GB Fall)."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def test_taken_after_grace_only_while_nothing_plays(self):
  t=[{'id':H,'name':'Fall.2022.2160p.WEB-DL.DV.mkv','progress':12},{'id':'b'*40,'name':'Done.2020.mkv','progress':100}]
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1000),[])        # just appeared (buffering, choosing)
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=True,now=1100),[])         # playing: never, and the clock restarts
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1200),[])
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=1200+debrid_drive.GRACE),[H])
  job=debrid_drive.load(self.p)['jobs'][0]
  self.assertEqual((job['kind'],job['title'],job['hash']),('movie','Fall',H))
  self.assertEqual(debrid_drive.adopt(self.p,t,playing=False,now=5000),[])        # once
 def test_kinds(self):
  self.assertEqual([debrid_drive.kind_of(n) for n in ('Fall.2022.mkv','Lanterns.S01E02.mkv','Lanterns.S01.2160p','Show Season 2 Complete')],
                   ['movie','episode','season','season'])
 def test_service_takes_them_back_from_elementum(self):
  src=(BOOT/'service.py').read_text()
  self.assertIn("debrid_drive.adopt(profile,notices.torrent_list(),xbmc.Player().isPlayingVideo())",src)
  self.assertIn("driveupload.remove_torrent(tid)",src[src.index('def debrid_loop'):])


class OneAtATimeOnTheConnection(unittest.TestCase):
 """Owner (build 168 log): Fall's copy from AllDebrid ran at ~0.2 MB/s while Inception's conversion read and wrote Drive."""
 def test_copying_flag_and_preparation_waits(self):
  import tempfile
  with tempfile.TemporaryDirectory() as p:
   self.assertFalse(debrid_drive.copying(p))
   debrid_drive.save(p,{'jobs':[],'current':{'stage':'copying','sent':1,'total':2}});self.assertTrue(debrid_drive.copying(p))
   debrid_drive.save(p,{'jobs':[],'current':{'stage':'fetching','sent':1,'total':2}});self.assertFalse(debrid_drive.copying(p))
  # build 170: preparation no longer waits for copies (they run at 6-8 MB/s now)
 def test_each_chunk_reports_both_sides(self):
  src=(LIB/'driveupload.py').read_text()
  self.assertIn("MB/s from the source), sent in %.1f s (%.2f MB/s to Google Drive)",src)

if __name__=='__main__':unittest.main()
