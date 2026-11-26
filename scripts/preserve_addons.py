#!/usr/bin/env python3
"""Preserved copies of the add-ons the phone has beyond the IPA (Umbrella, the Loop/Jet set): manifest, scanner and builder.

`migration/addon-preserve/*.zip` are Git LFS objects of the exact upstream archives pinned in migration/umbrella/source-lock.json and
migration/loop-addons/source-lock.json. `manifest.json` lists each one (id, version, sha256, bytes, the lock it must match, its notice file and any secret-shaped
text a person reviewed). `verify()` is what scripts/check_project.py runs: digest and lock match, safe members, no native code, and every secret-shaped match
must be a reviewed one for that exact member content. `build` (python3 scripts/preserve_addons.py build) refetches from the pins and rewrites the files.

Reviewed matches are third-party API keys that the upstream add-ons publish inside their own source (Umbrella's TMDb/Fanart/OpenSubtitles/YouTube keys, an Airtable
key in The Loop). They are not the owner's secrets (the archives come from public upstream repositories, never from the phone); a changed member is no longer reviewed."""
import hashlib,io,json,re,stat,sys,zipfile
from pathlib import Path,PurePosixPath
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'migration/addon-preserve'
MANIFEST=DIR/'manifest.json'
NATIVE=('.so','.dylib','.dll','.exe','.a','.o','.pyc','.pyo','.pyd','.node','.wasm')
TEXT=('.py','.xml','.po','.txt','.md','.rst','.json','.js','.html','.css','.cfg','.ini','.yml','.yaml','.csv','.tab','.zi','.pyi','.typed','.sh','.m3u','.m3u8','.srt','.strings')

def patterns():
    import check_project
    return check_project.PATTERNS

def member_hits(z,rx):
    """[(member, pattern name, sha256 of the member bytes)] for every secret-shaped match in text members."""
    out=[]
    for e in z.infolist():
        if e.is_dir() or not e.filename.lower().endswith(TEXT):continue
        body=z.read(e)
        try:text=body.decode('utf-8')
        except UnicodeDecodeError:continue
        for name,pat in rx.items():
            if pat.search(text):out.append((e.filename,name,hashlib.sha256(body).hexdigest()))
    return out

def locked(spec):
    """The (sha256, bytes) the named lock pins for this archive, or None."""
    lock=json.loads((ROOT/spec['lock']).read_text())
    if spec.get('lock_key'):
        p=lock[spec['lock_key']];return p['sha256'],p['size']
    for p in lock['packages']:
        if p['id']==spec['id'] and p['version']==spec['version']:return p['sha256'],p['size']
    return None

def check(spec,data,rx=None,needles=()):
    """Raises ValueError with a short reason, else returns."""
    rx=rx or patterns()
    if hashlib.sha256(data).hexdigest()!=spec['sha256'] or len(data)!=spec['bytes']:raise ValueError('digest')
    pinned=locked(spec)
    if pinned!=(spec['sha256'],spec['bytes']):raise ValueError('not the pinned archive')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        top=spec.get('folder') or spec['id'];seen=set()
        if spec['notice'] not in z.namelist():raise ValueError('notice')
        for e in z.infolist():
            name=PurePosixPath(e.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in e.filename or stat.S_ISLNK(e.external_attr>>16) or e.filename in seen or name.parts[0]!=top:raise ValueError('path')
            seen.add(e.filename)
            if name.suffix.lower() in NATIVE:raise ValueError('native code or bytecode')
        reviewed={(r['member'],r['pattern'],r['member_sha256']) for r in spec.get('reviewed_secret_shaped',[])}
        for hit in member_hits(z,rx):
            if hit not in reviewed:raise ValueError('unreviewed secret-shaped text in %s'%hit[0])
        for e in z.infolist():
            if needles and e.filename.lower().endswith(TEXT):
                try:text=z.read(e).decode('utf-8')
                except UnicodeDecodeError:continue
                if any(v in text for v in needles):raise ValueError('private value')

def verify(rel_path,needles=()):
    """For check_project: raises on any problem with the committed archive at this repo-relative path."""
    spec=next(x for x in json.loads(MANIFEST.read_text())['archives'] if x['path']==rel_path)
    check(spec,(ROOT/rel_path).read_bytes(),needles=needles)

def build(out=DIR):
    """Refetch every pinned archive (live), write them next to the manifest and regenerate manifest.json. Needs network."""
    sys.path.insert(0,str(ROOT/'scripts'))
    import fetch_umbrella,provider_addons,tempfile
    rx=patterns();out=Path(out);out.mkdir(parents=True,exist_ok=True);archives=[]
    ulock=json.loads((ROOT/'migration/umbrella/source-lock.json').read_text())
    for key,notice,folder in (('package','plugin.video.umbrella/LICENSE.txt',None),('repository','repository.umbrellaplug.github.io/addon.xml','repository.umbrellaplug.github.io')):
        p=ulock[key];data=fetch_umbrella.fetch(ulock,which=key);archives.append(entry(p['id'],p['version'],data,'migration/umbrella/source-lock.json',key,notice,folder,rx))
    llock=json.loads((ROOT/'migration/loop-addons/source-lock.json').read_text())
    with tempfile.TemporaryDirectory() as d:
        provider_addons.run(d,llock)
        for p in llock['packages']:
            data=(Path(d)/(p['id']+'.zip')).read_bytes();z=zipfile.ZipFile(io.BytesIO(data));names=z.namelist()
            notice=next((n for n in names if re.search(r'(?i)(^|/)(license|copying)[^/]*$',n)),p['id']+'/addon.xml')
            archives.append(entry(p['id'],p['version'],data,'migration/loop-addons/source-lock.json',None,notice,None,rx))
    for a in archives:(ROOT/a['path']).write_bytes(a.pop('_data'))
    MANIFEST.write_text(json.dumps({'schema':1,'scope':'Exact upstream archives of the add-ons the phone has beyond the IPA (see docs/ADDON-BACKUP-GAPS.md); Git LFS objects; pinned in the named locks','archives':archives},indent=1)+'\n')
    return archives

def entry(id,version,data,lock,lock_key,notice,folder,rx):
    z=zipfile.ZipFile(io.BytesIO(data));hits=member_hits(z,rx)
    spec={'path':'migration/addon-preserve/%s-%s.zip'%(id,version),'id':id,'version':version,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'lock':lock,'notice':notice}
    if lock_key:spec['lock_key']=lock_key
    if folder:spec['folder']=folder
    if hits:spec['reviewed_secret_shaped']=[{'member':m,'pattern':n,'member_sha256':h} for m,n,h in hits]
    spec['_data']=data;return spec

if __name__=='__main__':
    if sys.argv[1:2]==['build']:
        for a in build():print(a['id'],a['version'],a['bytes'],'reviewed matches:',len(a.get('reviewed_secret_shaped',[])))
    else:
        for a in json.loads(MANIFEST.read_text())['archives']:
            verify(a['path']);print('ok',a['path'])
