"""Serialize Fuse activation and real helper generation; never accept a skin dialog."""
import json,traceback,xml.etree.ElementTree as ET
from pathlib import Path
LOCK='KodiIOS.Activating'
FUSE='skin.arctic.fuse.3'

def generate(skin,current_skin,invoke,wait,skinuser='',stage=lambda value:None,timeout=45):
 skin=Path(skin)
 for name in ['skinvariables-splash.json','skinvariables-build-templates.json','skinvariables-generator.json','skinviewtypes.json']:
  json.loads((skin/'shortcuts'/name).read_text())
 def ready(path,required=(),views=False):
  try:
   root=ET.parse(path).getroot()
   if root.tag!='includes':return False
   names={e.get('name') for e in root}
   if views:return bool(root.findall('expression')) and 'Exp_ViewTypes_RebuildPending' not in names
   return set(required)<=names
  except (OSError,ET.ParseError):return False
 def stamp(path):
  try:return (path.stat().st_mtime_ns,path.stat().st_size)
  except OSError:return None
 def poll(path,before,required=(),views=False):
  # A count-based bounded wait is deterministic in tests and aborts on skin changes.
  for _ in range(int(timeout/0.25)):
   if current_skin()!=FUSE:raise RuntimeError('Active skin changed during generation')
   if stamp(path)!=before and ready(path,required,views):return
   if wait(0.25):raise RuntimeError('Startup generation cancelled')
  raise RuntimeError('Generated include verification timed out: '+path.name)
 if current_skin()!=FUSE:raise RuntimeError('Fuse is not active before generation')
 stage('build_views')
 views=skin/'1080i/script-skinviewtypes-includes.xml';before=stamp(views)
 invoke('RunScript(script.skinvariables,action=buildviews,force=true,no_reload=true)')
 poll(views,before,views=True)
 stage('build_shortcuts')
 meta=json.loads((skin/'shortcuts/skinvariables-generator.json').read_text())
 output=meta['output'].format(skinuser=skinuser)
 if Path(output).name!=output:raise ValueError('Unsafe generated filename')
 folder=meta.get('folder','1080i')
 if folder!='1080i':raise ValueError('Unexpected generated folder')
 target=skin/folder/output;before=stamp(target)
 invoke('RunScript(script.skinvariables,action=buildtemplate,force=true,no_reload=true,background=true,lastbuildtime=ios-touch-navigation-r2)')
 poll(target,before,['skinvariables-homewidgets-standard','skinvariables-homewidgets-standard-onunload','skinvariables-homewidgets-combined-info'])
 stage('generation_verified')
 return {'views_verified':True,'shortcuts_verified':True,'phone_navigation_verified':False}

def failure(error,stage):
 # No exception message, locals or absolute paths: those may contain account data.
 frames=traceback.extract_tb(error.__traceback__)
 return {'status':'FAILED','stage':stage,'error_type':type(error).__name__,
         'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in frames],
         'device_success':False}
