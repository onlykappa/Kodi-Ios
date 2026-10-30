"""Transactional profile seed; no addon database edits or native executable launches."""
import hashlib,json,os,shutil,xml.etree.ElementTree as ET
from pathlib import Path,PurePosixPath
ID='service.kodi.ios.bootstrap'
def sha(b):return hashlib.sha256(b).hexdigest()
def checked_name(name):
 p=PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix()!=name:raise ValueError('Unsafe seed path')
 return name

def tree_digest(root):
 parts=[]
 for path in sorted(root.rglob('*')):
  if path.is_symlink():raise ValueError('Skin source symlink refused')
  if path.is_file():parts.append(path.relative_to(root).as_posix()+' '+sha(path.read_bytes()))
 return sha(('\n'.join(parts)).encode())

def stage_skins(seed,home,descriptors,refresh):
 import uuid
 for item in descriptors:
  id=item['id']
  if not id.startswith('skin.') or '/' in id or '..' in id:raise ValueError('Invalid mutable skin ID')
  source=seed.parent.parent/id
  if tree_digest(source)!=item['tree_sha256']:raise ValueError('Packaged skin source hash mismatch')
 for item in descriptors:
  id=item['id'];source=seed.parent.parent/id;destination=home/'addons'/id
  if destination.is_symlink() or any(x.is_symlink() for x in destination.parents):raise ValueError('Writable skin symlink refused')
  if destination.exists():
   xml=ET.parse(destination/'addon.xml').getroot()
   if xml.get('id')!=id or xml.get('version')!=item['version']:raise ValueError('Existing writable skin version conflicts')
   continue # Preserve owner edits/generated files; no overwrite of an existing skin.
  destination.parent.mkdir(parents=True,exist_ok=True);temporary=destination.parent/('.ios-skin-'+uuid.uuid4().hex)
  try:
   shutil.copytree(source,temporary)
   if tree_digest(temporary)!=item['tree_sha256']:raise ValueError('Writable skin copy mismatch')
   os.replace(temporary,destination)
  finally:
   if temporary.exists():shutil.rmtree(temporary)
 if descriptors:
  if refresh is None:raise ValueError('Kodi rescan callback required for writable skins')
  refresh([home/'addons'/item['id'] for item in descriptors])

def restore(profile,api):
 state=profile/'addon_data'/ID;record=json.loads((state/'journal.json').read_text())
 for item in reversed(record['files']):
  dest=profile/checked_name(item['path'])
  if item['existed']:
   data=(state/'backup'/item['path']).read_bytes()
   if sha(data)!=item['backup_sha256']:raise ValueError('Recovery backup integrity mismatch')
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  elif dest.exists():dest.unlink()
 errors=[]
 for key,value in record.get('gui',{}).items():
  if api('Settings.SetSettingValue',{'setting':key,'value':value}).get('result') is not True:errors.append(key)
 for item in reversed(record.get('enabled',[])):
  if api('Addons.SetAddonEnabled',{'addonid':item,'enabled':False}).get('result')!='OK':errors.append(item)
 if api('Settings.SetSettingValue',{'setting':'lookandfeel.skin','value':'skin.estuary'}).get('result') is not True:errors.append('skin.estuary')
 if errors:
  (state/'status.json').write_text(json.dumps({'status':'RECOVERY INCOMPLETE','failed_api_requests':errors,'phone_verified':False}));raise RuntimeError('Recovery API requests failed')
 (state/'status.json').write_text(json.dumps({'status':'RESTORED','phone_verified':False}))
 return 'RESTORED'

