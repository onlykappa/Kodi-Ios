"""Kept copies of third-party downloads (scripts/source_mirror.py): used only when the upstream address fails and only after the pin check passes; every verified download is kept."""
import hashlib, io, json, os, sys, tarfile, tempfile, unittest, unittest.mock
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_mirror as mirror
import build_import_review as review
import fetch_elementum_inputs as elementum


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Kept(unittest.TestCase):
    def test_asset_names_come_from_the_address(self):
        self.assertEqual(mirror.asset_name('https://mirrors.kodi.tv/addons/omega/script.module.six/script.module.six-1.16.0+matrix.1.zip'), 'script.module.six-1.16.0+matrix.1.zip')
        self.assertEqual(mirror.asset_name('https://x/a%20b.zip?mirrorlist'), 'a b.zip')
        with self.assertRaises(ValueError): mirror.asset_name('https://x/')
    def test_upstream_is_tried_first_and_the_kept_copy_only_when_it_fails(self):
        calls = []
        def primary(url): calls.append(('up', url)); return b'fresh'
        get = lambda url: calls.append(('kept', url)) or b'old'
        self.assertEqual(mirror.fetch('https://x/a-1.zip', primary, get), (b'fresh', False)); self.assertEqual([c[0] for c in calls], ['up'])
        def broken(url): raise OSError('404')
        table = {'a-1.zip': sha(b'old')}
        manifest = json.dumps({'files': table}).encode()
        get = lambda url: manifest if url.endswith('MANIFEST.json') else b'old'
        self.assertEqual(mirror.fetch('https://x/a-1.zip', broken, get), (b'old', True))
    def test_a_kept_copy_must_match_the_callers_pin_or_the_manifest(self):
        def broken(url): raise OSError('404')
        with self.assertRaises(RuntimeError) as caught:
            mirror.fetch('https://x/a-1.zip', broken, lambda url: b'tampered', check=lambda data: self.assertEqual(sha(data), sha(b'old')))
        self.assertIn('upstream failed', str(caught.exception)); self.assertIn('kept copy failed', str(caught.exception))
        manifest = json.dumps({'files': {'a-1.zip': sha(b'old')}}).encode()
        get = lambda url: manifest if url.endswith('MANIFEST.json') else b'tampered'
        with self.assertRaises(RuntimeError): mirror.fetch('https://x/a-1.zip', broken, get)
        with self.assertRaises(RuntimeError): mirror.fetch('https://x/b-1.zip', broken, lambda url: manifest if url.endswith('MANIFEST.json') else b'old')   # not listed
    def test_keep_writes_files_and_refuses_two_downloads_under_one_name(self):
        with tempfile.TemporaryDirectory() as t:
            with unittest.mock.patch.dict(os.environ):
                os.environ.pop(mirror.ENV, None)   # CI sets it for the whole job
                self.assertIsNone(mirror.keep('a.zip', b'1', directory=''))
            mirror.keep('a.zip', b'1', t); mirror.keep('a.zip', b'1', t)
            with self.assertRaises(ValueError): mirror.keep('a.zip', b'2', t)
            mirror.keep('b.zip', b'22', t)
            table = mirror.write_manifest(t, {'old.zip': 'f' * 64})
            self.assertEqual(table, {'old.zip': 'f' * 64, 'a.zip': sha(b'1'), 'b.zip': sha(b'22')})
            self.assertEqual(json.loads((Path(t) / 'MANIFEST.json').read_text())['files'], table)


class Wiring(unittest.TestCase):
    def test_add_on_archive_falls_back_to_the_kept_copy_and_keeps_fresh_ones(self):
        data = b'zip-bytes'
        source = {'id': 'a', 'url': 'https://x/a-1.zip', 'sha256': sha(data)}
        def down(url): raise OSError('Name or service not known')
        with tempfile.TemporaryDirectory() as t:
            os.environ[mirror.ENV] = t
            try:
                self.assertEqual(review.acquire(source, down, lambda url: data), data)                      # kept copy, same pin
                self.assertEqual(list(Path(t).iterdir()), [])                                               # a kept copy is not kept again
                with self.assertRaises(AssertionError): review.acquire(source, down, lambda url: b'other')                # a copy that fails the pin is refused
                self.assertEqual(review.acquire(source, lambda url: data, lambda url: self.fail('kept copy used')), data)
                self.assertEqual((Path(t) / 'a-1.zip').read_bytes(), data)                                  # the verified fresh download is kept
            finally:
                os.environ.pop(mirror.ENV, None)
    def test_elementum_downloads_fall_back_and_are_kept(self):
        data = b'client'
        def down(url): raise OSError('404')
        with tempfile.TemporaryDirectory() as t:
            os.environ[mirror.ENV] = t
            try:
                self.assertEqual(elementum.verified(down, 'https://x/c-1.zip', sha(data), 'client', lambda url: data), data)
                with self.assertRaises(Exception): elementum.verified(down, 'https://x/c-1.zip', sha(data), 'client', lambda url: b'bad')
                self.assertEqual(elementum.verified(lambda url: data, 'https://x/c-1.zip', sha(data), 'client', lambda url: self.fail('used')), data)
                self.assertEqual((Path(t) / 'c-1.zip').read_bytes(), data)
                self.assertEqual(elementum.verified(lambda url: data, 'https://own/f.zip', sha(data), 'own'), data)   # our own releases: no mirror
            finally:
                os.environ.pop(mirror.ENV, None)
    def test_modules_tar_round_trip_is_checked_against_git_tree_hashes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / 'src'; (root / 'script.module.x' / 'lib').mkdir(parents=True)
            (root / 'script.module.x' / 'addon.xml').write_text('<addon id="script.module.x"/>'); (root / 'script.module.x' / 'lib' / 'm.py').write_text('x = 1\n')
            trees = elementum.tree_hashes(root, ['script.module.x'])
            spec = {'repository': 'xbmc/repo-scripts', 'commit': 'a' * 40, 'trees': trees}
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w') as tar: tar.add(root / 'script.module.x', arcname='script.module.x')
            manifest = json.dumps({'files': {}}).encode()
            dest = Path(t) / 'out'; dest.mkdir()
            elementum.kept_tree(spec, dest, lambda url: buffer.getvalue()); self.assertEqual((dest / 'script.module.x' / 'lib' / 'm.py').read_text(), 'x = 1\n')
            bad = dict(spec, trees={'script.module.x': '0' * 40})
            with self.assertRaises(Exception): elementum.kept_tree(bad, Path(t) / 'out2', lambda url: buffer.getvalue())
    def test_the_workflow_keeps_and_uses_the_copies(self):
        text = (ROOT / '.github/workflows/import-review.yml').read_text()
        self.assertIn('KODI_IOS_PRESERVE_DIR=$RUNNER_TEMP/third-party-sources', text)   # set in a step: the runner context is not allowed in a job-level env (run 695 was refused)
        self.assertNotIn('KODI_IOS_PRESERVE_DIR: ${{', text)
        for needle in ('KODI_IOS_PRESERVE_DIR', 'third-party-sources-1', 'scripts/source_mirror.py', 'scripts/test_source_mirror.py', 'org.xbmc.kodi-ios_21.3_iphoneos-arm64.deb'):
            self.assertIn(needle, text, needle)


if __name__ == '__main__':
    unittest.main()
