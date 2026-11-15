"""ISSUE-228: Cancel All Upscaling on Settings › AI Upscale shows at once and reaches the copy being made; a long press on
the copy being made opens Pause / Cancel This Copy / Cancel All instead of closing the page."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import upscale_queue as uq  # noqa: E402


def data():
    return {'copies': {'a': {'status': 'running', 'progress': 40}, 'b': {'status': 'waiting', 'progress': 0},
                       'c': {'status': 'ready', 'copy_id': 'x', 'progress': 100}}}


class CancelAll(unittest.TestCase):
    def test_a_cancel_all_shows_at_once_and_stays_for_the_copy_being_made(self):
        with tempfile.TemporaryDirectory() as p:
            uq.cancel_all(p)
            shown = uq.preview(p, data())
            self.assertEqual((shown['copies']['a']['status'], shown['copies']['b']['status'], shown['copies']['c']['status']),
                             ('cancelled', 'cancelled', 'ready'))              # made copies stay
            self.assertTrue(uq.has_pending(p))                                   # nothing was consumed by looking
            self.assertTrue(uq.cancelling(p, 'a'))                               # the running copy still sees it and stops
            # A page applies it to the saved data for display but keeps the request for the service.
            saved = data()
            self.assertTrue(uq.apply_control(p, saved, keep=True))
            self.assertTrue(uq.cancelling(p, 'a'))
            # The service, once it has applied it, clears it.
            uq.apply_control(p, saved)                                            # (already cancelled for display: nothing left to change)
            self.assertFalse(uq.has_pending(p));self.assertFalse(uq.cancelling(p, 'a'))

    def test_a_single_cancel_and_a_new_order_survive_a_page_view(self):
        with tempfile.TemporaryDirectory() as p:
            uq.cancel(p, ['b']);uq.reorder(p, ['b', 'a'])
            shown = uq.preview(p, data())
            self.assertEqual(shown['copies']['b']['status'], 'cancelled');self.assertEqual(shown['copies']['a']['status'], 'running')
            self.assertTrue(uq.cancelling(p, 'b'));self.assertFalse(uq.cancelling(p, 'a'))
            self.assertTrue(uq.has_pending(p))
            uq.apply_control(p, data())
            self.assertFalse(uq.has_pending(p))

    def test_nothing_pending_means_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as p:
            self.assertFalse(uq.has_pending(p))
            self.assertEqual(uq.preview(p, data()), data())

    def test_the_page_and_the_service_are_wired(self):
        page = (ROOT / 'migration/bundled-bootstrap/upscale_settings.py').read_text()
        self.assertIn('uq.preview(profile, uq.load(profile))', page)
        self.assertEqual(page.count('uq.apply_control(profile, data, keep=True)'), 3)       # pages never consume a request
        self.assertIn('LONG = (101, 117)', page);self.assertIn('def hold_menu(self):', page)
        for label in ("'Cancel This Copy'", "'Cancel All Upscaling'"):
            self.assertIn(label, page)
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('upscale_queue.has_pending(profile)', service);self.assertIn('upscale_queue.RUNNING[0]=True', service)


if __name__ == '__main__':
    unittest.main()
