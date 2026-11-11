"""Skin Settings as portrait pages (mockup boards 5-6): reading Fuse's own entries, levels, actions."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import skin_settings as ss

SAMPLE='''<?xml version="1.0" encoding="UTF-8"?><includes>
<include name="SkinSettings_Items_Menus">
 <include content="Settings_Label" description="Configure"><param name="window">skinsettings</param><param name="id">001</param><label>$LOCALIZE[24020]</label></include>
 <include content="Settings_Button" description="Customise Widgets"><param name="id">002</param><label>$LOCALIZE[31049]</label><onclick>ActivateWindow(1115)</onclick></include>
 <include content="Settings_Button" description="Startup"><param name="control">radiobutton</param><param name="slevel">2</param><label>$LOCALIZE[31027]</label>
  <onclick>Skin.ToggleSetting(HomeSwitcher.DisableFirstWidgetFocus)</onclick><selected>!Skin.HasSetting(HomeSwitcher.DisableFirstWidgetFocus)</selected></include>
 <include content="Settings_Label" description="Menu"><label>$LOCALIZE[33061]</label></include>
 <include content="Settings_Button" description="Position"><label>Position</label><label2>$VAR[Label_Position]</label2>
  <onclick condition="String.IsEmpty(Skin.String(P))">Skin.SetString(P,top)</onclick><onclick condition="Skin.String(P,top)">Skin.Reset(P)</onclick><visible>!Skin.HasSetting(V)</visible></include>
 <include content="Settings_Label" description="Empty group"><label>Nothing under me</label></include>
</include>
<include name="SkinSettings_Items_Other"><include content="Settings_Button"><label>Other thing</label><onclick>Noop</onclick></include></include>
</includes>'''

class Parse(unittest.TestCase):
 def setUp(self):self.p=ss.parse(SAMPLE)
 def test_entries(self):
  m=self.p['SkinSettings_Items_Menus'];self.assertEqual([e['kind'] for e in m],['title','button','switch','title','button','title'])
  sw=m[2];self.assertEqual((sw['label'],sw['level'],sw['selected']),('$LOCALIZE[31027]',2,'!Skin.HasSetting(HomeSwitcher.DisableFirstWidgetFocus)'))
  self.assertEqual(m[4]['value'],'$VAR[Label_Position]');self.assertEqual(m[4]['visible'],'!Skin.HasSetting(V)')
  self.assertIn('SkinSettings_Items_Other',self.p)
 def test_levels_visibility_and_empty_titles(self):
  m=self.p['SkinSettings_Items_Menus'];t=lambda c:c!='!Skin.HasSetting(V)'      # Position hidden by its condition
  std=ss.visible_entries(m,1,lambda c:True)
  self.assertEqual([e['label'] for e in std],['$LOCALIZE[24020]','$LOCALIZE[31049]','$LOCALIZE[33061]','Position'])   # Startup needs Advanced; the last empty title is dropped
  adv=ss.visible_entries(m,2,lambda c:True);self.assertIn('$LOCALIZE[31027]',[e['label'] for e in adv])
  hidden=ss.visible_entries(m,2,t);self.assertNotIn('Position',[e['label'] for e in hidden])
  self.assertEqual([e['label'] for e in hidden if e['kind']=='title'],['$LOCALIZE[24020]'])                          # "Menu" now has nothing under it
 def test_clicks_follow_their_conditions(self):
  e=self.p['SkinSettings_Items_Menus'][4]
  self.assertEqual(ss.click_actions(e,lambda c:c.startswith('String.IsEmpty')),['Skin.SetString(P,top)'])
  self.assertEqual(ss.click_actions(e,lambda c:c.startswith('Skin.String(P,top)')),['Skin.Reset(P)'])
  self.assertEqual(ss.click_actions(self.p['SkinSettings_Items_Other'][0],lambda c:False),['Noop'])
 def test_levels_and_sections(self):
  self.assertEqual((ss.level_from('2'),ss.level_from(''),ss.level_from('9')),(2,1,1))
  self.assertEqual([s[1] for s in ss.SECTIONS][:3],['Customisation','Appearance','Interface'])

class Pages(unittest.TestCase):
 BOOT=ROOT/'migration/bundled-bootstrap'
 def portrait(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('portrait_skin',LIB/'portrait.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_list_window_is_well_formed_with_one_list(self):
  import xml.etree.ElementTree as ET,settings_page as sp
  xml=sp.skin_list_page(self.portrait());root=ET.fromstring(xml.split('\n',2)[2])
  ids=[c.get('id') for c in root.iter('control') if c.get('id')]
  self.assertEqual(len(ids),len(set(ids)));self.assertIn('9310',ids);self.assertIn('9001',ids)
  for kind in ('title','switch','button'):self.assertIn('String.IsEqual(ListItem.Property(kind),%s)'%kind,xml)
 def test_scripts_registered_and_rows_routed(self):
  self.assertIn("'skin_settings_page'",(self.BOOT/'default.py').read_text())
  src=(LIB/'settings_page.py').read_text()
  self.assertEqual(src.count('RunScript(service.kodi.ios.bootstrap,skin_settings_page)'),2)         # Settings home and Customisation
  self.assertNotIn("'ActivateWindow(skinsettings)'",src)
  self.assertIn("p.FOLDER+'/IOSSkinList.xml'",src)
  page=(self.BOOT/'skin_settings_page.py').read_text()
  self.assertIn("Skin.SetString(Skin.SettingsLevel,%d)",page);self.assertIn("special://skin/1080i/Includes_SkinSettings.xml",page)

if __name__=='__main__':unittest.main()
