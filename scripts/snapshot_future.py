"""Make the documented runtime snapshot from the exact upstream future tree."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = 'script.module.future'
TREE = '1146a531d53140feb5d163de82a3e97fb1d88683'


def build(source, output):
    source, output = Path(source), Path(output)
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('symlink in source')
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        subprocess.run(['git', 'init', '-q', tmp], check=True)
        shutil.copytree(source, target / NAME)
        subprocess.run(['git', '-C', tmp, 'add', '-f', NAME], check=True)
        actual = subprocess.check_output(['git', '-C', tmp, 'write-tree', '--prefix=' + NAME], text=True).strip()
        if actual != TREE:
            raise ValueError('upstream tree mismatch')
        tree = target / NAME
        removed = sorted(p.relative_to(tree).as_posix() for p in tree.rglob('*.pem'))
        expected = json.loads((ROOT / 'migration/source-baseline/future-transform.json').read_text())
        if removed != expected['removed_files']:
            raise ValueError('unexpected certificate fixtures')
        for name in removed:
            (tree / name).unlink()
        request = tree / 'lib/future/backports/urllib/request.py'
        lines = request.read_text().splitlines(keepends=True)
        result = []
        skip = False
        count = 0
        for line in lines:
            if skip:
                skip = False
                continue
            if line.lstrip().startswith('>>> _parse_proxy(') and 'joe:password@' in line:
                skip = True
                count += 1
                continue
            result.append(line)
        if count != 6:
            raise ValueError('unexpected doctest examples')
        request.write_text(''.join(result))
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for path in sorted(tree.rglob('*')):
                if path.is_file():
                    info = zipfile.ZipInfo(path.relative_to(target).as_posix(), (1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    z.writestr(info, path.read_bytes())
    return hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.source, args.output))
