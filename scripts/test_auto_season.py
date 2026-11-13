"""Owner (build 205): "cant it automatically pick sources based off my first quality pick? like if i pick 4K hd, then it
can find compatible sources for each episode of that show automatically?"."""
import importlib.util,json,sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
dp=load('deck_picker_auto',ROOT/'migration/deck-picker/deck_picker.py')
sys.modules.setdefault('elementum_download',types.ModuleType('elementum_download'))
sys.modules.setdefault('elementum_engine',types.ModuleType('elementum_engine'))
notes=[];fake_notices=types.ModuleType('notices');fake_notices.note=lambda *a:notes.append(a);sys.modules['notices']=fake_notices
dl=load('download_auto',BOOT/'download.py')

def item(idx,name,quality,size,seeds=50):
 return dict(idx=idx,quality=quality,seeds=seeds,peers=0,size=size,tags_text='',name=name,providers=['x'],icon='',multi=False)

class Home:
 def __init__(self):self.p={}
 def getProperty(self,k):return self.p.get(k,'')
 def setProperty(self,k,v):self.p[k]=v
 def clearProperty(self,k):self.p.pop(k,None)

class Choose(unittest.TestCase):
 want={'quality':'4k','hdr':'HDR10','codec':'HEVC','source':'WEB-DL','size':8.4,'coverage':'Episode 1 only'}
 def test_same_quality_and_hdr_first(self):
  kept=[item(0,'Lanterns.S01E02.1080p.WEB-DL.H264','1080p',2.0,300),item(1,'Lanterns.S01E02.2160p.WEB-DL.HDR10.HEVC','4k',8.0,40),
        item(2,'Lanterns.S01E02.2160p.WEB-DL.AV1','4k',6.0,90),item(3,'Lanterns.S01E02.2160p.WEB-DL.HEVC','4k',8.2,60)]
  self.assertEqual(dp.auto_choose(kept,self.want)['idx'],1)
 def test_lower_quality_when_there_is_no_4k_and_never_a_dead_link(self):
  kept=[item(0,'Lanterns.S01E06.720p.HEVC','720p',1.0),item(1,'Lanterns.S01E06.1080p.HEVC','1080p',2.0),item(2,'Lanterns.S01E06.2160p.HEVC','4k',8.0,0)]
  self.assertEqual(dp.auto_choose(kept,self.want)['idx'],1)
  self.assertIsNone(dp.auto_choose([item(0,'x.2160p','4k',8,0)],self.want))
 def test_the_page_records_a_season_pick_and_its_coverage(self):
  home=Home();dp._CONTEXT['exp']={'kind':'season','season':1,'episode':None}
  dp._note_pick(dict(item(0,'Lanterns.S01E01.2160p.WEB-DL.HDR10.HEVC','4k',8.4),coverage='Episode 1 only'),home)
  pick=json.loads(home.p[dp.SEASON_PICK]);self.assertEqual((pick['quality'],pick['hdr'],pick['coverage']),('4k','HDR10','Episode 1 only'))
  dp._CONTEXT['exp']={'kind':'movie','season':None};home2=Home();dp._note_pick(item(0,'Fall.2022.2160p','4k',8),home2);self.assertEqual(home2.p,{})

