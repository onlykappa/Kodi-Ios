"""The approved Sports opening card (docs/design/sports-opening-options.html, owner 2026-11-21): game first, crests and one-line names, LIVE over the tag."""
import json,sys,types,unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace as NS
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import portrait,sports_opening as op,sports_opening_page as pg,notifications_skin as ns

def game(state='live',away=None,home=None,league='NCAAB'):
    return {'state':state,'league':league,'away':away or {'name':'Detroit Mercy Titans','short':'Titans','code':'DM','crest':'https://a.espncdn.com/i/teamlogos/ncaa/500/2174.png'},
            'home':home or {'name':'Michigan State Spartans','short':'Spartans','code':'MSU','crest':'https://a.espncdn.com/i/teamlogos/ncaa/500/127.png'}}
def source(g):return {'native_queue':[{'play':json.dumps({'l':{'game':g}})},{'play':'{}'}],'play':'{}'}

class Page(unittest.TestCase):
    def setUp(self):
        self.xml=pg.page(portrait);self.root=ET.fromstring(self.xml.encode())
    def controls(self,kind=None):
        return [c for c in self.root.iter('control') if kind is None or c.get('type')==kind]
    def test_the_buttons_and_the_default_focus(self):
        ids={c.get('id') for c in self.controls('button')}
        self.assertTrue({'9001','9003'}<=ids);self.assertEqual(self.root.findtext('defaultcontrol'),'9001')
    def test_the_card_fits_the_screen_and_every_control_stays_inside_it(self):
        total=sum(h for _,h in pg.rows());self.assertLess(total,portrait.HEIGHT*0.5)
        for c in self.controls():
            w,l=c.findtext('width'),c.findtext('left')
            if w and l and w.isdigit() and l.lstrip('-').isdigit() and c.get('type')!='image':self.assertLessEqual(int(l)+int(w),portrait.WIDTH)
    def test_the_page_behind_is_dimmed_first(self):
        first=self.controls('image')[0];self.assertEqual((first.findtext('width'),first.findtext('height')),(str(portrait.WIDTH),str(portrait.HEIGHT)))
        self.assertEqual(first.find('texture').get('colordiffuse'),pg.SHADE)
    def test_live_sits_over_the_tag_and_shows_only_for_a_live_game(self):
        self.assertIn('LIVE',self.xml);self.assertLess(self.xml.index('LIVE'),self.xml.index('Property(tag)'))
        group=[c for c in self.controls('group') if c.findtext('label') is None and 'LIVE' in ''.join(c.itertext()) or c.find('.//label') is not None and c.find('.//label').text=='LIVE'][0]
        self.assertIn('Property(live)',group.findtext('visible'))
    def test_failed_swaps_the_bar_and_cancel_for_back_to_sports(self):
        groups={g.findtext('visible'):g for g in self.root.find('controls').findall('control') if g.get('type')=='group' and g.findtext('visible')}
        shown=[v for v in groups if 'Property(failed)' in v]
        self.assertTrue(any(v.startswith('!') or v.startswith('String.IsEmpty') for v in shown) and any('Cancel' in ET.tostring(groups[v],encoding='unicode') for v in shown))
        self.assertTrue(any('Back to Sports' in ET.tostring(g,encoding='unicode') for g in groups.values()))
    def test_the_text_lines_fit_their_boxes(self):
        # every state's words, at the card's sizes, measured with the project's conservative Inter widths: one line, never cut (DEC-050)
        for text,size,bold in (('Connecting to the source',40,True),('Getting the source ready',40,True),('Trying the next source',40,True),('Taking longer than usual',40,True),(op.FAILED_STAGE,40,True)):
            self.assertLessEqual(ns.text_width(text,size,bold),pg.INNER,text)
        for text in (op.sub_text(3,'2/3'),op.sub_text(14.2,'2/3',True),op.sub_text(125,'10/10',True),op.FAILED_SUB):
            self.assertLessEqual(ns.text_width(text,35),pg.INNER,text)

