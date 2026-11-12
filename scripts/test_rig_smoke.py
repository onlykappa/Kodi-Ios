"""Roadmap 3.4: the real-Kodi smoke runner's own logic (no Kodi needed): what counts as a broken page, that every check
points at a page, helper or log line that exists, and that a failing page fails the run."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rig_smoke as rs


class Scanner(unittest.TestCase):
    def test_broken_page_lines_are_found(self):
        text = '\n'.join([
            '2026-11-12 03:00:00.000 T:1 error <general>: Traceback (most recent call last):',
            '2026-11-12 03:00:00.100 T:1 error <general>: EXCEPTION Thrown (PythonToCppException) : -->Python callback/script returned the following error<--',
            '2026-11-12 03:00:00.200 T:1 error <general>: Error parsing boolean expression $exp[exp_tmdbhelper_isdata]',
            '2026-11-12 03:00:00.300 T:1 error <general>: Window id does not exist',
            '2026-11-12 03:00:00.400 T:1 error <general>: XML File for Window is missing: IOSTransfers.xml',
            '2026-11-12 03:00:00.500 T:1 info <general>: a harmless line',
        ])
        labels = [label for label, _ in rs.scan(text)]
        self.assertEqual(labels, ['Python traceback', 'exception', 'skin expression error', 'window did not load', 'window did not load'])

    def test_known_harmless_lines_are_allowed(self):
        line = "2026-11-12 03:00:00.000 T:1 error <general>: Control 9310 in window 13000 has been asked to focus, but it can't"
        self.assertEqual(rs.scan(line), [])
        self.assertEqual(rs.scan('EXCEPTION in a line that also says Control 9310 in window 13000 has been asked to focus, but it can\'t'), [])

    def test_blank_pictures_fail(self):
        self.assertTrue(rs.blank(None))
        self.assertTrue(rs.blank(0.0))
        self.assertFalse(rs.blank(0.2))


class Checks(unittest.TestCase):
    def test_names_are_unique_and_each_check_opens_something_real(self):
        names = [c['name'] for c in CHECKS()]
        self.assertEqual(len(names), len(set(names)))
        default = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        pages = set(re.findall(r"'([a-z_]+)'", re.search(r'^PAGES=\((.*?)\)', default, re.M).group(1)))
        pages |= {'transfers'}                      # the rig's copy of default.py adds it (kodi_rig.bootstrap_copy)
        for check in CHECKS():
            if 'page' in check:
                self.assertIn(check['page'][0], pages, check['name'])
                self.assertTrue((ROOT / 'migration/bundled-bootstrap' / (check['page'][0] + '.py')).exists(), check['name'])
                self.assertEqual(check['expect'], '"page":"%s"' % check['page'][0], check['name'])
            elif 'script' in check:
                helper = (ROOT / 'scripts' / check['script'][0])
                self.assertTrue(helper.exists(), check['name'])
                self.assertIn(check['expect'].replace('rig smoke: sheet watch opened', 'rig smoke: sheet %s opened' % check['script'][1]).split(': ', 1)[0] + ': sheet', helper.read_text())
            else:
                self.assertTrue(check['builtin'].startswith('ActivateWindow('), check['name'])

    def test_the_diagnostic_line_the_pages_log_is_the_one_the_checks_look_for(self):
        default = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        self.assertIn("diagnostics.event(write,'ui','open',page=page)", default)
        import json
        compact = json.dumps({'component': 'ui', 'event': 'open', 'page': 'notifications'}, sort_keys=True, separators=(',', ':'))
        self.assertIn('"page":"notifications"', compact)

    def test_the_sheet_helper_uses_the_real_sheet_and_the_listed_names(self):
        helper = (ROOT / 'scripts/rig_smoke_sheet.py').read_text()
        self.assertIn('choice_sheet.choose(', helper)
        for name in ('watch', 'resume', 'quality'):
            self.assertIn("'%s': {" % name, helper)
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
        import choice_sheet
        namespace = {}
        source = helper[helper.index('SPECS = {'):helper.index("name = sys.argv")]
        exec(source, namespace)
        for name, spec in namespace['SPECS'].items():
            props = choice_sheet.properties(spec)
            self.assertEqual(int(props['rows']), len(spec['rows']), name)

    def test_the_gaps_are_stated(self):
        self.assertTrue(any('track menus' in line for line in rs.NOT_COVERED))
        self.assertTrue(any('phone' in line for line in rs.NOT_COVERED))


def CHECKS():
    return rs.CHECKS


class FakeRig(object):
    """Stands in for kodi_rig: records what is opened and writes a log line per page."""

    def __init__(self, folder, log_for, picture):
        self.RIG = folder
        self.HOME = folder / 'home'
        (self.HOME / '.kodi/temp').mkdir(parents=True)
        self.log = self.HOME / '.kodi/temp/kodi.log'
        self.log.write_text('')
        self.log_for, self.picture, self.opened = log_for, picture, []

    def rpc(self, method, params=None):
        return {'result': 'pong'}

    def sync(self, args):
        pass

    def start(self, args):
        pass

    def open_page(self, args, settle=0):
        self.opened.append(('page', args.page))
        with open(self.log, 'a') as f:
            f.write(self.log_for(args.page[0]) + '\n')

    def run_builtins(self, *lines):
        self.opened.append(('builtin', lines))

    def shot(self, name):
        path = self.RIG / (name + '.png')
        subprocess.run(['convert', '-size', '60x60', self.picture, str(path)], check=True)
        return path


class RunnerFlow(unittest.TestCase):
    CHECK = {'name': 'notifications', 'page': ['notifications'], 'expect': '"page":"notifications"'}

    def run_one(self, log_for, picture):
        with tempfile.TemporaryDirectory() as folder:
            rig = FakeRig(Path(folder), log_for, picture)
            runner = rs.Runner(rig)
            return runner.run(self.CHECK, settle=0), rig

    def test_a_page_that_opens_cleanly_and_draws_passes(self):
        result, rig = self.run_one(lambda page: 'Kodi iOS diagnostic {"event":"open","page":"%s"}' % page, 'gradient:white-black')
        self.assertTrue(result['ok'], result['problems'])
        self.assertEqual(rig.opened[0], ('page', ['notifications']))

    def test_a_traceback_fails_the_check(self):
        result, _ = self.run_one(lambda page: '"page":"notifications"\nerror <general>: Traceback (most recent call last):', 'gradient:white-black')
        self.assertFalse(result['ok'])
        self.assertTrue(any('Python traceback' in p for p in result['problems']))

    def test_a_page_that_never_logs_its_open_fails(self):
        result, _ = self.run_one(lambda page: 'nothing useful', 'gradient:white-black')
        self.assertTrue(any('did not open' in p for p in result['problems']))

    def test_a_blank_picture_fails(self):
        result, _ = self.run_one(lambda page: '"page":"notifications"', 'xc:black')
        self.assertTrue(any('blank picture' in p for p in result['problems']))

    def test_a_restarted_log_is_read_from_its_start(self):
        with tempfile.TemporaryDirectory() as folder:
            rig = FakeRig(Path(folder), lambda page: '', 'gradient:white-black')
            runner = rs.Runner(rig)
            rig.log.write_text('x' * 5000)
            offset = runner.offset()
            rig.log.write_text('short new log')
            self.assertEqual(runner.since(offset), 'short new log')

    def test_list_and_unknown_names(self):
        self.assertEqual(rs.main(['--list']), 0)
        self.assertEqual(rs.main(['no_such_check']), 2)


if __name__ == '__main__':
    unittest.main()
