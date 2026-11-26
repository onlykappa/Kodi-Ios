#!/usr/bin/env python3
"""Pin and rebuild the four Python modules Crew downloads and runs at every use (control.cdnImport): crewproxy, crewstreamer, crewschedule, crewreplays.

Crew fetches them from raw.githubusercontent.com/posadka/xmls2/main/<name>.xml (Python source despite the extension), always tries the network first and keeps a disk
copy as the fallback. This script reads the pinned upstream commit with git, checks every blob id and SHA-256 against migration/crew-remote/source-lock.json and builds the
deterministic archive `crew-remote-modules-<commit8>.zip` (fixed dates, stored, sorted) whose digest the lock also pins. Nothing is installed or run."""
import hashlib,io,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'migration/crew-remote/source-lock.json'
FOLDER='crew-remote-modules'

def git(args,cwd):return subprocess.run(['git']+args,cwd=cwd,check=True,capture_output=True).stdout

def readme(lock):
    lines=['Crew remote modules, preserved %s'%lock['commit'][:8],'',
     'Upstream: %s at commit %s (%s)'%(lock['upstream_repository'],lock['commit'],lock['commit_date']),
     'Crew (script.module.thecrew) downloads these four files at every use and runs them as Python (control.cdnImport), keeping a disk copy as its fallback.',
     'They are Python source even though they end in .xml. This archive is a frozen copy; upstream changes them often (the latest commit is days old).','']
    lines+=['%s  git blob %s  sha256 %s  %d bytes'%(m['path'],m['git_blob'],m['sha256'],m['size']) for m in lock['modules']]
    return '\n'.join(lines)+'\n'

def build_zip(lock,blobs):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_STORED) as z:
        for name,body in sorted([(FOLDER+'/README.txt',readme(lock).encode())]+[(FOLDER+'/'+m['path'],blobs[m['path']]) for m in lock['modules']]):
            zi=zipfile.ZipInfo(name,(1980,1,1,0,0,0));zi.external_attr=0o644<<16;zi.compress_type=zipfile.ZIP_STORED;z.writestr(zi,body)
    return out.getvalue()

def fetch(lock=None,remote=None):
    lock=lock or json.loads(LOCK.read_text());blobs={}
    with tempfile.TemporaryDirectory() as d:
        git(['init','-q'],d);git(['remote','add','o',remote or lock['upstream_repository']+'.git'],d);git(['fetch','-q','--depth','1','--filter=blob:none','o',lock['commit']],d)
        for m in lock['modules']:
            if git(['rev-parse','FETCH_HEAD:'+m['path']],d).decode().strip()!=m['git_blob']:raise ValueError('blob id mismatch: '+m['path'])
            data=git(['show','FETCH_HEAD:'+m['path']],d)
            if hashlib.sha256(data).hexdigest()!=m['sha256'] or len(data)!=m['size']:raise ValueError('digest mismatch: '+m['path'])
            blobs[m['path']]=data
    archive=build_zip(lock,blobs);a=lock['archive']
    if hashlib.sha256(archive).hexdigest()!=a['sha256'] or len(archive)!=a['size']:raise ValueError('archive digest mismatch')
    return archive

def stage(bootstrap,archive=None):
    """Build step: put the four pinned modules into <bootstrap>/crew_remote/ so the app can seed Crew's disk fallback on a phone that cannot download them.
    Returns the number staged; 0 when the preserved archive is missing or only a Git LFS pointer (a checkout without `git lfs pull`). A wrong digest raises."""
    lock=json.loads(LOCK.read_text());a=lock['archive'];path=Path(archive) if archive else ROOT/'migration/addon-preserve'/(a['id']+'-'+a['version']+'.zip')
    if not path.is_file() or path.stat().st_size<1000:return 0
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=a['sha256']:raise ValueError('preserved Crew module archive digest mismatch')
    dest=Path(bootstrap)/'crew_remote';dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for m in lock['modules']:
            body=z.read(FOLDER+'/'+m['path'])
            if hashlib.sha256(body).hexdigest()!=m['sha256']:raise ValueError('module digest mismatch: '+m['path'])
            (dest/m['path']).write_bytes(body)
    return len(lock['modules'])

if __name__=='__main__':
    out=Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir(parents=True,exist_ok=True);lock=json.loads(LOCK.read_text());(out/(lock['archive']['id']+'-'+lock['archive']['version']+'.zip')).write_bytes(fetch(lock));print('ok')
