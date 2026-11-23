"""Offline source restoration requires complete locally verified input, even without network."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import provider_addons
import source_offline_restore as restore


class OfflineRestore(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
