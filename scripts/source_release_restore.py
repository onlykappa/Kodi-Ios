"""Restore provider inputs from locally downloaded, digest-matched release assets."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import provider_addons
import source_offline_restore


def run(assets, output):
    assets = Path(assets)
    if not assets.is_dir():
        raise ValueError('Release asset directory missing')
    by_digest = {}
    for path in assets.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unsafe release asset')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in by_digest:
            raise ValueError('Duplicate release asset digest')
        by_digest[digest] = path
    lock = json.loads(provider_addons.LOCK.read_text())
    specs = lock['packages'] + lock.get('provider_packages', []) + lock.get('data_assets', [])
    with tempfile.TemporaryDirectory() as tmp:
        inputs = Path(tmp)
        for spec in specs:
            source = by_digest.get(spec['sha256'])
            if source is None:
                raise FileNotFoundError('Missing verified release asset: ' + spec.get('id', spec.get('name')))
            name = spec.get('file') or spec.get('id', spec.get('name')) + '.zip'
            if Path(name).name != name or (inputs / name).exists():
                raise ValueError('Unsafe or duplicate input name')
            shutil.copyfile(source, inputs / name)
        return source_offline_restore.run(inputs, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.assets, args.output), sort_keys=True))
