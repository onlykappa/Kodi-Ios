"""Prepare/apply/restore ONLY private staged copies of an owner-exported iOS profile."""
import argparse,json
from pathlib import Path
from import_runtime.safe_import import prepare_export,apply_bundle,restore_clean,export_private_profile
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 prep=sub.add_parser('prepare');prep.add_argument('--from-export',type=Path,required=True);prep.add_argument('--output',type=Path,required=True)
 app=sub.add_parser('apply');app.add_argument('--bundle',type=Path,required=True);app.add_argument('--target',type=Path,required=True);app.add_argument('--backups',type=Path,required=True);app.add_argument('--expected-sha256',required=True)
 restore=sub.add_parser('restore');restore.add_argument('--snapshot',type=Path,required=True);restore.add_argument('--target',type=Path,required=True)
 exp=sub.add_parser('export');exp.add_argument('--target',type=Path,required=True);exp.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 if a.action=='prepare':prepare_export(a.from_export,a.output);result={'status':'PRIVATE COPY PREPARED','phone_verified':False}
 elif a.action=='apply':result=apply_bundle(a.bundle,a.target,a.backups,a.expected_sha256)
 elif a.action=='restore':result=restore_clean(a.snapshot,a.target)
 else:result=export_private_profile(a.target,a.output)
 print(json.dumps(result,indent=2))
