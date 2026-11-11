"""Whole-show layout and compiled native scroll behavior from the actual staged Kodi patch.

This checks generated XML and executes the new production methods with small GUI geometry stubs;
it does not claim an iPhone GUI build or touch/render acceptance.
"""
import re,shutil,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import portrait

class Layout(unittest.TestCase):
 def setUp(self):self.root=ET.fromstring(portrait.video_nav('<window id="10025" />'))
 def control(self,id):return self.root.find(".//control[@id='%s']"%id)
 def test_one_page_contains_art_controls_seasons_and_both_episode_viewports(self):
  page=self.control(9900);self.assertEqual(page.get('type'),'grouplist');self.assertEqual(page.findtext('orientation'),'vertical')
  ids={c.get('id') for c in page.iter('control')}
  self.assertTrue({'50','52','60','9002','9003'}<=ids)
  for id in (52,60):
   listing=self.control(id);self.assertEqual(listing.findtext('top'),'0');self.assertEqual(listing.findtext('height'),str(portrait.HEIGHT));self.assertIsNone(listing.find('bottom'))
  art=[c for c in page.iter('control') if c.findtext('texture')=='$VAR[Portrait_Show_Art]']
  self.assertEqual(len(art),1)
  # Back and refresh deliberately stay reachable while content scrolls.
  self.assertIsNone(page.find(".//control[@id='9001']"));self.assertIsNone(page.find(".//control[@id='9010']"))
 def test_downloaded_primary_action_uses_existing_episode_route_and_provider_action_survives(self):
  button=self.control(9002);actions=button.findall('onclick')
  # Owner (build 229): the label sits beside the glyph, centred with it, not under it (pill_button inline).
  self.assertIn('$VAR[Portrait_Show_Play_Label]',[c.findtext('label') for c in self.root.iter('control') if c.get('type')=='label'])
  self.assertTrue(any('Container(50).ListItem.Property(KodiIOS.PlayPath)' in a.text and portrait.DOWNLOADED_SHOW in a.get('condition') for a in actions))
  self.assertTrue(any('Container.Property(KodiIOS.PlayPath)' in a.text and 'Container.Content(episodes)' in a.get('condition') for a in actions))
  self.assertTrue(any('Container(60).ListItemAbsolute(0)' in a.text and '!'+portrait.DOWNLOADED_SHOW in a.get('condition') for a in actions))
 def test_download_visibility_covers_its_glyph_and_collapses_its_page_space(self):
  button=self.control(9003)
  parents={c:p for p in self.root.iter() for c in p}
  condition=button.findtext('visible');self.assertIn('!'+portrait.DOWNLOADED_SHOW,condition)
  capsule=parents[button];self.assertEqual(capsule.findtext('visible'),condition)
  slot=parents[capsule];self.assertEqual(slot.findtext('visible'),condition)
 def test_non_episode_navigation_cannot_render_a_fake_episode_card(self):
  for id in (52,60):
   for tag in ('itemlayout','focusedlayout'):
    layout=self.control(id).find(tag);group=layout.find('control')
    self.assertEqual(group.findtext('visible'),'String.IsEqual(ListItem.DBType,episode)')
    self.assertEqual(len(list(layout)),1)
 def test_human_page_titles_and_stable_downloaded_metadata(self):
  self.assertIn('$VAR[Portrait_Page_Title]',ET.tostring(self.root,encoding='unicode'))
  variables=ET.fromstring('<includes>'+portrait.SHOW_VARS+'</includes>')
  title=variables.find("variable[@name='Portrait_Show_Title']")
  self.assertIn('$INFO[Container.PluginCategory]',[v.text for v in title])
  for field in ('Plot','Year','Rating','Genres'):
   var=variables.find("variable[@name='Portrait_Show_%s']"%field)
   self.assertIn('Container.Property(KodiIOS.Show%s)'%field,ET.tostring(var,encoding='unicode'))


