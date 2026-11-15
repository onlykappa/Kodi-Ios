"""ISSUE-346 (owner: "do the keyframe during prep"): a prepared movie's first cast still scanned every storage fragment
for keyframes (ISSUE-335 only saved the scan after a cast). The preparation now collects the picture's keyframes from
each fragment header as it is written, carries them in its resume marks, and saves them under the key a cast computes.
The C host tests (tests/test_remux.c, prepared_scan_matches) check the saved scan equals a fresh one; this checks the
wiring and that the Drive side keeps every mark's keyframe lines."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMUX = ROOT / 'migration/airplay-ios/remux'
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import drive_prepare as dp  # noqa: E402


class Marks(unittest.TestCase):
    def test_keyframe_lines_are_kept_with_the_index_lines(self):
        text = 'kr-resume 1\noffset 900\nseq 3\nlayout 2/1\nkfirst 0\nkcount 2\ntfra 1 0 40\nkf 40 0\nkf 40 48\n'
        offset, head, kept = dp.parse_mark(text)
        self.assertEqual(offset, 900)
        self.assertEqual(kept, ['tfra 1 0 40', 'kf 40 0', 'kf 40 48'])
        self.assertIn('kcount 2', head)
        self.assertIn('kfirst 0', head)


class Wiring(unittest.TestCase):
    def test_preparation_collects_and_saves(self):
        source = (REMUX / 'src/kr_prepare.c').read_text()
        self.assertIn('kr_mp4_moof_keys(rc->moof', source)
        self.assertIn('kr_mp4_cache_save(kr_mp4_cache_key((const uint8_t*)b.str,(uint32_t)b.len,rc->at,rc->vtrack),&rc->keys,1)', source)
        self.assertIn('"kfirst %lld\\nkcount %d\\n"', source)
        self.assertIn('rc->keys.n!=rc->kcount', source)   # an incomplete list from a mark is not saved

    def test_the_cast_uses_the_shared_cache(self):
        source = (REMUX / 'src/kr_remux.c').read_text()
        self.assertIn('kr_mp4_cache_load(key,&raw,&origin)', source)
        self.assertIn('made while preparing', source)
        self.assertNotIn('static int keyframe_cache_load', source)

    def test_the_host_tests_cover_it(self):
        tests = (REMUX / 'tests/test_remux.c').read_text()
        self.assertIn('static int prepared_scan_matches', tests)
        self.assertIn('the resumed run saved the joined movie', tests)
        self.assertIn('an incomplete keyframe list is not saved', tests)


if __name__ == '__main__':
    unittest.main()
