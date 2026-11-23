"""Offline source restoration requires complete locally verified input, even without network."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
import subprocess
from pathlib import Path
from unittest.mock import patch

import provider_addons
import source_offline_restore as restore
import source_elementum_offline as elementum


class OfflineRestore(unittest.TestCase):
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
                self.assertEqual(actual, spec['git_tree'])

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
