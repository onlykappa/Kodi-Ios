"""Opens the bootstrap add-on's choice sheet (service.kodi.ios.bootstrap/resources/lib/choice_sheet.py)."""
def load():
 try:
  import importlib.util,os,xbmcaddon
  here=xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
  source=os.path.join(here,'resources','lib','choice_sheet.py')
  if not os.path.isfile(source):return None
  spec=importlib.util.spec_from_file_location('kodi_ios_choice_sheet',source)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.HOME=here
  return module
 except Exception:return None
