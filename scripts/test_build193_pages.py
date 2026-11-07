"""Approved boards: XML contracts, model-only words, graph pixels, actions and grouping.

Structural evidence only; these checks do not establish Kodi or device appearance.
"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BOOT=ROOT/'migration/bundled-bootstrap'
sys.path[:0]=[str(BOOT/'resources/lib'),str(BOOT),str(ROOT/'scripts')]
import portrait as p
import library_page as lp
import library_rows as lr
import library_tools as lt
import library_tools_page as ltp
import notifications
import status_ui as ui
import tool_windows
import transfer_history as th
import transfers
import transfers_page as tp
import work_state as ws
from test_notices import label_boxes
from test_transfers import decode

MB=1048576


def model(now=1000):
    return ws.build({'prep':{'current':{'running':True,'title':'Film.2026.mkv','stage':'Converting','progress':42,
                                      'rate':4.8*MB,'eta_s':360,'updated':now},
                             'jobs':{'b':{'source':{'id':'b','name':'Next.mkv','size':MB},'status':'waiting'}}}},now)


class XML(unittest.TestCase):
    def pages(self):
        return {'Library':lp.page(p),'Movie':lp.item_sheet(p),'Transfers':tp.page(p),
                'Notifications':p.notices_page(),'Queue':ltp.queue_page(p),'History':ltp.history_page(p)}

    def test_each_page_ids_targets_fonts_truncation(self):
        sizes={name:size for name,_,size in p.FONTS}
        for name,xml in self.pages().items():
            with self.subTest(page=name):
                root=ET.fromstring(xml)
                self.assertNotIn('glass_118.png',xml)
                ids=[c.get('id') for c in root.iter('control') if c.get('id')]
                self.assertEqual(len(ids),len(set(ids)),name)
                for c in root.iter('control'):
                    if c.get('type')=='button':
                        self.assertGreaterEqual(float(c.findtext('width') or 0),118,c.get('id'))
                        self.assertGreaterEqual(float(c.findtext('height') or 0),118,c.get('id'))
                    if c.get('type')=='label':
                        self.assertGreater(float(c.findtext('width') or 0),0)
                        self.assertGreaterEqual(sizes[c.findtext('font')],30)
                        self.assertEqual(c.findtext('scroll'),'false',c.findtext('label'))
                        self.assertIsNone(c.find('wrapmultiline'))
                self.assertIn('9001' if name!='Movie' else '9200',ids)

    def test_no_two_text_runs_share_a_box(self):
        for name,xml in self.pages().items():
            for group in ET.fromstring(xml).iter('control'):
                boxes=label_boxes(group)
                for i,a in enumerate(boxes):
                    for b in boxes[i+1:]:
                        self.assertFalse(a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3],(name,a,b))

    def test_shared_card_and_movie_steps_graph_labels(self):
        for xml in (lp.page(p),p.notices_page()):
            self.assertIn('poster_mask.png',xml)
            self.assertIn('chevron-right.png',xml)
        sheet=lp.item_sheet(p)
        for n in range(3):self.assertIn('Window().Property(step%d.label)'%n,sheet)
        for xml,key in ((sheet,'card.'),(tp.page(p),'')):
            for suffix in ('axis0','axis1','axis2','peak','from'):
                labels=[c.findtext('label','') for c in ET.fromstring(xml).iter('control') if c.get('type')=='label']
                self.assertTrue(any('Window().Property(%s%s)'%(key,suffix) in label for label in labels))
        self.assertNotIn('Also running',tp.page(p))

    def test_landscape_airplay_sheet_unchanged(self):
        import subprocess
        source=subprocess.check_output(['git','show','ecfbecc:migration/bundled-bootstrap/resources/lib/library_tools_page.py'],cwd=ROOT,text=True)
        a=source[source.index('def airplay_sheet'):source.index('def arrow')]
        now=(BOOT/'resources/lib/library_tools_page.py').read_text()
        self.assertEqual(a,now[now.index('def airplay_sheet'):now.index('def arrow')])


class Bell(unittest.TestCase):
    def test_idle_running_slowed_and_needs(self):
        now=1000
        running=model(now)
        props=ws.bell_properties(running)
        self.assertEqual((props['Notices.Pct'],props['Notices.Count'],props['Notices.Tint']),('42','1',ws.PURPLE))
        idle=ws.bell_properties(ws.build({},now))
        self.assertEqual((idle['Notices.Active'],idle['Notices.Count'],idle['Notices.Needs']),('','',''))
        slow=model(now);slow['bell'].update(state='slowed',tint=ws.GREY)
        self.assertEqual(ws.bell_properties(slow)['Notices.Tint'],ws.GREY)
        need=ws.build({'needs':[{'title':'Sign in','text':'Again','button':'Sign in','action':'signin'}]},now)
        self.assertEqual(ws.bell_properties(need)['Notices.Needs'],'1')
        xml=p.bell(0,0)
        self.assertNotIn('Notices.Unread',xml);self.assertNotIn('rotate',xml)
        self.assertIn('Notices.Pct',xml);self.assertIn('Notices.Tint',xml)
        self.assertIn('Notices.Needs',xml)
        self.assertEqual(xml.count('ring_'),21)


class Graph(unittest.TestCase):
    def test_requested_pixels_and_supersampled_stroke(self):
        pts=[[0,2*MB],[1,4*MB],[2,3*MB],[3,5*MB]]
        w,h,rows=decode(th.render(pts,ws.PURPLE,240,100,scale=1.5))
        self.assertEqual((w,h),(360,150))
        alphas={row[i] for row in rows for i in range(3,len(row),4)}
        # Stroke edge samples (multiples of 1/16), beyond the 90-alpha fill.
        self.assertTrue(any(90<a<255 for a in alphas))
        self.assertIn(255,alphas)
        self.assertEqual(th.graph_labels(pts)['axis2'],'0')
        sw,sh,_=decode(th.render(pts,ws.PURPLE,180,64,guides=False))
        self.assertEqual((sw,sh),(180,64))


class StateAndActions(unittest.TestCase):
    def test_summary_counts_are_disjoint_and_segments_cumulative(self):
        view={'rows':{'preparing':[{'id':'a','title':'A','eta_s':360}], 'downloading':[{'id':'d'}],
                      'waiting':[{'id':'b'},{'id':'c'}], 'ready':[{'id':str(i)} for i in range(8)], 'kept':[{'id':'k'}]},
              'ready':8,'kept':1,'total':13,'pct':62,'checked':'checked just now'}
        props=lr.page_properties(view)
        self.assertEqual([props['count.'+k] for k in ('ready','working','next','kept')],['8','2','2','1'])
        self.assertEqual(float(props['summary.kept']),100)
        self.assertLess(float(props['summary.ready']),float(props['summary.working']))
        self.assertIn('about 6 min to go',props['remaining'])
        self.assertNotIn('ring.png',lp.page(p))

    def test_all_live_words_are_the_model_even_if_history_disagrees(self):
        m=model();j=m['jobs'][0];self.assertEqual(ws.metrics_line(j),'4.8 MB/s · 6 min left');j.update(state='slowed',line='Slower while AirPlay plays · 1.1 MB/s · 25 min left',tint_now=ws.GREY)
        history={'jobs':{'conv':{'title':j['title'],'last':1,'start':1,'points':[[1,99*MB]],'pct':99}}}
        props,pct,kind,_=transfers.page_state(history,1000,'conv',[],m)
        self.assertEqual(props['line'],j['line']);self.assertEqual(pct,42);self.assertEqual(props['tint'],ws.GREY)
        self.assertEqual(notifications.model_cards(m)[0]['line'],j['line'])
        self.assertEqual(ws.metrics_line(j),j['line'])
        for mode in ('stale','queued','waiting_network','needs_you','paused_by_you'):
            m=ws.build({},1000);m.update(mode=mode,headline='Updating…')
            self.assertNotIn('Nothing is moving',transfers.page_state({},1000,'conv',[],m)[0]['empty.title'])
        self.assertEqual(transfers.page_state({},1000,'conv',[],ws.build({},1000))[0]['empty.title'],'Nothing is moving right now')
        self.assertEqual(transfers.page_state({},1000,'conv',[],None)[0]['empty.title'],'Updating…')

    def test_ready_sheet_only_shows_needs_when_present(self):
        row={'id':'r','title':'Ready','state':'ready','size':MB,'probe':{'width':3840}}
        m=ws.build({},1000)
        sheet=lr.details(row,{'model':m})
        self.assertEqual([t for _,t in sheet['steps']],[p.GREEN]*3)
        self.assertEqual(sheet['actions'],[('Play','play'),('Play on TV','tv')])
        self.assertEqual(sheet['need'],{})
        m['needs']=[{'title':'Sign in','text':'Again','button':'Sign in','action':'signin'}]
        self.assertEqual(lr.details(row,{'model':m})['need'],m['needs'][0])

    def test_queue_end_arrows_and_failed_first(self):
        m=model();m['next']=[{'id':str(i),'title':str(i),'what':'convert','size':MB} for i in range(3)]
        view={'model':m,'rows':{'waiting':[{'id':str(i),'state':'waiting','title':str(i),'sub':'convert'} for i in range(3)]}}
        q=lt.queue_view(view)
        self.assertEqual((q['line'][0]['up'],q['line'][-1]['down']),('',''))
        self.assertEqual(q['line'][1]['up'],'true')
        self.assertIn('<enable>!String.IsEmpty(Window().Property(line.1.up))</enable>',ltp.queue_page(p))
        self.assertIn(p.DIM,ltp.queue_page(p))
        now=time.time()
        h=lt.history_view([{'kind':'up','title':'Done','start':now-100,'end':now,'size':MB,'done':MB,'total':MB}],
                          [{'kind':'conv','title':'Failed','time':now-50,'reason':'Could not read it'}],now)
        self.assertEqual([e['title'] for e in h['rows']],['Failed','Done'])
        self.assertEqual(lt.history_properties(h,'today')['h.1.section'],'unfinished')

    def test_every_simultaneous_job_gets_a_selectable_chip(self):
        m=model()
        j=dict(m['jobs'][0],kind='upload',title='Copy A')
        m['jobs']=[j,dict(j,title='Copy B')]
        props,_,kind,keys=transfers.page_state({},1000,'up.2',[],m)
        self.assertEqual(keys,['up','up.2'])
        self.assertEqual(kind,'up.2');self.assertEqual(props['title'],'Copy B')
        self.assertTrue(props['other.1.label']);self.assertTrue(props['other.2.label'])

    def test_queued_faster_start_is_counted_once_and_keeps_play(self):
        row={'id':'r','title':'Ready','state':'ready','sub':'4K','size':MB}
        m=ws.build({},1000);m['next']=[{'id':'r','title':'Ready','what':'faster start','size':MB}]
        view={'rows':{'preparing':[],'downloading':[],'waiting':[],'ready':[row],'kept':[]}}
        view=lr.with_model(view,m)
        self.assertEqual(view['total'],1)
        self.assertEqual(lr.page_properties(dict(view,checked='checked just now'))['count.next'],'1')
        self.assertEqual(lt.queue_view(view)['line'][0]['id'],'r')
        self.assertEqual(lr.details(view['rows']['waiting'][0],view)['actions'],[('Play','play'),('Play on TV','tv')])

    def test_shared_remaining_estimate_is_not_guessed_by_pages(self):
        m=model()
        estimate=ws.remaining_text(m)
        self.assertEqual(estimate,'about 6 min')
        for mode in ('stale','paused_by_you','waiting_network'):
            m['mode']=mode
            self.assertEqual(ws.remaining_text(m),'')
        m=model();m['jobs'][0]['rate']=0
        self.assertEqual(ws.remaining_text(m),'')

    def test_retry_calls_the_owning_queue(self):
        import prepare_downloads as prep
        import debrid_drive
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as profile:
            prep.save(profile,{'jobs':{'a':{'source':{'id':'drive-id','name':'Failed.mkv'},'status':'failed'}}})
            target=tool_windows.retry_target(profile,{'tone':'bad','kind':'conv','title':'Failed'})
            self.assertEqual(target,('conv','drive-id'))
            tool_windows.retry_history(profile,target)
            self.assertEqual(prep.pending_requests(profile),[{'action':'retry','id':'drive-id'}])
            j={'hash':'a'*40,'name':'A.mkv','kind':'movie','title':'A','status':'failed'}
            with patch.object(debrid_drive,'queue') as enqueue:
                tool_windows.retry_history(profile,('up',j))
                self.assertEqual(enqueue.call_args.args[1],{'id':'a'*40,'name':'A.mkv'})


class ReviewFindings(unittest.TestCase):
    """The eight owner-supplied build-193 review findings, exercised without Kodi accounts."""
    def work(self,kind='conv',**extra):
        j=dict(model()['jobs'][0],kind=kind,title='Inception (2010)',name='Inception.2010.mkv',id='new-id',hash='a'*40,total=10*MB)
        j.update(extra)
        return j

    def view(self,jobs,kept=()):
        m=dict(model(),jobs=jobs,next=[])
        v={'rows':{'preparing':[],'downloading':[],'waiting':[],'ready':[],'kept':list(kept)},'checked':'checked just now'}
        return lr.with_model(v,m)

    def run_library(self,profile,m,script,state=None):
        import test_library_status as fixture
        import prepare_downloads as prep
        import library_status
        from unittest.mock import patch
        prep.save(profile,state or {})
        fake=fixture.FakeKodi(profile,script)
        with patch.dict(sys.modules,fake.modules),patch.object(ws,'load',return_value=m):
            library_status.run()
        return fake

    def test_1_transfer_titles_cannot_replace_or_bind_the_kept_drive_copy(self):
        kept={'id':'old-drive-id','title':'Inception (2010)','name':'Inception.2010.AV1.mkv','state':'kept',
              'sub':'Being replaced · a version without conversion is downloading','size':MB,'owner':False}
        for kind in ('copy','upload','down'):
            for ident in (None,'another-id'):
                with self.subTest(kind=kind,id=ident):
                    j=self.work(kind,id=ident)
                    view=self.view([j],[dict(kept)])
                    self.assertEqual(view['rows']['kept'],[kept])
                    sheet=lr.details(view['rows']['kept'][0],view)
                    self.assertIsNone(sheet['live']);self.assertEqual(sheet['status'],'Kept as it is')
                    self.assertEqual(sheet['actions'],[])
                    self.assertEqual([i['label2'] for i in lr.list_items(view) if i['props']['state']=='kept'],
                                     ['Being replaced by the new download above'])
                    self.assertNotEqual(view['rows']['downloading'][0]['id'],'old-drive-id')
        for kind in ('conv','repack'):
            self.assertTrue(lr.matches_job(self.work(kind,id=None),kept))
        self.assertTrue(lr.matches_job(self.work('copy',id='old-drive-id'),kept))
        self.assertFalse(lr.matches_job(self.work('copy',id=None),dict(kept,id=None)))

    def test_2_elementum_pause_and_resume_use_the_engine(self):
        import test_library_status as fixture
        import transfer_control as tc
        import notices
        from unittest.mock import patch
        for state,command in (('running','pause'),('paused_by_you','resume')):
            with self.subTest(state=state),tempfile.TemporaryDirectory() as profile:
                j=self.work('down',id='torrent-id',state=state)
                m=dict(model(),jobs=[j],next=[])
                script=[(lp.WINDOW,fixture.tap(lp.SLOT)),(lp.ITEM,fixture.tap(9201)),(lp.WINDOW,fixture.tap(lp.BACK))]
                with patch.object(notices,'engine_action',return_value=True) as engine,patch.object(tc,'set_paused') as flags:
                    self.run_library(profile,m,script)
                engine.assert_called_once_with(command,'torrent-id');flags.assert_not_called()

    def test_3_transfer_sheets_have_pause_cancel_without_play(self):
        for kind in ('copy','down','upload'):
            with self.subTest(kind=kind):
                j=self.work(kind,id='up' if kind=='copy' else 'torrent')
                view=self.view([j]);row=view['rows']['downloading'][0]
                sheet=lr.details(row,view)
                self.assertEqual(sheet['actions'][0],('Pause','toggle'))
                self.assertFalse(any(action in ('play','tv') for _,action in sheet['actions']))
                self.assertEqual(sheet['sentence'],'')
                if kind!='upload':self.assertEqual(sheet['actions'][1],('Cancel','cancel'))
        import test_library_status as fixture
        import transfer_control as tc
        import notices
        from unittest.mock import patch
        for kind in ('copy','down'):
            with self.subTest(cancel=kind),tempfile.TemporaryDirectory() as profile:
                j=self.work(kind,id='torrent')
                m=dict(model(),jobs=[j],next=[])
                script=[(lp.WINDOW,fixture.tap(lp.SLOT)),(lp.ITEM,fixture.tap(9202)),(lp.WINDOW,fixture.tap(lp.BACK))]
                with patch.object(notices,'engine_action',return_value=True) as engine:
                    self.run_library(profile,m,script)
                if kind=='down':engine.assert_called_once_with('cancel','torrent')
                else:
                    engine.assert_not_called();self.assertEqual(tc.cancelled_copies(profile),{'a'*40})

    def test_4_notification_cards_keep_both_cancel_targets(self):
        import test_library_status as fixture
        import prepare_downloads as prep
        import transfer_control as tc
        import types
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as profile:
            prep.save(profile,fixture.library_state())
            m=dict(model(),jobs=[self.work('conv',id=None),self.work('copy',id=None)],next=[])
            seen={}
            def inspect(w):
                seen['conv']=dict(w.current);seen['copy']=dict(w.ups[0])
            fake=fixture.FakeKodi(profile,[('IOSNotifications.xml',inspect),('IOSNotifications.xml',fixture.tap(9001))])
            fake.modules['xbmcgui'].Window=lambda ident:types.SimpleNamespace(setProperty=lambda *a:None)
            with patch.dict(sys.modules,fake.modules),patch.object(ws,'load',return_value=m):notifications.run()
            self.assertEqual(seen['conv']['id'],'p1')
            self.assertIn(('Cancel conversion','cancel'),tc.menu('conv',seen['conv']))
            self.assertEqual((seen['copy']['source'],seen['copy']['hash']),('debrid','a'*40))
            self.assertIn(('Cancel this download','cancel'),tc.menu('up',seen['copy']))

    def test_5_reencoding_keeps_quicker_as_the_third_sheet_button(self):
        j=self.work('conv')
        view=self.view([j]);row=view['rows']['preparing'][0];row['reencode']=True
        self.assertEqual(lr.details(row,view)['actions'],[('Play','play'),('Pause','toggle'),lr.QUICKER])
        j['state']='paused_by_you'
        self.assertEqual(lr.details(row,view)['actions'],[('Play','play'),('Resume','toggle'),lr.QUICKER])
        row['reencode']=False
        self.assertEqual(len(lr.details(row,view)['actions']),2)
        self.assertIn('id="9203"',lp.item_sheet(p))

    def test_6_recovery_dismisses_all_modals_before_running_its_action(self):
        import test_library_status as fixture
        import library_status
        import prepare_downloads as prep
        from unittest.mock import patch
        action='ActivateWindow(Videos,plugin://plugin.googledrive/,return)'
        for in_sheet in (False,True):
            with self.subTest(sheet=in_sheet),tempfile.TemporaryDirectory() as profile:
                prep.save(profile,{})
                m=dict(model(),jobs=[self.work()],next=[],needs=[{'title':'Sign in','text':'Again','button':'Sign in','action':action}])
                script=([(lp.WINDOW,fixture.tap(lp.WORK)),(lp.ITEM,fixture.tap(lp.NEED))] if in_sheet else [(lp.WINDOW,fixture.tap(lp.NEED))])
                fake=fixture.FakeKodi(profile,script);seen=[]
                fake.modules['xbmc'].executebuiltin=lambda command:seen.append((command,[w.closed for w in fake.windows]))
                with patch.dict(sys.modules,fake.modules),patch.object(ws,'load',return_value=m):library_status.run()
                self.assertEqual(seen,[(action,[True]*(2 if in_sheet else 1))])

    def test_7_plot_cache_redraws_at_most_every_10_s_and_tidies(self):
        # Owner (build 193 review): redraw only with new points and at most every 10 s; no graph images pile up.
        from unittest.mock import patch
        for namespace in ('item','spark','transfers'):
            with self.subTest(namespace=namespace),tempfile.TemporaryDirectory() as folder,patch.object(th,'render',return_value=b'png') as render:
                clock=[100.0];cache=th.GraphCache(namespace,clock=lambda:clock[0]);key=ws.job_key(self.work())
                for old in ('graph_3.png',):open(os.path.join(folder,old),'wb').close()        # a build-192 loose file
                os.makedirs(os.path.join(folder,namespace+'-oldjob'))                          # an earlier opening's job
                points=[[1,MB],[2,2*MB]]
                image=cache.image(key,points,ws.PURPLE,folder,'special://plot',width=40,height=20)
                self.assertEqual(sorted(os.listdir(folder)),[image.split('/')[-2]])           # both old ones gone
                for _ in range(5):self.assertEqual(cache.image(key,points,ws.GREY,folder,'special://plot'),image)
                self.assertEqual(render.call_count,1)
                points.append([3,3*MB]);clock[0]+=2
                self.assertEqual(cache.image(key,points,ws.PURPLE,folder,'special://plot'),image)   # new point, too soon
                self.assertEqual(render.call_count,1)
                clock[0]+=10;updated=cache.image(key,points,ws.PURPLE,folder,'special://plot')
                self.assertNotEqual(updated,image);self.assertEqual(render.call_count,2)
                clock[0]+=10;cache.image(key,points,ws.PURPLE,folder,'special://plot');self.assertEqual(render.call_count,2)  # nothing new
                other=ws.job_key(self.work(id='other'))
                cache.image(other,points,ws.PURPLE,folder,'special://plot');self.assertEqual(render.call_count,3)
                self.assertEqual(len(os.listdir(folder)),2)
                clock[0]+=th.GraphCache.KEEP+1;cache.image(other,points+[[9,MB]],ws.PURPLE,folder,'special://plot')
                self.assertEqual(len(os.listdir(folder)),1)                                     # the first job's folder went
                cache.image(key,points,ws.PURPLE,folder,'special://plot');self.assertEqual(render.call_count,5)   # shown again: drawn again

    def test_7_all_three_page_graphs_use_the_cache_on_repeated_refresh(self):
        import test_library_status as fixture
        import transfers as controller
        from unittest.mock import patch
        j=self.work();m=dict(model(),jobs=[j],next=[])
        now=time.time();history={'jobs':{'conv':{'title':j['title'],'start':now-60,'last':now,'points':[[now-60,MB],[now,2*MB]],'n':2,'sum':3*MB,'peak':2*MB}}}
        with tempfile.TemporaryDirectory() as profile,patch.object(th,'load',return_value=history),patch.object(th,'render',return_value=b'png') as render:
            script=[(lp.WINDOW,lambda w:w.refresh()),(lp.WINDOW,fixture.tap(lp.WORK)),
                    (lp.ITEM,lambda w:(w.show(w.sheet),w.show(w.sheet))),
                    (lp.ITEM,fixture.tap(9200)),(lp.WINDOW,fixture.tap(lp.BACK))]
            self.run_library(profile,m,script)
            self.assertEqual(render.call_count,2)  # one sparkline, one movie plot
            fake=fixture.FakeKodi(profile,[(tp.WINDOW,lambda w:(w.refresh(),w.refresh())),(tp.WINDOW,fixture.tap(tp.BACK))])
            with patch.dict(sys.modules,fake.modules),patch.object(ws,'load',return_value=m):controller.run()
            self.assertEqual(render.call_count,3)  # one Transfers plot

    def test_8_missing_history_keeps_first_seen_time_per_job(self):
        j=self.work('copy',id=None);m=dict(model(),jobs=[j],next=[]);seen={}
        props=transfers.page_state({},1000,'up',[],m,seen)[0]
        self.assertEqual(props['started'],'just now')
        props=transfers.page_state({},1200,'up',[],m,seen)[0]
        self.assertEqual(props['started'],'3 min ago')
        history={'jobs':{'up':{'title':j['title'],'start':950,'last':1200,'points':[]}}}
        transfers.page_state(history,1200,'up',[],m,seen)
        self.assertEqual(transfers.page_state({},1250,'up',[],m,seen)[0]['started'],'5 min ago')
        transfers.page_state({},1300,'up',[],dict(m,jobs=[]),seen)
        self.assertEqual(transfers.page_state({},1400,'up',[],m,seen)[0]['started'],'just now')

    def test_8_stopped_faster_start_has_no_ineffective_history_retry(self):
        import prepare_downloads as prep
        with tempfile.TemporaryDirectory() as profile:
            job={'source':{'id':'failed-id','name':'Failed.mkv'},'status':'failed','blocked':True,
                 'repack':True,'repack_failed':'MP4 packet: Invalid argument'}
            prep.save(profile,{'jobs':{'slot':job}})
            entry={'tone':'bad','kind':'conv','title':'Failed','result':'MP4 packet: Invalid argument','end':time.time()}
            entry['retry']=tool_windows.retry_target(profile,entry)
            self.assertIsNone(entry['retry'])
            h={'rows':[entry],'total':'0 MB','count':0,'failed':1,'busiest':''}
            self.assertEqual(lt.history_properties(h,'today')['h.1.retry'],'')
            self.assertTrue(prep.load(profile)['jobs']['slot']['blocked'])
            job.pop('blocked');job.pop('repack_failed');prep.save(profile,{'jobs':{'slot':job}})
            self.assertEqual(tool_windows.retry_target(profile,entry),('conv','failed-id'))


if __name__=='__main__':unittest.main()
