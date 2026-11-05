"""Compare only navigation upgrade overhead on isolated copies of a supplied Fuse skin.

Does not start Kodi, download anything or measure time to visible posters. The same current portrait generator
prepares both variants, so this isolates the navigation change. Input skin/profile remain read-only.
"""
import argparse,importlib.util,json,shutil,statistics,subprocess,sys,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import navigation,portrait

def benchmark(source,before_ref,samples):
 result={'scope':'navigation subsystem only; Linux host, no Kodi renderer or iPhone',
         'before_ref':before_ref,'samples':samples,'calls_per_sample':2,'metrics':{}}
 with tempfile.TemporaryDirectory(prefix='kodi-startup-checks-') as tmp:
  tmp=Path(tmp);oldfile=tmp/'navigation_before.py'
  oldfile.write_bytes(subprocess.check_output(['git','show',before_ref+':migration/bundled-bootstrap/resources/lib/navigation.py'],cwd=ROOT))
  spec=importlib.util.spec_from_file_location('navigation_before',oldfile);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
  for label,nav in [('before',old),('after',navigation)]:
   home=tmp/label;skin=home/'addons/skin.arctic.fuse.3';profile=home/'userdata'
   shutil.copytree(source,skin);shutil.copytree(ROOT/'migration/ios/userdata',profile)
   nav.upgrade(home,profile);portrait.build(skin,profile);portrait.refresh_if_needed(skin,profile);nav.upgrade(home,profile)
   timings=[]
   for _ in range(samples):
    start=time.perf_counter();first=nav.upgrade(home,profile);second=nav.upgrade(home,profile)
    timings.append(time.perf_counter()-start)
    if first['changed_files'] or second['changed_files']:raise RuntimeError('Warm sample unexpectedly modified the skin')
   result['metrics'][label]={'seconds':timings,'median_seconds':statistics.median(timings),
                             'skin_xml_files':len(list((skin/'1080i').glob('*.xml'))),
                             'templates':len(list((skin/nav.TEMPLATES).glob('*.xmltemplate')))}
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--skin-source',type=Path,required=True)
 parser.add_argument('--before-ref',default='fbedba8c6602c7085d9d19794adb21e9005bdf70')
 parser.add_argument('--samples',type=int,default=5)
 args=parser.parse_args()
 if args.samples<1:parser.error('--samples must be positive')
 print(json.dumps(benchmark(args.skin_source,args.before_ref,args.samples),indent=2))
