"""Every Python file shipped in the app must parse (ISSUE-351: PR #32 put a statement between an `if` and its `elif` in service.py)."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOLDERS = ('migration/bundled-bootstrap', 'migration/deck-picker', 'scripts')


class Syntax(unittest.TestCase):
    def test_every_shipped_python_file_parses(self):
        bad = []
        count = 0
        for folder in FOLDERS:
            for path in sorted((ROOT / folder).rglob('*.py')):
                count += 1
                try:
                    ast.parse(path.read_text(encoding='utf-8'), str(path))
                except SyntaxError as error:
                    bad.append('%s:%s %s' % (path.relative_to(ROOT), error.lineno, error.msg))
        self.assertGreater(count, 100)
        self.assertEqual(bad, [])

    def test_service_hooks_the_provider_fallback_after_the_umbrella_window_check(self):
        text = (ROOT / 'migration/bundled-bootstrap/service.py').read_text(encoding='utf-8')
        self.assertLess(text.index("elif source_window.is_file()"), text.index('provider_fallback_hooks.install('))


if __name__ == '__main__':
    unittest.main()
