"""Notifications › tap a message → its details and its part of kodi.log (owner, build 159). notices.parse_log /
excerpt / attach_logs, notifications.detail_properties, notice_page (the sheet) and the tap on the real page."""
import importlib.util,json,os,sys,tempfile,time,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(Path(__file__).resolve().parent)]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import notices
portrait=load('portrait_notice',LIB/'portrait.py')
notice_page=load('notice_page_t',LIB/'notice_page.py')

def stamp(seconds):return time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(seconds))+'.%03d'%int((seconds%1)*1000)
BASE=time.mktime((2026,11,5,19,14,0,0,0,-1))
REPORT=['                                                    - NOTE: IGNORING THIS CAN LEAD TO MEMORY LEAKS!',
 "                                                   Error Type: <class 'RuntimeError'>",
 '                                                   Error Contents: No valid addon id could be obtained.',
 '                                                   Traceback (most recent call last):',
 '                                                     File "/private/var/containers/Bundle/Application/X/App.app/AppData/AppHome/addons/service.kodi.ios.bootstrap/default.py", line 21, in <module>',
 '                                                     File "<frozen runpy>", line 291, in run_path',
 '                                                     File "/private/var/containers/Bundle/Application/X/App.app/AppData/AppHome/addons/service.kodi.ios.bootstrap/library_status.py", line 39, in run',
 '                                                   RuntimeError: No valid addon id could be obtained.',
 '                                                   -->End of Python script error report<--']
def log_text(taps=3):
 """Shaped like the owner's build-159 kodi.log: Elementum's chatter, touch tracing, then one error report per tap."""
 lines=[stamp(BASE)+' T:1 info <general>: Kodi iOS tab bar: KodiGlassBar driven by Kodi',
        stamp(BASE+4)+' T:2 warning <general>: [plugin.video.elementum]   AutoloadTorrentsPaused: true,',
        stamp(BASE+4)+' T:2 warning <general>: [plugin.video.elementum] \x1b[34mINFO  bittorrent   ▶ func1            \x1b[0mService started',
        stamp(BASE+4)+' T:2 warning <general>: [plugin.video.elementum] \x1b[33mWARN  bittorrent   ▶ logAlerts        \x1b[0mlisten_succeeded_alert',
        stamp(BASE+5)+' T:2 warning <general>: [plugin.video.elementum] \x1b[31mERRO  repository   ▶ CheckRepository  \x1b[0mUnable to create repository add-on: open /private/var/containers/Bundle/Application/X/App.app/AppData/AppHome/addons/repository.elementum/addon.xml: operation not permitted',
        stamp(BASE+6)+' T:2 warning <general>: [plugin.video.elementum] [GIN] 2026/11/06 - 03:14:06 | 200 | GET "/"',
        stamp(BASE+6)+' T:3 info <general>: Kodi iOS listing cache: served hero.1101, 21 items in 13.0ms',
        stamp(BASE+6.8)+' T:3 info <general>: Click at 715 x 1561 in Settings.xml (1080 x 2090 layout): control 9457 (handled)']
 for n in range(taps):
  t=BASE+7+n
  lines+= [stamp(t)+' T:4   error <general>: EXCEPTION: No valid addon id could be obtained.',
           stamp(t+0.02)+' T:4   error <general>: EXCEPTION Thrown (PythonToCppException) : -->Python callback/script returned the following error<--']+REPORT+['  ']
 lines.append(stamp(BASE+12)+' T:3 info <general>: Kodi iOS background: may sleep (no download or upload)')
 return '﻿'+'\n'.join(lines)+'\n'

