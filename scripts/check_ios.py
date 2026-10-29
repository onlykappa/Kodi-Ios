"""Static verification only; never certifies iPhone runtime compatibility."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def check(root=ROOT):
 dest=root/'migration/ios';manifest=json.loads((dest/'manifest.json').read_text())
 assert manifest['runtime_verified'] is False and manifest['ipa_created'] is False
 expected={x['path'] for x in manifest['files']}
 actual={str(p.relative_to(dest)) for p in dest.rglob('*') if p.is_file()}-{'manifest.json'}
 assert expected==actual,'Target manifest coverage'
 for item in manifest['files']:
  p=dest/item['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'Target hash mismatch'
  if p.suffix=='.json':json.loads(p.read_text())
  elif p.suffix=='.xml' or p.suffix=='.xsp':ET.parse(p)
 plan=json.loads((dest/'addon-plan.json').read_text());selected={a['id']:a for a in plan['addons']}
 for a in selected.values():
  assert not a['runtime_verified']
  for dep in a['requires']:
   assert dep['id'] in selected,'Missing required dependency'
   version=lambda s:tuple(map(int,re.match(r'[0-9.]+',s).group(0).rstrip('.').split('.')))
   if dep['minimum_version']:assert version(selected[dep['id']]['source_version_candidate'])>=version(dep['minimum_version']),'Candidate version below dependency requirement'
 valid={a['id'] for a in json.loads((root/'inventory/addons.json').read_text())['addons'] if a['manifest_valid']}
 contracts=root/'reports/drive-addon-contracts.json'
 if contracts.exists():valid.update(x['id'] for x in json.loads(contracts.read_text())['addons'])
 refs=set();playlists=set()
 for p in (dest/'userdata').rglob('*'):
  if not p.is_file():continue
  s=p.read_text()
  assert not re.search(r'umbrella|plugin.video.elementum|script.elementum|service.deck.keeper|script.loop.sportshub|plugin.video.the-loop|plugin.video.loop',s,re.I),'Excluded runtime reference'
  assert not re.search(r'/home/|/run/media/|/app/|\$\{|REDACTED_',s),'Unresolved target path'
  refs.update(re.findall(r'plugin://([A-Za-z0-9_.-]+)',s))
  for rel in re.findall(r'''special://profile/(playlists/[^<"'?&)]+\.xsp)''',s):
   assert (dest/'userdata'/rel).is_file(),'Missing playlist';playlists.add(rel)
 assert refs<=set(selected) and refs<=valid,'Plugin outside selected dependency plan'
 classification=json.loads((root/'reports/ios-compatibility.json').read_text())
 assert len(classification['records'])==len(json.loads((root/'inventory/addons.json').read_text())['addons'])
 assert all(not a['ios_runtime_verified'] and a['evidence'] for a in classification['records'])
 return {'passed':True,'static_only':True,'target_files':len(actual)+1,'dependency_candidates':len(selected),'plugin_references':sorted(refs),'referenced_playlists':len(playlists),'classified_manifest_records':len(classification['records']),'ios_runtime_verified':False,'limitations':'Candidate versions satisfy recorded numeric minimums; actual iOS availability, full source skin-code parity, touch operation and exact iOS 27.0.1 behavior not verified.'}
if __name__=='__main__':
 result=check();(ROOT/'reports/ios-static-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
