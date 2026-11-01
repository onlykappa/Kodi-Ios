"""Exercise the full public review bundle on an isolated synthetic profile, never Kodi."""
import argparse,json,tempfile,hashlib
from pathlib import Path
from import_runtime.safe_import import prepare_export,apply_bundle,restore_clean,snapshot_hashes,validate_bundle,digest

def smoke(bundle,sha):
 manifest,addons,config=validate_bundle(bundle,sha)
 with tempfile.TemporaryDirectory(prefix='kodi-ios-full-import-') as tmp:
  base=Path(tmp);source=base/'synthetic-export';(source/'userdata').mkdir(parents=True)
  (source/'userdata/guisettings.xml').write_text('<settings version="2"><setting id="lookandfeel.skin">skin.estuary</setting><setting id="audio.device">synthetic-target</setting></settings>')
  target=prepare_export(source,base/'staged-profile');before=snapshot_hashes(target)
  result=apply_bundle(bundle,target,base/'private-clean-snapshots',sha)
  assert all((target/name).read_bytes()==body for name,body in addons.items()),'Source add-on bytes changed during apply'
  repeated=apply_bundle(bundle,target,base/'private-clean-snapshots',sha);assert repeated['writes']==0
  restore_clean(Path(result['backup']),target);assert snapshot_hashes(target)==before
 return {'passed':True,'bundle_sha256':sha,'addon_source_files_verified':len(addons),'configuration_files':len(config),'apply':'PASS','repeat_zero_writes':'PASS','restore_all_clean_hashes':'PASS','fixture':'synthetic private exported-profile copy','actual_phone_tested':False,'original_deck_read_or_written':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=smoke(a.bundle,digest(a.bundle.read_bytes()));a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
