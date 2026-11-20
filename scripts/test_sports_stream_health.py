"""Sports source checking and ranking (owner, 2026-11-20): a tapped source is verified by what is really playing, a dead one is skipped
automatically, and what worked before decides the order."""
import json,sys,tempfile,unittest,os
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_stream_health as H
import sports_loop_router as router

class WatchTests(unittest.TestCase):
 def run_watch(self,positions,step=.5,stats=None):
  w=H.Watch();verdict='wait';t=0
  for position in positions:
   verdict=w.feed(t,position,stats or {'height':720});t+=step
   if verdict!='wait':break
  return verdict,w
 def test_a_stream_that_moves_in_real_time_is_good_after_the_observation(self):
  verdict,w=self.run_watch([i*.5 for i in range(40)])
  self.assertEqual(verdict,'good');self.assertEqual(w.stats['height'],720)
 def test_it_is_not_good_before_the_picture_has_been_seen_for_a_few_seconds(self):
  verdict,_=self.run_watch([i*.5 for i in range(6)]);self.assertEqual(verdict,'wait')
 def test_a_stream_that_freezes_after_starting_is_bad(self):
  verdict,w=self.run_watch([0,.5,1,1.5,2]+[2]*40)
  self.assertEqual(verdict,'bad');self.assertIn('froze',w.reason)
 def test_a_starved_stream_that_crawls_is_bad(self):
  verdict,w=self.run_watch([i*.1 for i in range(80)])   # 0.2 s of picture per second
  self.assertEqual(verdict,'bad');self.assertIn('slow',w.reason)
 def test_a_clock_that_never_moves_is_bad_eventually(self):
  verdict,w=self.run_watch([0]*60);self.assertEqual(verdict,'bad');self.assertIn('never',w.reason)
 def test_unreadable_clock_just_waits(self):
  w=H.Watch();self.assertEqual(w.feed(0,None),'wait')

class StatsTests(unittest.TestCase):
 def test_labels_are_read_and_blank_ones_are_zero(self):
  labels={'Player.Process(videoheight)':'1,080','Player.Process(videofps)':'29.97','VideoPlayer.VideoBitrate':''}
  stats=H.read_stats(lambda label:labels.get(label,''))
  self.assertEqual((stats['height'],stats['fps'],stats['kbps']),(1080,29,0))
  self.assertEqual(H.describe(stats),'1080p 29 fps')
 def test_a_failing_label_reader_never_raises(self):
  def boom(label):raise RuntimeError('no player')
  self.assertEqual(H.read_stats(boom)['height'],0)

class HealthTests(unittest.TestCase):
 def make(self):
  self.now=[10000.0];return H.Health(None,lambda:self.now[0])
 def test_a_recent_failure_ranks_below_a_recent_success(self):
  h=self.make();h.ok('Crew A',{'height':720});self.now[0]+=5;h.fail('Crew B','froze')
  self.assertEqual(h.order(['Crew B','Crew A'],key=lambda x:x),['Crew A','Crew B'])
 def test_sharper_and_higher_bitrate_wins_between_two_that_worked(self):
  h=self.make();h.ok('Crew A',{'height':480});h.ok('Crew B',{'height':1080,'kbps':5000})
  self.assertEqual(h.order(['Crew A','Crew B'],key=lambda x:x)[0],'Crew B')
 def test_unknown_sources_keep_their_given_order(self):
  h=self.make();self.assertEqual(h.order(['x','y','z'],key=lambda v:v),['x','y','z'])
 def test_the_tapped_source_leads_unless_it_is_known_dead(self):
  h=self.make();h.ok('Crew A');h.ok('Crew B');self.now[0]+=5
  self.assertEqual(h.order(['Crew A','Crew B'],key=lambda x:x,first='Crew B')[0],'Crew B')
  h.fail('Crew B','froze')
  self.assertEqual(h.order(['Crew A','Crew B'],key=lambda x:x,first='Crew B'),['Crew A','Crew B'])
 def test_a_failure_fades_and_a_later_success_clears_dead(self):
  h=self.make();h.fail('Crew A');self.assertTrue(h.dead('Crew A'))
  self.now[0]+=3600;self.assertFalse(h.dead('Crew A'))
  h.fail('Crew A');self.now[0]+=10;h.ok('Crew A');self.assertFalse(h.dead('Crew A'))
 def test_it_persists_only_labels_and_numbers(self):
  with tempfile.TemporaryDirectory() as folder:
   path=os.path.join(folder,'x','health.json');h=H.Health(path);h.ok('Crew A',{'height':720,'kbps':2400});h.fail('Crew B','froze for 6 s')
   text=Path(path).read_text();self.assertNotIn('http',text)
   again=H.Health(path);self.assertEqual(again.data['Crew A']['height'],720);self.assertEqual(again.data['Crew B']['fail'],1)
 def test_a_corrupt_file_starts_empty(self):
  with tempfile.TemporaryDirectory() as folder:
   path=os.path.join(folder,'h.json');Path(path).write_text('{not json');self.assertEqual(H.Health(path).data,{})

