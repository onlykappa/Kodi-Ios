"""Restore pinned Elementum staging inputs from a local directory; never builds an IPA."""
import argparse
import json
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

import fetch_elementum_inputs as source


def run(inputs, output):
    inputs, output = Path(inputs), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty')
    lock = json.loads(source.LOCK.read_text())
    airplay = json.loads(source.AIRPLAY.read_text())['framework_release']
    framework = lock['framework_release']
    root = 'https://github.com/onlykappa/Kodi-Ios/releases/download/'
    lookup = {
        lock['plugin_release']['client_zip_url']: inputs / 'elementum-client.zip',
        lock['burst']['url']: inputs / 'burst.zip',
        root + framework['tag'] + '/' + framework['asset']: inputs / 'elementum.framework.zip',
        root + airplay['tag'] + '/' + airplay['asset']: inputs / 'KodiAirPlay.framework.zip',
    }
    for name, spec in lock.get('extras', {}).items():
        lookup[spec['url']] = inputs / ('extra-' + name + '.zip')

    def local_only(url):
        path = lookup.get(url)
        if path is None or not path.is_file():
            raise FileNotFoundError('Required local Elementum input unavailable')
        return path.read_bytes()

    def modules(specs, dest):
        dest.mkdir()
        for spec in specs:
            for name, expected in spec['trees'].items():
                candidate = inputs / 'module-trees' / name
                if not candidate.is_dir() or any(p.is_symlink() for p in candidate.rglob('*')):
                    raise ValueError('Missing or unsafe module tree: ' + name)
                with tempfile.TemporaryDirectory() as temp:
                    target = Path(temp)
                    subprocess.run(['git', 'init', '-q', temp], check=True, capture_output=True)
                    shutil.copytree(candidate, target / name)
                    subprocess.run(['git', '-C', temp, 'add', '-f', '--', name], check=True, capture_output=True)
                    actual = subprocess.check_output(['git', '-C', temp, 'write-tree', '--prefix=' + name], text=True).strip()
                    if actual != expected:
                        raise ValueError('Module tree digest mismatch: ' + name)
                    shutil.copytree(target / name, dest / name)

    original_socket, original_connection = socket.socket, socket.create_connection
    class BlockedSocket(original_socket):
        def connect(self, *args, **kwargs):
            raise OSError('Network blocked during offline restoration')
        def connect_ex(self, *args, **kwargs):
            raise OSError('Network blocked during offline restoration')
    try:
        socket.socket = BlockedSocket
        def blocked(*args, **kwargs):
            raise OSError('Network blocked during offline restoration')
        socket.create_connection = blocked
        result = source.run(output, lock, get=local_only, modules=modules, airplay=airplay)
    finally:
        socket.socket, socket.create_connection = original_socket, original_connection
    return {'elementum': result['elementum'], 'verified_module_trees': len(result['modules']),
            'verified_extra_archives': len(result['extras']), 'frameworks': result['frameworks'],
            'scope': 'local staging only; no runtime, IPA or iPhone test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.output), sort_keys=True))