def patched_fragment(file):
 patch=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text();out=[];inside=False
 for line in patch.splitlines():
  if line.startswith('diff --git '):inside=line=='diff --git a/xbmc/guilib/'+file+' b/xbmc/guilib/'+file;continue
  if not inside or line.startswith(('---','+++','@@','index ')):continue
  if line.startswith(('+',' ')):out.append(line[1:])
  elif not line:out.append('')
 return '\n'.join(out)

def method(fragment,name):
 start=fragment.index(name);brace=fragment.index('{',start);depth=0
 for end in range(brace,len(fragment)):
  if fragment[end]=='{':depth+=1
  elif fragment[end]=='}':
   depth-=1
   if depth==0:return fragment[start:end+1]
 raise AssertionError('Unclosed production method: '+name)

class NativeScroll(unittest.TestCase):
 def test_real_production_scroll_methods(self):
  compiler=shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')
  self.assertIsNotNone(compiler,'C++ compiler required for native scroll regression')
  methods=[]
  for file,names in (
   ('GUIBaseContainer.cpp',('CGUIControlGroupList* CGUIBaseContainer::PortraitScroller() const','float CGUIBaseContainer::PortraitContentHeight() const','float CGUIBaseContainer::PortraitScroll(float distance)')),
   ('GUIControlGroupList.cpp',('bool CGUIControlGroupList::IsPortraitShowPage() const','float CGUIControlGroupList::Size(const CGUIControl *control) const','float CGUIControlGroupList::ScrollPortrait(float distance)'))):
   text=patched_fragment(file)
   methods.extend(method(text,name) for name in names)
  harness=r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <vector>
