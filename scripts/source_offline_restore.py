"""Exercise provider source restoration from preverified local inputs; never builds an IPA."""
import argparse
import json
import socket
from pathlib import Path

import provider_addons


def run(inputs, output):
    inputs, output = Path(inputs), Path(output)
    lock = json.loads(provider_addons.LOCK.read_text())
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be absent or empty')
    specs = lock['packages'] + lock.get('provider_packages', []) + lock.get('data_assets', [])
    by_url = {}
    for spec in specs:
        name = spec.get('id', spec.get('name'))
        filename = spec.get('file') or name + '.zip'
        if spec['url'] in by_url:
            raise ValueError('Duplicate input URL')
        by_url[spec['url']] = inputs / filename

    def local_only(url):
        path = by_url.get(url)
        if path is None or not path.is_file():
            raise FileNotFoundError('Required local provider input unavailable')
        return path.read_bytes()

    # Guard this process against accidental network access, including unexpected new provider fetches.
    old_socket, old_connection = socket.socket, socket.create_connection
    class BlockedSocket(old_socket):
        def connect(self, *args, **kwargs):
            raise OSError('Network blocked during offline restoration')
        def connect_ex(self, *args, **kwargs):
            raise OSError('Network blocked during offline restoration')
    try:
        socket.socket = BlockedSocket
        def blocked(*args, **kwargs):
            raise OSError('Network blocked during offline restoration')
        socket.create_connection = blocked
        result = provider_addons.run(output, lock, get=local_only)
    finally:
        socket.socket, socket.create_connection = old_socket, old_connection
    return {'verified_inputs': len(result['packages']), 'network_guard': 'python socket connect blocked',
            'scope': 'provider inputs only; no addon runtime, engine, IPA or phone test'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.inputs, args.output), sort_keys=True))
