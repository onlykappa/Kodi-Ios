"""Fetch and package pinned, Python-only movie/TV fallback engines. Never reads accounts or builds an IPA."""
import argparse,time,hashlib,io,json,re,shutil,sqlite3,stat,subprocess,tempfile,urllib.parse,urllib.request,zipfile
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'migration/provider-fallback/source-lock.json'
NATIVE=('.so','.dll','.dylib','.exe','.pyd','.a','.framework')

def digest(data):return hashlib.sha256(data).hexdigest()

# The Loop's repository only answers Kodi's own client (anything else gets a search-engine page). The owner approved fetching it as Kodi does (2026-11-15).
KODI_CLIENT='Kodi/21.3 (Linux; Android 11) App_Bitness/64 Version/21.3'
KODI_ONLY=('https://loopaddon.uk/',)

PRIVATE_RELEASE='https://github.com/onlykappa/Kodi-Ios/releases/download/provider-sources-1/'

def fetch(url):
 if url.startswith(PRIVATE_RELEASE):
  name=url[len(PRIVATE_RELEASE):]
  if name not in ('plugin.video.pov-6.11.03.zip','script.module.magneto-6.11.01.zip'):
   raise ValueError('Unapproved private provider asset')
  return subprocess.run(['gh','release','download','provider-sources-1','--repo','onlykappa/Kodi-Ios','--pattern',name,'--output','-'],check=True,stdout=subprocess.PIPE).stdout
 agent=KODI_CLIENT if url.startswith(KODI_ONLY) else 'Kodi-iOS-provider-build'
 for attempt in range(4):   # a download can fail on a passing network or proxy error; the digest check still decides what is accepted
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':agent}),timeout=120) as response:return response.read()
  except OSError:
   if attempt==3:raise
   time.sleep(2*(attempt+1))

def verified(path,spec):
 data=Path(path).read_bytes()
 if digest(data)!=spec['sha256']:raise ValueError('Provider archive digest mismatch: '+spec.get('id',spec.get('name','package')))
 return data

def members(data,prefix):
 """Reject traversal, links, duplicate paths and foreign executable code before extracting any archive."""
 result={}
 with zipfile.ZipFile(io.BytesIO(data)) as archive:
  for entry in archive.infolist():
   name=entry.filename;path=PurePosixPath(name)
   if entry.is_dir():continue
   if path.is_absolute() or '..' in path.parts or '\\' in name or not name.startswith(prefix) or stat.S_ISLNK(entry.external_attr>>16):
    raise ValueError('Unsafe provider archive entry')
   relative=name[len(prefix):]
   if not relative or relative in result:raise ValueError('Duplicate provider archive entry')
   if any(part.lower().endswith(NATIVE) for part in path.parts):raise ValueError('Native provider artifact is not supported on iOS')
   if relative.startswith(('userdata/','addon_data/','profile/')) or relative=='settings.xml':raise ValueError('Private profile state is not a provider source artifact')
   if '__pycache__' in path.parts or name.endswith(('.pyc','.pyo')):continue
   result[relative]=archive.read(entry)
 return result

def version(value):
 parts=[int(n) for n in re.findall(r'\d+',str(value).split('+',1)[0])]
 return tuple((parts+[0]*8)[:8])

def manifest(data,spec):
 root=ET.fromstring(data)
 if root.get('id')!=spec['id'] or root.get('version')!=spec['version']:raise ValueError('Provider manifest identity mismatch: '+spec['id'])
 return root

def patched_manifest(data,spec):
 root=manifest(data,spec);changes=[]
 for extension in list(root.findall('extension')):
  if spec.get('remove_services') and extension.get('point')=='xbmc.service':root.remove(extension);changes.append('disabled background service')
  if spec.get('hide_context_menus') and extension.get('point')=='kodi.context.item':
   for item in extension.findall('.//item'):
    visible=item.find('visible')
    if visible is None:visible=ET.SubElement(item,'visible')
    visible.text='false';changes.append('hidden unrelated context menu')
 requires=root.find('requires')
 for requirement in list(requires) if requires is not None else []:
  if requirement.get('addon') in spec.get('remove_requires',[]):requires.remove(requirement);changes.append('removed unused '+requirement.get('addon'))
 if not changes:return data,changes
 return ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n',changes