enum { HORIZONTAL, VERTICAL, GUICONTAINER_LIST, GUICONTROL_GROUPLIST };
struct Scroller { float value=0; float GetValue() const{return value;} void SetValue(float x){value=x;} };
struct Timer {void Start(){} void Stop(){}};
struct Layout {float size=420;float Size(int) const{return size;}};
struct CGUIControl {
 int id=0,parentID=10025,type=GUICONTAINER_LIST;float y=0,height=2090,width=1080;bool visible=true;CGUIControl* parent=nullptr;
 virtual ~CGUIControl()=default;
 int GetID()const{return id;}int GetParentID()const{return parentID;}int GetControlType()const{return type;}
 float GetHeight()const{return height;}float GetWidth()const{return width;}float GetYPosition()const{return y;}float GetXPosition()const{return 0;}
 bool IsVisible()const{return visible;}CGUIControl* GetParentControl()const{return parent;}
};
struct CGUIControlGroupList;
struct CGUIBaseContainer: CGUIControl {
 int m_orientation=VERTICAL,offset=0,cursor=0;Layout layout;Layout* m_layout=&layout;
 std::vector<int> m_items;Scroller m_scroller;Timer m_lastScrollStartTimer,m_scrollTimer;
 CGUIControlGroupList* PortraitScroller()const;float PortraitContentHeight()const;float PortraitScroll(float);
 bool GetOffsetRange(int& a,int& b)const{a=0;b=std::max(0,int(m_items.size())-int(height/layout.size));return true;}
 int GetOffset()const{return offset;}int GetCursor()const{return cursor;}int CorrectOffset(int a,int b)const{return a+b;}
 void SetOffset(int x){offset=x;}void SetCursor(int x){cursor=x;}
 void ValidateOffset(){int a,b;GetOffsetRange(a,b);offset=std::max(a,std::min(offset,b));m_scroller.SetValue(std::max(0.f,std::min(m_scroller.GetValue(),b*layout.size)));}
 void SetInvalid(){}
};
struct CGUIControlGroupList: CGUIControl {
 int m_orientation=VERTICAL;float m_totalSize=0,m_height=2090;Scroller m_scroller;std::vector<CGUIControl*> m_children;
 bool IsPortraitShowPage()const;float Size(const CGUIControl*)const;float Size()const{return m_height;}float ScrollPortrait(float);
 void ValidateOffset(){m_totalSize=0;for(auto* child:m_children)if(child->IsVisible())m_totalSize+=Size(child);m_scroller.SetValue(std::max(0.f,std::min(m_scroller.GetValue(),std::max(0.f,m_totalSize-Size()))));}
 void SetInvalid(){}
};
'''+ '\n'.join(methods)+r'''
void eq(float a,float b){assert(std::abs(a-b)<0.01f);}
int main(){
 CGUIControlGroupList page;page.id=9900;page.type=GUICONTROL_GROUPLIST;
 CGUIControl header;header.height=1200;
 CGUIBaseContainer episodes;episodes.id=60;episodes.parent=&page;episodes.m_items.resize(20);
 page.m_children={&header,&episodes};assert(page.IsPortraitShowPage());assert(episodes.PortraitScroller()==&page);
 // The same production entry point is used from header and child gesture routes.
 eq(page.ScrollPortrait(500),500);eq(page.m_scroller.GetValue(),500);eq(episodes.m_scroller.GetValue(),0);
 eq(page.ScrollPortrait(800),800);eq(page.m_scroller.GetValue(),1200);eq(episodes.m_scroller.GetValue(),100);
 eq(page.ScrollPortrait(1000),1000);eq(episodes.m_scroller.GetValue(),1100);assert(episodes.offset+episodes.cursor==0);
 eq(page.ScrollPortrait(-1250),-1250);eq(episodes.m_scroller.GetValue(),0);eq(page.m_scroller.GetValue(),1050);
 eq(page.ScrollPortrait(-2000),-1050);eq(page.m_scroller.GetValue(),0);eq(episodes.m_scroller.GetValue(),0);
 // Huge movements clamp correctly, no loss/double processing, and reverse reaches the header again.
 const float bottom=1200+16*420;eq(page.ScrollPortrait(100000),bottom);eq(page.ScrollPortrait(1000),0);
 eq(page.ScrollPortrait(-100000),-bottom);eq(page.ScrollPortrait(-1),0);
 // Short/empty seasons occupy actual card space, not a blank full-screen list.
 episodes.m_items.resize(1);eq(page.Size(&episodes),420);eq(page.ScrollPortrait(1000),0);eq(page.m_scroller.GetValue(),0);
 header.height=1900;eq(page.ScrollPortrait(1000),230);eq(page.m_scroller.GetValue(),230);eq(episodes.m_scroller.GetValue(),0);
 episodes.m_items.clear();eq(page.Size(&episodes),0);eq(page.ScrollPortrait(100),0);eq(page.m_scroller.GetValue(),0);
 // Ordinary Home/landscape/dialog lists and horizontal season chips never enter this branch.
 episodes.m_orientation=HORIZONTAL;assert(!episodes.PortraitScroller());episodes.m_orientation=VERTICAL;
 episodes.id=50;assert(!episodes.PortraitScroller());episodes.id=60;
 page.id=5000;assert(!page.IsPortraitShowPage());assert(!episodes.PortraitScroller());eq(page.ScrollPortrait(500),0);
 page.id=9900;page.parentID=10000;assert(!page.IsPortraitShowPage());episodes.parentID=10000;assert(!episodes.PortraitScroller());
 std::cout<<"native production scroll cases passed\n";
}
'''
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'scroll.cpp';binary=Path(tmp)/'scroll';source.write_text(harness)
   compiled=subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
   self.assertEqual(compiled.returncode,0,compiled.stderr)
   result=subprocess.run([str(binary)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_gestures_share_one_route_and_end_without_independent_episode_snap(self):
  text=patched_fragment('GUIBaseContainer.cpp')
  self.assertIn('page->ScrollPortrait(-event.m_offsetY)',text)
  self.assertIn('if (PortraitScroller())',text)
  self.assertIn('Keep the exact combined page position',text)
  group=patched_fragment('GUIControlGroupList.cpp')
  self.assertIn('ScrollPortrait(-event.m_offsetY)',group)
  self.assertIn('static_cast<CGUIBaseContainer*>(control)->PortraitTouchFocus()',group)
  self.assertIn('m_portraitTouchFocus = PortraitScroller() != nullptr;',text)
  self.assertIn('m_portraitTouchFocus = false;',text)

if __name__=='__main__':unittest.main()
