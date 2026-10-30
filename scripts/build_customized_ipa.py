"""Bundle the validated configuration in an isolated official app; no native patching."""
import argparse,contextlib,hashlib,io,json,shutil,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from build_unsigned_ipa import build as unsigned,validate_staging
from import_runtime.safe_import import validate_bundle,digest
import importlib.util
_spec=importlib.util.spec_from_file_location('ipa_bootstrap_helpers',Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/bootstrap.py')
_helpers=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_helpers)
tree_digest=_helpers.tree_digest
_navspec=importlib.util.spec_from_file_location('ipa_navigation',Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/navigation.py')
_nav=importlib.util.module_from_spec(_navspec);_navspec.loader.exec_module(_nav)
ROOT=Path(__file__).resolve().parents[1]
BOOT='service.kodi.ios.bootstrap'

def prepare(app,bundle,expected,work):
 validate_staging(app,work)
 manifest,addons,config=validate_bundle(bundle,expected)
 target=work/'Kodi.app';shutil.copytree(app,target,symlinks=True)
 manifests=list(target.rglob('system/addon-manifest.xml'));assert len(manifests)==1,'Unique Kodi system manifest required'
 system=manifests[0];base=system.parent.parent;addonroot=base/'addons';assert addonroot.is_dir()
 for name,data in addons.items():
  dest=base/name
  assert not dest.exists(),'Unexpected bundled addon collision: '+name
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 navigation_files=_nav.patch_skin(addonroot/'skin.arctic.fuse.3') if (addonroot/'skin.arctic.fuse.3').is_dir() else []
 bootstrap=addonroot/BOOT;shutil.copytree(ROOT/'migration/bundled-bootstrap',bootstrap)
 seed=bootstrap/'seed';seed.mkdir();entries=[]
 for name,data in sorted(config.items()):
  relative=name[len('userdata/'):]
  if relative=='guisettings.xml':
   gui=ET.fromstring(data)
   for setting in list(gui.findall('setting')):
    if setting.get('id')=='input.enablemouse':gui.remove(setting)
   data=ET.tostring(gui,encoding='utf-8')+b'\n'
  dest=seed/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);entries.append({'path':relative,'sha256':digest(data)})
 keymap=seed/'keymaps/zz-kodi-ios-navigation.xml';keymap.parent.mkdir(parents=True,exist_ok=True);keymap.write_bytes(_nav.TOUCH.encode()+b'\n');entries.append({'path':'keymaps/zz-kodi-ios-navigation.xml','sha256':digest(keymap.read_bytes())})
 # Topological dependency order, excluding native/core providers already in the foundation.
 requires={}
 for id in manifest['addon_ids']:
  xml=ET.parse(addonroot/id/'addon.xml').getroot();requires[id]=[d.get('addon') for d in xml.findall('requires/import') if d.get('optional')!='true']
 order=[];visiting=set()
 def visit(id):
  if id in order:return
  assert id not in visiting,'Dependency cycle';visiting.add(id)
  for dep in requires[id]:
   if dep in requires:visit(dep)
  visiting.remove(id);order.append(id)
 for id in sorted(requires):visit(id)
 mutable=[{'id':id,'version':ET.parse(addonroot/id/'addon.xml').getroot().get('version'),'tree_sha256':tree_digest(addonroot/id)} for id in order if id.startswith('skin.')]
 (seed/'seed-manifest.json').write_text(json.dumps({'version':'3-touch-r2','files':entries,'addons':order,'mutable_skins':mutable,'navigation_revision':_nav.REVISION},indent=2)+'\n')
 tree=ET.parse(system);root=tree.getroot();existing={a.text for a in root.findall('addon')}
 for id in order+[BOOT]:
  assert id not in existing,'System manifest collision';ET.SubElement(root,'addon',{} if id==BOOT else {'optional':'true'}).text=id
 ET.indent(root);tree.write(system,encoding='utf-8',xml_declaration=True)
 return target,{'addon_ids':order,'seed_files':entries,'system_manifest':str(system.relative_to(target)),'bootstrap_id':BOOT,'import_sha256':expected,'mutable_skins':mutable,'navigation_patch':{'revision':_nav.REVISION,'files':navigation_files}}

def build(app,bundle,expected,deb,output,work):
 staged,details=prepare(app,bundle,expected,work)
 # The shared native packer emits a diagnostic-only intermediate label; publish only the final verified customized report.
 with contextlib.redirect_stdout(io.StringIO()):report=unsigned(staged,output,deb)
 old=output/report['filename'];ipa=output/'Kodi-iOS-Customized-Touch-r2.ipa';old.rename(ipa)
 with zipfile.ZipFile(ipa) as z:
  assert z.testzip() is None
  base='Payload/Kodi.app/'+details['system_manifest'].rsplit('/system/',1)[0]
  for id in details['addon_ids']+[BOOT]:assert base+'/addons/'+id+'/addon.xml' in z.namelist()
  patches={'addons/skin.arctic.fuse.3/'+e['path']:e for e in details['navigation_patch']['files']}
  for name,body in validate_bundle(bundle,expected)[1].items():
   if name in patches:assert digest(body)==patches[name]['before_sha256'],'Navigation patch source mismatch'
   expected_hash=patches[name]['after_sha256'] if name in patches else digest(body)
   assert digest(z.read(base+'/'+name))==expected_hash,'Bundled addon bytes changed unexpectedly'
  for e in details['seed_files']:assert digest(z.read(base+'/addons/'+BOOT+'/seed/'+e['path']))==e['sha256']
 report.update(filename=ipa.name,sha256=digest(ipa.read_bytes()),configuration_bundled=True,addons_added=True,status='CUSTOMIZED_UNSIGNED_HOST_VALIDATED_DEVICE_TEST_PENDING',bootstrap=details,device_tested=False,manual_import_required=False,elementum_engine_included=False,navigation_revision=_nav.REVISION,patched_navigation_windows=len(details['navigation_patch']['files']),configuration_files=len(details['seed_files']),limitations=['iPhone bootstrap execution, skin rendering, signing, Google Drive and rollback still require actual device evidence','Use foreground Kodi; no unverified native engine or remote service'])
 (output/'ipa-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in {'native_inventory','bootstrap'}}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--deb',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();build(a.app,a.bundle,a.expected_sha256,a.deb,a.output,a.work)