def src(name,path,quality=''):
 return {'addon':name,'quality':quality,'play':json.dumps({'e':'TheCrewRoute','l':{'address':'plugin://plugin.video.thecrew/?action=play&url='+path}})}

class Queue(unittest.TestCase):
 def test_a_tap_plays_that_source_first_then_the_games_other_sources(self):
  a,b,c=src('Crew A','a'),src('Crew B','b'),src('Crew C','c')
  chosen=router.tapped_source(b,[a,b,c])
  self.assertEqual([q['addon'] for q in chosen['native_queue']],['Crew B','Crew A','Crew C']);self.assertTrue(chosen['native_pinned'])
 def test_the_pin_reaches_the_script_that_plays(self):
  import sports_jet
  props={};home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''))
  a,b=src('Crew A','a'),src('Crew B','b');launched=[]
  sports_jet.play_request(router.tapped_source(b,[a,b]),lambda s:None,home,lambda *x:launched.append(x))
  payload=json.loads(props[sports_jet.PLAY+launched[0][-1]]);self.assertTrue(payload['native_pinned']);self.assertEqual(len(payload['native_queue']),2)
 def test_a_tap_in_the_game_page_goes_through_the_queue(self):
  text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/sports_game.py').read_text()
  self.assertIn('self.start_play(sports_loop_router.tapped_source(source,every))',text)
 def test_a_non_native_source_is_left_alone(self):
  s={'addon':'Independent','play':'x'};self.assertIs(router.tapped_source(s,[s]),s)

