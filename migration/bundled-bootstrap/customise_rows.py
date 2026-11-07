"""RunScript(service.kodi.ios.bootstrap,customise_rows,tab=<home|movies|tv>): Settings › Customisation › Tabs & Rows ›
a tab. Shows the tab's rows (portrait/IOSRows.xml, rows_page.py), and every change goes through rows_editor into the
same Skin Variables list Home reads. When the page closes after a change, the portrait folder is rebuilt from the new
list and the skin reloads, so the tab shows the new rows at once."""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import rows_editor as re_
import rows_page as page

BACK_ACTIONS=(9,10,92,110)

def tab_from(args):
 for a in args:
  value=a.split('=',1)[1] if a.startswith('tab=') else a
  if value in [k for k,_,_ in re_.TABS]:return value
 return 'home'

class Editor:
 """The page's state and what each tap does (no Kodi calls: `ui` asks the questions, tests pass a fake)."""
 def __init__(self,profile,tab,ui):
  self.profile=profile;self.key,self.name,self.list=re_.tab(tab);self.ui=ui
  self.rows=re_.load(profile,self.list);self.editing=False;self.current=None;self.changed=False
 def props(self):
  out=re_.properties(self.rows,page.SLOTS)
  out.update({'title':self.name if self.current is None else (self.rows[self.current].get('label') or 'Row'),
              'sub':out['count'] if self.current is None else 'On %s'%self.name,
              'edit_label':'Done' if self.editing else 'Edit','editing':'true' if self.editing else '',
              'page':'' if self.current is None else 'row'})
  out.update(re_.row_properties(self.rows[self.current]) if self.current is not None else
             {k:'' for k in ('one.title','one.on','one.style','one.source','one.path')})
  return out
 def _set(self,rows):
  self.rows=rows;self.changed=True;re_.save(self.profile,self.list,rows)
 def back(self):
  """True when the page should close."""
  if self.current is not None:self.current=None;return False
  if self.editing:self.editing=False;return False
  return True
 def click(self,control):
  n=lambda base:control-base if 1<=control-base<=min(page.SLOTS,len(self.rows)) else 0
  if control==page.EDIT:self.editing=not self.editing
  elif n(page.ROW_BASE) and not self.editing:self.current=n(page.ROW_BASE)-1
  elif n(page.UP):self._set(re_.move(self.rows,n(page.UP)-1,-1))
  elif n(page.DOWN):self._set(re_.move(self.rows,n(page.DOWN)-1,1))
  elif n(page.REMOVE):
   i=n(page.REMOVE)-1
   if self.ui.confirm('Delete "%s"?'%(self.rows[i].get('label') or 'this row')):self._set(re_.delete(self.rows,i))
  elif control==page.ADD:self.add()
  elif control==page.RESTORE:
   if self.ui.confirm('Put back the rows %s had before you changed them here?'%self.name) and re_.restore(self.profile,self.list):
    self.rows=re_.load(self.profile,self.list);self.changed=True
   elif not os.path.exists(os.path.join(self.profile,re_.DEFAULTS%self.list)):self.ui.notify('These are already the rows it came with.')
  elif self.current is not None:
   i=self.current;row=self.rows[i]
   if control==page.SHOW:self._set(self.rows[:i]+[re_.set_on(row,not re_.is_on(row))]+self.rows[i+1:])
   elif control==page.RENAME:
    name=self.ui.text('Name',row.get('label',''))
    if name:self._set(re_.rename(self.rows,i,name))
   elif control==page.STYLE:
    names=[n for _,n in re_.STYLES];pick=self.ui.select('Row Style',names,names.index(re_.style_name(row)))
    if pick>=0:self._set(re_.set_style(self.rows,i,re_.STYLES[pick][0]))
   elif control==page.DELETE:
    if self.ui.confirm('Delete "%s"?'%(row.get('label') or 'this row')):self.current=None;self._set(re_.delete(self.rows,i))
 def add(self):
  items=re_.CATALOGUE[self.key];names=[n for n,_ in items]+['From an add-on or folder…']
  pick=self.ui.select('Add Row',names,-1)
  if pick<0:return
  if pick<len(items):label,path=items[pick]
  else:
   path=self.ui.browse('Choose the folder that fills the row')
   if not path:return
   label=self.ui.text('Name',os.path.basename(path.rstrip('/')) or 'New Row')
   if not label:return
  self._set(re_.add(self.rows,label,path))

class KodiUI:
 def __init__(self):
  import xbmcgui;self.d=xbmcgui.Dialog()
 def confirm(self,text):return self.d.yesno('Rows',text)
 def notify(self,text):self.d.notification('Rows',text,time=2500)
 def text(self,heading,default):return self.d.input(heading,default)
 def select(self,heading,names,preselect):return self.d.select(heading,names,preselect=preselect)
 def browse(self,heading):
  value=self.d.browse(0,heading,'videos')
  return value if isinstance(value,str) and value and value!='videos' else ''

def run(args):
 import xbmc,xbmcgui,xbmcvfs
 import tool_windows
 profile=xbmcvfs.translatePath('special://profile/')
 editor=Editor(profile,tab_from(args),KodiUI())

 class Rows(xbmcgui.WindowXMLDialog):
  def onInit(self):self.show_state()
  def show_state(self):
   for k,v in editor.props().items():self.setProperty(k,v)
  def onAction(self,action):
   if action.getId() in BACK_ACTIONS:self.go_back()
  def go_back(self):
   if editor.back():self.close()
   else:self.show_state();self.setFocusId(page.BACK)
  def onClick(self,control):
   if control==page.BACK:self.go_back();return
   was=editor.current;editor.click(control);self.show_state()
   if editor.current!=was:self.setFocusId(page.BACK)
 tool_windows.show(Rows,page.NAME)
 if editor.changed:
  import importlib.util
  spec=importlib.util.spec_from_file_location('portrait_rows',os.path.join(HERE,'resources','lib','portrait.py'))
  portrait=importlib.util.module_from_spec(spec);spec.loader.exec_module(portrait)
  portrait.refresh_skin(xbmc,xbmc.executebuiltin,xbmcvfs.translatePath('special://skin/'),profile)
  xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,customise_counts)')

if __name__=='__main__':run(sys.argv[1:])
