#!/usr/bin/env python3
"""Per-add-on lock of the add-ons inside an IPA (what the app ships, one digest per add-on folder).

`python3 scripts/ipa_addon_lock.py write IPA OUT.json` records, for every folder under Payload/Kodi.app/AppData/AppHome/addons: id, version (from addon.xml), file count,
bytes and a tree digest (SHA-256 over the sorted lines "path NUL file-sha256"). `verify IPA LOCK.json` recomputes and reports added, removed and changed add-ons, so a later
build can be compared with a reviewed one. Bytecode (`__pycache__`, `.pyc`) is left out: the build regenerates it. Reads the IPA only; nothing is extracted or run."""
import hashlib,json,re,sys,zipfile
from pathlib import PurePosixPath
sys.dont_write_bytecode=True
PREFIX='Payload/Kodi.app/AppData/AppHome/addons/'

def digest_ipa(path):
    z=zipfile.ZipFile(path);add={}
    for e in z.infolist():
        if e.is_dir() or not e.filename.startswith(PREFIX):continue
        rel=PurePosixPath(e.filename[len(PREFIX):]);parts=rel.parts
        if len(parts)<2 or '__pycache__' in parts or rel.suffix in ('.pyc','.pyo'):continue
        a=add.setdefault(parts[0],{'files':[],'bytes':0});h=hashlib.sha256(z.read(e)).hexdigest();a['files'].append((str(PurePosixPath(*parts[1:])),h));a['bytes']+=e.file_size
        if parts[1:]==('addon.xml',):a['xml']=z.read(e).decode('utf-8','replace')
    out={}
    for name,a in sorted(add.items()):
        lines=''.join('%s\0%s\n'%f for f in sorted(a['files']));m=re.search(r'<addon[^>]*\bversion="([^"]+)"',a.get('xml',''))
        out[name]={'version':m.group(1) if m else '','files':len(a['files']),'bytes':a['bytes'],'tree_sha256':hashlib.sha256(lines.encode()).hexdigest()}
    return out

def ipa_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def write(ipa,out,label=''):
    data={'schema':1,'ipa':{'label':label,'sha256':ipa_sha(ipa)},'addons':digest_ipa(ipa)}
    open(out,'w').write(json.dumps(data,indent=1)+'\n');return data

def compare(ipa,lock):
    now=digest_ipa(ipa);old=lock['addons']
    return {'added':sorted(set(now)-set(old)),'removed':sorted(set(old)-set(now)),'changed':sorted(k for k in set(now)&set(old) if now[k]['tree_sha256']!=old[k]['tree_sha256'])}

if __name__=='__main__':
    if sys.argv[1:2]==['write']:d=write(sys.argv[2],sys.argv[3],sys.argv[4] if len(sys.argv)>4 else '');print(len(d['addons']),'add-ons')
    elif sys.argv[1:2]==['verify']:
        r=compare(sys.argv[2],json.load(open(sys.argv[3])));print(json.dumps(r,indent=1));sys.exit(1 if any(r.values()) else 0)
    else:print(__doc__)
