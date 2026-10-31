"""Verify an isolated recovery against private manifest and read-only source.
Never prints file contents, names from the private manifest, or account values.
"""
import argparse,json,hashlib,os,stat
from pathlib import Path
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('source',type=Path);p.add_argument('restored',type=Path);p.add_argument('--restore-mtimes',action='store_true');a=p.parse_args()
 source=a.source.resolve();restored=a.restored.resolve()
 assert not restored.is_relative_to(source) and not source.is_relative_to(restored),'Recovery must be isolated'
 entries=json.loads(a.manifest.read_text());seen=set();files=attrs=0
 for parent,dirs,names in os.walk(restored,followlinks=False):
  for name in dirs+names:seen.add(str((Path(parent)/name).relative_to(restored)))
 assert seen==set(entries),'Coverage mismatch'
 for key,e in entries.items():
  rel=Path(key);assert not rel.is_absolute() and '..' not in rel.parts
  original=source/rel;copy=restored/rel
  assert not any(x.is_symlink() for x in copy.parents if x!=restored.parent),'Symlink parent'
  s=copy.lstat();o=original.lstat()
  assert stat.S_IMODE(s.st_mode)==e['mode']
  if e['type']=='file':assert digest(copy)==e['sha256'] and s.st_size==e['size'];files+=1
  elif e['type']=='symlink':assert os.readlink(copy)==e['target']
  else:assert copy.is_dir()
  x={k:os.getxattr(original,k,follow_symlinks=False) for k in os.listxattr(original,follow_symlinks=False)}
  y={k:os.getxattr(copy,k,follow_symlinks=False) for k in os.listxattr(copy,follow_symlinks=False)}
  assert x==y;attrs+=len(x)
  assert (s.st_uid,s.st_gid)==(o.st_uid,o.st_gid)
  if a.restore_mtimes:os.utime(copy,ns=(e['mtime_ns'],e['mtime_ns']),follow_symlinks=False)
  assert copy.lstat().st_mtime_ns==e['mtime_ns'],'Use companion manifest to restore timestamp precision'
 print(json.dumps({'passed':True,'files':files,'entries':len(entries),'xattrs':attrs,'source_written':False}))
