"""Owner (build 160): "Interstellar isnt being transferred ... It needs to be ready for airplay". KodiAirPlay r15 keeps
Blu-ray picture subtitles (PGS) in .sup files beside the prepared MP4; the queue saves them next to the video on Google
Drive (before the video is replaced) and gives videos kept only for that one new try."""
import json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import prepare_downloads as prep

class Names(unittest.TestCase):
 def test_named_after_the_video_as_kodi_looks_for_them(self):
  files=['/w/prepared.mp4.sub4.eng.sup','/w/prepared.mp4.sub3.eng.forced.sup','/w/prepared.mp4.sub5.eng.sup','/w/prepared.mp4.sub6.fre.sup','/w/other.txt']
  self.assertEqual(prep.sidecar_names('Interstellar.2014.2160p.UHD.BluRay.mkv',files),
   [('/w/prepared.mp4.sub3.eng.forced.sup','Interstellar.2014.2160p.UHD.BluRay.eng.forced.sup'),
    ('/w/prepared.mp4.sub4.eng.sup','Interstellar.2014.2160p.UHD.BluRay.eng.sup'),
    ('/w/prepared.mp4.sub5.eng.sup','Interstellar.2014.2160p.UHD.BluRay.eng.2.sup'),
    ('/w/prepared.mp4.sub6.fre.sup','Interstellar.2014.2160p.UHD.BluRay.fre.sup')])

class Drive:
 def __init__(self,existing=()):self.existing=list(existing);self.uploads=[];self.queries=[]
 def call(self,method,url,body=None,headers=None):
  self.queries.append(url)
  return 200,{},json.dumps({'files':self.existing}).encode()
 def upload(self,path,parent,sessions,save,keep_going=lambda:True,progress=None,name=None):
  self.uploads.append((Path(path).name,parent,name));return {'id':'up-%d'%len(self.uploads)}

class Save(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
  (self.folder/'prepared.mp4.sub2.eng.sup').write_bytes(b'P'*10);(self.folder/'prepared.mp4.sub3.spa.sup').write_bytes(b'G'*20)
 def tearDown(self):self.tmp.cleanup()
 def test_each_sup_goes_beside_the_video(self):
  drive=Drive()
  ids=prep.save_sidecars(drive,{'id':'v','name':'Interstellar (2014).mkv','parents':['movies-folder']},self.folder,{},lambda:None,lambda:True)
  self.assertEqual(ids,['up-1','up-2'])
  self.assertEqual(drive.uploads,[('prepared.mp4.sub2.eng.sup','movies-folder','Interstellar (2014).eng.sup'),
                                  ('prepared.mp4.sub3.spa.sup','movies-folder','Interstellar (2014).spa.sup')])
  self.assertIn("%27movies-folder%27%20in%20parents",drive.queries[0])
 def test_one_already_on_drive_is_not_sent_again(self):
  drive=Drive(existing=[{'id':'old','size':'10'}])
  ids=prep.save_sidecars(drive,{'id':'v','name':'Interstellar (2014).mkv','parents':['p']},self.folder,{},lambda:None,lambda:True)
  self.assertEqual(ids[0],'old');self.assertEqual([u[2] for u in drive.uploads],['Interstellar (2014).spa.sup'])
 def test_no_folder_no_upload(self):
  drive=Drive()
  with unittest.mock.patch.object(prep,'metadata',return_value={'parents':[]}):
   with self.assertRaises(RuntimeError):prep.save_sidecars(drive,{'id':'v','name':'x.mkv'},self.folder,{},lambda:None,lambda:True)
  self.assertEqual(drive.uploads,[])
 def test_saved_before_the_video_is_replaced(self):
  source=(ROOT/'migration/bundled-bootstrap/resources/lib/prepare_downloads.py').read_text()
  self.assertLess(source.index('job[\'sidecars\']=save_sidecars('),source.index("job['status']='committing';self.commit()"))
  self.assertIn('trashed,parents',source)

class Fn:
 """A ctypes-like function: callable, with argtypes/restype to set."""
 def __init__(self,f):self.f=f;self.argtypes=None;self.restype=None
 def __call__(self,*a):return self.f(*a)
class Lib:
 def __init__(self,keeps):
  self.calls=[];self.kodi_airplay_prepare=Fn(lambda *a:0);self.kodi_airplay_probe=Fn(lambda *a:0)
  if keeps:self.kodi_airplay_prepare_keep_image_subs=Fn(self.calls.append)

class Switch(unittest.TestCase):
 def test_the_native_switch_is_turned_on_only_when_present(self):
  lib=Lib(True);native=prep.Native(lib);self.assertTrue(native.keeps_image_subs);self.assertEqual(lib.calls,[1])
  self.assertFalse(prep.Native(Lib(False)).keeps_image_subs)
 def test_kept_videos_get_one_new_try(self):
  q=prep.Queue.__new__(prep.Queue);q.commit=lambda:None
  q.native=type('N',(),{'keeps_image_subs':True})()
  q.state={'jobs':{'i':{'source':{'id':'i'},'blocked':True,'status':'failed','error':'This file has tracks MP4 cannot preserve; original retained'},
                   'h':{'source':{'id':'h'},'blocked':True,'status':'failed','error':'This HDR codec cannot be prepared without changing HDR'}}}
  self.assertEqual(q.retry_image_subtitles(),1)
  i=q.state['jobs']['i'];self.assertEqual((i['blocked'],i['status'],i['image_subs_retried']),(False,'waiting',True));self.assertNotIn('error',i)
  self.assertTrue(q.state['jobs']['h']['blocked'])
  i.update(blocked=True,error='This file has tracks MP4 cannot preserve; original retained')   # a DVD subtitle: kept for good
  self.assertEqual(q.retry_image_subtitles(),0)
  q.native=type('N',(),{'keeps_image_subs':False})();q.state['jobs']['i'].pop('image_subs_retried')
  self.assertEqual(q.retry_image_subtitles(),0)
 def test_plain_reason_after_r15(self):
  self.assertEqual(prep.plain('This file has tracks MP4 cannot preserve'),'DVD picture subtitles or a second video track cannot go into MP4')

class Native(unittest.TestCase):
 def test_build_exports_and_ffmpeg_writer(self):
  build=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  self.assertIn('_kodi_airplay_prepare_keep_image_subs',build);self.assertIn("== 13 ]]",build)
  self.assertIn('--enable-muxer=sup',(ROOT/'migration/airplay-ios/build-remux-ffmpeg.sh').read_text())
  self.assertIn("assert b'_kodi_airplay_prepare_keep_image_subs' in binary",(ROOT/'.github/workflows/airplay-ios.yml').read_text())
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('static int keep_image_subs=0;',c)   # off unless the add-on can save them: never silently dropped
  self.assertIn('the .sup file holds every picture subtitle byte',(ROOT/'migration/airplay-ios/remux/tests/test_remux.c').read_text())

import unittest.mock
if __name__=='__main__':unittest.main()
