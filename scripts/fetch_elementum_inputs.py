"""Download the pinned Elementum client, its iPhoneOS engine framework, Burst and the Python modules they need,
verifying every byte. Writes nothing and exits 0 when the framework release is not pinned yet, so the IPA builds
without Elementum."""
import argparse,hashlib,json,shutil,subprocess,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'migration/elementum-ios/source-lock.json'
AIRPLAY=ROOT/'migration/airplay-ios/source-lock.json'

def fetch(url,tries=4):
 for attempt in range(tries):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'kodi-ios-build'}),timeout=120) as r:return r.read()
  except Exception:
   if attempt==tries-1:raise
   time.sleep(2**(attempt+1))

def git_modules(specs,dest):
 """Sparse checkout of each pinned commit; each add-on directory must match its pinned git tree hash."""
 for spec in specs if isinstance(specs,list) else [specs]:git_tree(spec,dest)

def tar_name(spec):
 return spec['repository'].replace('/','_')+'-'+spec['commit'][:10]+'.tar'

def tree_hashes(root,ids):
 """Git's own tree hash of each directory `ids` under `root` (a scratch repository: add, write-tree), to compare with the pinned ones."""
 import os
 env=dict(os.environ,GIT_AUTHOR_NAME='x',GIT_AUTHOR_EMAIL='x@x',GIT_COMMITTER_NAME='x',GIT_COMMITTER_EMAIL='x@x')
 git=lambda *a:subprocess.run(['git','-C',str(root),*a],check=True,capture_output=True,text=True,env=env).stdout.strip()
 git('init','-q');git('config','core.autocrlf','false');git('add','-A');tree=git('write-tree')
 return {i:git('rev-parse',tree+':'+i) for i in ids}

def kept_tree(spec,dest,get=None):
 """The pinned modules from the kept copy (a tar of the trees written by git_tree), accepted only when every tree hash equals the pin."""
 import io,source_mirror,tarfile
 get=get or fetch
 def check(data):
  with tempfile.TemporaryDirectory() as t,tarfile.open(fileobj=io.BytesIO(data)) as tar:
   tar.extractall(t,filter='data')
   assert tree_hashes(t,list(spec['trees']))==spec['trees'],'Kept module trees differ from their pins'
 data=source_mirror.mirrored('https://x/'+tar_name(spec),get,check)
 with tarfile.open(fileobj=io.BytesIO(data)) as tar:tar.extractall(dest,filter='data')

def git_tree(spec,dest):
 with tempfile.TemporaryDirectory() as t:
  git=lambda *a:subprocess.run(['git','-C',t,*a],check=True,capture_output=True,text=True).stdout.strip()
  try:
   git('init','-q');git('sparse-checkout','set','--no-cone',*spec['trees'])
   for attempt in range(4):
    try:git('fetch','-q','--depth=1','--filter=blob:none','https://github.com/'+spec['repository'],spec['commit']);break
    except subprocess.CalledProcessError:
     if attempt==3:raise
     time.sleep(2**(attempt+1))
   git('checkout','-q','FETCH_HEAD');assert git('rev-parse','HEAD')==spec['commit']
  except subprocess.CalledProcessError as upstream:
   print('modules '+spec['repository']+': upstream failed ('+str(upstream.stderr)[:100]+'); trying the kept copy',flush=True)
   kept_tree(spec,dest);return
  for id,tree in spec['trees'].items():
   assert git('rev-parse','HEAD:'+id)==tree,'Module tree mismatch: '+id
   shutil.copytree(Path(t)/id,dest/id)
 import io,source_mirror,tarfile
 buffer=io.BytesIO()
 with tarfile.open(fileobj=buffer,mode='w') as tar:
  for id in spec['trees']:tar.add(dest/id,arcname=id)
 source_mirror.keep(tar_name(spec),buffer.getvalue())

def verified(get,url,sha,what,mirror=None,preserved=None):
 """The download, checked against its pinned digest. Third-party files (`mirror` = a fetcher for the kept copies, source_mirror) fall back to the kept copy when the
 upstream address fails, and are kept again for the next emergency; our own releases are not mirrored."""
 def check(data):assert hashlib.sha256(data).hexdigest()==sha,what+' digest mismatch'
 if preserved and sha in preserved:   # the owner's preserved copy first, matched by digest only (a tampered file is never found); no network
  data=preserved[sha].read_bytes();check(data);return data
 if mirror is None:data=get(url);check(data);return data
 import source_mirror
 def primary(u):
  data=get(u);check(data);return data
 data,kept=source_mirror.fetch(url,primary,mirror,check,log=lambda m:print(what+': '+m,flush=True))
 if not kept:source_mirror.keep(source_mirror.asset_name(url),data)
 return data

def run(out,lock=None,get=fetch,modules=git_modules,airplay=None,mirror=None,preserved=None):
 if isinstance(preserved,(str,Path)):
  import provider_addons;preserved=provider_addons.preserved_store(preserved)
 mirror=mirror if mirror is not None else (fetch if get is fetch else None)
 lock=lock or json.loads(LOCK.read_text());fw=lock.get('framework_release') or {}
 airplay=airplay or json.loads(AIRPLAY.read_text())['framework_release']
 if not fw.get('sha256'):return {'elementum':False,'reason':'framework release not pinned'}
 client=verified(get,lock['plugin_release']['client_zip_url'],lock['plugin_release']['client_zip_sha256'],'Elementum client',mirror,preserved)
 framework=verified(get,'https://github.com/onlykappa/Kodi-Ios/releases/download/'+fw['tag']+'/'+fw['asset'],fw['sha256'],'Elementum framework',None,preserved)
 burst=verified(get,lock['burst']['url'],lock['burst']['sha256'],'Elementum Burst',mirror,preserved)
 extras={id:verified(get,x['url'],x['sha256'],id,mirror,preserved) for id,x in sorted(lock.get('extras',{}).items())}
 # Other native frameworks for Kodi.app/Frameworks, each published once per tag by its own macOS workflow.
 frameworks={}
 if airplay.get('sha256'):
  frameworks['KodiAirPlay']=verified(get,'https://github.com/onlykappa/Kodi-Ios/releases/download/'+airplay['tag']+'/'+airplay['asset'],airplay['sha256'],'AirPlay framework',None,preserved)
 out.mkdir(parents=True,exist_ok=True);modules(lock['modules'],out/'modules')
 # 'app' add-ons ship inside Kodi.app; 'profile' ones are copied into the writable add-ons folder at first start.
 for id,data in extras.items():
  dest=out/('extras-'+lock['extras'][id]['install'])/(id+'.zip');dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
 for name,data in frameworks.items():
  dest=out/'frameworks'/(name+'.framework.zip');dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)
 (out/'client.zip').write_bytes(client);(out/'framework.zip').write_bytes(framework);(out/'burst.zip').write_bytes(burst)
 return {'elementum':True,'client_sha256':lock['plugin_release']['client_zip_sha256'],'framework_sha256':fw['sha256'],'burst_sha256':lock['burst']['sha256'],'modules':sorted(id for spec in (lock['modules'] if isinstance(lock['modules'],list) else [lock['modules']]) for id in spec['trees']),'extras':sorted(extras),'frameworks':sorted(frameworks)}

if __name__=='__main__':
 import os
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
 p.add_argument('--preserved',type=Path,default=os.environ.get('KODI_IOS_PRESERVED_INPUTS') or None,help='folder of preserved inputs, matched by SHA-256 and used before any download')
 a=p.parse_args();print(json.dumps(run(a.output,preserved=a.preserved)))