class Season(unittest.TestCase):
 def test_what_is_missing(self):
  self.assertEqual(dl.covered('Episodes 1-3 only'),{1,2,3})
  self.assertEqual(dl.missing_episodes([1,2,3,4,5],{4},{'coverage':'Episode 1 only'}),[2,3,5])
  self.assertEqual(dl.missing_episodes([1,2,3],set(),{'coverage':''}),[])   # a full season: nothing else to find
 def test_the_rest_of_the_season_is_queued_in_the_first_picks_quality(self):
  home=Home();home.setProperty(dl.SEASON_PICK,json.dumps({'quality':'4k','hdr':'HDR10','coverage':'Episode 1 only','size':8.4}))
  started=[];requests=[]
  def start(n):
   requests.append(json.loads(home.getProperty(dl.AUTO_PICK)))
   started.append(n)
   home.setProperty(dl.AUTO_RESULT,json.dumps({'found':n!=5,'quality':'1080p' if n==4 else '4k','name':'E%d'%n}))
  class Progress:
   def create(self,*a):pass
   def update(self,*a):pass
   def iscanceled(self):return False
   def close(self):pass
  xbmc=types.SimpleNamespace(Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:False),log=lambda *a:None,LOGINFO=1,LOGWARNING=2)
  gui=types.SimpleNamespace(DialogProgress=Progress,NOTIFICATION_INFO=0)
  asked=[];dialog=types.SimpleNamespace(yesno=lambda h,t,**k:asked.append(t) or True,notification=lambda *a:None)
  results=dl.rest_of_season(xbmc,gui,dialog,home,'Lanterns','1',[1,2,3,4,5],{3},start,now=100)
  self.assertEqual(started,[2,4,5]);self.assertIn('Get the other 3 episodes automatically in the same quality (4K · HDR10)?',asked[0])
  self.assertEqual(requests[0]['profile']['quality'],'4k');self.assertNotIn(dl.AUTO_PICK,home.p)
  heading,text=dl.summary('Lanterns','1',results,'4k')
  self.assertEqual((heading,text),('Lanterns season 1','2 episodes queued in 4K · E04 in 1080p · not found yet: E05'))
 def test_queueing_without_asking_again(self):
  text=(LIB/'elementum_cloud.py').read_text()
  self.assertIn("mode = auto.get('mode', 0) if auto is not None else ask(dialog, 'Save to Google Drive'",text)
  self.assertIn("existing = None if auto is not None else existing_url(profile,choice)",text)

class NeedsNoWork(unittest.TestCase):
 """F5 (PR #24, ISSUE-210): same quality, the file that needs no preparation first; never below the chosen quality."""
 want={'quality':'1080p','strict_quality':True}
 def pick(self,*names,quality='1080p'):
  kept=[item(i,n,quality,2.0+i,50) for i,n in enumerate(names)]
  return dp.auto_choose(kept,self.want)['idx']
 def test_mp4_beats_mkv_of_the_same_quality(self):
  self.assertEqual(self.pick('Show.S01E02.1080p.WEB.x264.mkv','Show.S01E02.1080p.WEB.x264.mp4'),1)
  self.assertEqual(dp.prep_cost(item(0,'Show.S01E02.1080p.x264.m4v','1080p',2))[0],0)
 def test_h264_and_hevc_before_10bit_or_av1(self):
  # H.264 and HEVC pictures are copied as they are (no re-encode), so they cost the same; Hi10P and AV1 are re-encoded.
  names=['Show.S01E02.1080p.AV1.mkv','Show.S01E02.1080p.10bit.x264.mkv','Show.S01E02.1080p.HEVC.mkv','Show.S01E02.1080p.x264.mkv']
  self.assertIn(self.pick(*names),(2,3))
  self.assertEqual(self.pick(*names[:3]),2)
  self.assertEqual(dp.prep_cost(item(0,names[2],'1080p',2)),dp.prep_cost(item(0,names[3],'1080p',2)))
  self.assertEqual(dp.prep_cost(item(0,names[0],'1080p',2))[1],2);self.assertEqual(dp.prep_cost(item(0,names[1],'1080p',2))[1],2)
 def test_a_lower_quality_mp4_never_beats_the_chosen_quality_mkv(self):
  kept=[item(0,'Show.S01E02.720p.x264.mp4','720p',1.0,500),item(1,'Show.S01E02.1080p.HEVC.mkv','1080p',2.0,5)]
  self.assertEqual(dp.auto_choose(kept,{'quality':'1080p'})['idx'],1)

if __name__=='__main__':unittest.main()
