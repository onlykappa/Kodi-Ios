"""Download the pinned Elementum client, its iPhoneOS engine framework, Burst and the Python modules they need,
verifying every byte. Writes nothing and exits 0 when the framework release is not pinned yet, so the IPA builds
without Elementum."""
import argparse,hashlib,json,shutil,subprocess,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'migration/elementum-ios/source-lock.json'

def fetch(url,tries=4):
 for attempt in range(tries):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'kodi-ios-build'}),timeout=120) as r:return r.read()
  except Exception:
   if attempt==tries-1:raise
   time.sleep(2**(attempt+1))

def git_modules(spec,dest):
 """Sparse checkout of the pinned commit; each add-on directory must match its pinned git tree hash."""
 with tempfile.TemporaryDirectory() as t:
  git=lambda *a:subprocess.run(['git','-C',t,*a],check=True,capture_output=True,text=True).stdout.strip()
  git('init','-q');git('sparse-checkout','set','--no-cone',*spec['trees'])
  for attempt in range(4):
   try:git('fetch','-q','--depth=1','--filter=blob:none','https://github.com/'+spec['repository'],spec['commit']);break
   except subprocess.CalledProcessError:
    if attempt==3:raise
    time.sleep(2**(attempt+1))
  git('checkout','-q','FETCH_HEAD');assert git('rev-parse','HEAD')==spec['commit']
  for id,tree in spec['trees'].items():
   assert git('rev-parse','HEAD:'+id)==tree,'Module tree mismatch: '+id
   shutil.copytree(Path(t)/id,dest/id)

def verified(get,url,sha,what):
 data=get(url);assert hashlib.sha256(data).hexdigest()==sha,what+' digest mismatch';return data

def run(out,lock=None,get=fetch,modules=git_modules):
 lock=lock or json.loads(LOCK.read_text());fw=lock.get('framework_release') or {}
 if not fw.get('sha256'):return {'elementum':False,'reason':'framework release not pinned'}
 client=verified(get,lock['plugin_release']['client_zip_url'],lock['plugin_release']['client_zip_sha256'],'Elementum client')
 framework=verified(get,'https://github.com/onlykappa/Kodi-Ios/releases/download/'+fw['tag']+'/'+fw['asset'],fw['sha256'],'Elementum framework')
 burst=verified(get,lock['burst']['url'],lock['burst']['sha256'],'Elementum Burst')
 out.mkdir(parents=True,exist_ok=True);modules(lock['modules'],out/'modules')
 (out/'client.zip').write_bytes(client);(out/'framework.zip').write_bytes(framework);(out/'burst.zip').write_bytes(burst)
 return {'elementum':True,'client_sha256':lock['plugin_release']['client_zip_sha256'],'framework_sha256':fw['sha256'],'burst_sha256':lock['burst']['sha256'],'modules':sorted(lock['modules']['trees'])}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.output)))
