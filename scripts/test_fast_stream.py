"""Continue resumes an Umbrella title from the link it was playing (owner, build 618: continuing took 15 s because Umbrella ran again)."""
import importlib.util,json,sys,time,unittest
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
sys.path.insert(0,str(LIB))
import ios_continue as c

def store():
    box={'text':'{}'}
    return (lambda location:box['text']),(lambda location,text:box.__setitem__('text',text)),box

def player(tmdb='312359',season='1',episode='1'):
    import types
    return types.SimpleNamespace(tmdb_type='tv',tmdb_id=tmdb,season=season,episode=episode,details=types.SimpleNamespace(infolabels={'title':'The God Who Destroys','tvshowtitle':'Dragon Ball Super: Beerus'},art={'poster':'p.jpg'}))

class Record(unittest.TestCase):
    def test_the_link_is_kept_for_umbrella_titles_only_and_never_the_phones_own_proxy(self):
        read,write,box=store();c.record(player(),read,write,choice='umbrella')
        c.update(read,write,120,1400,stream='http://127.0.0.1:50465/x');self.assertNotIn('stream',json.loads(box['text'])['items']['episode:312359:1:1'])
        c.update(read,write,130,1400,stream='https://dl.example.invalid/f.mkv');entry=json.loads(box['text'])['items']['episode:312359:1:1']
        self.assertEqual(entry['stream']['url'],'https://dl.example.invalid/f.mkv')
        read2,write2,box2=store();c.record(player(),read2,write2,choice='elementum');c.update(read2,write2,5,10,stream='https://x.invalid/a')
        self.assertNotIn('stream',json.loads(box2['text'])['items']['episode:312359:1:1'])
    def test_the_age_is_the_links_age_and_starting_again_keeps_it(self):
        read,write,box=store();c.record(player(),read,write,choice='umbrella')
        c.update(read,write,10,100,now=lambda:1000.0,stream='https://x.invalid/a');c.update(read,write,20,100,now=lambda:5000.0,stream='https://x.invalid/a')
        self.assertEqual(json.loads(box['text'])['items']['episode:312359:1:1']['stream']['at'],1000.0)
        c.record(player(),read,write,choice='umbrella',preserve_player=True)
        self.assertIn('stream',json.loads(box['text'])['items']['episode:312359:1:1'])

class Fast(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('watch_fast2',LIB/'ios_watch_dialog.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def seeded(self,position=300,total=1400,at=1000.0,player_name='umbrella',url='https://dl.example.invalid/f.mkv'):
        read,write,box=store();c.record(player(),read,write,choice=player_name)
        c.update(read,write,position,total,now=lambda:at,stream=url);return read
    PARAMS={'tmdb_type':'tv','tmdb_id':'312359','season':'1','episode':'1','ios_continue':'1'}
    def test_a_fresh_working_link_resumes_without_umbrella(self):
        m=self.load();played=[];read=self.seeded()
        self.assertTrue(m.fast_stream(7,self.PARAMS,read,alive=lambda url:True,play=lambda h,entry,url,pos,total:played.append((h,url,pos,total)),now=lambda:1500.0))
        self.assertEqual(played,[(7,'https://dl.example.invalid/f.mkv',300.0,1400.0)])
    def test_every_reason_to_use_the_normal_way(self):
        m=self.load();never=lambda *a:self.fail('must not play')
        run=lambda read,params=None,**k:m.fast_stream(7,params or self.PARAMS,read,alive=k.get('alive',lambda url:True),play=never,now=k.get('now',lambda:1500.0))
        self.assertFalse(run(self.seeded(),dict(self.PARAMS,ios_continue='0')))           # not started by Continue
        self.assertFalse(run(self.seeded(),dict(self.PARAMS,ios_choose='1')))             # the person asked to choose a source
        self.assertFalse(run(self.seeded(player_name='elementum')))                       # not an Umbrella title
        self.assertFalse(run(self.seeded(),now=lambda:1000.0+m.STREAM_FRESH+1))           # the link is too old
        self.assertFalse(run(self.seeded(),alive=lambda url:False))                       # it no longer answers
        self.assertFalse(run(self.seeded(position=2)))                                    # nothing to resume
        self.assertFalse(run(self.seeded(position=1350)))                                 # finished: the next episode is the normal way
        self.assertFalse(run(self.seeded(),dict(self.PARAMS,episode='2')))                # another episode has no link
    def test_the_fast_copy_door_tries_a_stream_after_a_local_copy(self):
        text=(LIB/'ios_watch_dialog.py').read_text()
        self.assertIn('if _fast_local(handle,params,read_art,find,play,resume):return True\n return fast_stream(handle,params)',text)
    def test_continue_goes_through_the_services_cache_with_the_resume_point(self):
        # Step 2 (owner, build 620 log 80ea6c76): Continue took 12.3 s; Kodi read the debrid link over one connection because Continue skipped Umbrella's cache
        m=self.load();played=[];asked=[];read=self.seeded(position=350,total=1400)
        route=lambda url,resume:(asked.append((url,resume)),'http://127.0.0.1:5555/media')[1]
        self.assertTrue(m.fast_stream(7,self.PARAMS,read,alive=lambda url:True,play=lambda h,entry,url,pos,total:played.append(url),now=lambda:1500.0,route=route))
        self.assertEqual(asked,[('https://dl.example.invalid/f.mkv',0.25)]);self.assertEqual(played,['http://127.0.0.1:5555/media'])
    def test_without_the_cache_the_link_itself_plays(self):
        m=self.load();played=[];read=self.seeded()
        self.assertTrue(m.fast_stream(7,self.PARAMS,read,alive=lambda url:True,play=lambda h,entry,url,pos,total:played.append(url),now=lambda:1500.0,route=lambda url,resume:url))
        self.assertEqual(played,['https://dl.example.invalid/f.mkv'])
        self.assertEqual(m._cache_route('https://dl.example.invalid/f.mkv',0.5),'https://dl.example.invalid/f.mkv')   # no Kodi, no service: unchanged
    def test_the_resume_blocks(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
        import remote_media as rm
        mb=1024*1024
        self.assertEqual(rm.resume_blocks(0.5,400*mb,4*mb),[49,50,51])
        self.assertEqual(rm.resume_blocks(None,400*mb,4*mb),[]);self.assertEqual(rm.resume_blocks(0,400*mb,4*mb),[]);self.assertEqual(rm.resume_blocks(1.2,400*mb,4*mb),[])
        self.assertEqual(rm.resume_blocks(0.999,400*mb,4*mb),[98])   # never the last block (asked for already) or past it
        text=(Path(rm.__file__)).read_text()
        self.assertIn("kwargs={'blocks':OPEN_BLOCKS,'extra':KODI_AHEAD,'resume':resume}",text)
    def test_a_link_check_never_raises_or_logs_the_address(self):
        m=self.load();self.assertFalse(m._link_alive('http://127.0.0.1:9/x|User-Agent=a'))

if __name__=='__main__':unittest.main()