class Game(unittest.TestCase):
    def test_details_for_a_live_game(self):
        import sports_rows
        g=game();found={sports_rows.crest_url(g['away']):'/crests/a.png'}
        p=op.details(source(g),found)
        self.assertEqual((p['live'],p['tag'],p['away.name'],p['home.name'],p['away.code'],p['home.code']),('1','NCAAB','Titans','Spartans','DM','MSU'))
        self.assertEqual(p['away.logo'],'/crests/a.png');self.assertEqual(p['home.logo'],'')   # the other crest is not in yet: its code shows
    def test_an_upcoming_game_has_no_live_line(self):
        self.assertEqual(op.details(source(game('upcoming')))['live'],'')
    def test_a_name_that_does_not_fit_one_line_falls_back_to_its_code_never_cut(self):
        long={'name':'Brigham Young University Cougars Of Provo Utah','short':'Brigham Young University Cougars','code':'BYU'}
        self.assertEqual(op.team_name(long),'BYU')
        for short in ('Timberwolves','Trail Blazers','Diamondbacks','Blue Jackets','Golden Knights','Fighting Irish','Spartans','Titans'):   # the longest real short names
            self.assertEqual(op.team_name({'short':short,'name':short,'code':'XXX'}),short,short)
        self.assertLessEqual(ns.text_width(op.team_name({'short':'W'*16,'code':'WWW'}),pg.NAME_SIZE,True),pg.NAME_FIT)
    def test_bad_data_never_raises(self):
        for bad in ({},{'native_queue':[]},{'native_queue':[{'play':'x'}]},{'play':json.dumps({'l':{'game':5}})}):
            self.assertEqual(op.details(bad)['away.name'],'')

class Card(unittest.TestCase):
    def make(self,home_props=None):
        props=home_props if home_props is not None else {}
        home=NS(getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None))
        o=op.Opening({'native_owner':'mine','native_queue':[{},{}]},home);return o,props
    def test_the_source_count_only_when_there_is_more_than_one(self):
        o,props=self.make({'KodiIOS.SportsOpeningChoice':'2/3'});self.assertEqual(o.choice(),'2/3')
        props['KodiIOS.SportsOpeningChoice']='1/1';self.assertEqual(o.choice(),'');props['KodiIOS.SportsOpeningChoice']='junk';self.assertEqual(o.choice(),'')
        self.assertEqual(op.sub_text(3.4,'2/3'),'Source 2 of 3 · 0:03');self.assertEqual(op.sub_text(14,'',True),'0:14 · You can cancel')
    def test_fail_shows_the_failed_card_and_waits_for_back(self):
        o,_=self.make();shown={}
        o.window=NS(setProperty=lambda k,v:shown.__setitem__(k,v),setFocusId=lambda i:shown.__setitem__('focus',i),close=lambda:None)
        o.dismissed.set();self.assertTrue(o.fail(wait=1))
        self.assertEqual((shown['failed'],shown['stage'],shown['sub'],shown['focus']),('1',op.FAILED_STAGE,op.FAILED_SUB,pg.BACK))
        self.assertTrue(o.failed)
    def test_a_cancelled_or_closed_card_is_not_shown_as_failed(self):
        o,_=self.make();o.window=NS(setProperty=lambda k,v:None,close=lambda:None);o.cancelled=True;self.assertFalse(o.fail(wait=0))
        o2,_=self.make();o2.window=NS(setProperty=lambda k,v:None,close=lambda:None);o2.closed.set();self.assertFalse(o2.fail(wait=0))
    def test_the_stage_line_follows_what_the_play_says(self):
        o,_=self.make();seen={};o.window=NS(setProperty=lambda k,v:seen.__setitem__(k,v));o.stage('Getting the source ready')
        self.assertEqual((o.stage_text,seen['stage']),('Getting the source ready',)*2)
    def test_the_pieces_are_connected(self):
        lib=ROOT/'migration/bundled-bootstrap/resources/lib'
        self.assertIn("home.setProperty('KodiIOS.SportsOpeningChoice'",(lib/'sports_loop_router.py').read_text())
        jet=(lib/'sports_jet.py').read_text();self.assertIn('shown = bool(opening and opening.fail())',jet);self.assertIn("stage('Connecting to the source')",jet)
        self.assertIn("elif control==page.BACK:parent.dismissed.set()",(lib/'sports_opening.py').read_text())
if __name__=='__main__':unittest.main()
