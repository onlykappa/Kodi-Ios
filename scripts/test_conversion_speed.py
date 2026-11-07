"""Owner (build 168): Inception (AV1 10-bit HDR 4K) stayed at 0% on an iPhone 16 Pro. "add how fast its moving too, and
increase cpu limit to how all other apps operate". app_state.Pace, the live progress line and the r18 HDR hardware path."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
import app_state,prepare_downloads as prep

class Clock:
 def __init__(self):self.t=0.0;self.cpu=0.0;self.slept=[]
 def wall(self):return self.t
 def thread(self):return self.cpu
 def sleep(self,s):self.slept.append(s);self.t+=s

class Pacing(unittest.TestCase):
 def run_pace(self,on_screen):
  c=Clock();p=app_state.Pace(on_screen=lambda:on_screen,cpu_clock=c.thread,clock=c.wall,sleep=c.sleep)
  for _ in range(100):c.t+=0.1;c.cpu+=0.1;p.tick()   # a thread that would use a whole core
  return c
 def test_no_limit_while_kodi_is_on_screen(self):
  self.assertEqual(self.run_pace(True).slept,[])
 def test_background_stays_under_ios_limit(self):
  c=self.run_pace(False)
  self.assertLessEqual(c.cpu/c.t,app_state.BACKGROUND_SHARE+0.01);self.assertGreater(c.cpu/c.t,0.5)
 def test_unknown_state_counts_as_background(self):
  app_state._cache.update(at=-10.0,value=None)
  self.assertFalse(app_state.foreground(clock=lambda:100.0,read=lambda:None))
  app_state._cache.update(at=-10.0)
  self.assertTrue(app_state.foreground(clock=lambda:200.0,read=lambda:app_state.ACTIVE))
  self.assertFalse(app_state.foreground(clock=lambda:300.0,read=lambda:app_state.BACKGROUND))
 def test_both_converters_use_it(self):
  src=(LIB/'prepare_downloads.py').read_text()
  self.assertEqual(src.count('pace=app_state.Pace()'),2);self.assertNotIn('2*cpu-wall',src)

class LiveLine(unittest.TestCase):
 def test_never_a_bare_zero(self):
  self.assertEqual(prep.speed_text(0,0),'')
  self.assertEqual(prep.speed_text(79477322,0),'75 MB read')
  self.assertEqual(prep.speed_text(int(1.2*1024**3),8.4*1024**2),'1.2 GB read · 8.4 MB/s')
  self.assertEqual(prep.live_line({'progress':0,'detail':'75 MB read · 0.4 MB/s'}),' · 75 MB read · 0.4 MB/s')
  self.assertEqual(prep.live_line({'progress':12,'detail':'1.2 GB read · 8.4 MB/s'}),' · 12% · 1.2 GB read · 8.4 MB/s')
  self.assertEqual(prep.live_line({'progress':0}),'')
 def test_speed_over_the_last_seconds(self):
  q=prep.Queue.__new__(prep.Queue)
  reads=iter([0,10*1024**2,30*1024**2])
  q.stream=type('S',(),{'stats':lambda s:{'read_bytes':next(reads)}})()
  self.assertEqual(q.read_speed(0.0),(0,0.0))
  self.assertEqual(q.read_speed(5.0)[1],2*1024**2)
  self.assertEqual(q.read_speed(10.0),(30*1024**2,3*1024**2))

class HardwareHDR(unittest.TestCase):
 def test_r18_passes_decoder_frames_to_the_hevc_encoder(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  self.assertIn('frames->sw_format == AV_PIX_FMT_P010',c)
  self.assertIn('c->pix_fmt=AV_PIX_FMT_VIDEOTOOLBOX;c->sw_pix_fmt=AV_PIX_FMT_P010LE;',c)
  self.assertIn('j->conv = av_frame_clone(fr);',c)
  self.assertIn('hdr_pass_broken = 1',c)
  self.assertLess(c.index('if (!j->enc) j->hdr_pass ='),c.index('if (!j->enc) j->gpu ='))
  self.assertIn('--enable-decoder=av1 --enable-hwaccel=av1_videotoolbox',(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text())

class Build169Log(unittest.TestCase):
 def test_bad_subtitle_packet_skipped_not_fatal(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('if(q==AVERROR_INVALIDDATA || q==AVERROR(EINVAL)){skipped_subs++',c)
 def test_converter_hangups_not_logged_as_errors(self):
  s=(LIB/'drive_stream.py').read_text()
  self.assertIn('def handle_error(self, request, client_address):',s);self.assertIn('ConnectionResetError',s)
 def test_conversion_runs_alongside_downloads(self):
  src=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertNotIn('debrid_drive.copying(profile)',src)

class Build173Log(unittest.TestCase):
 """Build-173 log: no "prepare:" lines in 13 min and the same speed as r19: the phone uses the storage-free path
 (kodi_airplay_prepare_to), which r20 had not changed (6-second units, no timing)."""
 def test_storage_free_path_uses_30_second_units_and_logs(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  # r23: units are made (and noted) by each track's worker thread, generated_note / generated_work.
  reader=c[c.index('static void generated_note'):c.index('typedef struct {\n    kr_prepare_write')]
  self.assertIn('gm_stream_open(kr_source_gm(l->source),PREP_UNIT,err,en)',reader)
  self.assertNotIn('kr_source_gm(l->source),6,',reader)
  self.assertIn('kr_remux_note("prepare: %s %d/%d made in %.1f s',reader);self.assertIn('kr_video_route(l->video)',reader)

class Build170Log(unittest.TestCase):
 """Owner (build 170 log): Inception read ~0.55 MB/s, about a quarter of real time, in 6-second live units."""
 def test_whole_file_units_and_safe_resume(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('#define PREP_UNIT 30',c);self.assertIn('gm_stream_open(kr_source_gm(source),PREP_UNIT,err,en)',c)
  self.assertIn('if(unit_s!=PREP_UNIT){first=0;offset=0;}',c)   # an r19 6-second checkpoint is not misread
  self.assertIn('"%d %lld %d\\n",i+1,offset,PREP_UNIT',c)
 def test_log_says_route_and_speed(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('prepare: %s %d/%d made in %.1f s for %d s of film (%.2fx real time)',c)
  v=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  for route in ('hardware HDR (%s decoder to %s)','GPU path (%s decoder to %s)','CPU path (%s decoder%s, %s)'):self.assertIn(route,v)

class SpeedEverywhere(unittest.TestCase):
 """Owner (build 170 screenshots): "no way for me to see download or upload speed anywhere … the details are blank and
 seem ugly"; the folder tiles had no icons."""
 def test_time_and_video_words(self):
  self.assertEqual(prep.eta_text(0),'');self.assertEqual(prep.eta_text(30),'less than a minute left')
  self.assertEqual(prep.eta_text(300),'about 5 min left');self.assertEqual(prep.eta_text(3*3600+600),'about 3 h 10 min left')
  self.assertEqual(prep.video_text({'codec':'av1','bit_depth':10,'hdr':True,'copy_video':False}),'AV1 10-bit HDR → HEVC (re-encoded)')
  self.assertEqual(prep.video_text({'codec':'hevc','bit_depth':10,'hdr':False,'copy_video':True}),'HEVC 10-bit, copied as it is')
 def test_upload_card_and_details(self):
  import tempfile,notices,debrid_drive,library_rows
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.save(p,{'jobs':[],'current':{'name':'Fall.2.Deadpoint.mkv','folder':'Movies','sent':14.6*1024**3,'total':16.9*1024**3,
                                             'stage':'copying','rate':8.4*1024**2,'eta_s':290}})
   up=notices.uploads(p)[0]
   self.assertIn('8.4 MB/s',up['line']);self.assertIn('about 4 min left',up['line']);self.assertEqual(up['short'],'86% · 8.4 MB/s · about 4 min left')
   view=prep.library_view({},uploads=[up])
   row=view['rows']['downloading'][0];self.assertEqual(row['sub'],'Uploading to Google Drive · 86% · 8.4 MB/s · about 4 min left')
   s=library_rows.details(row,view);facts=dict(s['facts'])
   # Build 177 (approved sheet): the speed lives in the card; the rows say what is left and where it goes.
   self.assertEqual(s['card'],'up');self.assertEqual(s['status'],'Downloading · 86%');self.assertEqual(facts['Downloaded'],'14.6 of 16.9 GB')
   self.assertEqual(facts['Through'],'AllDebrid');self.assertEqual(facts['Saving to'],'Drive › Kodi Downloads › Movies')
   self.assertRegex(facts['Done around'],r'^\d{1,2}:\d\d [AP]M$');self.assertNotIn('On Google Drive',facts)
 def test_converting_sheet_rows(self):
  import library_rows
  row={'state':'preparing','title':'Inception (2010)','pct':24,'size':8.9*1024**3,'film_done':46*60+20,'film_total':148*60,
       'pace':3.8,'eta_s':1620,'out_total':5.2*1024**3,'probe':{'width':3840,'height':1600,'hdr':True}}
  s=library_rows.details(row,{'free':0});facts=dict(s['facts'])
  self.assertEqual((s['status'],s['tone'],s['card']),('Converting for Apple TV · 24%','conv','conv'))
  self.assertEqual([f[0] for f in s['facts']],['Done so far','Ready around','Pace','Picture','Size'])
  self.assertEqual(facts['Done so far'],'46 of 148 min of the film');self.assertEqual(facts['Pace'],'3.8× faster than the film plays')
  self.assertEqual(facts['Picture'],'4K HDR, kept as 4K HDR');self.assertEqual(facts['Size'],'8.9 GB now · about 5.2 GB after')
  self.assertEqual((s['bar'],s['bar_tint']),('24','FFBF5AF2'))
  early=library_rows.details(dict(row,pct=0,film_done=None,film_total=None,pace=None,eta_s=0,out_total=0,probe=None),{'free':0})
  self.assertEqual(dict(early['facts'])['Done so far'],'starting');self.assertEqual(dict(early['facts'])['Ready around'],'working it out')
  self.assertEqual(early['bar'],'');self.assertNotIn('Pace',dict(early['facts']))
  self.assertIn('<control type="progress" id="9210">',(LIB/'library_page.py').read_text())
 def test_ready_sheet(self):
  import library_rows,time
  now=time.time()
  row={'state':'ready','title':'Fall 2','size':16.9*1024**3,'folder':'Movies','sub':'4K','probe':{'width':3840,'hdr':True},
       'completed':now-60,'started_at':now-60-41*60}
  s=library_rows.details(row,{'free':0});facts=dict(s['facts'])
  self.assertEqual(s['actions'],[('Play','play'),('Play on TV','tv')]);self.assertEqual(s['card'],'')
  self.assertEqual(facts['Picture'],'4K HDR');self.assertEqual(facts['Made ready'],'Today · took 41 min');self.assertEqual(facts['Size'],'16.9 GB')
 def test_live_card(self):
  import library_rows,transfer_history as th
  d={}
  for i in range(0,60,2):th.track(d,1000+i,{'conv':{'title':'Inception (2010)','rate':7*1024**2,'extra':{'eta':'about 27 min left'}}})
  props,pts=library_rows.card(d,'conv','Inception (2010)',1060)
  self.assertEqual((props['card.now'],props['card.left']),('7.0 MB/s','about 27 min'));self.assertGreater(len(pts),1)
  props,pts=library_rows.card(d,'conv','Interstellar (2014)',1060);self.assertEqual((props['card.now'],pts),('starting',[]))
 def test_cloud_progress_records_speed_and_folder_icons_resolve(self):
  self.assertIn("detail=prep.speed_text(*speed),eta=eta,eta_s=eta_s",(LIB/'prepare_cloud.py').read_text())
  self.assertIn("p.ICONS + '$INFO[ListItem.Property(icon)]'",(LIB/'library_page.py').read_text())