class Excerpt(unittest.TestCase):
 def setUp(self):self.records=notices.parse_log(log_text())
 def test_a_python_error_report_is_one_record_in_one_sentence(self):
  errors=[r for r in self.records if r['level']=='error']
  self.assertEqual(len(errors),6)
  self.assertEqual(notices.plain_record(errors[1]),'RuntimeError: No valid addon id could be obtained. (library_status.py, line 39)')
  self.assertNotIn('\x1b',''.join(r['text'] for r in self.records))
 def test_the_crash_toast_gets_the_crash_once_with_its_count(self):
  shown=notices.excerpt(self.records,BASE+9.5,'Kodi iOS Automatic Setup and Recovery')
  self.assertEqual([(r['level'],r.get('count',1)) for r in shown],[('error',3)])
 def test_elementum_gets_its_real_error_not_its_chatter(self):
  shown=notices.excerpt(self.records,BASE+5.5,'Elementum')
  self.assertEqual(len(shown),1);self.assertIn('Unable to create repository',shown[0]['text'])
 def test_nothing_from_after_the_message_or_long_before(self):
  self.assertEqual(notices.excerpt(self.records,BASE+3,'Kodi iOS Automatic Setup and Recovery'),[])
  self.assertEqual(notices.excerpt(self.records,BASE+500,'TMDbHelper'),[])

