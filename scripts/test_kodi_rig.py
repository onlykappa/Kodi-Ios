"""The desktop Kodi rig (scripts/kodi_rig.py) stays usable: its scenarios build the states the approved boards
show, the add-on entry it patches still exists, and every board has a recipe. No Kodi needed."""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Rig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['KODI_RIG_HOME'] = self.tmp.name
        self.rig = load('kodi_rig')
        self.scenarios = load('kodi_rig_scenarios')

    def tearDown(self):
        os.environ.pop('KODI_RIG_HOME', None)
        self.tmp.cleanup()

    def test_rig_files_live_outside_the_repository(self):
        self.assertEqual(self.rig.RIG, Path(self.tmp.name))
        self.assertFalse(str(self.rig.SHOTS).startswith(str(ROOT)))

    def test_every_board_has_a_recipe(self):
        self.assertEqual(sorted(self.rig.BOARDS), list(range(1, 10)))
        for name, page, click in self.rig.BOARDS.values():
            self.assertIn(name, self.scenarios.SCENARIOS)

    def test_scenarios_give_the_boards_states(self):
        with tempfile.TemporaryDirectory() as profile:
            modes = {name: self.scenarios.run(profile, name)['mode'] for name in ('running', 'airplay', 'idle', 'stale')}
        self.assertEqual(modes['running'], 'running')
        self.assertEqual(modes['airplay'], 'needs_you')
        self.assertNotEqual(modes['idle'], 'running')
        self.assertNotEqual(modes['stale'], 'running')

    def test_bootstrap_copy_turns_the_service_off_and_adds_the_rig_entry(self):
        dest = Path(self.tmp.name) / 'boot'
        self.rig.bootstrap_copy(dest)
        self.assertNotIn('xbmc.service', (dest / 'addon.xml').read_text())
        self.assertIn("'rig_builtin','transfers','recover')", (dest / 'default.py').read_text())
        self.assertIn(str(self.rig.BUILTINS), (dest / 'rig_builtin.py').read_text())
        self.assertFalse(list(dest.rglob('__pycache__')))

    def test_side_by_side_is_labelled(self):
        from PIL import Image
        a, b, out = (Path(self.tmp.name) / n for n in ('a.png', 'b.png', 'out.png'))
        Image.new('RGB', (603, 1300), 'black').save(a)
        Image.new('RGB', (603, 1167), 'black').save(b)
        self.rig.side(a, b, out)
        with Image.open(out) as image:
            self.assertEqual(image.size, (1216, 1207))


if __name__ == '__main__':
    unittest.main()
