"""RunScript(service.kodi.ios.bootstrap,customise_counts): the values on Settings › Customisation and Tabs & Rows
("9 on", "13 rows", "Poster Grid"), from the same skin settings and row lists the pages change
(settings_page.count_rules, rows_editor)."""
import importlib.util,os
HERE=os.path.dirname(os.path.abspath(__file__))
LIB=os.path.join(HERE,'resources','lib')

def module(name):
 spec=importlib.util.spec_from_file_location(name+'_counts',os.path.join(LIB,name+'.py'))
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def rules():return module('settings_page').count_rules()

def values(rules,visible,profile=None,settings=None,rows=None):
 """{property: text}: switches on per page; with a profile, rows that show per tab and in all; the view type."""
 out={'custom.'+key:'%d on'%sum(1 for c in conds if visible(c)) for key,conds in rules.items()}
 if profile is not None and rows is not None:
  total=0
  for key,_,lst in rows.TABS:
   n=rows.count(profile,lst);total+=n;out['custom.rows.'+key]='%d rows'%n
  out['custom.rows']='%d rows'%total
 if settings is not None:out['custom.views']=settings.view_name(visible)
 return out

if __name__=='__main__':
 import xbmc,xbmcgui,xbmcvfs
 window=xbmcgui.Window(10004);settings=module('settings_page')
 for key,text in values(settings.count_rules(),xbmc.getCondVisibility,xbmcvfs.translatePath('special://profile/'),settings,module('rows_editor')).items():
  window.setProperty(key,text)
