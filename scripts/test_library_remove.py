"""ISSUE-286 (owner, build 442: deleting the "Unnamed download" did nothing). Videos that are not on Google Drive leave
the library through library_index.remove: every failed version of a copy that ended, and a running copy is stopped."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
import debrid_drive  # noqa: E402
import library_index  # noqa: E402
import transfer_control  # noqa: E402


def job(h, status, added, **kw):
    base = {'hash': h * 40, 'title': '', 'kind': 'episode', 'season': '1', 'episode': '6', 'status': status,
            'added': added, 'name': 'x.mkv'}
    base.update(kw)
    return base


class Remove(unittest.TestCase):
    def test_unnamed_problem_leaves_with_every_failed_version(self):
        with tempfile.TemporaryDirectory() as p:
            # Two failed versions of one video without a title (the "Unnamed download"); problems() shows the latest.
            debrid_drive.save(p, {'jobs': [
                job('a', 'failed', 1, error='Problem: No one is sharing this source', finished=10),
                job('a', 'failed', 2, error='Problem: No one is sharing this source', finished=20),
            ]})
            index = library_index.refresh(p)
            loose = [e for e in index['videos'] if not e.get('id') and e['state'] == library_index.PROBLEM]
            self.assertEqual(len(loose), 1)
            self.assertEqual(library_index.remove(p, [loose[0]['key']]), 1)
            self.assertEqual(debrid_drive.problems(debrid_drive.load(p)), [])
            after = library_index.load(p)
            self.assertFalse([e for e in after['videos'] if e['key'] == loose[0]['key']])

    def test_running_copy_is_stopped(self):
        with tempfile.TemporaryDirectory() as p:
            debrid_drive.save(p, {'jobs': [job('b', 'copying', 1, title='Rick and Morty', season='3', episode='2', size=100)]})
            index = library_index.refresh(p)
            key = [e['key'] for e in index['videos'] if e['state'] == library_index.COPYING][0]
            self.assertEqual(library_index.remove(p, [key]), 1)
            self.assertIn('b' * 40, transfer_control.cancelled_copies(p))

    def test_drive_videos_are_not_touched(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertEqual(library_index.remove(p, ['nothing-here']), 0)

    def test_the_item_sheet_offers_remove_for_videos_not_on_drive(self):
        source = (BOOT / 'library_manager.py').read_text()
        self.assertIn("'delete' if row.get('id') else 'remove'", source)
        self.assertIn("if action == 'remove':", source)
        self.assertIn('library_index.remove(profile', source)
        self.assertIn('remove_rows(loose', source)          # Delete Season takes its copies and problems too


if __name__ == '__main__':
    unittest.main()
