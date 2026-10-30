"""Validate and apply a reviewed bundle ONLY to an explicitly marked private copy.
No Kodi runtime is executed. Actual iPhone transfer/activation/rollback need device tests.
"""
import hashlib,json,os,re,shutil,stat,tempfile,uuid,zipfile,xml.etree.ElementTree as ET
from pathlib import Path,PurePosixPath
MARKER='.kodi-ios-private-staging.json'
RECEIPT='.kodi-ios-import-receipt.json'
MAX_BYTES=2_000_000_000
class ImportFailure(RuntimeError):pass

def require(ok,message):
 if not ok:raise ImportFailure(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def relative(name):
 p=PurePosixPath(name)
 require(bool(name) and not p.is_absolute() and '\\' not in name and ':' not in name and '..' not in p.parts and p.as_posix()==name,'Unsafe archive path')
 return p

def safe_location(root):
 root=Path(root);resolved=root.resolve();text=resolved.as_posix()
 require('/.var/app/tv.kodi.Kodi' not in text and 'Kodi-iOS-Backups' not in resolved.parts and resolved.name!='.kodi','Original Kodi/backup paths are forbidden')
 require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents),'Symlink profile path')
 shared_roots={Path(tempfile.gettempdir()).resolve(),Path.home().resolve()}
 require(not any((p/'.git').exists() for p in [resolved,*resolved.parents] if p not in shared_roots),'Private profile cannot be inside a project repository')
 return root

def safe_profile(root,marked=True):
 root=safe_location(root)
 require(root.is_dir(),'Profile must be a real directory')
 if marked:require((root/MARKER).is_file(),'Explicit private staging marker required')
 for p in root.rglob('*'):require(not p.is_symlink(),'Profile symlinks are not accepted')
 return root

def snapshot_hashes(root):
 return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def prepare_export(source,destination):
 source=safe_profile(source,marked=False);destination=safe_location(destination)
 require(not destination.exists(),'Fresh staging destination required')
 require(not destination.resolve().is_relative_to(source.resolve()) and not source.resolve().is_relative_to(destination.resolve()),'Source/staging must not overlap')
 destination.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,destination)
 (destination/MARKER).write_text(json.dumps({'purpose':'Kodi iOS offline import staging','private_profile':True})+'\n')
 return destination

def archive_files(data,allow_identical_duplicates=False):
 import io
 result={};casefold_names={}
 try:
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   require(sum(i.file_size for i in z.infolist())<=MAX_BYTES,'Archive exceeds size limit')
   for info in z.infolist():
    name=info.filename.rstrip('/') if info.is_dir() else info.filename;relative(name)
    require(not stat.S_ISLNK(info.external_attr>>16),'Archive symlink rejected')
    if info.is_dir():continue
    previous=casefold_names.get(info.filename.casefold())
    body=z.read(info)
    if previous is not None:
     require(allow_identical_duplicates and result[previous]==body,'Duplicate/case-colliding archive member: '+previous+' / '+info.filename)
     continue
    casefold_names[info.filename.casefold()]=info.filename
    result[info.filename]=body
 except ImportFailure:raise
 except (zipfile.BadZipFile,RuntimeError,OSError) as e:raise ImportFailure('Corrupt or unreadable ZIP') from e
 return result

def version(text):
 match=re.match(r'^\d+(?:\.\d+)*',text or '')
 require(match is not None,'Invalid add-on version')
 return tuple(int(x) for x in match[0].split('.'))

