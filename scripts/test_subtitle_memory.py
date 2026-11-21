"""A downloaded subtitle stays on for its video, and an embedded track that would show nothing is not shown as "on" (owner, build 634 log f75957fe)."""
import io,os,struct,sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import mp4_tracks as mt,subtitle_memory as sm
sys.path.insert(0,str(ROOT/'scripts'))
from test_mp4_tracks import box,trak,moof,mfra

def labels(**k):return lambda name:k.get(name.replace('VideoPlayer.',''),'')

class Identity(unittest.TestCase):
    def test_a_video_is_its_episode_or_its_film_or_its_file(self):
        self.assertEqual(sm.identity(labels(TVShowTitle='Lanterns',Season='1',Episode='3')),'tv|lanterns|1|3')
        self.assertEqual(sm.identity(labels(Title='Heat',Year='1995')),'film|heat|1995')
        self.assertEqual(sm.identity(labels(),'http://127.0.0.1:61229/drive/ID/Show.S01E03.mp4?x=1|User-Agent=K'),'file|show.s01e03.mp4');self.assertEqual(sm.identity(labels(),''),'')
class Memory(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.addCleanup(__import__('shutil').rmtree,self.dir,True)
    def file(self,name='a.srt'):
        p=os.path.join(self.dir,name);open(p,'w').write('1\n');return p
    def test_remember_recall_forget(self):
        p=self.file();self.assertTrue(sm.remember(self.dir,'tv|x|1|1',p,'a.srt','en'))
        self.assertEqual(sm.recall(self.dir,'tv|x|1|1')['path'],p);self.assertIsNone(sm.recall(self.dir,'tv|x|1|2'))
        os.remove(p);self.assertIsNone(sm.recall(self.dir,'tv|x|1|1'))      # a file that is gone is not offered
        self.assertFalse(sm.remember(self.dir,'',p,'','') or sm.remember(self.dir,'k','/missing.srt','',''))
        p=self.file('b.srt');sm.remember(self.dir,'k',p,'','');sm.forget(self.dir,'k');self.assertIsNone(sm.recall(self.dir,'k'))
    def test_the_oldest_beyond_the_limit_go_with_their_files(self):
        clock=[1000]
        for n in range(sm.KEEP+3):
            clock[0]+=1;sm.remember(self.dir,'k%d'%n,self.file('f%d.srt'%n),'','',lambda:clock[0])
        self.assertIsNone(sm.recall(self.dir,'k0'));self.assertIsNotNone(sm.recall(self.dir,'k%d'%(sm.KEEP+2)));self.assertFalse(os.path.exists(os.path.join(self.dir,'f0.srt')))
class Start(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.addCleanup(__import__('shutil').rmtree,self.dir,True);self.did=[];self.logs=[]
    def run_start(self,current,zero):
        return sm.at_start(self.dir,labels(TVShowTitle='Lanterns',Season='1',Episode='3'),'',lambda p:self.did.append(('set',p)),lambda on:self.did.append(('show',on)),lambda:current,lambda i:zero,self.logs.append)
    def test_a_remembered_download_goes_back_on(self):
        p=os.path.join(self.dir,'a.srt');open(p,'w').write('x');sm.remember(self.dir,'tv|lanterns|1|3',p,'a.srt','en')
        self.assertEqual(self.run_start((True,1,False),True),'remembered');self.assertEqual(self.did,[('set',p),('show',True)]);self.assertIn('on again',self.logs[0])
    def test_an_embedded_track_with_cues_of_no_length_is_turned_off(self):
        self.assertEqual(self.run_start((True,1,False),True),'off');self.assertEqual(self.did,[('show',False)])
    def test_everything_else_is_left_alone(self):
        for current,zero in (((True,1,False),False),((True,1,False),None),((False,1,False),True),((True,3,True),True)):   # fine cues, unknown, already off, the viewer's own file
            self.did.clear();self.assertEqual(self.run_start(current,zero),'left');self.assertEqual(self.did,[])
class Probe(unittest.TestCase):
    """mp4_tracks.zero_length and probe on a synthetic fragmented file shaped like the Lanterns' copy: text cues of no length."""
    def build(self,text_len):
        head=box(b'ftyp',b'isom'+bytes(8))+box(b'moov',trak(1,b'vide',b'hvc1')+trak(3,b'sbtl',b'tx3g','eng')+box(b'mvex',box(b'trex',bytes(24))))
        pad=box(b'mdat',bytes(1100000))
        # three fragments: a text cue (18 bytes), a blank (2 bytes), again; durations in ms (timescale 1000)
        frags=[];
        for n in range(3):
            base=n*9000
            frags.append(moof({1:(base,[(1000,100)]*9),3:(base,[(text_len,18),(9000-text_len,2)])}))
        body=head+pad;offsets=[]
        for f in frags:offsets.append(len(body));body+=f
        index=mfra({1:[(n*9000,o) for n,o in enumerate(offsets)],3:[(n*9000,o) for n,o in enumerate(offsets)]})
        return body+index
    def opener(self,data):
        class R(io.BytesIO):
            def __init__(s,b,total,a,z):super().__init__(b);s.headers={'Content-Range':'bytes %d-%d/%d'%(a,z,total)}
            def __enter__(s):return s
            def __exit__(s,*a):return False
        def open_(request,timeout):
            a,z=map(int,request.get_header('Range')[6:].split('-'));z=min(z,len(data)-1);return R(data[a:z+1],len(data),a,z)
        return open_
    def test_cues_with_no_length_are_found_and_normal_ones_are_not(self):
        bad=mt.probe('http://127.0.0.1:1/x.mp4',self.opener(self.build(0)))
        self.assertEqual([(t['id'],t['zero_length']) for t in bad['tracks']],[(3,True)])
        good=mt.probe('http://127.0.0.1:1/x.mp4',self.opener(self.build(3000)));self.assertEqual([(t['id'],t['zero_length']) for t in good['tracks']],[(3,False)])
    def test_unreadable_files_give_none(self):
        self.assertIsNone(mt.probe('http://127.0.0.1:1/x.mp4',lambda r,timeout:(_ for _ in ()).throw(OSError('no'))))
        self.assertFalse(mt.zero_length([]));self.assertFalse(mt.zero_length([(0,0,18)]))   # one cue is too little to say
class Wiring(unittest.TestCase):
    def test_the_pieces_are_connected(self):
        t=(ROOT/'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn("special://profile/addon_data/service.kodi.ios.bootstrap/subtitles/",t);self.assertNotIn("special://temp/kodiios-subtitles",t)
        self.assertIn('subtitle_memory.remember(folder,',t);self.assertIn('subtitle_memory.forget(folder,',t);self.assertIn('mp4_tracks.zero_length(raw[t[',t)
        p=(ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn('on_start=subtitles_back',p);self.assertIn('subtitle_memory.at_start(root,',p);self.assertIn('if on_start:',p)
class UmbrellaKey(unittest.TestCase):   # build 646 log d8f39741: an Umbrella stream's labels say only "Episode 8"
    def label(self,**v):return lambda name:v.get(name,'')
    def test_continue_watching_gives_the_key_when_the_labels_lack_the_show(self):
        import json,time
        data=json.dumps({'current':'k','items':{'k':{'kind':'episode','title':'Episode 8','tvshowtitle':'Black Clover','season':'2','episode':'8','played':time.time()}}})
        known=sm.known_from(lambda path:data,'Episode 8')
        self.assertEqual(known,{'show':'Black Clover','season':'2','episode':'8'})
        label=self.label(**{'VideoPlayer.Title':'Episode 8','VideoPlayer.Year':'2017'})
        self.assertEqual(sm.identity(label,'http://x/a.mkv',known),'tv|black clover|2|8')
        self.assertEqual(sm.identity(label,'http://x/a.mkv'),'film|episode 8|2017')   # without it: what filed every show's "Episode 8" together
    def test_another_title_an_old_entry_or_a_movie_gives_nothing(self):
        import json,time
        entry={'kind':'episode','title':'Episode 8','tvshowtitle':'Black Clover','season':'2','episode':'8','played':time.time()}
        for e,title in ((entry,'Other'),(dict(entry,played=time.time()-7*3600),'Episode 8'),(dict(entry,kind='movie'),'Episode 8')):
            self.assertEqual(sm.known_from(lambda path,e=e:json.dumps({'current':'k','items':{'k':e}}),title),{})
        self.assertEqual(sm.known_from(lambda path:1/0,'x'),{})
    def test_kodis_own_labels_win(self):
        label=self.label(**{'VideoPlayer.TVShowTitle':'Show','VideoPlayer.Season':'1','VideoPlayer.Episode':'2'})
        self.assertEqual(sm.identity(label,'',{'show':'Other','season':'9','episode':'9'}),'tv|show|1|2')

if __name__=='__main__':unittest.main()
