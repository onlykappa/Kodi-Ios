"""Offline source restoration requires complete locally verified input, even without network."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import provider_addons
import source_offline_restore as restore
import source_elementum_offline as elementum
import source_release_restore as release


class OfflineRestore(unittest.TestCase):
    def test_engine_toolchain_checksum_is_available_without_metadata_api(self):
        root = Path(__file__).resolve().parents[1]
        pin = json.loads((root / 'migration/elementum-ios/source-lock.json').read_text())['go_toolchain']
        build = (root / 'migration/elementum-ios/build-ios-engine.sh').read_text()
        self.assertIn('GO_VERSION=' + pin['version'], build)
        self.assertIn('GO_SHA256=' + pin['sha256'], build)
        self.assertNotIn('mode=json&include=all', build)
        self.assertEqual(pin['url'], 'https://go.dev/dl/go' + pin['version'] + '.darwin-arm64.tar.gz')

    def test_preserved_repository_archives_restore_exact_git_trees(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / 'migration/source-baseline/manifest.json').read_text())
        for spec in manifest['archives']:
            archive = root / spec['path']
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), spec['sha256'])
            with tempfile.TemporaryDirectory() as tmp:
                with zipfile.ZipFile(archive) as z:
                    self.assertIn(spec['notice'], z.namelist())
                    self.assertTrue(all(n.startswith(spec['id'] + '/') and '..' not in Path(n).parts for n in z.namelist()))
                    z.extractall(tmp)
                subprocess.run(['git', 'init', '-q', tmp], check=True)
                subprocess.run(['git', '-C', tmp, 'add', '-f', '--', spec['id']], check=True)
                actual = subprocess.check_output(['git', '-C', tmp, 'write-tree', '--prefix=' + spec['id']], text=True).strip()
                self.assertEqual(actual, spec.get('snapshot_tree', spec['git_tree']))
                if spec['id'] == 'script.module.future':
                    import os
                    env = dict(os.environ, PYTHONPATH=str(Path(tmp) / spec['id'] / 'lib'), PYTHONDONTWRITEBYTECODE='1')
                    subprocess.run([os.environ.get('KODI_IOS_PYTHON311', sys.executable), '-S', '-c', "import future, past, future.standard_library, future.backports.urllib.request; from future.builtins import str, bytes, range"], env=env, cwd=tmp, check=True)

    def test_sanitized_future_is_accepted_and_tampering_rejected(self):
        root = Path(__file__).resolve().parents[1]
        spec = next(x for x in json.loads((root / 'migration/source-baseline/manifest.json').read_text())['archives'] if x['id'] == 'script.module.future')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            inputs = base / 'inputs'
            modules = inputs / 'module-trees'
            modules.mkdir(parents=True)
            with zipfile.ZipFile(root / spec['path']) as z:
                z.extractall(modules)
            def stage(out, lock, get, modules, airplay):
                out.mkdir()
                modules([{'trees': {spec['id']: spec['git_tree']}}], out / 'modules')
                return {'elementum': True, 'modules': [spec['id']], 'extras': [], 'frameworks': []}
            with patch.object(elementum.source, 'run', side_effect=stage):
                result = elementum.run(inputs, base / 'good')
                self.assertEqual(result['verified_module_trees'], 1)
                (modules / spec['id'] / 'addon.xml').write_text('tampered')
                with self.assertRaisesRegex(ValueError, 'tree digest mismatch'):
                    elementum.run(inputs, base / 'bad')

    def test_release_restore_matches_digest_not_filename_and_rejects_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / 'assets'
            assets.mkdir()
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('plugin.fixture/addon.xml', '<addon id="plugin.fixture" version="1"/>')
            body = archive.getvalue()
            spec = {'id': 'plugin.fixture', 'version': '1', 'url': 'https://example.invalid/p.zip',
                    'sha256': hashlib.sha256(body).hexdigest()}
            lockfile = root / 'lock.json'
            lockfile.write_text(json.dumps({'packages': [spec]}))
            with patch.object(provider_addons, 'LOCK', lockfile):
                with self.assertRaisesRegex(FileNotFoundError, 'Missing verified release asset'):
                    release.run(assets, root / 'missing')
                (assets / 'any-name.zip').write_bytes(body)
                self.assertEqual(release.run(assets, root / 'good')['verified_inputs'], 1)
                (assets / 'duplicate.zip').write_bytes(body)
                with self.assertRaisesRegex(ValueError, 'Duplicate release asset digest'):
                    release.run(assets, root / 'duplicate')

    def test_restore_missing_and_tampered_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('plugin.fixture/addon.xml', '<addon id="plugin.fixture" version="1"/>')
                z.writestr('plugin.fixture/LICENSE', 'fixture notice')
            body = archive.getvalue()
            spec = {'id': 'plugin.fixture', 'version': '1', 'url': 'https://example.invalid/p.zip',
                    'sha256': hashlib.sha256(body).hexdigest()}
            lock = {'packages': [spec]}
            lockfile = root / 'source-lock.json'
            lockfile.write_text(json.dumps(lock))
            inputs = root / 'inputs'
            inputs.mkdir()
            archive_path = inputs / 'plugin.fixture.zip'
            with patch.object(provider_addons, 'LOCK', lockfile):
                with self.assertRaises(FileNotFoundError):
                    restore.run(inputs, root / 'missing')
                archive_path.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    restore.run(inputs, root / 'bad')
                archive_path.write_bytes(body)
                result = restore.run(inputs, root / 'good')
                self.assertEqual(result['verified_inputs'], 1)
                self.assertEqual((root / 'good/plugin.fixture.zip').read_bytes(), body)
                with self.assertRaisesRegex(ValueError, 'absent or empty'):
                    restore.run(inputs, root / 'good')

    def test_elementum_tree_restoration_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); inputs = root / 'inputs'; tree = inputs / 'module-trees' / 'fixture.module'
            tree.mkdir(parents=True); (tree / 'source.py').write_text('original\n')
            subprocess.run(['git', 'init', '-q', str(root / 'index')], check=True)
            import shutil
            shutil.copytree(tree, root / 'index/fixture.module')
            subprocess.run(['git', '-C', str(root / 'index'), 'add', 'fixture.module'], check=True)
            tree_hash = subprocess.check_output(['git', '-C', str(root / 'index'), 'write-tree', '--prefix=fixture.module'], text=True).strip()
            blob = b'synthetic fixture'; sha = hashlib.sha256(blob).hexdigest()
            for name in ('elementum-client.zip', 'burst.zip', 'elementum.framework.zip', 'KodiAirPlay.framework.zip'):
                (inputs / name).write_bytes(blob)
            lock = {'plugin_release': {'client_zip_url': 'https://example.invalid/client', 'client_zip_sha256': sha},
                    'burst': {'url': 'https://example.invalid/burst', 'sha256': sha},
                    'framework_release': {'tag': 'engine', 'asset': 'engine.zip', 'sha256': sha},
                    'modules': [{'trees': {'fixture.module': tree_hash}}], 'extras': {}}
            airplay = {'framework_release': {'tag': 'air', 'asset': 'air.zip', 'sha256': sha}}
            lock_path = root / 'elementum.json'; lock_path.write_text(json.dumps(lock))
            air_path = root / 'airplay.json'; air_path.write_text(json.dumps(airplay))
            with patch.object(elementum.source, 'LOCK', lock_path), patch.object(elementum.source, 'AIRPLAY', air_path):
                result = elementum.run(inputs, root / 'good')
                self.assertEqual(result['verified_module_trees'], 1)
                (tree / 'source.py').write_text('changed\n')
                with self.assertRaisesRegex(ValueError, 'tree digest mismatch'):
                    elementum.run(inputs, root / 'bad')


if __name__ == '__main__':
    unittest.main()
