"""Create reproducible upstream-only Kodi add-on ZIPs outside the repository.
Input files must match the pinned source-lock. No account profiles are accepted.
"""
import argparse,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from check_project import PATTERNS,source_secrets
ROOT=Path(__file__).resolve().parents[1]
def package(lock,cache,output,private_values=()):
 output=output.resolve();cache=cache.resolve()
 assert not output.is_relative_to(ROOT.resolve()),'Archives must remain outside Git'
 assert not output.is_relative_to(cache) and not cache.is_relative_to(output),'Separate input and output required'
 verified=[]
 for repo in lock['repositories']:
  selected=[];addonid=repo['addon_id']
  for entry in repo['files']:
   rel=Path(entry['path']);assert not rel.is_absolute() and '..' not in rel.parts
   path=cache/addonid/rel;assert not path.is_symlink()
   assert not any(p.is_symlink() for p in path.parents),'Symlink source parent'
   data=path.read_bytes();assert len(data)==entry['bytes']
   assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entry['git_blob_sha'],'Pinned source content mismatch'
   if rel.parts[0].startswith('.') or rel.parts[0]=='tests':continue
   assert rel.suffix.lower() in {'.py','.xml','.po','.png','.jpg','.jpeg','.txt','.md'} or rel.name=='LICENSE','Unexpected production file'
   assert not any(p.lower() in {'userdata','addon_data','accounts'} for p in rel.parts),'Account state path'
   assert not data.startswith((b'\x7fELF',b'MZ',b'\xcf\xfa\xed\xfe')),'Native executable payload'
   if rel.suffix.lower() in {'.py','.xml','.po','.txt','.md'} or rel.name=='LICENSE':
    text=data.decode('utf-8')
    assert not any(rx.search(text) for rx in PATTERNS.values()),'Secret pattern in upstream source'
    assert not any(v in text for v in private_values),'Matches private source value'
    if rel.suffix=='.py':compile(data,str(rel),'exec')
   selected.append((entry['path'],data))
  manifest=ET.fromstring(dict(selected)['addon.xml']);assert manifest.get('id')==addonid and manifest.get('version')==repo['version']
  assert any(p.startswith('LICENSE') for p,_ in selected),'License missing'
  verified.append((repo,selected))
 output.mkdir(parents=True,exist_ok=True)
 reports=[]
 for repo,selected in verified:
  filename=repo['addon_id']+'-'+repo['version']+'.zip';path=output/filename
  with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
   for name,data in sorted(selected):
    info=zipfile.ZipInfo(repo['addon_id']+'/'+name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED
    archive.writestr(info,data,compresslevel=9)
  with zipfile.ZipFile(path) as archive:
   assert archive.testzip() is None
   for name,data in selected:assert archive.read(repo['addon_id']+'/'+name)==data
  reports.append({'filename':filename,'addon_id':repo['addon_id'],'version':repo['version'],'source_commit':repo['commit'],'files':len(selected),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'archive_integrity_verified':True,'credentials_included':False,'personal_media_included':False,'ios_runtime_verified':False})
 return reports
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-source-userdata',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
 needles=source_secrets(a.private_source_userdata) if a.private_source_userdata else ()
 result={'packages':package(json.loads((ROOT/'migration/google-drive/source-lock.json').read_text()),a.source_cache,a.output,needles),'private_value_comparison_performed':bool(a.private_source_userdata),'scope':'Kodi add-on installation ZIPs only; not an IPA, not installed on the Steam Deck or iPhone'}
 if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