class Scenario(unittest.TestCase):
 """The router with a scripted Kodi: each choice is 'good', 'stall' (plays 2 s, then freezes), 'dead' (open error) or 'silent' (nothing)."""
 def run_queue(self,behaviours,pinned=False,health=None,names=None):
  state={'now':0.0,'log':[],'order':[],'cur':None,'t0':0.0,'stops':0,'entries':[]};logs=[];props={}
  names=names or ['Crew %s'%chr(65+i) for i in range(len(behaviours))]
  by_address={'plugin://plugin.video.thecrew/?action=play&url='+n[-1].lower():b for n,b in zip(names,behaviours)}
  class Player:
   def play(self,playlist,**kw):
    address=state['entries'][-1];state['cur']=by_address[address];state['order'].append(address);state['t0']=state['now'];state['avs']=False;state['player']=self
   def isPlayingVideo(self):return state['cur'] in ('good','stall') and state['now']-state['t0']>=.4
   def getTime(self):
    t=state['now']-state['t0']-.4
    return min(t,2.0) if state['cur']=='stall' else max(t,0)
   def stop(self):
    if state.get('player') is not None and type(self) is not Player:state['stops']+=1
    state['cur']=None
  class Playlist:
   def clear(self):state['entries']=[]
   def add(self,address,item):state['entries'].append(address)
   def getposition(self):return 0
   def size(self):return len(state['entries'])
  def sleep(ms):
   state['now']+=ms/1000;p=state.get('player')
   if p is None or state['cur'] is None:return
   if state['cur'] in ('good','stall') and state['now']-state['t0']>=.4 and not state['avs']:state['avs']=True;p.onPlayBackStarted();p.onAVStarted()
   if state['cur']=='dead' and not state.get('errored_'+str(len(state['order']))):state['errored_'+str(len(state['order']))]=True;p.onPlayBackError()
  info=lambda label:{'Player.Process(videoheight)':'720','Player.Process(videofps)':'30'}.get(label,'')
  backend=NS(Player=Player,PlayList=lambda _:Playlist(),PLAYLIST_VIDEO=1,sleep=sleep,executebuiltin=lambda v:None,getInfoLabel=info,
             Monitor=lambda:NS(abortRequested=lambda:False),getCondVisibility=lambda cond:False)
  home=NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
  gui=NS(ListItem=lambda **kw:NS(setProperty=lambda *a:None),Window=lambda ident:home)
  queue=[src(n,n[-1].lower()) for n in names]
  health=health or H.Health(None,lambda:state['now']+10000)
  with patch.dict(sys.modules,{'xbmcgui':gui}),patch.object(router.routes,'prepare_proxy'):
   try:result=router.play(queue,logs.append,backend,lambda:state['now'],timeout=90,pinned=pinned,health=health,info=info)
   except Exception as error:result=error
  return result,state,logs,health
 def test_a_good_first_source_is_checked_then_recorded(self):
  result,state,logs,health=self.run_queue(['good','good'])
  self.assertTrue(result);self.assertEqual(len(state['order']),1)
  self.assertTrue(any('Crew A is playing (720p 30 fps)' in l for l in logs));self.assertEqual(health.data['Crew A']['height'],720)
 def test_a_source_that_freezes_after_starting_is_replaced_by_the_next_automatically(self):
  result,state,logs,health=self.run_queue(['stall','good'])
  self.assertTrue(result);self.assertEqual(len(state['order']),2)
  self.assertTrue(any('Crew A is not usable (the picture froze' in l for l in logs))
  self.assertTrue(health.dead('Crew A'));self.assertFalse(health.dead('Crew B'))
 def test_a_dead_link_then_a_frozen_one_then_a_good_one(self):
  result,state,logs,health=self.run_queue(['dead','stall','good'])
  self.assertTrue(result);self.assertEqual(len(state['order']),3)
 def test_a_source_that_never_answers_is_dropped_after_the_first_picture_limit(self):
  result,state,logs,health=self.run_queue(['silent','good'])
  self.assertTrue(result);self.assertEqual(len(state['order']),2)
  self.assertTrue(any('showed no picture' in l for l in logs))
 def test_when_every_source_is_dead_it_says_so(self):
  result,state,logs,health=self.run_queue(['dead','dead'])
  self.assertIsInstance(result,RuntimeError);self.assertIn('exhausted',str(result))
 def test_a_source_that_died_before_is_tried_after_one_that_worked(self):
  clock=[10000.0];health=H.Health(None,lambda:clock[0]);health.fail('Crew A','froze');health.ok('Crew B',{'height':720})
  result,state,logs,_=self.run_queue(['good','good'],health=health)
  self.assertTrue(result);self.assertTrue(state['order'][0].endswith('b'))
  self.assertTrue(any('source order from what worked before' in l for l in logs))
 def test_the_tapped_source_leads_even_against_a_better_record_but_not_when_dead(self):
  clock=[10000.0];health=H.Health(None,lambda:clock[0]);health.ok('Crew A',{'height':1080})
  result,state,*_=self.run_queue(['good','good'],pinned=True,health=health,names=['Crew B','Crew A'])
  self.assertTrue(state['order'][0].endswith('b'))
  clock[0]+=5;health.fail('Crew B','froze')
  result,state,*_=self.run_queue(['good','good'],pinned=True,health=health,names=['Crew B','Crew A'])
  self.assertTrue(state['order'][0].endswith('a'))

if __name__=='__main__':unittest.main()
