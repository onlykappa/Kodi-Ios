"""Compare all pinned upstream skin blobs to an isolated private recovery copy."""
import argparse,hashlib,json
from pathlib import Path

def compare(root,tree):
 assert not tree['truncated'],'Incomplete upstream tree'
 expected={f['path']:f for f in tree['files']};assert len(expected)==len(tree['files'])
 files={p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
 same=[];changed=[];absent=[]
 for name,f in expected.items():
  rel=Path(name);assert not rel.is_absolute() and '..' not in rel.parts
  p=files.get(name)
  if p is None:absent.append(name);continue
  assert not p.is_symlink(),'Symlink source not compared'
  data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  if blob==f['git_blob_sha']:same.append(name)
  else:changed.append({'path':name,'upstream_git_blob':f['git_blob_sha'],'private_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 extra=set(files)-set(expected)
 return {'upstream_commit':tree['commit'],'upstream_version':'3.4.8','upstream_file_count':len(expected),'installed_file_count':len(files),'matching_files':len(same),'changed_upstream_files':changed,'absent_upstream_files':sorted(absent),'additional_installed_file_count':len(extra),'comparison':'All upstream source/asset blobs against isolated private recovery; no target execution or original writes','source_experience_runtime_verified':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--upstream-tree',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 result=compare(a.private_root,json.loads(a.upstream_tree.read_text()));result['upstream_tree_metadata_sha256']=hashlib.sha256(a.upstream_tree.read_bytes()).hexdigest();a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('changed_upstream_files','absent_upstream_files')}))
