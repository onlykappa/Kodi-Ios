"""RunScript(service.kodi.ios.bootstrap,customise_counts): the values on Settings › Customisation ("9 on"), counted
from the same skin settings the Poster Badges and Video Controls switches write (settings_page.count_rules)."""
import importlib.util,os
HERE=os.path.dirname(os.path.abspath(__file__))

def rules():
 spec=importlib.util.spec_from_file_location('settings_page_counts',os.path.join(HERE,'resources','lib','settings_page.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.count_rules()

def values(rules,visible):
 """{property: text} from {key: [conditions]} and getCondVisibility."""
 return {'custom.'+key:'%d on'%sum(1 for c in conds if visible(c)) for key,conds in rules.items()}

if __name__=='__main__':
 import xbmc,xbmcgui
 window=xbmcgui.Window(10004)
 for key,text in values(rules(),xbmc.getCondVisibility).items():window.setProperty(key,text)