def initialize(seed,profile,api,fail_after=None,verify_skin=None,home=None,refresh=None):
 seed=Path(seed);profile=Path(profile)
 if '/.var/app/tv.kodi.Kodi' in str(profile.resolve()) or profile.is_symlink():raise ValueError('Original Deck/symlink refused')
 manifest=json.loads((seed/'seed-manifest.json').read_text());state=profile/'addon_data'/ID;status=state/'status.json'
 if status.exists():return json.loads(status.read_text())['status']
 # Validate every input and all API availability before the first profile write.
 bodies={}
 for entry in manifest['files']:
  name=checked_name(entry['path']);data=(seed/name).read_bytes()
  if sha(data)!=entry['sha256']:raise ValueError('Seed hash mismatch')
  dest=profile/name
  if dest.is_symlink() or any(p.is_symlink() for p in dest.parents):raise ValueError('Profile symlink refused')
  bodies[name]=data
 states={}
 for addon in manifest['addons']:
  r=api('Addons.GetAddonDetails',{'addonid':addon,'properties':['enabled','version']})
  if 'error' in r:raise ValueError('Bundled add-on not registered: '+addon)
  states[addon]=r['result']['addon']['enabled']
 state.mkdir(parents=True,exist_ok=True);journal={'files':[],'enabled':[],'gui':{}}
 for name,data in bodies.items():
  if name=='guisettings.xml':continue
  dest=profile/name;entry={'path':name,'existed':dest.exists()}
  if dest.exists():
   original=dest.read_bytes();backup=state/'backup'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original);entry['backup_sha256']=sha(original)
  journal['files'].append(entry)
 def save():
  (state/'journal.json').write_text(json.dumps(journal,indent=2));status.write_text(json.dumps({'status':'IN PROGRESS','phone_verified':False}))
 save()
 try:
  stage_skins(seed,Path(home) if home is not None else profile.parent,manifest.get('mutable_skins',[]),refresh)
  for name,data in bodies.items():
   if name=='guisettings.xml':continue
   dest=profile/name
   if name.startswith('addon_data/') and name.endswith('/settings.xml') and dest.exists():
    old=ET.fromstring(dest.read_bytes());incoming=ET.fromstring(data);mapping={e.get('id'):e for e in old.findall('setting')}
    for entry in incoming.findall('setting'):
     if entry.get('id') in mapping:old.remove(mapping[entry.get('id')])
     old.append(entry)
    data=ET.tostring(old,encoding='utf-8')
   dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_name(dest.name+'.ios-seed-tmp');temp.write_bytes(data);os.replace(temp,dest)
   if fail_after=='files':raise RuntimeError('Injected setup failure')
  for addon,enabled in states.items():
   if enabled:continue
   # Persist intent before API mutation so recovery can undo an interrupted request.
   journal['enabled'].append(addon);save()
   if api('Addons.SetAddonEnabled',{'addonid':addon,'enabled':True}).get('result')!='OK':raise RuntimeError('Enable failed: '+addon)
  # Load the selected GUI preferences using Kodi's live API; never overwrite live guisettings.xml.
  gui=ET.fromstring(bodies['guisettings.xml'])
  for setting in gui.findall('setting'):
   key=setting.get('id')
   if key=='lookandfeel.skin':continue
   current=api('Settings.GetSettingValue',{'setting':key})
   if 'error' in current:raise RuntimeError('Unknown GUI setting: '+key)
   old=current['result']['value'];journal['gui'][key]=old;save();raw=setting.text or '';value=(raw.lower()=='true') if isinstance(old,bool) else int(raw) if isinstance(old,int) else raw
   if api('Settings.SetSettingValue',{'setting':key,'value':value}).get('result') is not True:raise RuntimeError('GUI preference failed: '+key)
  if api('Settings.SetSettingValue',{'setting':'lookandfeel.skin','value':'skin.arctic.fuse.3'}).get('result') is not True:raise RuntimeError('Skin activation failed')
  if verify_skin is not None and not verify_skin():raise RuntimeError('Fuse did not load or its confirmation was declined')
  status.write_text(json.dumps({'status':'COMPLETE','seed':manifest['version'],'phone_verified':False}))
  return 'COMPLETE'
 except BaseException:
  restore(profile,api);status.write_text(json.dumps({'status':'FAILED; RECOVERED TO ESTUARY','phone_verified':False}));raise
