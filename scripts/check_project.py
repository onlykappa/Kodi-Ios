#!/usr/bin/env python3
"""Check every publishable file, source-secret matches and snapshot references.

Uses Python's standard library. Reports file/rule locations, never secret values.
This is a conservative local scanner, not a guarantee that all secrets are detectable.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_KEY = re.compile(r'password|passwd|token|secret|api[_.-]?key|credential|authorization|cookie|client[_.-]?id', re.I)
PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'google-api-key': re.compile(r'\bAIza[A-Za-z0-9_-]{30,}\b'),
    'google-access-token': re.compile(r'\bya29\.[A-Za-z0-9_.-]{20,}'),
    'google-refresh-token': re.compile(r'\b1//[A-Za-z0-9_-]{20,}'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'slack-token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b'),
    'credential-url': re.compile(r'(?:https?|smb|ftp)://[^\s/<]+:[^\s/<]+@', re.I),
    'assigned-secret': re.compile(r'''(?ix)(?:["']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)["']?)\s*[:=]\s*["']([A-Za-z0-9_+/.=-]{12,})["']'''),
}
FORBIDDEN_EXTENSIONS = {'.ipa','.deb','.mobileprovision','.p12','.pfx','.zip','.zst','.tgz','.tar','.db','.sqlite','.sqlite3','.log','.mp4','.mkv','.mov','.avi','.mp3','.flac','.jpg','.jpeg','.png','.webp','.pem','.key','.so','.dll','.dylib','.exe','.strm'}
ALLOWED_TOP_LEVEL = {'README.md','ROADMAP.md','.gitignore','migration','docs','scripts','inventory','snapshot','reports'}
ALLOWED_SUFFIXES = {'.md','.json','.py','.xml','.xsp'}

def files():
    return sorted(p for p in ROOT.rglob('*') if '.git' not in p.relative_to(ROOT).parts and (p.is_file() or p.is_symlink()))

def source_secrets(userdata):
    values=set()
    def add(value):
        if isinstance(value,str) and len(value.strip())>=8 and value.strip().lower() not in {'redacted','not configured','none','disabled'}:
            values.add(value.strip())
    def walk(value):
        if isinstance(value,dict):
            for key,child in value.items():
                if SENSITIVE_KEY.search(key):add(child)
                walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for p in userdata.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.xml','.json'} or p.stat().st_size>10_000_000:continue
        try:
            if p.suffix.lower()=='.json':walk(json.loads(p.read_text()))
            else:
                root=ET.parse(p).getroot()
                for e in root.iter():
                    if SENSITIVE_KEY.search(e.get('id','')+' '+e.tag):
                        add(e.text);add(e.get('value'))
                        for v in e.findall('.//value'):add(v.text)
            s=p.read_text(errors='replace')
            for rx in PATTERNS.values():
                for m in rx.finditer(s):
                    candidate=m.group(1) if m.lastindex else m.group(0)
                    add(candidate)
        except (ET.ParseError,json.JSONDecodeError,UnicodeError,OSError):continue
    return values

def check(source_userdata=None, git_history=False):
    issues=[];allfiles=files();snapshot=ROOT/'snapshot/userdata'
    def issue(path,rule):issues.append({'path':str(path.relative_to(ROOT)),'rule':rule})
    needles=source_secrets(source_userdata) if source_userdata else set()
    for p in allfiles:
        rel=p.relative_to(ROOT)
        if p.is_symlink():issue(p,'symlink-not-publishable');continue
        if rel.parts[0] not in ALLOWED_TOP_LEVEL and rel.as_posix() not in {'.github/workflows/drive-upstream.yml','.github/workflows/ios-foundation.yml','.github/workflows/elementum-ios-probe.yml','.github/workflows/import-review.yml','.github/workflows/elementum-ios-engine.yml'}:issue(p,'unexpected-top-level-file')
        if p.name!='.gitignore' and p.suffix.lower() not in ALLOWED_SUFFIXES and rel.as_posix() not in {'migration/elementum-ios/probe-build.sh','migration/elementum-ios/build-ios-engine.sh'} and rel.as_posix() not in {'.github/workflows/drive-upstream.yml','.github/workflows/ios-foundation.yml','.github/workflows/elementum-ios-probe.yml','.github/workflows/import-review.yml','.github/workflows/elementum-ios-engine.yml'}:issue(p,'unexpected-file-type')
        if p.suffix.lower() in FORBIDDEN_EXTENSIONS or '.private.' in p.name:issue(p,'private-or-runtime-file')
        if p.stat().st_size>1_000_000:issue(p,'oversized-file')
        try:s=p.read_text(encoding='utf-8')
        except UnicodeError:issue(p,'binary-file');continue
        decoded=s
        for _ in range(4):decoded=urllib.parse.unquote(decoded)
        for name,rx in PATTERNS.items():
            if rx.search(decoded):issue(p,name)
        if any(value in decoded or value in s for value in needles):issue(p,'matches-private-source-value')
        if p.suffix=='.json':
            try:json.loads(s)
            except json.JSONDecodeError:issue(p,'invalid-json')
        elif p.suffix in {'.xml','.xsp'}:
            try:ET.fromstring(s)
            except ET.ParseError:issue(p,'invalid-xml')
        if rel.parts[0]=='snapshot':
            if re.search(r'(?:/home/|/run/media/|/mnt/|/app/)',decoded):issue(p,'device-specific-absolute-path')
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',decoded):issue(p,'email-address')
            if re.search(r'(?:https?|smb|nfs|ftp|sftp|davs?)://',decoded,re.I):issue(p,'unsanitized-network-source')
    manifest=json.loads((ROOT/'reports/snapshot-manifest.json').read_text())
    listed=set()
    for entry in manifest['files']:
        p=ROOT/entry['path'];listed.add(p)
        if not p.is_file():issue(p,'missing-manifest-file');continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:issue(p,'snapshot-hash-mismatch')
        if p.stat().st_size!=entry['bytes']:issue(p,'snapshot-size-mismatch')
    if listed!=set(p for p in snapshot.rglob('*') if p.is_file()):issue(ROOT/'reports/snapshot-manifest.json','manifest-coverage-mismatch')
    inventory=json.loads((ROOT/'inventory/addons.json').read_text())
    valid={a['id'] for a in inventory['addons'] if a['manifest_valid']}
    expected=json.loads((ROOT/'reports/references.json').read_text())
    refs=collections.Counter();missing_playlists=set()
    for p in sorted(listed):
        if not p.is_file():continue
        s=urllib.parse.unquote(p.read_text())
        refs.update(re.findall(r'plugin://([A-Za-z0-9_.-]+)',s))
        for rel in re.findall(r'''special://profile/(playlists/[^<"'?&)]+\.xsp)''',s):
            if not (snapshot/rel).is_file():missing_playlists.add(rel)
    if dict(refs)!=expected['plugin_reference_counts']:issue(ROOT/'reports/references.json','plugin-reference-counts-changed')
    if sorted(set(refs)-valid)!=expected['missing_from_valid_source_manifests']:issue(ROOT/'reports/references.json','undocumented-plugin-reference')
    for rel in sorted(missing_playlists):issue(snapshot/rel,'missing-referenced-playlist')
    known={x['id'] for x in inventory['addons'] if x['location']=='user' and not x['manifest_valid']}
    if known!={'plugin.video.umbrella','script.module.jetextractors'}:issue(ROOT/'inventory/addons.json','invalid-manifest-set-changed')
    for entry in inventory['addons']:
        if 'umbrella' in entry['id'] and entry['ios_status']!='excluded_by_user':issue(ROOT/'inventory/addons.json','umbrella-must-be-excluded-from-ios')
    history_blobs=0
    if git_history:
        objects=subprocess.run(['git','rev-list','--objects','--all'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.splitlines()
        for line in objects:
            oid=line.split(' ',1)[0]
            kind=subprocess.run(['git','cat-file','-t',oid],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
            if kind!='blob':continue
            history_blobs+=1
            raw=subprocess.run(['git','cat-file','blob',oid],cwd=ROOT,check=True,capture_output=True).stdout
            try:s=raw.decode('utf-8')
            except UnicodeError:issues.append({'path':'git-blob:'+oid,'rule':'binary-in-history'});continue
            decoded=s
            for _ in range(4):decoded=urllib.parse.unquote(decoded)
            for name,rx in PATTERNS.items():
                if rx.search(decoded):issues.append({'path':'git-blob:'+oid,'rule':name})
            if any(v in s or v in decoded for v in needles):issues.append({'path':'git-blob:'+oid,'rule':'matches-private-source-value'})
    return {'passed':not issues,'files_scanned':len(allfiles),'git_history_blobs_scanned':history_blobs,'source_value_comparison_performed':source_userdata is not None,'source_sensitive_candidates_checked':len(needles),'scanner':'Python standard-library patterns, exact private-source value comparison, file allowlist and structural/reference checks','limitations':'No scanner can establish absence of every possible secret. No external secret-scanning engine was available. iOS runtime compatibility is not tested.','snapshot_files_checked':len(listed),'missing_referenced_playlists':sorted(missing_playlists),'known_baseline_issues':{'empty_manifests':sorted(known),'missing_plugin_manifests':sorted(set(refs)-valid),'ios_status':'unvalidated baseline; placeholders and desktop-specific behavior remain'},'issues':issues}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-userdata',type=Path,help='Optional local userdata directory; values are read in memory and never printed')
    parser.add_argument('--git-history',action='store_true',help='Also scan every blob reachable from local Git refs')
    parser.add_argument('--report',type=Path,help='Write a sanitized JSON report')
    args=parser.parse_args()
    result=check(args.source_userdata,args.git_history)
    if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
