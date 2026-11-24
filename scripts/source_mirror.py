"""A kept copy of every third-party file a build downloads (owner, 2026-11-24, after POV's repository began answering 404 and stopped build 679 -> 682: "ensure you fork them so this
doesn't happen again", "back up all 3rd party add-ons").

Each build, once its downloads are verified, writes the raw files into the folder named by $KODI_IOS_PRESERVE_DIR (`keep`); the workflow publishes that folder as the release
`third-party-sources-1` of this repository with a MANIFEST.json (file name -> sha256). When an upstream address fails, `get` falls back to the release copy. A copy is only used
after the caller's own check passes (the pin the lock files hold: sha256 or Git blob), or, for a file with no pin of its own, after the manifest's digest matches.
The release is a copy for emergencies, never a replacement: the upstream address is always tried first, so a fixed upstream is still what builds use.
Everything is injected, so the rules are tested on the host (scripts/test_source_mirror.py)."""
import hashlib, json, os, urllib.parse
from pathlib import Path

BASE = 'https://github.com/onlykappa/Kodi-Ios/releases/download/third-party-sources-1'
MANIFEST = 'MANIFEST.json'
ENV = 'KODI_IOS_PRESERVE_DIR'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def asset_name(url):
    """The release asset name of a download: the file name of its address (every pinned archive carries its version in it)."""
    name = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit('/', 1)[-1])
    if not name or name in ('.', '..') or '/' in name:
        raise ValueError('No usable file name in ' + url)
    return name


def manifest(get):
    """The release's name -> sha256 table, or {} when the release or the table is not there."""
    try:
        table = json.loads(get(BASE + '/' + MANIFEST).decode())
    except Exception:
        return {}
    return table.get('files', {}) if isinstance(table, dict) else {}


def mirrored(url, get, check=None, table=None):
    """The release copy of `url`, or raises. `check(data)` is the caller's own pin check; without one the manifest digest must match."""
    name = asset_name(url)
    data = get(BASE + '/' + name)
    if check is not None:
        check(data)
        return data
    table = table if table is not None else manifest(get)
    if table.get(name) != digest(data):
        raise ValueError('The kept copy of %s is not in the manifest, or differs from it' % name)
    return data


def fetch(url, primary, get, check=None, log=None):
    """Download `url` with `primary(url)`; if that raises, use the kept copy. Returns (data, used_kept_copy). The error of the upstream address is kept in the message
    when both fail, so the cause is not hidden."""
    try:
        return primary(url), False
    except Exception as upstream:
        if log:
            log('upstream failed (%s: %s); trying the kept copy' % (type(upstream).__name__, str(upstream)[:120]))
        try:
            return mirrored(url, get, check), True
        except Exception as kept:
            raise RuntimeError('%s: upstream failed (%s: %s) and the kept copy failed (%s: %s)' % (
                url, type(upstream).__name__, str(upstream)[:120], type(kept).__name__, str(kept)[:120])) from kept


def keep(name, data, directory=None):
    """Write a verified file into the preserve folder (when the build has one). Returns the path, or None."""
    directory = directory or os.environ.get(ENV)
    if not directory:
        return None
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    if target.exists() and target.read_bytes() != data:
        raise ValueError('Two different downloads would be kept under the name ' + name)
    target.write_bytes(data)
    return target


def write_manifest(directory, previous=None):
    """MANIFEST.json for the files in `directory`, merged over the release's earlier table `previous` (an older file stays listed). Returns the table."""
    folder = Path(directory)
    files = dict(previous or {})
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name != MANIFEST:
            files[path.name] = digest(path.read_bytes())
    (folder / MANIFEST).write_text(json.dumps({'schema': 1, 'files': files}, indent=1, sort_keys=True) + '\n')
    return files


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Write MANIFEST.json for the kept files.')
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--previous', type=Path, help='the release\'s earlier MANIFEST.json')
    args = parser.parse_args()
    before = {}
    if args.previous and args.previous.exists():
        before = json.loads(args.previous.read_text()).get('files', {})
    print(json.dumps(sorted(write_manifest(args.directory, before))))