class Attach(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.profile=self.tmp.name;self.log=Path(self.tmp.name)/'kodi.log'
  self.log.write_text(log_text(),encoding='utf-8')
 def tearDown(self):self.tmp.cleanup()
 def test_each_message_keeps_its_lines_once(self):
  crash=notices.add(self.profile,'problem','Kodi iOS Automatic Setup and Recovery','Check the log for more information.',now=BASE+9.5)
  quiet=notices.add(self.profile,'general','TMDbHelper','Trakt authorized in 1.946s',now=BASE+2)
  fresh=notices.add(self.profile,'general','Elementum','Elementum daemon has started',now=BASE+11.5)
  self.assertEqual(notices.attach_logs(self.profile,str(self.log),now=BASE+12),2)   # the newest waits for Kodi to finish writing
  items={i['id']:i for i in notices.load(self.profile)}
  self.assertTrue(items[crash['id']]['log']);self.assertFalse(items[quiet['id']]['log']);self.assertNotIn('log',items[fresh['id']])
  self.assertEqual(notices.log_of(self.profile,items[crash['id']])[0]['count'],3)
  self.assertEqual(notices.attach_logs(self.profile,str(self.log),now=BASE+12),0)
  self.assertEqual(notices.attach_logs(self.profile,str(self.log),now=BASE+20),1)
 def test_clearing_removes_the_copies(self):
  notices.add(self.profile,'problem','Kodi iOS Automatic Setup and Recovery','x',now=BASE+9.5)
  notices.attach_logs(self.profile,str(self.log),now=BASE+12)
  self.assertEqual(len(list(notices.logs(self.profile).glob('*.json'))),1)
  notices.clear(self.profile);self.assertEqual(list(notices.logs(self.profile).glob('*.json')),[])
 def test_service_passes_the_log(self):
  service=(BOOT/'service.py').read_text()
  self.assertIn("kwargs={'log_path':os.path.join(xbmcvfs.translatePath('special://logpath/'),'kodi.log')}",service)

class Sheet(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.xml=notice_page.sheet(portrait);cls.tree=ET.fromstring(cls.xml.split('\n',2)[2])
 def test_every_button_is_at_least_44_pt(self):
  for c in self.tree.iter('control'):
   if c.get('type')=='button':self.assertGreaterEqual(float(c.findtext('height') or 0),notice_page.HIT,c.get('id'))
 def test_ids_and_properties_the_page_uses(self):
  ids={c.get('id') for c in self.tree.iter('control')}
  for n in (notice_page.CLOSE,notice_page.ACTION,notice_page.LOG,notice_page.DIM):self.assertIn(str(n),ids)
  boot=load('notifications_props',BOOT/'notifications.py')
  props,_=boot.detail_properties({'kind':'problem','title':'t','time':BASE},[])
  for k in props:
   if not k.endswith('.action'):self.assertIn('Window().Property(%s)'%k,self.xml,k)   # .action: which fix the controller runs
  self.assertIn('ListItem.Property(level)',self.xml)
 def test_log_rows_wrap_and_open_the_complete_record(self):
  boxes=[c for c in self.tree.iter('control') if c.get('type')=='textbox']
  self.assertTrue(any(c.findtext('label')=='$INFO[ListItem.Label]' for c in boxes))
  self.assertIn('Dialog().textviewer(self.rows[index][1],self.rows[index][0])',(BOOT/'notifications.py').read_text())
 def test_closes_with_a_cross_and_fits_the_screen(self):
  self.assertIn('close_cross.png',self.xml);self.assertNotIn('>Done<',self.xml)
  listing=[c for c in self.tree.iter('control') if c.get('id')==str(notice_page.LOG)][0]
  top=portrait.HEIGHT-1780+870+64   # DEC-046: under the facts table in Technical details
  self.assertLessEqual(top+int(listing.findtext('height')),portrait.HEIGHT-170)
 def test_registered_and_pill_hidden(self):
  self.assertIn('notice_page.files(ns)',(LIB/'portrait.py').read_text())
  self.assertIn('IOSNoticeDetail.xml',(LIB/'activity_skin.py').read_text())

class TapAMessage(unittest.TestCase):
 """The real notifications.py against the fake Kodi of test_library_status."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.profile=self.tmp.name
  self.log=Path(self.profile)/'kodi.log';self.log.write_text(log_text(),encoding='utf-8')
 def tearDown(self):self.tmp.cleanup()
 def run_page(self,script):
  from unittest.mock import patch
  import test_library_status as lib
  kodi=lib.FakeKodi(self.profile,script)
  kodi.modules['xbmcvfs'].translatePath=lambda path:self.profile
  ran=[];kodi.modules['xbmc'].executebuiltin=ran.append
  class Window:
   def __init__(self,n):pass
   def setProperty(self,*a):pass
  kodi.modules['xbmcgui'].Window=Window
  with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(notices,'uploads',lambda p:[]):
   load('notifications_run',BOOT/'notifications.py').run()
  return kodi,ran
 def test_tapping_the_crash_shows_what_happened_and_the_log(self):
  notices.add(self.profile,'problem','Kodi iOS Automatic Setup and Recovery','Check the log for more information.',now=BASE+9.5)
  seen={}
  def look(w):seen.update(props=dict(w.props),rows=[(i.label,i.label2,i.getProperty('level')) for i in w.getControl(notice_page.LOG).items])
  kodi,ran=self.run_page([('IOSNotifications.xml',lambda w:w.onClick(9501)),(notice_page.SHEET,look),(notice_page.SHEET,lambda w:w.onClick(notice_page.CLOSE)),
                          ('IOSNotifications.xml',lambda w:w.onClick(9001))])
  # DEC-046 board H2: the vague setup problem in plain words, with something to do; the raw lines stay in Technical details.
  self.assertEqual(seen['props']['title'],'Setup and repair stopped')
  self.assertEqual((seen['props']['fix0.label'],seen['props']['fix1.label']),('Run Setup Again','Share the log'))
  self.assertEqual(seen['props']['safe'],'Everything that was already set up still works.')
  self.assertEqual(seen['props']['nolog'],'');self.assertEqual(seen['props']['tech.available'],'true')
  self.assertEqual(seen['rows'],[('RuntimeError: No valid addon id could be obtained. (library_status.py, line 39)',
                                  time.strftime('%H:%M:%S',time.localtime(BASE+9.02))+' · Error · 3 times','error')])
  self.assertEqual(ran,[]);self.assertTrue(all(w.closed for w in kodi.windows))
 def test_a_message_with_an_action_opens_it_from_the_sheet(self):
  notices.add(self.profile,'update','Build 160 is ready','Tap to install',action='RunScript(service.kodi.ios.bootstrap,check_updates)',now=BASE+2)
  seen={}
  kodi,ran=self.run_page([('IOSNotifications.xml',lambda w:w.onClick(9501)),(notice_page.SHEET,lambda w:seen.update(dict(w.props))),
                          (notice_page.SHEET,lambda w:w.onClick(notice_page.ACTION))])
  self.assertEqual(seen['fix0.label'],'Open');self.assertEqual(seen['nolog'],'Kodi wrote nothing else about this around that time.')
  self.assertEqual(ran,['RunScript(service.kodi.ios.bootstrap,check_updates)'])
 def test_the_dimmed_page_and_back_close_it(self):
  notices.add(self.profile,'general','TMDbHelper','Trakt authorized',now=BASE+2)
  kodi,ran=self.run_page([('IOSNotifications.xml',lambda w:w.onClick(9501)),(notice_page.SHEET,lambda w:w.onClick(notice_page.DIM)),
                          ('IOSNotifications.xml',lambda w:w.onClick(9501)),(notice_page.SHEET,lambda w:w.onAction(type('A',(),{'getId':lambda s:92})())),
                          ('IOSNotifications.xml',lambda w:w.onClick(9001))])
  self.assertEqual(len([w for w in kodi.windows if w.xml==notice_page.SHEET]),2);self.assertEqual(ran,[])

class Explained(unittest.TestCase):
 """DEC-046: what each notice means, in plain words, with its fixes (notice_help)."""
 def test_the_owners_three_screenshots(self):
  import notice_help as nh
  kept=nh.explain({'kind':'problem','title':'Video preparation paused','text':'Naruto Shippuuden · S1 E16: This file has tracks MP4 cannot preserve; original retained'})
  self.assertEqual((kept['title'],kept['line']),("Couldn't prepare Naruto Shippuuden · S1 E16","It has a track an MP4 can't keep"))
  self.assertTrue(kept['safe'].startswith('Nothing was lost'));self.assertEqual(kept['fixes'][0][0],'Find Another Version')
  trakt=nh.explain({'kind':'general','title':'TMDbHelper','text':'Trakt authorized in 1.886s'})
  self.assertEqual((trakt['title'],trakt['good'],trakt['fixes'][0][2]),('Trakt connected',True,'accounts'))
  setup=nh.explain({'kind':'problem','title':'Kodi iOS Automatic Setup and Repair','text':'Check the log for more information.'})
  self.assertEqual((setup['title'],setup['fixes'][0][2],setup['fixes'][1][2]),('Setup and repair stopped','setup','share_log'))
 def test_copies_and_unknown_problems(self):
  import notice_help as nh
  blocked=nh.explain({'kind':'problem','title':"Couldn't download to Google Drive",'text':'Fall 2 Deadpoint: AllDebrid blocked the sign-in'})
  self.assertEqual((blocked['title'],blocked['warn'],blocked['fixes'][0][2]),('Fall 2 Deadpoint is waiting',True,'accounts'))
  other=nh.explain({'kind':'problem','title':'Kodi iOS Something odd','text':'ValueError: bad thing; original retained'})
  self.assertEqual((other['title'],other['happened'],other['fixes'][0][2]),('Something odd','bad thing','share_log'))
  action=nh.explain({'kind':'update','title':'Build 160 is ready','text':'Tap to install','action':'RunScript(x)'})
  self.assertEqual(action['fixes'][0],('Open','Where this happened','notice'))
 def test_facts_read_the_failure_line(self):
  import notice_help as nh
  line='preparation: failed for X: This file has tracks MP4 cannot preserve; phase=Step 3 of 3 · Opening conversion tracks; video={"audio_tracks": 2, "codec": "h264", "height": 480, "other_image_subtitles": 1, "subtitle_tracks": 1}'
  f=dict(nh.facts({'time':BASE},[{'text':line}]))
  self.assertEqual((f['Step'],f['Video'],f['Subtitles']),('Opening conversion tracks','480p H.264 · 2 audio · 1 subtitle','DVD picture subtitles'))
 def test_rows_wrap_and_problems_have_a_fix(self):
  xml=notifications_skin_page()
  self.assertIn('id="9601"',xml);self.assertNotIn('$INFO[Window().Property(msg.1.title)]</label><font>p_pill</font><textcolor>FFFFFFFF</textcolor><scroll>false',xml)
  boot=load('notifications_rows',BOOT/'notifications.py')
  props,_=boot.message_properties([{'kind':'problem','title':'Video preparation paused','text':'Naruto Shippuuden · S1 E16: This file has tracks MP4 cannot preserve','time':BASE},
                                   {'kind':'general','title':'TMDbHelper','text':'Trakt authorized in 1.886s','time':BASE}],'all',now=BASE+60)
  self.assertEqual((props['msg.1.title'],props['msg.1.fix'],props['msg.2.title'],props['msg.2.fix']),
                   ("Couldn't prepare Naruto Shippuuden · S1 E16",'Fix','Trakt connected',''))


def notifications_skin_page():
 import notifications_skin
 return notifications_skin.page(type('PortraitTokens',(),portrait.__dict__))


if __name__=='__main__':unittest.main()
