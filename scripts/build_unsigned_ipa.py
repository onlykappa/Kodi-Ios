"""Create an unsigned diagnostic IPA from isolated, hash-pinned official app files.
Never executes Kodi. No profile bootstrap is injected; configuration imports separately.
"""
import argparse,hashlib,json,os,plistlib,shutil,stat,struct,zipfile
from pathlib import Path
from inspect_ios_foundation import macho
ROOT=Path(__file__).resolve().parents[1]
MACHO=b'\xcf\xfa\xed\xfe'
def unsign(data):
 info=macho(data);out=bytearray(data);n,size=struct.unpack_from('<II',data,16);cursor=32;commands=[];removed=0
 for _ in range(n):
  cmd,length=struct.unpack_from('<II',data,cursor)
  if cmd==0x1d:
   offset,count=struct.unpack_from('<II',data,cursor+8)
   assert offset>=32+size,'Signature overlaps headers'
   out[offset:offset+count]=b'\0'*count;removed+=1
  else:commands.append(data[cursor:cursor+length])
  cursor+=length
 if removed:
  new=b''.join(commands);struct.pack_into('<II',out,16,n-removed,len(new));out[32:32+size]=new+b'\0'*(size-len(new))
 assert not macho(out)['code_signature_commands']
 return bytes(out),removed

def zip_tree(root,path):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(root.rglob('*')):
   rel=p.relative_to(root).as_posix();mode=p.lstat().st_mode
   if p.is_dir() and not p.is_symlink():continue
   i=zipfile.ZipInfo(rel,(1980,1,1,0,0,0));i.create_system=3;i.external_attr=mode<<16;i.compress_type=zipfile.ZIP_DEFLATED
   data=os.readlink(p).encode() if p.is_symlink() else p.read_bytes();z.writestr(i,data,compresslevel=9)
 with zipfile.ZipFile(path) as z:assert z.testzip() is None
 return hashlib.sha256(path.read_bytes()).hexdigest()
def validate_staging(app,output):
 app=app.resolve();output=output.resolve()
 assert app.name=='Kodi.app' and app.is_dir(),'Isolated Kodi.app required'
 assert not output.is_relative_to(ROOT.resolve()),'Artifacts must remain outside Git'
 assert not output.is_relative_to(app) and not app.is_relative_to(output),'Separate source and output required'
 assert not output.exists(),'Fresh output directory required'

def build(app,output,deb):
 validate_staging(app,output)
 expected='c80e2e4eded0b3be9f9c8cd19a73e3f3ac7171575dd6f08cfddf14312ca81eb8'
 assert hashlib.sha256(deb.read_bytes()).hexdigest()==expected,'Foundation changed'
 output.mkdir(parents=True);stage=output/'stage';target=stage/'Payload/Kodi.app'
 shutil.copytree(app,target,symlinks=True)
 native=[];removed=[]
 for p in sorted(target.rglob('*')):
  if p.is_symlink():
   assert p.resolve().is_relative_to(target.resolve()),'External symlink';continue
  if not p.is_file():continue
  if p.name=='embedded.mobileprovision' or '_CodeSignature' in p.parts:
   removed.append(str(p.relative_to(target)));p.unlink();continue
  with p.open('rb') as f:magic=f.read(4)
  if magic==MACHO:
   old=p.read_bytes();new,count=unsign(old)
   if count:p.write_bytes(new)
   info=macho(new);assert not info['encrypted']
   native.append({'path':str(p.relative_to(target)),'signatures_removed':count,'sha256':hashlib.sha256(new).hexdigest(),'dylib_loads':info['dylib_loads'],'rpaths':info['rpaths']})
  elif magic in (b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xfe\xed\xfa\xce',b'\xfe\xed\xfa\xcf',b'\xce\xfa\xed\xfe'):
   raise AssertionError('Unsupported native format: '+str(p.relative_to(target)))
 assert native and any(x['path']=='Kodi' for x in native)
 unresolved=[]
 for entry in native:
  for load in entry['dylib_loads']:
   name=load['name']
   if name.startswith(('/System/Library/','/usr/lib/')):continue
   if name.startswith('@executable_path/'):candidate=target/name[len('@executable_path/'):]
   elif name.startswith('@loader_path/'):candidate=(target/entry['path']).parent/name[len('@loader_path/'):]
   else:
    unresolved.append({'image':entry['path'],'load':name,'reason':'Unsupported resolution expression','weak':load['weak']});continue
   if not candidate.exists():unresolved.append({'image':entry['path'],'load':name,'reason':'Missing bundled dependency','weak':load['weak']})
 assert not [x for x in unresolved if not x['weak']],'Unresolved required dylib dependencies'
 ipa=output/'Kodi-21.3-arm64-unsigned-candidate.ipa';digest=zip_tree(stage,ipa)
 with zipfile.ZipFile(ipa) as z:
  assert z.read('Payload/Kodi.app/Info.plist')==(target/'Info.plist').read_bytes()
  for entry in native:assert not macho(z.read('Payload/Kodi.app/'+entry['path']))['code_signature_commands']
 report={'filename':ipa.name,'sha256':digest,'bytes':ipa.stat().st_size,'foundation_sha256':expected,'native_images':len(native),'signature_commands_removed':sum(x['signatures_removed'] for x in native),'native_inventory':native,'removed_profile_signature_files':removed,'unresolved_weak_loads':unresolved,'zip_integrity_passed':True,'all_inspected_native_images_arm64':True,'active_embedded_signatures':False,'signing_required':True,'configuration_bundled':False,'addons_added':False,'personal_data_added':False,'device_tested':False,'sideloader_acceptance_verified':False,'status':'UNSIGNED_DIAGNOSTIC_CANDIDATE_NOT_MIGRATION_COMPLETE','limitations':['No active LC_CODE_SIGNATURE; original signature regions zeroed without truncation; signer must rebuild signatures/LINKEDIT as needed','System dyld shared-cache availability and entitlement requirements unverified','No migrated skin/add-on/configuration included in this diagnostic foundation','Full migrated IPA remains blocked on source parity/dependencies and device testing']}
 (output/'ipa-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='native_inventory'}))
 shutil.rmtree(stage)
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',type=Path);p.add_argument('--deb',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.app,a.output,a.deb)