def validate_bundle(path,expected_sha256):
 raw=Path(path).read_bytes();require(digest(raw)==expected_sha256,'Import SHA-256 mismatch')
 files=archive_files(raw)
 try:manifest=json.loads(files['manifest.json'])
 except (KeyError,ValueError) as e:raise ImportFailure('Missing/invalid import manifest') from e
 require(manifest.get('schema')==1,'Unsupported import schema')
 entries=manifest.get('files',[]);names=[e['path'] for e in entries]
 require(len(names)==len(set(names)) and set(files)==set(names)|{'manifest.json'},'Import file coverage mismatch')
 addons={};expanded={};config={}
 for entry in entries:
  name=entry['path'];data=files[name];relative(name)
  require(len(data)==entry['bytes'] and digest(data)==entry['sha256'],'Import content hash mismatch')
  if entry['kind']=='addon':
   content=archive_files(data)
   addonid=entry['addon_id'];require(bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]+',addonid)),'Invalid add-on ID')
   require(addonid not in addons,'Duplicate add-on ID')
   require(all(p.startswith(addonid+'/') for p in content),'Add-on root mismatch')
   try:xml=ET.fromstring(content[addonid+'/addon.xml'])
   except (KeyError,ET.ParseError) as e:raise ImportFailure('Missing/corrupt add-on manifest') from e
   require(xml.get('id')==addonid and xml.get('version')==entry['version'],'Add-on identity mismatch')
   for member,b in content.items():
    rel=PurePosixPath(member)
    require(not any(x in {'userdata','addon_data','__pycache__'} for x in rel.parts),'Private/runtime add-on path')
    require(rel.suffix.lower() not in {'.db','.sqlite','.sqlite3','.pyc','.pyo','.so','.dll','.dylib','.exe','.strm'},'Native/state payload rejected')
    require(not b.startswith((b'\x7fELF',b'MZ',b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe')),'Executable payload rejected')
   addons[addonid]={'version':xml.get('version'),'requires':[d for d in xml.findall('requires/import') if d.get('optional')!='true']}
   expanded.update({'addons/'+p:b for p,b in content.items()})
  elif entry['kind']=='configuration':
   require(name.startswith('configuration/userdata/'),'Configuration root mismatch')
   dest=name[len('configuration/'):];relative(dest)
   require(PurePosixPath(dest).suffix in {'.json','.xml','.xsp'},'Unexpected configuration format')
   require(not any(x in {'Database','Thumbnails','cache','temp'} for x in PurePosixPath(dest).parts),'Runtime profile data rejected')
   config[dest]=data
  else:require(entry['kind'] in {'documentation','tool'},'Unexpected import member role')
 expected=set(manifest.get('addon_ids',[]));require(set(addons)==expected,'Missing add-on package')
 provided=manifest.get('provided_addons',{})
 for id,a in addons.items():
  for dep in a['requires']:
   target=addons.get(dep.get('addon')) or provided.get(dep.get('addon'))
   require(target is not None,'Missing required add-on: '+str(dep.get('addon')))
   require(not dep.get('version') or version(target['version'])>=version(dep.get('version')),'Dependency below minimum: '+str(dep.get('addon')))
 return manifest,expanded,config

def merge_settings(current,incoming,defer_skin=False):
 try:
  target=ET.fromstring(current) if current else ET.Element('settings',{'version':'2'})
  source=ET.fromstring(incoming)
 except ET.ParseError as e:raise ImportFailure('Invalid target/import settings XML') from e
 require(target.tag==source.tag=='settings','Unexpected settings root')
 byid={x.get('id'):x for x in target.findall('setting')}
 for setting in source.findall('setting'):
  id=setting.get('id');require(bool(id),'Missing setting ID')
  if defer_skin and id=='lookandfeel.skin':continue
  if id in byid:target.remove(byid[id])
  target.append(setting)
 ET.indent(target);return ET.tostring(target,encoding='utf-8')+b'\n'

def apply_bundle(bundle,target,backup_dir,expected_sha256,fail_at=None):
 target=safe_profile(target);backup_dir=safe_location(backup_dir)
 require(not backup_dir.resolve().is_relative_to(target.resolve()),'Backup must be outside target')
 manifest,addons,config=validate_bundle(bundle,expected_sha256)
 receipt_path=target/RECEIPT
 if receipt_path.exists():
  receipt=json.loads(receipt_path.read_text())
  if receipt.get('bundle_sha256')==expected_sha256:
   require(all((target/p).is_file() and digest((target/p).read_bytes())==h for p,h in receipt['managed_files'].items()),'Managed file changed; owner review required before repeated import')
   return {'status':'ALREADY APPLIED','writes':0,'phone_verified':False}
  require(all((target/p).is_file() and digest((target/p).read_bytes())==h for p,h in receipt['managed_files'].items()),'Existing import conflicts with local changes')
 before=snapshot_hashes(target);backup_dir.mkdir(parents=True,exist_ok=True)
 backup=backup_dir/('clean-'+uuid.uuid4().hex);shutil.copytree(target,backup)
 require(snapshot_hashes(backup)==before,'Clean snapshot verification failed')
 stage=Path(tempfile.mkdtemp(prefix='.kodi-ios-import-',dir=target.parent));shutil.rmtree(stage);shutil.copytree(target,stage)
 prior=target.parent/('.kodi-ios-prior-'+uuid.uuid4().hex)
 managed={};renamed=False
 try:
  for name,data in {**addons,**config}.items():
   dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True)
   if (name.startswith('userdata/addon_data/') and name.endswith('/settings.xml')) or name=='userdata/guisettings.xml':data=merge_settings(dest.read_bytes() if dest.exists() else None,data,defer_skin=name=='userdata/guisettings.xml')
   dest.write_bytes(data);managed[name]=digest(data)
   if fail_at=='staging':raise ImportFailure('Injected staging failure')
  (stage/RECEIPT).write_text(json.dumps({'bundle_sha256':expected_sha256,'managed_files':managed,'pending_skin_activation':'skin.arctic.fuse.3','private_profile_do_not_publish':True},indent=2)+'\n')
  require(all(digest((stage/p).read_bytes())==h for p,h in managed.items()),'Staged result verification failed')
  os.replace(target,prior);renamed=True
  if fail_at=='commit':raise ImportFailure('Injected commit failure')
  os.replace(stage,target);renamed=False;shutil.rmtree(prior,ignore_errors=True)
  return {'status':'APPLIED TO PRIVATE STAGING','managed_files':len(managed),'backup':str(backup),'target_was_original':False,'phone_verified':False,'activation':'Kodi will discover copied non-system add-ons disabled; enable via Kodi after device transfer, then select Fuse'}
 except BaseException:
  if renamed and prior.exists():os.replace(prior,target)
  raise
 finally:
  if stage.exists():shutil.rmtree(stage)

def restore_clean(snapshot,target):
 target=safe_profile(target);snapshot=safe_profile(snapshot)
 require(not snapshot.resolve().is_relative_to(target.resolve()) and not target.resolve().is_relative_to(snapshot.resolve()),'Restore source/target overlap')
 stage=Path(tempfile.mkdtemp(prefix='.kodi-ios-restore-',dir=target.parent));shutil.rmtree(stage);shutil.copytree(snapshot,stage)
 expected=snapshot_hashes(snapshot);require(snapshot_hashes(stage)==expected,'Restore verification failed')
 prior=target.parent/('.kodi-ios-restore-prior-'+uuid.uuid4().hex);os.replace(target,prior)
 try:os.replace(stage,target)
 except BaseException:os.replace(prior,target);raise
 shutil.rmtree(prior);require(snapshot_hashes(target)==expected,'Restored profile mismatch')
 return {'status':'PRIVATE STAGED PROFILE RESTORED','files':len(expected),'phone_verified':False}


def export_private_profile(target,output):
 target=safe_profile(target);output=safe_location(output)
 require(not output.exists() and not output.resolve().is_relative_to(target.resolve()),'Fresh external private ZIP output required')
 output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(target.rglob('*')):
   if p.is_file():z.write(p,'Kodi/'+p.relative_to(target).as_posix())
 with zipfile.ZipFile(output) as z:require(z.testzip() is None,'Private export CRC failure')
 return {'status':'PRIVATE PROFILE ZIP EXPORTED','sha256':digest(output.read_bytes()),'contains_private_profile_state':True,'publish_to_github':False,'phone_transfer_tested':False}
