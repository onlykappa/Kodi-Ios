"""Copies every pinned third-party source of migration/provider-fallback/source-lock.json, as the build just downloaded and verified it, into one folder with the names the
lock's `mirror_base` expects. The build publishes that folder as a release of this repository (import-review.yml), so a source that disappears upstream never stops a build
again (provider_addons.source falls back to it, digest checked). Never reads accounts; nothing but the pinned archives and data files."""
import argparse,hashlib,json,shutil
from pathlib import Path
import provider_addons as providers

def preserve(inputs,output,lock=None):
 lock=lock or json.loads(providers.LOCK.read_text());inputs=Path(inputs);output=Path(output);output.mkdir(parents=True,exist_ok=True);names=[]
 for spec in lock['packages']+lock.get('provider_packages',[])+lock.get('data_assets',[]):
  source=inputs/(spec['file'] if spec.get('file') else spec.get('id',spec.get('name'))+'.zip');data=source.read_bytes()
  if hashlib.sha256(data).hexdigest()!=spec['sha256']:raise ValueError('Preserved source differs from its pin: '+providers.asset_name(spec))
  name=providers.asset_name(spec)
  if name in names:raise ValueError('Two pinned sources share a preserved name: '+name)
  (output/name).write_bytes(data);names.append(name)
 return names

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 print(json.dumps(preserve(args.inputs,args.output)))
