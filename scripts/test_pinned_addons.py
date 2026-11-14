"""ISSUE-267 (owner log b98d5fc2, build 421): Kodi's add-on updater put plugin.googledrive 1.6.13 and
script.module.clouddrive.common 1.5.20 into special://home/addons over the app's patched copies; the copy thread died on
"import tls_context" and no AllDebrid copy ran."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import pinned_addons as pa  # noqa: E402


def addon(folder, ident, version):
    path = Path(folder) / ident
    path.mkdir(parents=True)
    (path / 'addon.xml').write_text('<?xml version="1.0"?>\n<addon id="%s" name="x" version="%s"></addon>' % (ident, version))


class Restore(unittest.TestCase):
    def test_a_repository_update_is_moved_aside_and_the_same_version_is_left(self):
        with tempfile.TemporaryDirectory() as t:
            home, bundled, aside = Path(t, 'home'), Path(t, 'xbmc'), Path(t, 'aside')
            addon(bundled, 'script.module.clouddrive.common', '1.5.11');addon(home, 'script.module.clouddrive.common', '1.5.20')
            addon(bundled, 'plugin.googledrive', '1.6.8');addon(home, 'plugin.googledrive', '1.6.13')
            addon(bundled, 'plugin.video.elementum', '0.1.0');addon(home, 'plugin.video.elementum', '0.1.0')   # the rig's copy
            addon(home, 'plugin.video.umbrella', '6.0')                                                       # not patched
            self.assertEqual(sorted(a for a, _, _ in pa.shadowed(home, bundled)), ['plugin.googledrive', 'script.module.clouddrive.common'])
            moved = pa.restore(home, bundled, aside, now=5)
            self.assertEqual(sorted(moved), [('plugin.googledrive', '1.6.13', '1.6.8'), ('script.module.clouddrive.common', '1.5.20', '1.5.11')])
            self.assertFalse((home / 'plugin.googledrive').exists());self.assertTrue((aside / 'plugin.googledrive-1.6.13-5').is_dir())
            self.assertTrue((home / 'plugin.video.elementum').exists());self.assertTrue((home / 'plugin.video.umbrella').exists())
            self.assertEqual(pa.shadowed(home, bundled), [])


class BlockUpdates(unittest.TestCase):
    def test_kodis_no_auto_update_rule_is_written_once(self):
        with tempfile.TemporaryDirectory() as t:
            db = os.path.join(t, 'Addons33.db')
            c = sqlite3.connect(db);c.execute('CREATE TABLE update_rules (id INTEGER PRIMARY KEY, addonID TEXT, updateRule INTEGER)');c.commit();c.close()
            open(os.path.join(t, 'Addons27.db'), 'w').close()
            self.assertEqual(pa.addons_database(t), db)
            self.assertEqual(sorted(pa.block_updates(db)), sorted(pa.PATCHED))
            self.assertEqual(pa.block_updates(db), [])
            rows = sqlite3.connect(db).execute('SELECT addonID, updateRule FROM update_rules').fetchall()
            self.assertEqual(sorted(rows), sorted((a, 1) for a in pa.PATCHED))

    def test_the_service_runs_the_guard_and_survives_an_unpatched_clouddrive(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertLess(service.index('pinned_addons.restore('), service.index('target=drive_uploads'))
        self.assertIn('except ImportError:', service);self.assertIn("special://xbmc/addons/script.module.clouddrive.common/", service)


if __name__ == '__main__':
    unittest.main()
