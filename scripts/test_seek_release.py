"""Compile Kodi's real slider methods and gesture dispatch with small platform stubs.

Default: fetch three files from the pinned Kodi commit and apply the slider patch.
--source-tree: use the already-patched native build tree (no network).
"""
import argparse,json,shutil,subprocess,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def function(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=0
 for end in range(brace,len(text)):
  if text[end]=='{':depth+=1
  elif text[end]=='}':
   depth-=1
   if not depth:return text[start:end+1]
 raise AssertionError('Unclosed function: '+signature)

STUBS=r'''
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>
enum {PLAYER_PROGRESS=99,LOGINFO=1,HORIZONTAL=0,SLIDER_CONTROL_TYPE_FLOAT,SLIDER_CONTROL_TYPE_INT,SLIDER_CONTROL_TYPE_PERCENTAGE};
enum {ACTION_MOUSE_DRAG=20,ACTION_MOUSE_DRAG_END,ACTION_MOUSE_LEFT_CLICK,ACTION_MOUSE_WHEEL_UP,ACTION_MOUSE_WHEEL_DOWN,ACTION_GESTURE_NOTIFY,ACTION_GESTURE_BEGIN,ACTION_GESTURE_PAN,ACTION_GESTURE_END,ACTION_GESTURE_ABORT,GUI_MSG_EXCLUSIVE_MOUSE,GUI_MSG_EXECUTE};
enum EVENT_RESULT {EVENT_RESULT_UNHANDLED,EVENT_RESULT_HANDLED,EVENT_RESULT_PAN_HORIZONTAL_WITHOUT_INERTIA};
enum class HoldAction {DRAG=1,DRAG_END=2};
struct CPoint {float x=0,y=0;CPoint(float a=0,float b=0):x(a),y(b){} CPoint operator-(CPoint b)const{return {x-b.x,y-b.y};}};
namespace KODI {namespace MOUSE {struct CMouseEvent {int m_id,m_state;float m_offsetX,m_offsetY;CMouseEvent(int id,int state=0,float x=0,float y=0):m_id(id),m_state(state),m_offsetX(x),m_offsetY(y){}};}}
namespace MOUSE=KODI::MOUSE;
struct CGUIMessage {std::string param;CGUIMessage(int,int,int){}void SetStringParam(std::string s){param=s;}};
struct CLog {template<class...T>static void Log(T...){}};
namespace MathUtils {inline int round_int(double v){return std::lround(v);}inline float RoundF(float v,float interval){return interval?std::round(v/interval)*interval:v;}}
namespace StringUtils {inline std::string Format(std::string,float p){return std::to_string(p);}}
std::vector<float> submitted;
#define SEND_CLICK_MESSAGE(a,b,c) ((void)0)
struct Context {float scale=1;template<class T>void SetScalingResolution(T,bool){}void InvertFinalCoords(float& x,float& y){x/=scale;y/=scale;}};
struct WindowManager {void SendMessage(CGUIMessage& m){submitted.push_back(std::stof(m.param));}};
struct GUI {WindowManager manager;WindowManager& GetWindowManager(){return manager;}};
struct WindowSystem {Context ctx;Context& GetGfxContext(){return ctx;}};
struct CServiceBroker {static GUI* GetGUI(){static GUI g;return &g;}static WindowSystem* GetWinSystem(){static WindowSystem s;return &s;}};
struct Texture {float GetXPosition(){return 100;}float GetYPosition(){return 200;}float GetWidth(){return 1000;}float GetHeight(){return 20;}bool HitTest(CPoint p){return p.x>=100&&p.x<=1100;}};
struct CGUIControl {virtual EVENT_RESULT OnMouseEvent(const CPoint&,const MOUSE::CMouseEvent&)=0;CPoint GetRenderPosition(){return {};}float GetXPosition(){return 0;}float GetYPosition(){return 0;}};
struct SliderAction {int infoCode=PLAYER_PROGRESS;bool fireOnDrag=false;std::string formatString="PlayerControl(SeekPercentage({}))";};
struct CGUISliderControl:CGUIControl {
 bool m_dragging=false,m_rangeSelection=false;long long m_touchSeekAt=0;unsigned m_touchSeekMoves=0;
 int m_controlID=1,m_parentID=2;int m_orientation=HORIZONTAL,m_iType=SLIDER_CONTROL_TYPE_PERCENTAGE,m_currentSelector=0,m_iStart=0,m_iEnd=100;
 float m_fStart=0,m_fEnd=100,m_fInterval=1,percent=0;enum{RangeSelectorLower,RangeSelectorUpper};
 SliderAction action;SliderAction* m_action=&action;Texture texture;Texture* m_guiBackground=&texture;
 int GetID(){return 1;}int GetParentID(){return 2;}void SendWindowMessage(CGUIMessage&){}void Move(int){}
 float GetProportion(){return percent/100;}float GetPercentage(int){return percent;}
 void SetPercentage(float p,int,bool){percent=p;}void SetFloatValue(float p,int,bool){percent=p;}void SetIntValue(int p,int,bool){percent=p;}
 void SetFromPosition(const CPoint&,bool=false);void SendClick();EVENT_RESULT OnMouseEvent(const CPoint&,const MOUSE::CMouseEvent&) override;
};
struct CAction {int id;float a[6];int GetID()const{return id;}int GetHoldTime()const{return 0;}float GetAmount(int i)const{return a[i];}};
struct Resolution {int iWidth=2340,iHeight=1080;};struct Property {std::string asString(){return "VideoOSD.xml";}};
struct CGUIWindow {CGUISliderControl* slider;Resolution m_coordsRes;int m_exclusiveMouseControl=1;bool m_needsScaling=false;
 Property GetProperty(const char*){return {};}int GetFocusedControlID(){return 1;}
 CGUIControl* GetControl(int){return slider;}void UnfocusFromPoint(CPoint){}EVENT_RESULT SendMouseEvent(CPoint,const MOUSE::CMouseEvent&){return EVENT_RESULT_UNHANDLED;}
 EVENT_RESULT OnMouseAction(const CAction&);
};
struct CGenericTouchActionHandler {CGUIWindow* window;void sendEvent(int id,float a,float b,float c,float d,float e,float f){window->OnMouseAction({id,{a,b,c,d,e,f}});}bool OnTouchGestureEnd(float,float,float,float,float,float);};
'''
SCENARIOS=r'''
int main(){int cases=0;
 for(float scale:{1.f,2.f})for(float target:{0.f,25.f,50.f,99.f,100.f})for(float velocity:{0.f,-10000.f,10000.f}) {
  submitted.clear();CGUISliderControl s;CGUIWindow w{&s};CGenericTouchActionHandler h{&w};CServiceBroker::GetWinSystem()->ctx.scale=scale;
  w.OnMouseAction({ACTION_GESTURE_BEGIN,{100*scale,200*scale}});assert(s.m_dragging);
  const float x=100+target*10;
  for(int i=1;i<=100;i++) {w.OnMouseAction({ACTION_GESTURE_PAN,{(100+(x-100)*i/100)*scale,200*scale}});assert(s.m_dragging&&submitted.empty());}
  assert(std::abs(s.percent-target)<.01);
  h.OnTouchGestureEnd(x*scale,200*scale,0,0,velocity,velocity);
  if(submitted.size()!=1||std::abs(submitted[0]-target)>.01){std::cerr<<"release target "<<target<<", got "<<(submitted.empty()?-1:submitted[0])<<"\n";return 1;}
  assert(!s.m_dragging);cases++;
 }
 submitted.clear();CGUISliderControl s;CGUIWindow w{&s};CServiceBroker::GetWinSystem()->ctx.scale=1;
 w.OnMouseAction({ACTION_GESTURE_BEGIN,{100,200}});w.OnMouseAction({ACTION_GESTURE_PAN,{600,200}});
 w.OnMouseAction({ACTION_GESTURE_ABORT,{0,0}});assert(submitted.empty()&&!s.m_dragging);cases++;
 w.OnMouseAction({ACTION_MOUSE_LEFT_CLICK,{600,200}});assert(submitted.size()==1&&std::abs(submitted[0]-50)<.01);cases++;
 std::cout<<cases<<" real gesture/slider scenarios passed\n";
}
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-tree',type=Path);p.add_argument('--patch',type=Path,default=ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch');args=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='kodi-seek-') as tmp:
  tmp=Path(tmp);tree=args.source_tree or tmp/'source'
  files={'slider':'guilib/GUISliderControl.cpp','window':'guilib/GUIWindow.cpp','gesture':'input/touch/generic/GenericTouchActionHandler.cpp'}
  if not args.source_tree:
   commit=json.loads((ROOT/'migration/ios-portrait/source-lock.json').read_text())['commit']
   for path in files.values():
    out=tree/'xbmc'/path;out.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen('https://raw.githubusercontent.com/xbmc/xbmc/'+commit+'/xbmc/'+path,timeout=30) as r:out.write_bytes(r.read())
   subprocess.run(['git','apply','--include=xbmc/guilib/GUISliderControl.cpp','--include=xbmc/guilib/GUIWindow.cpp',str(args.patch.resolve())],cwd=tree,check=True)
  text={k:(tree/'xbmc'/v).read_text() for k,v in files.items()}
  methods=[function(text['slider'],s) for s in ('void CGUISliderControl::SendClick()','void CGUISliderControl::SetFromPosition(','EVENT_RESULT CGUISliderControl::OnMouseEvent(')]
  methods += [function(text['window'],'EVENT_RESULT CGUIWindow::OnMouseAction('),function(text['gesture'],'bool CGenericTouchActionHandler::OnTouchGestureEnd(')]
  # Default arguments belong in the stub declaration, not in the extracted definition too.
  methods=[s.replace('bool guessSelector /* = false */','bool guessSelector') for s in methods]
  source=tmp/'seek.cpp';source.write_text(STUBS+'\n'.join(methods)+SCENARIOS)
  exe=tmp/'seek';subprocess.run([shutil.which('c++') or 'c++','-std=c++17','-O0',str(source),'-o',str(exe)],check=True)
  subprocess.run([str(exe)],check=True)
if __name__=='__main__':main()
