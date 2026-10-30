"""Build a credential-free review bundle from pinned public add-on archives.
Runs in isolated CI with network access; never reads original Kodi/account state.
"""
import argparse,ast,concurrent.futures,hashlib,io,json,re,shutil,sys,urllib.request,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from import_runtime.safe_import import archive_files,validate_bundle,digest,ImportFailure
ROOT=Path(__file__).resolve().parents[1]
CORE_NATIVE={'script.module.pil','inputstream.adaptive'}

def deterministic_zip(files):
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,body in sorted(files.items()):
   i=zipfile.ZipInfo(name,(1980,1,1,0,0,0));i.create_system=3;i.external_attr=0o100644<<16;i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,body)
 return data.getvalue()

def fetch(url):
 request=urllib.request.Request(url,headers={'User-Agent':'Kodi-iOS-reviewed-import/1'})
 with urllib.request.urlopen(request,timeout=90) as r:
  if not r.geturl().startswith('https://'):raise RuntimeError('HTTPS redirect required')
  return r.read()

def acquire(source):
 data=fetch(source['url'])
 if source.get('git_blob_sha'):
  actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert actual==source['git_blob_sha'],'Public Git blob mismatch'
 elif source.get('sha256'):assert digest(data)==source['sha256'],'Published digest mismatch'
 else:
  html=fetch(source['url']+'?mirrorlist').decode()
  flat=re.sub('<[^>]*>',' ',html)
  match=re.search(r'SHA256\s*([0-9a-f]{64})',flat,re.I)
  assert match and digest(data)==match[1].lower(),'Publisher mirror digest missing/mismatched'
 return data

def patch_helper(files,id):
 changes=[];prefix=id+'/'
 xmlpath=prefix+'addon.xml';root=ET.fromstring(files[xmlpath]);root.set('version','6.18.1+ios.1')
 root.find('requires').append(ET.Element('import',{'addon':'plugin.video.kodi.ios.watch','version':'1.0.0'}));ET.indent(root);files[xmlpath]=ET.tostring(root,encoding='utf-8')+b'\n'
 player=prefix+'resources/tmdbhelper/lib/player/dialog/player.py';text=files[player].decode();tree=ast.parse(text)
 methods=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='get_player'];assert len(methods)==1
 n=methods[0];lines=text.splitlines(keepends=True);indent=' '*(n.col_offset+4)
 replacement=lines[n.lineno-1]+indent+'from ios_watch_dialog import choose_player\n'+indent+'selected = choose_player(self)\n'+indent+'return self.set_resolver(selected) if selected else None\n'
 lines[n.lineno-1:n.end_lineno]=[replacement];files[player]=''.join(lines).encode();changes.append('Movie/episode resolver always requests explicit native Kodi watch choice before selecting a backend')
 item=prefix+'resources/tmdbhelper/lib/items/listitem.py';text=files[item].decode();old='        return BuildURL(self.path, **self.params).url';assert text.count(old)==1
 files[item]=text.replace(old,'        from ios_watch_routes import wrap_item\n        return wrap_item(self, BuildURL(self.path, **self.params).url)').encode();changes.append('TV show routes open watch/episode options; original metadata/art/context entries remain')
 return files,changes

def clean_addon(data,source):
 original=archive_files(data);id=source['id'];files={};dropped=[]
 # Some publisher ZIPs have a versioned directory or macOS packaging metadata.
 roots=[]
 for name,b in original.items():
  if Path(name).name!='addon.xml' or len(Path(name).parts)>2:continue
  try:manifest=ET.fromstring(b)
  except ET.ParseError:continue
  if manifest.get('id')==id and manifest.get('version')==source['version']:roots.append(name[:-len('addon.xml')])
 assert len(roots)==1,'Expected one matching manifest root for '+id+': '+str(sorted({x.split('/')[0] for x in original}))
 archive_root=roots[0]
 for archive_name,b in original.items():
  if archive_name.split('/')[0]=='__MACOSX' or Path(archive_name).name=='.DS_Store':dropped.append(archive_name);continue
  assert archive_name.startswith(archive_root),'Unexpected archive sibling for '+id+': '+archive_name
  name=id+'/'+archive_name[len(archive_root):]
  parts=Path(name).parts
  if any(x.startswith('.') or x in {'__pycache__','tests','test'} for x in parts[1:]) or Path(name).suffix in {'.pyc','.pyo'}:
   dropped.append(name);continue
  if id=='skin.arctic.fuse.3' and Path(name).name=='script-skinvariables-generator-includes-.xml':
   dropped.append(name);continue
  assert not any(x in {'userdata','addon_data'} for x in parts),'Private state path in source archive'
  files[name]=b
 xml=ET.fromstring(files[id+'/addon.xml']);assert xml.get('id')==id and xml.get('version')==source['version'],'Source manifest/version mismatch'
 patches=[]
 if id=='plugin.video.themoviedb.helper':files,patches=patch_helper(files,id)
 for name,b in files.items():
  if name.endswith('.py'):ast.parse(b.decode('utf-8-sig'),feature_version=(3,11))
 version=ET.fromstring(files[id+'/addon.xml']).get('version')
 return deterministic_zip(files),version,{'id':id,'source_version':source['version'],'import_version':version,'source_url':source['url'],'source_sha256':digest(data),'sanitized_archive_sha256':None,'dropped_cache_test_files':len(dropped),'patches':patches}