def restore_required_services(dest,spec,files):
 """Restore only a verified upstream service for a reused pinned add-on."""
 required=spec.get('required_services',[])
 if not required:return None
 installed=dest/'addon.xml';before=installed.read_bytes();root=ET.fromstring(before)
 upstream=manifest(files['addon.xml'],spec)
 if root.get('version')!=spec['version']:raise ValueError('Required service add-on version differs: '+spec['id'])
 changes=[]
 for library in required:
  original=[x for x in upstream.findall("extension[@point='xbmc.service']") if x.get('library')==library]
  if len(original)!=1 or library not in files:raise ValueError('Pinned provider service missing: '+spec['id'])
  path=dest/library
  if not path.is_file() or path.read_bytes()!=files[library]:raise ValueError('Reused provider service differs from pinned source: '+spec['id'])
  existing=root.findall("extension[@point='xbmc.service']")
  if len(existing)>1 or any(x.attrib!=original[0].attrib or len(x)!=len(original[0]) for x in existing):raise ValueError('Unexpected reused provider service: '+spec['id'])
  if not existing:root.append(original[0]);changes.append('restored required upstream service')
 if not changes:return None
 after=ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n';installed.write_bytes(after)
 return {'id':spec['id'],'path':'addon.xml','before_sha256':digest(before),'after_sha256':digest(after),'changes':changes}

