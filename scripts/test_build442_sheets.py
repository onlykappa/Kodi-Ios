"""Owner-approved build-442 sheets on the backend's data (docs/design/build442-mockups.html N2 and Q2,
docs/design/unified-status-mockups.html board B): ISSUE-298 Build Season chips, ISSUE-299 notification timeline,
ISSUE-300 the copy sheet. Host checks of the models and the generated XML; the desktop rig and the phone are separate."""
import importlib.util,sys,types,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import portrait,pages,season_check,season_sheet,notice_page,library_rows   # noqa: E402


def parse(xml):
    return ET.fromstring(xml.split('\n',2)[2])


class Q2Chips(unittest.TestCase):
    def survey(self,n,qualities):
        sv=season_check.Survey(range(21))
        for e in range(n):sv.record(e,{'qualities':qualities(e)})
        return season_sheet.checking_props('Naruto Shippuden',2,21,(),0,{'coverage':sv.model()})
    def test_no_sample_episodes_and_an_honest_start(self):
        props=self.survey(0,lambda e:[])
        self.assertEqual(props['check.title'],'Finding versions of season 2')
        self.assertIn('about half a minute',props['check.intro']);self.assertEqual(props['check.found'],'')
        self.assertFalse(any('episodes 1' in v for v in props.values()))
        self.assertEqual(props['check.chip.1.text'],'');self.assertEqual(props['check.busy'],'true')
    def test_found_qualities_become_chips_green_when_whole(self):
        props=self.survey(21,lambda e:['1080p','720p'] if e<18 else ['1080p'])
        self.assertEqual((props['check.chip.1.text'],props['check.chip.1.whole']),('1080p · all 21','true'))
        self.assertEqual((props['check.chip.2.text'],props['check.chip.2.part']),('720p · 18 of 21','true'))
        self.assertEqual(props['check.looking'],'None found · 4K');self.assertEqual(props['check.busy'],'')
    def test_header_never_starts_with_a_dot(self):
        props=season_sheet.checking_props('',3,10,(),0,{})
        self.assertEqual(props['season.sub'],'10 episodes')   # owner screenshot: "· 10 episodes"
    def test_sheet_draws_chips_and_no_placeholders(self):
        xml=pages.season_quality_sheet(portrait);parse(xml)
        for k in ('check.chip.1.text','check.chip.3.text','check.looking','check.intro','check.found'):self.assertIn(k,xml)
        self.assertNotIn('check.q.1',xml);self.assertNotIn('!!',xml)


class N2Timeline(unittest.TestCase):
    def notifications(self):
        sys.modules.setdefault('xbmc',types.SimpleNamespace(log=lambda *a,**k:None,LOGINFO=1,LOGWARNING=2))
        spec=importlib.util.spec_from_file_location('notifications_n2',BOOT/'notifications.py');n=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(n);return n
    def test_props_carry_up_to_three_timed_steps(self):
        n=self.notifications()
        item={'kind':'problem','title':"Couldn't download to Google Drive",'text':'Rick and Morty · S3 E1: AllDebrid stopped answering','time':1000,
              'timeline':[{'at':1001,'kind':'copying','text':'3 episodes started copying'},{'at':1120,'kind':'problem','text':'AllDebrid stopped answering'}]}
        props,_=n.detail_properties(item,[])
        self.assertEqual(props['tl.1.text'],'3 episodes started copying');self.assertEqual(props['tl.1.tint'],'FF0A84FF')
        self.assertEqual(props['tl.2.tint'],'FFFF9F0A');self.assertEqual(props['tl.3.text'],'')
        props,_=n.detail_properties(dict(item,timeline=[]),[])
        self.assertEqual(props['tl.1.text'],'')          # old notices: no invented steps
    def test_sheet_stacks_so_missing_parts_leave_no_gap(self):
        xml=notice_page.sheet(portrait);root=parse(xml)
        stack=[c for c in root.iter('control') if c.get('type')=='grouplist'][0]
        self.assertIn('tl.1.text',ET.tostring(stack).decode());self.assertNotIn('!!',xml)
        self.assertIn('Window().Property(tl.3.time)',xml)


class BoardBCopySheet(unittest.TestCase):
    def test_copy_steps_and_speed_card(self):
        row={'title':'Naruto Shippuden','state':'uploading','pct':92,'sent':1,'total':2,'size':2*1024**3}
        sheet=library_rows.details(row,{})
        self.assertEqual([s[0] for s in sheet['steps']],['Found on AllDebrid','Copying to Drive · 92%','Ready for Kodi and AirPlay'])
        self.assertEqual(sheet['card'],'up')
        fetching=library_rows.details(dict(row,stage='fetching'),{})
        self.assertEqual(fetching['steps'][0][0],'Fetching on AllDebrid')
    def test_average_done_and_started_from_the_lane(self):
        card=library_rows.speed_card_text({'state':'running','rate':7.2*1048576,'speed_history':[[1700000000,4e6],[1700000001,6e6]],
                                           'confirmed_bytes':100*1048576,'eta_s':60},{},2*1024**3,5)
        self.assertEqual((card['card.num'],card['card.avg'],card['card.done']),('7.2','4.8 MB/s','0.1 of 2.0 GB'))
        self.assertNotEqual(card['card.started'],'—')


if __name__=='__main__':
    unittest.main()
