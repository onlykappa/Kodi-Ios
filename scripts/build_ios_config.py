"""Build a sanitized, provisional import configuration from the reviewed snapshot.
No add-on code, credentials, media or IPA executable is copied.
"""
from pathlib import Path
import json,re,hashlib,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'migration/ios'
BAD=['umbrella','plugin.video.elementum','script.elementum','service.deck.keeper','context.kannon.delete','plugin.video.the-loop','plugin.video.loop','script.loop.sportshub','repository.loop','repository.gsports','script.module.jetextractors']
def build():
 assert not (ROOT/'migration').is_symlink() and not DEST.is_symlink()
 if DEST.exists():shutil.rmtree(DEST)
 DEST.mkdir(parents=True)
 changes=[];directories=set();mapping=[]
 def remap(s):
  def path(m):
   tail='media/'+m[1].lower()+'/'
   directories.add(tail);return 'special://profile/'+tail
  return re.sub(r'\$\{((?:LOCAL_MEDIA_ROOT|NETWORK_SOURCE)_\d+)\}',path,s)
 def bad(s):return any(x in s.lower() for x in BAD)
 def value(v,location):
  if isinstance(v,list):
   out=[]
   for i,x in enumerate(v):
    result=value(x,location+f'[{i}]')
    if result is not None:out.append(result)
   return out
  if isinstance(v,dict):
   # Preserve the menu slot/label, but replace unsupported playback with local-library browsing.
   out={}
   for key,x in v.items():
    if isinstance(x,str) and bad(x):
     changes.append({'location':location+'/'+key,'reason':'Excluded or deferred backend','replacement':'Local library browsing; playback backend not yet configured'})
     if key=='path':out[key]='videodb://movies/titles/'
     elif key=='label':out[key]='Local library'
     else:out[key]=''
    elif key=='path' and x=='Quit()':
     changes.append({'location':location+'/'+key,'reason':'Desktop application-exit action replaced with accessible settings route','replacement':'ActivateWindow(Settings)'})
     out[key]='ActivateWindow(Settings)'
    else:out[key]=value(x,location+'/'+key)
   if 'label' in out:mapping.append({'location':location,'target_label':out['label'],'retained_menu_slot':True})
   return out
  if isinstance(v,str):return remap(v)
  return v
 for p in sorted((ROOT/'snapshot/userdata').rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(ROOT/'snapshot/userdata');loc=str(rel)
  if bad(loc) or 'players/' in loc or 'reconfigured_players/' in loc or rel.parts[0]=='keymaps':
   changes.append({'location':loc,'reason':'Desktop keymap or excluded player definition; retained in immutable baseline'});continue
  out=DEST/'userdata'/rel;out.parent.mkdir(parents=True,exist_ok=True)
  if p.suffix=='.json':data=json.dumps(value(json.loads(p.read_text()),loc),indent=2)+'\n'
  else:
   root=ET.parse(p).getroot()
   for parent in root.iter():
    for child in list(parent):
     if child.tag=='setting' and (bad(ET.tostring(child,encoding='unicode')) or 'REDACTED_' in child.get('id','')):
      parent.remove(child);changes.append({'location':loc+'/'+child.get('id',''),'reason':'Excluded backend preference removed from target only'})
    if parent.text:parent.text=remap(parent.text)
   if rel.name=='sources.xml':
    files=root.find('files')
    if files is not None:
     for child in list(files):
      if child.tag=='source':files.remove(child)
   ET.indent(root);data=ET.tostring(root,encoding='unicode')+'\n'
  assert not bad(data),'Excluded reference remains in target'
  out.write_text(data)
 touch=DEST/'userdata/keymaps/ios-touch.xml';touch.parent.mkdir(parents=True,exist_ok=True)
 touch.write_text('<keymap>\n  <global><touch><tap>LeftClick</tap><longpress>RightClick</longpress><pan>PanGesture</pan><swipe direction="left" pointers="2">Back</swipe><swipe direction="right" pointers="2">Menu</swipe></touch></global>\n  <FullScreenVideo><touch><tap pointers="3">PlayPause</tap><swipe direction="left">StepBack</swipe><swipe direction="right">StepForward</swipe></touch></FullScreenVideo>\n</keymap>\n')
 records=json.loads((ROOT/'reports/ios-compatibility.json').read_text())['records']
 preferred={}
 for a in records:preferred[a['id']]=a
 drive_contracts=ROOT/'reports/drive-addon-contracts.json'
 if drive_contracts.exists():
  contracts=json.loads(drive_contracts.read_text());assert contracts['owner_approved'] and contracts['architecture']=='direct-addon-maintainer-oauth-relay'
  for a in contracts['addons']:
   preferred[a['id']]={'id':a['id'],'version':a['version'],'manifest_valid':True,'compatibility_category':'approved_drive_candidate_runtime_unverified','requires':a['requires']}
 roots=['skin.arctic.fuse.3','skin.arctic.zephyr.mod','plugin.video.youtube','plugin.video.youtube.fusion','script.trakt']
 if drive_contracts.exists():roots.append('plugin.googledrive')
 selection={}
 def add(id):
  if id in selection:return
  a=preferred[id];assert a['manifest_valid']
  selection[id]={'id':id,'source_version_candidate':a['version'],'status':a['compatibility_category'],'runtime_verified':False,'requires':[x for x in a['requires'] if not x['optional']]}
  for dep in selection[id]['requires']:add(dep['id'])
 for id in roots:add(id)
 if drive_contracts.exists():
  settings=DEST/'userdata/addon_data/plugin.googledrive/settings.xml';settings.parent.mkdir(parents=True,exist_ok=True)
  settings.write_text('<settings version="2">\n  <setting id="sign-in-server">https://drive.signinserver.com</setting>\n  <setting id="set_subtitle">true</setting>\n  <setting id="ask_resume">true</setting>\n  <setting id="allow_directory_listing">false</setting>\n  <setting id="clean_folder">false</setting>\n</settings>\n')
  menu=DEST/'userdata/addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/skinvariables-shortcut-homesubmenu.json'
  items=json.loads(menu.read_text());items.append({'label':'Google Drive','path':'plugin://plugin.googledrive/','icon':'DefaultFolder.png','target':'videos'})
  menu.write_text(json.dumps(items,indent=2)+'\n')
  mapping.append({'location':'homesubmenu/Google Drive','target_label':'Google Drive','retained_menu_slot':False,'new_integration':True})
  changes.append({'location':'addon_data/plugin.googledrive/settings.xml','reason':'Approved direct Drive relay and safe subtitles/resume preferences; account state absent; optional directory listing disabled'})
 (DEST/'addon-plan.json').write_text(json.dumps({'policy':'Candidate install plan only; no add-on code distributed. Acquire matching iOS-compatible versions from reviewed official Kodi/Jurialmunkey repositories or the approved pinned Drive upstream source-lock and verify licenses/dependencies before target activation. Source versions are candidate pins, not proof of availability.','roots':roots,'addons':list(selection.values()),'excluded_or_deferred':[a['id'] for a in records if a['compatibility_category'] in ['excluded_by_owner','deferred_by_owner','blocked_invalid_manifest','incompatible_native_payload','incompatible_existing_implementation']]},indent=2)+'\n')
 (DEST/'adaptations.json').write_text(json.dumps({'changes':changes,'menu_mapping':mapping,'empty_media_directories_to_create':sorted(directories),'touch_runtime_verified':False,'fuse_layout_touch_compatibility':'Unverified; upstream touch issue remains. Gesture adapter does not fix individual skin control geometry.','media_library':'Empty until private sources/Drive added in later phase; browse replacements are not equivalent stream providers.'},indent=2)+'\n')
 hashes=[{'path':str(p.relative_to(DEST)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(DEST.rglob('*')) if p.is_file()]
 (DEST/'manifest.json').write_text(json.dumps({'target':'iPhone 16 Pro / iOS 27.0.1 / non-jailbroken / arm64','configuration_status':'PROVISIONAL_STATIC_IMPORT_CONFIGURATION','ipa_created':False,'runtime_verified':False,'files':hashes},indent=2)+'\n')
 return len(hashes)
if __name__=='__main__':print(json.dumps({'generated_files':build()}))
