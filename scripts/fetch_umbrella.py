#!/usr/bin/env python3
"""Fetch the pinned Umbrella package from its upstream git repository and verify it (nothing is installed or built).

`python3 scripts/fetch_umbrella.py --output DIR [--preserved DIR]`: a preserved copy (matched by SHA-256 only) is used first; otherwise the exact upstream commit is
fetched with git (one commit, no file contents until asked) and the zip is read from it. Blob id, SHA-256 and size must match migration/umbrella/source-lock.json."""
import argparse,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'migration/umbrella/source-lock.json'

def git(args,cwd,run=subprocess.run):
    return run(['git']+args,cwd=cwd,check=True,capture_output=True).stdout

def fetch(lock=None,remote=None,run=subprocess.run,preserved=None):
    lock=lock or json.loads(LOCK.read_text());pkg=lock['package']
    if preserved:
        import provider_addons
        store=provider_addons.preserved_store(preserved)
        if pkg['sha256'] in store:
            data=store[pkg['sha256']].read_bytes()
            if len(data)==pkg['size'] and hashlib.sha256(data).hexdigest()==pkg['sha256']:return data
    with tempfile.TemporaryDirectory() as d:
        git(['init','-q'],d,run);git(['remote','add','o',remote or pkg['upstream_repository']+'.git'],d,run)
        git(['fetch','-q','--depth','1','--filter=blob:none','o',pkg['commit']],d,run)
        blob=git(['rev-parse','FETCH_HEAD:'+pkg['zip_path']],d,run).decode().strip()
        if blob!=pkg['git_blob']:raise ValueError('Umbrella package blob id mismatch')
        data=git(['show','FETCH_HEAD:'+pkg['zip_path']],d,run)
    if len(data)!=pkg['size'] or hashlib.sha256(data).hexdigest()!=pkg['sha256']:raise ValueError('Umbrella package digest mismatch')
    return data

def main():
    sys.path.insert(0,str(ROOT/'scripts'))
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preserved',type=Path,default=os.environ.get('KODI_IOS_PRESERVED_INPUTS') or None)
    a=p.parse_args();lock=json.loads(LOCK.read_text());data=fetch(lock,preserved=a.preserved)
    a.output.mkdir(parents=True,exist_ok=True);name='%s-%s.zip'%(lock['package']['id'],lock['package']['version']);(a.output/name).write_bytes(data)
    print(json.dumps({'file':name,'sha256':lock['package']['sha256'],'size':len(data)}))

if __name__=='__main__':main()