def drive_archives(output):
 lock=json.loads((ROOT/'migration/google-drive/source-lock.json').read_text());results=[]
 for repo in lock['repositories']:
  raw=fetch('https://github.com/'+repo['repository']+'/archive/'+repo['commit']+'.zip')
  content=archive_files(raw);prefix=next(iter(content)).split('/')[0]+'/'
  selected={}
  for f in repo['files']:
   b=content[prefix+f['path']];assert len(b)==f['bytes'] and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['git_blob_sha']
   if f['path'].split('/')[0].startswith('.') or f['path'].startswith('tests/'):continue
   selected[repo['addon_id']+'/'+f['path']]=b
  results.append((repo['addon_id'],repo['version'],deterministic_zip(selected),{'id':repo['addon_id'],'source_commit':repo['commit'],'git_tree_files_verified':len(repo['files'])}))
 return results

def build(output,foundation_report):
 output=output.resolve();assert not output.exists(),'Fresh output required'
 assert not output.is_relative_to(ROOT),'Archives stay outside Git'
 output.mkdir(parents=True)
 plan=json.loads((ROOT/'migration/ios/addon-plan.json').read_text());jurial={s['id']:s for s in json.loads((ROOT/'migration/import-inputs/jurial-sources.json').read_text())}
 sources=[]
 for a in plan['addons']:
  id=a['id']
  if id.startswith(('xbmc.','kodi.')) or id in CORE_NATIVE or id in {'plugin.googledrive','script.module.clouddrive.common'} or (ROOT/'migration/import-overlays'/id).is_dir():continue
  if id=='plugin.video.themoviedb.helper':base='6.18.1'
  else:base=a['source_version_candidate']
  if id in jurial:sources.append(jurial[id])
  else:sources.append({'id':id,'version':base,'url':'https://mirrors.kodi.tv/addons/omega/'+id+'/'+id+'-'+base+'.zip','kind':'zip','origin':'Official Kodi Omega archive and published mirror checksum'})
 acquired=[];failures=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  pending={pool.submit(acquire,s):s for s in sources}
  for future in concurrent.futures.as_completed(pending):
   s=pending[future]
   try:acquired.append((s,future.result()))
   except Exception as e:failures.append({'id':s['id'],'url':s['url'],'error_type':type(e).__name__,'error':str(e)[:240]})
 if failures:
  (output/'acquisition-failures.json').write_text(json.dumps(failures,indent=2)+'\n');print(json.dumps({'acquisition_failures':failures}));raise RuntimeError('Source acquisition incomplete; no complete import artifact created')
 payload={};entries=[];provenance=[]
 def add(path,data,kind,**kw):payload[path]=data;entries.append({'path':path,'kind':kind,'bytes':len(data),'sha256':digest(data),**kw})
 for source,data in sorted(acquired,key=lambda x:x[0]['id']):
  try:archive,ver,receipt=clean_addon(data,source)
  except Exception as error:
   failure={'id':source['id'],'error_type':type(error).__name__,'error':str(error),'source_url':source['url']}
   (output/'source-layout-failure.json').write_text(json.dumps(failure,indent=2)+'\n');print(json.dumps(failure));raise
  receipt['sanitized_archive_sha256']=digest(archive);provenance.append(receipt)
  add('addons/'+source['id']+'-'+ver+'.zip',archive,'addon',addon_id=source['id'],version=ver)
 for id,ver,data,receipt in drive_archives(output):
  provenance.append(receipt);add('addons/'+id+'-'+ver+'.zip',data,'addon',addon_id=id,version=ver)
 for directory in sorted((ROOT/'migration/import-overlays').iterdir()):
  if not directory.is_dir():continue
  content={directory.name+'/'+p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()};root=ET.fromstring(content[directory.name+'/addon.xml']);ver=root.get('version')
  add('addons/'+directory.name+'-'+ver+'.zip',deterministic_zip(content),'addon',addon_id=directory.name,version=ver)
 for p in sorted((ROOT/'migration/ios/userdata').rglob('*')):
  if p.is_file():add('configuration/userdata/'+p.relative_to(ROOT/'migration/ios/userdata').as_posix(),p.read_bytes(),'configuration')
 provided=json.loads(foundation_report.read_text());provided={id:{'version':values[0]['version'],'origin':'Verified official iOS foundation'} for id,values in provided['found'].items()}
 ids=[e['addon_id'] for e in entries if e['kind']=='addon']
 manifest={'schema':1,'addon_ids':ids,'files':entries,'provided_addons':provided,'primary_elementum_ios_engine_built':False,'owner_credentials_or_personal_media_added':False,'device_import_tested':False,'skin_activation':'Defer selecting Arctic Fuse until new addons have been enabled through Kodi; no direct addon SQLite edits'}
 for tool in [ROOT/'scripts/import_profile.py',ROOT/'scripts/import_runtime/__init__.py',ROOT/'scripts/import_runtime/safe_import.py']:
  rel=tool.relative_to(ROOT/'scripts').as_posix();add('tools/'+rel,tool.read_bytes(),'tool')
 add('INSTALL.md',(ROOT/'docs/iphone-import.md').read_bytes(),'documentation')
 payload['manifest.json']=json.dumps(manifest,indent=2).encode()+b'\n'
 bundle=output/'Kodi-iOS-Customized-Import.zip';bundle.write_bytes(deterministic_zip(payload));sha=digest(bundle.read_bytes())
 validate_bundle(bundle,sha)
 report={'filename':bundle.name,'sha256':sha,'bytes':bundle.stat().st_size,'addon_packages':len(ids),'addon_ids':ids,'configuration_files':sum(e['kind']=='configuration' for e in entries),'provided_dependencies':provided,'provenance':provenance,'integrity_and_closure_passed':True,'native_engine_included':False,'owner_credentials_included':False,'device_tested':False}
 (output/'import-review-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in {'provenance','provided_dependencies'}}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--foundation-report',type=Path,required=True);a=p.parse_args();build(a.output,a.foundation_report)
