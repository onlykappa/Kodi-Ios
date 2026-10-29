"""Static inspection of an isolated official Kodi.app; never executes target code."""
import argparse,hashlib,json,plistlib,struct
from pathlib import Path

def macho(data):
 assert len(data)>=32 and data[:4]==b'\xcf\xfa\xed\xfe','Expected thin little-endian Mach-O 64'
 _,cpu,subtype,filetype,ncmds,size,flags,reserved=struct.unpack_from('<8I',data)
 assert cpu==0x100000c,'Expected ARM64'
 assert size<=len(data)-32 and ncmds<=size//8,'Invalid load command bounds'
 cursor=32;loads=[];rpaths=[];platforms=[];signatures=[]
 for _ in range(ncmds):
  assert cursor+8<=32+size,'Truncated command'
  cmd,length=struct.unpack_from('<II',data,cursor)
  assert length>=8 and length%4==0 and cursor+length<=32+size,'Invalid command size'
  def string(offset):
   assert 0<=offset<length
   raw=data[cursor+offset:cursor+length];assert b'\0' in raw
   return raw.split(b'\0',1)[0].decode()
  if cmd in (0xc,0x80000018,0x8000001f,0x80000023):
   assert length>=24;loads.append({'name':string(struct.unpack_from('<I',data,cursor+8)[0]),'weak':cmd==0x80000018})
  if cmd==0x8000001c:
   assert length>=12;rpaths.append(string(struct.unpack_from('<I',data,cursor+8)[0]))
  if cmd==0x32:
   assert length>=24;platform,minos,sdk,ntools=struct.unpack_from('<4I',data,cursor+8)
   assert 24+ntools*8<=length
   platforms.append({'platform':platform,'minimum_os':version(minos),'sdk':version(sdk)})
  if cmd==0x25:
   assert length>=16;minos,sdk=struct.unpack_from('<II',data,cursor+8)
   platforms.append({'platform':'legacy-ios','minimum_os':version(minos),'sdk':version(sdk)})
  if cmd==0x1d:
   assert length==16;offset,count=struct.unpack_from('<II',data,cursor+8);assert offset+count<=len(data)
   signatures.append({'offset':offset,'bytes':count})
  cursor+=length
 assert cursor==32+size,'Load command count/size mismatch'
 return {'cpu':'arm64','cpu_subtype':subtype,'filetype':filetype,'platforms':platforms,'dylib_loads':loads,'rpaths':rpaths,'code_signature_commands':signatures,'encrypted':encrypted(data,ncmds)}
def encrypted(data,ncmds):
 cursor=32
 for _ in range(ncmds):
  cmd,length=struct.unpack_from('<II',data,cursor)
  if cmd in (0x21,0x2c):
   assert length>=20
   if struct.unpack_from('<I',data,cursor+16)[0]:return True
  cursor+=length
 return False
def version(v):return f'{v>>16}.{(v>>8)&255}.{v&255}'
def inspect(app):
 assert app.name=='Kodi.app' and app.is_dir() and not app.is_symlink()
 plist=plistlib.loads((app/'Info.plist').read_bytes());exe=plist['CFBundleExecutable']
 assert Path(exe).name==exe,'Unsafe executable path'
 binary=app/exe;assert not binary.is_symlink()
 info=macho(binary.read_bytes());assert not info['encrypted'],'Encrypted foundation'
 return {'app_name':app.name,'bundle_identifier':plist.get('CFBundleIdentifier'),'version':plist.get('CFBundleShortVersionString'),'bundle_version':plist.get('CFBundleVersion'),'minimum_os_plist':plist.get('MinimumOSVersion'),'supported_platforms':plist.get('CFBundleSupportedPlatforms'),'device_families':plist.get('UIDeviceFamily'),'executable':exe,'executable_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'executable_mode':oct(binary.stat().st_mode&0o777),'mach_o':info,'embedded_profile':(app/'embedded.mobileprovision').exists(),'signature_directory':(app/'_CodeSignature').exists(),'app_files':sum(p.is_file() for p in app.rglob('*')),'static_only':True,'ios_27_0_1_runtime_verified':False,'unsigned_ipa_created':False,'limitations':['Main executable parsed; nested native dependency/signature audit not complete','No independent detached signature authentication established','No entitlement validity, signer acceptance or device execution established']}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--deb',type=Path,required=True);a=p.parse_args()
 result=inspect(a.app);result['upstream_url']='https://mirrors.kodi.tv/releases/darwin/ios-arm64/org.xbmc.kodi-ios_21.3_iphoneos-arm64.deb';result['deb_sha256']=hashlib.sha256(a.deb.read_bytes()).hexdigest();result['deb_bytes']=a.deb.stat().st_size
 a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
