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


if __name__=='__main__':unittest.main()
