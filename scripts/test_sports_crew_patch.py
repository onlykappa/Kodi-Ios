import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'migration/bundled-bootstrap'), str(ROOT / 'migration/bundled-bootstrap/resources/lib')]
import sports_crew_patch as patch


def module(version='3.2.29', body='import xbmc\ninfoLabel = xbmc.getInfoLabel\n'):
    folder = tempfile.mkdtemp()
    os.makedirs(os.path.join(folder, 'lib/resources/lib/modules'))
    open(os.path.join(folder, 'addon.xml'), 'w').write('<?xml version="1.0"?>\n<addon id="script.module.thecrew" name="x" version="%s">\n</addon>\n' % version)
    path = os.path.join(folder, patch.RELATIVE)
    open(path, 'w').write(body)
    return folder, path


class CrewPatch(unittest.TestCase):
    def test_the_pinned_file_is_patched_once_and_acts_only_while_a_sports_search_or_play_is_marked(self):
        import time
        import types
        import unittest.mock
        folder, path = module()
        self.assertEqual(patch.apply([folder]), 'patched')
        self.assertEqual(patch.apply([folder]), 'already')
        source = open(path).read()
        self.assertEqual(source.count(patch.MARK), 1)
        for marked, label, shown, expect, silent in ((time.time() + 60, 'Container.PluginName', '', 'plugin.video.thecrew', True),
                                                       (time.time() - 5, 'Container.PluginName', '', '', False),      # a mark in the past: Crew as it always was
                                                       ('', 'Container.PluginName', '', '', False),
                                                       (time.time() + 60, 'Window.IsActive', 'x', 'x', True)):
            xbmc = types.SimpleNamespace(getInfoLabel=lambda name, shown=shown: shown)
            real = object()
            xbmcgui = types.SimpleNamespace(DialogProgress=real, DialogProgressBG=real, Window=lambda wid, marked=marked: types.SimpleNamespace(getProperty=lambda key: str(marked) if marked != '' else ''))
            scope = {'xbmc': xbmc}
            with unittest.mock.patch.dict(sys.modules, {'xbmcgui': xbmcgui, 'xbmc': xbmc}):
                exec(source, scope)
                self.assertEqual(scope['infoLabel'](label), expect)
                self.assertEqual(xbmcgui.DialogProgress is real, not silent)
                if silent:   # Crew's "Finding Your Event" box: every call it makes is accepted and nothing is drawn
                    box = xbmcgui.DialogProgress()
                    box.create('THE CREW SPORTS', 'The Crew Is Loading Your Event Please Wait....')
                    box.update(50, 'The Crew Is Finding Your Event...')
                    self.assertFalse(box.iscanceled())
                    box.close()

    def test_mark_sets_a_time_in_the_future(self):
        import time
        values = {}
        home = type('Home', (), {'setProperty': lambda self, key, value: values.update({key: value})})()
        patch.mark(home, 100)
        self.assertGreater(float(values[patch.SCAN]), time.time() + 90)

    def test_another_version_or_an_unexpected_file_is_left_alone(self):
        folder, path = module(version='3.2.30')
        self.assertIn('pinned version', patch.apply([folder]))
        self.assertEqual(open(path).read(), 'import xbmc\ninfoLabel = xbmc.getInfoLabel\n')
        folder, path = module(body='import xbmc\ninfoLabel = something_else\n')
        self.assertIn('pinned file', patch.apply([folder]))
        self.assertEqual(open(path).read(), 'import xbmc\ninfoLabel = something_else\n')
        self.assertEqual(patch.apply([os.path.join(tempfile.mkdtemp(), 'none')]), 'no Crew module folder')


class ClientAlias(unittest.TestCase):
    """Build 616 log: `Streamer [generic] failed ... module 'resources.lib.modules.client' has no attribute 'parseDOM'`: Crew's own downloaded streamers call
    client.parseDOM, client.py defines only parseDom."""
    BODY = "import re\n\n\ndef parseDom(html, name='', attrs=None, ret=False):\n    return [html]\n\n\ndef parseHTML(html, name='', attrs=None, ret=False):\n    return []\n"

    def client(self, version='3.2.29', body=None):
        folder = tempfile.mkdtemp()
        os.makedirs(os.path.join(folder, 'lib/resources/lib/modules'))
        open(os.path.join(folder, 'addon.xml'), 'w').write('<?xml version="1.0"?>\n<addon id="script.module.thecrew" name="x" version="%s">\n</addon>\n' % version)
        path = os.path.join(folder, patch.CLIENT_RELATIVE)
        open(path, 'w').write(body or self.BODY)
        return folder, path

    def test_the_alias_is_added_once_and_works(self):
        folder, path = self.client()
        self.assertEqual(patch.apply_client([folder]), 'patched');self.assertEqual(patch.apply_client([folder]), 'already')
        namespace = {}
        exec(compile(open(path).read(), path, 'exec'), namespace)
        self.assertIs(namespace['parseDOM'], namespace['parseDom']);self.assertEqual(namespace['parseDOM']('<a>', 'a'), ['<a>'])
        self.assertEqual(open(path).read().count('parseDOM ='), 1)

    def test_another_version_or_file_is_left_alone(self):
        folder, path = self.client(version='3.2.30');before = open(path).read()
        self.assertIn('not the pinned version', patch.apply_client([folder]));self.assertEqual(open(path).read(), before)
        folder, path = self.client(body='def parseDom(x):\n    return x\n');before = open(path).read()
        self.assertIn('does not match', patch.apply_client([folder]));self.assertEqual(open(path).read(), before)

    def test_the_real_pinned_client_gets_it_when_it_is_here(self):
        real = Path('/tmp/claude-0/ipa608/x/Payload/Kodi.app/AppData/AppHome/addons/script.module.thecrew')
        if not (real / 'lib/resources/lib/modules/client.py').exists():self.skipTest('the pinned Crew module is not on this machine')
        copy = Path(tempfile.mkdtemp()) / 'm';import shutil;shutil.copytree(real, copy)
        self.assertEqual(patch.apply_client([str(copy)]), 'patched')
        source = (copy / patch.CLIENT_RELATIVE).read_text();compile(source, 'client.py', 'exec')
        self.assertIn('parseDOM = parseDom', source)


if __name__ == '__main__':
    unittest.main()
