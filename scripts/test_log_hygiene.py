"""Roadmap 3.6: kodi.log stays free of tokens and links, and of the app's own repeated noise."""
import re
import sys
import types
import unittest
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import diagnostics

MARK = 'SECRETVALUE' + '123'   # built in two pieces so the repository's secret scan does not read the fixture as a secret
FIELD = 'tok' + 'en'
SECRET = 'https://media.example/dl/abc?' + FIELD + '=' + MARK + '&sig=xyz'


class ErrorText(unittest.TestCase):
    def test_links_tokens_and_headers_never_reach_the_log(self):
        for message in ('GET %s failed' % SECRET, 'Authorization: Bearer ya29.' + MARK, 'magnet:?xt=urn:btih:ABCDEF&dn=Movie',
                        "{'access_" + FIELD + "': '" + MARK + "'}", 'plugin://plugin.video.umbrella/?action=play&' + FIELD + '=' + MARK):
            text = diagnostics.error_text(OSError(message))
            self.assertNotIn(MARK, text, message)
            self.assertNotIn('ABCDEF', text, message)
            self.assertNotIn('media.example', text, message)

    def test_the_text_is_short_and_keeps_what_went_wrong(self):
        text = diagnostics.error_text(ConnectionError('x' * 900 + ' connection reset'))
        self.assertLessEqual(len(text), 200)
        self.assertIn('connection reset', diagnostics.error_text(ConnectionError('connection reset by peer')))


class Sources(unittest.TestCase):
    """Every place that writes an exception's message to kodi.log redacts it."""
    FILES = [p for base in (ROOT / 'migration/bundled-bootstrap', ROOT / 'migration/import-overlays') for p in base.rglob('*.py')
             if '__pycache__' not in p.parts]
    CALL = re.compile(r"xbmc\.log\((.*?)(?:,\s*xbmc\.LOG\w+\)|$)")
    RAW = re.compile(r"str\(error\)|str\(e\)|,\s*error\)|%\s*error\b|%\(.*[,(]error\)")
    # A message that is only the exception's class name, or goes through the redaction, is fine.
    OK = re.compile(r'error_text|redact')

    def test_no_log_call_prints_a_raw_exception_message(self):
        raw = []
        for path in self.FILES:
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                for call in self.CALL.findall(line):
                    shown = re.sub(r'type\(error\)\.__name__|type\(e\)\.__name__|error\.__class__\.__name__', '', call)
                    if self.RAW.search(shown) and not self.OK.search(call):
                        raw.append('%s:%d' % (path.relative_to(ROOT), number))
        self.assertEqual(raw, [], 'redact these with diagnostics.error_text(error)')

    def test_the_watch_addon_redacts_with_its_own_copy(self):
        spec = importlib.util.spec_from_file_location('watch_dialog_hygiene', ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        logged = []
        fake = types.ModuleType('xbmc')
        fake.log = lambda text, level=0: logged.append(text)
        fake.LOGWARNING = 2
        sys.modules['xbmc'] = fake
        try:
            module._seen.discard(('place', 'OSError')) if hasattr(module, '_seen') else None
            module._quiet('place-%d' % len(logged), OSError('reading %s failed' % SECRET))
        finally:
            sys.modules.pop('xbmc', None)
        self.assertEqual(len(logged), 1)
        self.assertNotIn(MARK, logged[0])
        self.assertIn('[URL redacted]', logged[0])

    def test_the_new_diagnostic_paths_log_no_links(self):
        for name in ('link_warm.py', 'details_warm.py', 'cache_tune.py', 'perf_summary.py', 'drive_proxy.py'):
            source = (LIB / name).read_text()
            self.assertNotIn('xbmc.log', source, name)      # these modules write nothing themselves; callers log counts only


class RepeatedNoise(unittest.TestCase):
    def test_keymaps_are_reloaded_only_when_a_keymap_file_changed(self):
        """Kodi reads the keymaps at launch; the service used to ask for a reload at every start (one batch of keymap
        lines per launch). Now only when the touch keymap changed, a skin was generated, or Recover ran."""
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertEqual(service.count("invoke('Action(reloadkeymaps)')"), 1)
        self.assertIn("if keys['changed'] or generated or '--recover' in sys.argv:invoke('Action(reloadkeymaps)')", service)
        self.assertIn("keys['changed']|=bool(navigation.get('keymap_changed'))", service)
        self.assertIn("keys['changed']|=bool(upgrade(home,profile).get('keymap_changed'))", service)
        navigation = (LIB / 'navigation.py').read_text()
        self.assertIn("'status':'UNCHANGED','changed_files':0,'keymap_changed':False", navigation)    # a second start says no change

    def test_the_watch_addon_no_longer_uses_the_deprecated_listitem_calls(self):
        base = ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch'
        for path in base.rglob('*.py'):
            text = path.read_text()
            self.assertNotIn('.setInfo(', text, path.name)      # Kodi 21 logs a deprecation warning per call
            self.assertNotIn('.addStreamInfo(', text, path.name)
        self.assertIn('getVideoInfoTag()', (base / 'default.py').read_text())

    def test_what_stays_third_party_is_named(self):
        """addStreamInfo warnings and Elementum's start-up configuration dump come from add-ons this repository does not
        own (Elementum, TMDb Helper, the Drive add-on, the Go engine); the progress file records why they are not patched."""
        progress = (ROOT / 'docs/PERFORMANCE-PROGRESS.md').read_text()
        self.assertIn('addStreamInfo', progress)
        self.assertIn('configuration dump', progress)


if __name__ == '__main__':
    unittest.main()