class Build175Log(unittest.TestCase):
 """Build-175 log: per 30 s of Inception the video took 37 s on the phone's hardware and each of its two audio tracks
 23 s more, one after another, every track reading the whole file from Drive; and each video played restarted the
 movie from 0% (owner: "this needs to be fixed for ... All movies")."""
 def test_tracks_are_made_at_the_same_time(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('pthread_create(&l->thread,NULL,generated_work,l)',c)
  self.assertIn('if(l->started)pthread_join(l->thread,NULL);',c.split('static void generated_close')[1][:900])
  read=c.split('static int generated_read(')[1].split('static void generated_close')[0]
  self.assertNotIn('kr_video_unit',read);self.assertNotIn('kr_audio_unit',read)   # only the worker makes units
  self.assertIn('kr_video_unit',c.split('static void *generated_work(')[1][:2000])
 def test_drive_is_read_once_in_blocks(self):
  s=(LIB/'drive_stream.py').read_text()
  self.assertIn('class _Blocks',s);self.assertIn('stream.blocks.ahead(item, index + 1)',s)
 def test_a_video_playing_pauses_instead_of_stopping(self):
  import prepare_downloads as prep,types,time as clock
  from unittest.mock import patch
  calls=[];state={'playing':False}
  def prepare_to(source,writer,ctx,callback,cctx,error,size):
   for n in range(6):
    if n==2:state['playing']=True
    if n==4:state['playing']=False
    if not callback(0,n,6,None):return -2
    calls.append(n)
   return 0
  lib=types.SimpleNamespace(kodi_airplay_prepare=lambda *a:0,kodi_airplay_probe=lambda *a:0,kodi_airplay_prepare_to=prepare_to,
                            kodi_airplay_verify=lambda *a:0)
  native=prep.Native(lib);waits=[]
  sleeps=[]
  def fake_sleep(s):
   sleeps.append(s)
   if len(sleeps)>=3:state['playing']=False   # the video ends after a few seconds
  with patch.object(prep.time,'sleep',fake_sleep),patch.object(prep.app_state,'Pace',lambda:types.SimpleNamespace(tick=lambda:None)):
   native.convert_to('src',types.SimpleNamespace(write=lambda *a:None),lambda:not state['playing'],lambda *a:None,
                     paused=lambda:state['playing'],waiting=lambda:waits.append(1))
  self.assertEqual(calls,[0,1,2,3,4,5]);self.assertTrue(waits)   # held, then carried on: nothing thrown away
  # A real stop (Prepare next, Kodi closing) still stops it.
  state['playing']=False;stopped={'v':False}
  def prepare_to2(source,writer,ctx,callback,cctx,error,size):
   stopped['v']=True
   return 0 if callback(0,0,1,None) else -2
  lib.kodi_airplay_prepare_to=prepare_to2;native.lib=lib
  with patch.object(prep.app_state,'Pace',lambda:types.SimpleNamespace(tick=lambda:None)):
   with self.assertRaises(prep.driveupload.Stop):
    native.convert_to('src',None,lambda:False,lambda *a:None,paused=lambda:False)
 def test_the_service_and_upload_wait_through_playback(self):
  svc=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('preparation.paused=lambda:(not monitor.abortRequested() and xbmc.Player().isPlayingVideo()',svc)
  cloud=(LIB/'prepare_cloud.py').read_text()
  self.assertIn('drive_prepare.Sink(q.drive,parent,slot,lambda:keep_going() or paused(),on_file)',cloud)
  self.assertIn('converted_progress,paused,waiting)',cloud)

class AV1Speed(unittest.TestCase):
 """Owner: "we need a way to really boost speed for av1". r24: the HEVC encoder favours speed during preparation, and a
 picture decoded by the hardware is made in two lanes (units 1, 3, 5... and 2, 4, 6...), taken in order."""
 def test_encoder_prioritises_speed_for_preparation(self):
  v=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  hevc=v.split('if(!strcmp(codec->name,"hevc_videotoolbox")) {')[1].split('}')[0]
  self.assertIn('if(v->offline)av_opt_set_int(c->priv_data,"prio_speed",1,0);',hevc)
 def test_two_lanes_in_order(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('#define VIDEO_LANES 2',c);self.assertIn('if(kr_video_hw_decode(first->video))g->nlanes=VIDEO_LANES;',c)
  self.assertIn('int li=g->segment%g->nlanes;generated_lane *l=g->lanes[li];',c)
  self.assertIn('if(r>=0 && l->next_segment!=g->segment)r=-1;',c)
  self.assertIn('for(int segment=l->first;;segment+=l->stride)',c)
  t=(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text()
  self.assertIn('setenv("KR_PREP_LANES","2",1);',t)

class Build178Log(unittest.TestCase):
 """Build-178 log: ~2.5x real time; at 15:59 Kodi left the screen, VideoToolbox refused a unit and that lane stayed
 on the CPU (0.75x); Transfers showed 0.0 MB/s before the first 32 MB piece was up. Owner: keep our audio only."""
 def test_hardware_decoding_is_asked_again_each_unit(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  self.assertIn('v->want_hw = v->hw != NULL;',c)
  block=c[c.index('if (v->offline) {'):c.index('seek_before(v, start);\n    avcodec_flush_buffers(v->dec);')]
  self.assertIn('} else if (!software && v->want_hw && !v->hw) {',block)
  self.assertIn('open_decoder(v, 1, e2, sizeof e2) < 0 && open_decoder(v, 0, err, errlen) < 0',block)
  self.assertIn('hdr_pass_broken = 0;',block)
 def test_audio_language_rule_and_export(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('if(p->codec_type==AVMEDIA_TYPE_AUDIO && !keep_audio(original,i))continue;',c)
  self.assertIn('(p->codec_type==AVMEDIA_TYPE_AUDIO && keep_audio(original,i))',c)   # verify counts the same tracks
  b=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('_kodi_airplay_prepare_audio_languages',b);self.assertIn("== 20 ]]",b)
 def test_language_codes(self):
  self.assertEqual(prep.audio_languages('English','resource.language.en_gb'),'en,eng')
  self.assertEqual(prep.audio_languages('original','resource.language.de_de'),'de,ger,deu')
  self.assertEqual(prep.audio_languages('mediadefault','resource.language.en_us'),'en,eng')
  self.assertEqual(prep.audio_languages('','resource.language.xx_yy'),'')
 def test_native_passes_languages(self):
  calls=[]
  class F:
   def __init__(s):s.argtypes=None;s.restype=None
   def __call__(s,v):calls.append(v)
  n=prep.Native.__new__(prep.Native);n.filters_audio=True;n.lib=type('L',(),{'kodi_airplay_prepare_audio_languages':F()})()
  n.set_audio_languages('en,eng');self.assertEqual(calls,[b'en,eng'])
  self.assertIn('native.set_audio_languages(languages)',(ROOT/'migration/bundled-bootstrap/service.py').read_text())
 def test_background_pace_counts_the_whole_app(self):
  import app_state
  self.assertIs(app_state.Pace(on_screen=lambda:False).cpu_clock,app_state.time.process_time)
 def test_starting_instead_of_zero(self):
  sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap'));import transfers,transfer_history as th,library_rows,time as _t
  now=_t.time();d=th.track({},now,{'conv':{'title':'Inception (2010)','rate':0}})
  self.assertEqual(transfers.page_state(d,now,'conv',[])[0]['now'],'Starting…')
  self.assertEqual(library_rows.card(d,'conv','Inception (2010)',now)[0]['card.now'],'Starting…')
  import drive_prepare
  t=[0.0];sink=drive_prepare.Sink(None,'p','x',lambda:True,background=False,clock=lambda:t[0])
  sink.tracks[0]=dict(url='u',offset=0,buffer=bytearray(),md5=__import__('hashlib').md5(),name='x',chunk=1<<40)
  for i in range(6):t[0]=i*1.0;sink.write(0,'.mp4',b'x'*1000)
  self.assertAlmostEqual(sink.made_rate(),1000.0)

class Build178Freeze(unittest.TestCase):
 """Build-178 log, 15:59 to 16:19: a VideoToolbox unit started at 15:59:00 never finished after Kodi left the screen at
 15:59:05; the muxer waited for it in order, so nothing was read, made or uploaded for 20 min, even back on screen."""
 def test_a_stuck_unit_is_made_again(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  read=c[c.index('static int generated_read('):c.index('static void generated_close(')]
  self.assertIn('pthread_cond_timedwait(&h->cond,&h->lock,&until);',read)
  self.assertIn('if(t-g->seen_at[li]<stall_seconds())continue;',read)
  self.assertIn('l->dead=1;h->abandoned++;',read);self.assertIn('kr_video_software_next(fresh->video);',read)
  self.assertIn('#define STALL_S 90',c)
  close=c[c.index('static void generated_close('):c.index('static int generated_open(')]
  self.assertIn('if(!keep){pthread_mutex_destroy(&h->lock);',close)   # a stuck lane keeps the hub alive
  t=(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text()
  self.assertIn('setenv("KR_PREP_STALL_UNIT","0",1);',t);self.assertIn('made no progress for 3 s; making it again',t)
 def test_background_decodes_on_the_cpu_and_the_add_on_says_when(self):
  v=(ROOT/'migration/airplay-ios/remux/src/kr_video.c').read_text()
  self.assertIn('int software = atomic_load(&prepare_background) || v->soft_next;',v)
  self.assertIn('atomic_fetch_add(&v->frames, 1);',v)
  p=(LIB/'prepare_downloads.py').read_text()
  self.assertIn('self.lib.kodi_airplay_prepare_background(int(off))',p)
  self.assertIn('_kodi_airplay_prepare_background',(ROOT/'migration/airplay-ios/build-airplay.sh').read_text())

class StartNow(unittest.TestCase):
 """Owner (build 178): a third choice, "Start converting now", that overrides the conversion running."""
 def setUp(self):
  import tempfile
  self.tmp=tempfile.TemporaryDirectory();p=self.tmp.name
  prep.save(p,{'jobs':{'a':{'source':{'id':'inc','name':'Inception.2010.mkv'},'status':'waiting'},
                       'b':{'source':{'id':'int','name':'Interstellar.2014.mkv'},'status':'waiting'}},
               'current':{'title':'Inception.2010.mkv','running':True}})
 def tearDown(self):self.tmp.cleanup()
 def test_only_start_now_or_keeping_the_running_one_stops_it(self):
  p=self.tmp.name
  self.assertEqual(prep.running_id(prep.load(p)),'inc')
  prep.request(p,'next','int');self.assertFalse(prep.interrupts(p))   # Prepare next waits its turn
  prep.request(p,'keep','int');self.assertFalse(prep.interrupts(p))   # keeping another one does not stop this one
  prep.request(p,'now','int');self.assertTrue(prep.interrupts(p))
 def test_keep_on_the_running_one_stops_it(self):
  p=self.tmp.name;prep.request(p,'keep','inc');self.assertTrue(prep.interrupts(p))
 def test_start_now_goes_first(self):
  state=prep.load(self.tmp.name)
  prep.apply_to(state,[{'action':'next','id':'inc'},{'action':'now','id':'int'}],5000)
  self.assertGreater(state['jobs']['b']['priority'],state['jobs']['a']['priority'])

if __name__=='__main__':unittest.main()