def validate_asset(data,spec):
 if spec.get('bytes') is not None and len(data)!=spec['bytes']:raise ValueError('Provider data asset size mismatch')
 if spec.get('format')!='sqlite':raise ValueError('Unsupported provider data asset')
 if not data.startswith(b'SQLite format 3\0'):raise ValueError('Provider mapping database header mismatch')
 with tempfile.TemporaryDirectory() as temp:
  path=Path(temp)/'mappings.db';path.write_bytes(data)
  with sqlite3.connect('file:'+str(path)+'?mode=ro&immutable=1',uri=True) as database:
   if database.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Provider mapping database integrity failure')
   found={row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if found!=set(spec['tables']):raise ValueError('Unexpected provider mapping database tables')
   for table,required in spec['tables'].items():
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',table):raise ValueError('Invalid provider mapping table')
    columns={row[1] for row in database.execute('PRAGMA table_info('+table+')')}
    if not set(required)<=columns:raise ValueError('Provider mapping database schema mismatch')

_IPA={}

def from_ipa(spec,addon,get):
 """The archive of a pinned add-on rebuilt from the reviewed tree that shipped in an earlier published build (the IPA kept as a release asset, pinned by its own digest).
 Bytecode is left out; the entries are written in sorted order with fixed dates and no compression, so the archive's bytes, and its digest, are the same on every machine.
 (2026-11-24: the upstream repository of POV and its helper began answering 404; build 679's IPA is the preserved copy of what was reviewed.)"""
 key=spec['url']
 if key not in _IPA:
  data=get(key)
  if digest(data)!=spec['sha256']:raise ValueError('Preserved build digest mismatch')
  _IPA.clear();_IPA[key]=data
 prefix=spec['prefix'].rstrip('/')+'/'+addon+'/'
 out=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(_IPA[key])) as source,zipfile.ZipFile(out,'w',zipfile.ZIP_STORED) as archive:
  for name in sorted(source.namelist()):
   if not name.startswith(prefix) or name.endswith('/') or '__pycache__' in name or name.endswith(('.pyc','.pyo')):continue
   info=zipfile.ZipInfo(addon+'/'+name[len(prefix):],date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o644<<16
   archive.writestr(info,source.read(name))
 return out.getvalue()

def asset_name(spec):
 """The file name a pinned package has in the project's own copy (the `provider-sources` release): data assets keep their file name, add-ons are id-version.zip."""
 if spec.get('file'):return spec['file']
 return '%s-%s.zip'%(spec.get('id',spec.get('name')),spec['version'])

def mirror_url(lock,spec):
 base=(lock or {}).get('mirror_base')
 return base.rstrip('/')+'/'+urllib.parse.quote(asset_name(spec)) if base else None

def preserved_store(folder):
 """Content-addressed view of a folder of preserved inputs: {sha256: bytes of the file}. Files are only ever matched by their digest, so a renamed, damaged or
 tampered file is simply not found (and never trusted by name)."""
 store={}
 if folder:
  for path in sorted(Path(folder).rglob('*')):
   if path.is_file() and not path.is_symlink() and path.stat().st_size<=1<<30:store.setdefault(digest(path.read_bytes()),path)
 return store

def source(spec,get,lock=None,preserved=None):
 """The bytes of a pinned package, whose digest matches the lock: rebuilt from a preserved build when the lock names one (`from_ipa`), else downloaded from its pinned
 address, and when that fails or answers something else, from the project's own copy (`mirror_base`, the release that scripts/preserve_provider_sources.py fills).
 (2026-11-24: POV's upstream repository began answering 404 and stopped a build; every pinned source now has a copy that cannot go away.)"""
 name=spec.get('id',spec.get('name'))
 if preserved and spec['sha256'] in preserved:return preserved[spec['sha256']].read_bytes()   # the owner's preserved copy first: no network, same pinned digest
 if spec.get('from_ipa'):return from_ipa(spec['from_ipa'],spec['id'],get)
 mirror=mirror_url(lock,spec);failure=None
 for address in [spec['url']]+([mirror] if mirror else []):
  try:data=get(address)
  except OSError as error:failure=failure or error;continue
  if digest(data)==spec['sha256']:return data
  failure=failure or ValueError('Provider download digest mismatch: '+name)
 raise failure

def run(output,lock=None,get=fetch,preserved=None):
 lock=lock or json.loads(LOCK.read_text());output=Path(output);output.mkdir(parents=True,exist_ok=True);receipts=[]
 if isinstance(preserved,(str,Path)):preserved=preserved_store(preserved)
 for spec in lock['packages']+lock.get('provider_packages',[]):
  name=spec.get('id',spec.get('name'));data=source(spec,get,lock,preserved)
  if digest(data)!=spec['sha256']:raise ValueError('Provider download digest mismatch: '+name)
  members(data,spec.get('root',name+'/'))
  if 'id' in spec:manifest(members(data,name+'/')['addon.xml'],spec)
  (output/(name+'.zip')).write_bytes(data);receipts.append({'id':name,'sha256':spec['sha256']})
 for spec in lock.get('data_assets',[]):
  data=source(spec,get,lock,preserved)
  if digest(data)!=spec['sha256']:raise ValueError('Provider data asset digest mismatch: '+spec['name'])
  validate_asset(data,spec);(output/spec['file']).write_bytes(data);receipts.append({'id':spec['name'],'sha256':spec['sha256']})
 (output/'source-lock.json').write_text(json.dumps(lock,sort_keys=True)+'\n')
 return {'packages':receipts,'native_code':False,'accounts_included':False}

def install(inputs,addonroot,bootstrap,lock=None):
 """Install app add-ons, required writable copies, and the Prism scraper payload; report every source patch."""
 inputs=Path(inputs);addonroot=Path(addonroot);bootstrap=Path(bootstrap);lock=lock or json.loads(LOCK.read_text())
 if json.loads((inputs/'source-lock.json').read_text())!=lock:raise ValueError('Provider input lock differs from reviewed source lock')
 receipt={'addons':[],'profile_copies':[],'reused':[],'patches':[],'excluded':[],'providers':[],'data_assets':[]}
 # Minimums apply to the dependency graph, rather than forcing an older module over the foundation's newer one.
 minimums={}
 for spec in lock['packages']:
  data=verified(inputs/(spec['id']+'.zip'),spec);files=members(data,spec['id']+'/')
  root=manifest(files['addon.xml'],spec)
  for dependency in root.findall('requires/import'):
   if dependency.get('optional')=='true' or dependency.get('addon') in spec.get('remove_requires',[]):continue
   id=dependency.get('addon');minimums[id]=max(minimums.get(id,version('0')),version(dependency.get('version','0')))
 for spec in lock['packages']:
  id=spec['id'];dest=addonroot/id
  if (dest/'addon.xml').is_file():
   found=ET.parse(dest/'addon.xml').getroot()
   if found.get('id')!=id or version(found.get('version'))<minimums.get(id,version('0')):raise ValueError('Bundled provider dependency is too old: '+id)
   patch=restore_required_services(dest,spec,members(verified(inputs/(id+'.zip'),spec),id+'/'))
   if patch:receipt['patches'].append(patch)
   receipt['reused'].append({'id':id,'version':found.get('version')});continue
  if dest.exists():raise ValueError('Provider destination collision: '+id)
  files=members(verified(inputs/(id+'.zip'),spec),id+'/');before=files['addon.xml'];files['addon.xml'],changes=patched_manifest(before,spec)
  if changes:receipt['patches'].append({'id':id,'path':'addon.xml','before_sha256':digest(before),'after_sha256':digest(files['addon.xml']),'changes':changes})
  for library in spec.get('required_services',[]):
   if library not in files or not any(x.get('library')==library for x in ET.fromstring(files['addon.xml']).findall("extension[@point='xbmc.service']")):
    raise ValueError('Required provider service missing: '+id)
  for name,data in files.items():
   if name in spec.get('exclude_files',[]) or any(name.startswith(p) for p in spec.get('exclude_prefixes',[])):
    receipt['excluded'].append({'id':id,'path':name,'sha256':digest(data)});continue
   path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  receipt['addons'].append(id)
  if spec.get('profile_copy'):
   payload=bootstrap/'payload'/id
   if payload.exists():raise ValueError('Provider writable payload collision: '+id)
   shutil.copytree(dest,payload);receipt['profile_copies'].append(id)
 # Validate all non-core imports against the exact staged app, including reused dependencies.
 for spec in lock['packages']:
  id=spec['id'];root=ET.parse(addonroot/id/'addon.xml').getroot()
  for dependency in root.findall('requires/import'):
   dep=dependency.get('addon')
   if dependency.get('optional')=='true' or dep in lock.get('core_dependencies',[]):continue
   path=addonroot/dep/'addon.xml'
   if not path.is_file() or version(ET.parse(path).getroot().get('version'))<version(dependency.get('version','0')):raise ValueError('Missing provider dependency: '+id+' -> '+dep)
 for spec in lock.get('provider_packages',[]):
  files=members(verified(inputs/(spec['name']+'.zip'),spec),spec['root']);dest=bootstrap/spec['destination']
  for name,data in files.items():
   if name!='meta.json' and not name.startswith(('providers/','providerModules/','providerMedia/')) and not any(x in PurePosixPath(name).name.lower() for x in ('license','copying')):continue
   path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  receipt['providers'].append({'name':spec['name'],'version':spec['version'],'path':spec['destination'],'sha256':spec['sha256']})
 for license in lock.get('license_texts',[]):
  source=LOCK.parent/license['path'];data=source.read_bytes()
  if digest(data)!=license['sha256']:raise ValueError('Provider licence text digest mismatch')
  dest=bootstrap/'provider-fallback'/license['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 for spec in lock.get('data_assets',[]):
  data=verified(inputs/spec['file'],spec);validate_asset(data,spec)
  dest=bootstrap/spec['destination'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  receipt['data_assets'].append({'name':spec['name'],'path':spec['destination'],'sha256':spec['sha256'],'bytes':len(data)})
 # Keep public provenance/licence declarations with the shipped source, without storing any user profile state.
 notices={'source_lock':lock,'installation':receipt,'scope':'Movie/TV fallback only; existing account settings remain external.'}
 bootstrap.mkdir(parents=True,exist_ok=True);(bootstrap/'provider-fallback-notices.json').write_text(json.dumps(notices,indent=2)+'\n')
 return receipt

if __name__=='__main__':
 import os
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--preserved',type=Path,default=os.environ.get('KODI_IOS_PRESERVED_INPUTS') or None,help='folder of preserved inputs, matched by SHA-256 and used before any download')
 args=parser.parse_args()
 print(json.dumps(run(args.output,preserved=args.preserved),sort_keys=True))
