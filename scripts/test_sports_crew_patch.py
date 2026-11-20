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
    def test_the_pinned_file_is_patched_once_and_reports_crew_only_during_a_scan(self):
        import types
        folder, path = module()
        self.assertEqual(patch.apply([folder]), 'patched')
        self.assertEqual(patch.apply([folder]), 'already')
        source = open(path).read()
        self.assertEqual(source.count(patch.MARK), 1)
        for scanning, label, shown, expect in ((True, 'Container.PluginName', '', 'plugin.video.thecrew'), (False, 'Container.PluginName', '', ''),
                                               (True, 'Window.IsActive', 'x', 'x')):
            xbmc = types.SimpleNamespace(getInfoLabel=lambda name, shown=shown: shown)
            xbmcgui = types.SimpleNamespace(Window=lambda wid, scanning=scanning: types.SimpleNamespace(getProperty=lambda key: '1' if scanning else ''))
            scope = {'xbmc': xbmc}
            import unittest.mock
            with unittest.mock.patch.dict(sys.modules, {'xbmcgui': xbmcgui, 'xbmc': xbmc}):
                exec(source, scope)
                self.assertEqual(scope['infoLabel'](label), expect)

    def test_another_version_or_an_unexpected_file_is_left_alone(self):
        folder, path = module(version='3.2.30')
        self.assertIn('pinned version', patch.apply([folder]))
        self.assertEqual(open(path).read(), 'import xbmc\ninfoLabel = xbmc.getInfoLabel\n')
        folder, path = module(body='import xbmc\ninfoLabel = something_else\n')
        self.assertIn('pinned file', patch.apply([folder]))
        self.assertEqual(open(path).read(), 'import xbmc\ninfoLabel = something_else\n')
        self.assertEqual(patch.apply([os.path.join(tempfile.mkdtemp(), 'none')]), 'no Crew module folder')


if __name__ == '__main__':
    unittest.main()
