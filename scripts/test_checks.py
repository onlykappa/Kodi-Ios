import importlib.util,json,shutil,tempfile,unittest,urllib.parse
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('checks',PROJECT/'scripts/check_project.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)

class Checks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='kodi-ios-checks-')
        self.root=Path(self.temp.name)/'project'
        shutil.copytree(PROJECT,self.root,ignore=shutil.ignore_patterns('.git'))
        checks.ROOT=self.root
    def tearDown(self):self.temp.cleanup()
    def rules(self,source=None):return {x['rule'] for x in checks.check(source)['issues']}
    def test_clean_baseline(self):self.assertTrue(checks.check()['passed'])
    def test_google_api_key(self):
        (self.root/'docs/probe.md').write_text('AIza'+'A'*35)
        self.assertIn('google-api-key',self.rules())
    def test_encoded_credential_url(self):
        value='https'+chr(58)+chr(47)*2+'example'+chr(58)+'examplepass'+chr(64)+'host.invalid'
        encoded=urllib.parse.quote(value,safe='')
        (self.root/'docs/probe.md').write_text(encoded)
        self.assertIn('credential-url',self.rules())
    def test_snapshot_tamper(self):
        (self.root/'snapshot/userdata/guisettings.xml').write_text('<settings/>')
        self.assertIn('snapshot-hash-mismatch',self.rules())
    def test_missing_playlist(self):
        (self.root/'snapshot/userdata/playlists/video/offline_movies_action.xsp').unlink()
        self.assertIn('missing-referenced-playlist',self.rules())
    def test_archive_file(self):
        (self.root/'docs/probe.zip').write_text('test archive placeholder')
        self.assertIn('private-or-runtime-file',self.rules())
    def test_ipa_artifact(self):
        (self.root/'docs/probe.ipa').write_text('test unsigned artifact placeholder')
        self.assertIn('private-or-runtime-file',self.rules())
    def test_device_path(self):
        (self.root/'snapshot/userdata/probe.xml').write_text('<path>/home/example/private</path>')
        self.assertIn('device-specific-absolute-path',self.rules())
    def test_source_value_comparison(self):
        source=Path(self.temp.name)/'userdata';source.mkdir()
        value='sample-private-'+'value-for-check'
        (source/'settings.xml').write_text('<settings><setting id="refresh_token">'+value+'</setting></settings>')
        (self.root/'docs/probe.md').write_text(value)
        self.assertIn('matches-private-source-value',self.rules(source))
    def test_unapproved_workflow(self):
        p=self.root/".github/workflows/unapproved.yml";p.parent.mkdir(parents=True,exist_ok=True);p.write_text("name: unapproved\n")
        self.assertIn("unexpected-top-level-file",self.rules())
    def test_symlink_directory(self):
        (self.root/'snapshot/userdata/linked').symlink_to(self.root/'docs',target_is_directory=True)
        self.assertIn('symlink-not-publishable',self.rules())

unittest.main(verbosity=1)
