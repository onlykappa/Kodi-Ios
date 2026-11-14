"""ISSUE-282 (owner log 6cf2a4c5, build 442: "Kodi iOS Drive: downloads stopped (NameError)" from startup on): the Drive
service function used a name defined in another function. Every function of the service and the add-on's library must
only use names that exist: its own, an enclosing function's, the module's, or a builtin."""
import builtins
import symtable
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap'
FILES = [ROOT / 'service.py', ROOT / 'library_status.py', ROOT / 'copy_problems.py', ROOT / 'quality_choice.py',
         ROOT / 'library_repair_page.py'] + sorted((ROOT / 'resources/lib').glob('*.py'))


def missing(path):
    table = symtable.symtable(path.read_text(encoding='utf-8'), str(path), 'exec')
    module = set(table.get_identifiers())
    out = []

    def walk(t, enclosing):
        names = set(t.get_identifiers()) | enclosing
        for sym in t.get_symbols():
            if sym.is_global() and not sym.is_declared_global() and sym.is_referenced():
                n = sym.get_name()
                if n not in module and not hasattr(builtins, n) and n not in ('__file__', '__name__'):
                    out.append('%s:%s uses %s' % (path.name, t.get_name(), n))
        for child in t.get_children():
            walk(child, names if t.get_type() == 'function' else enclosing)
    for child in table.get_children():
        walk(child, set())
    return out


class NoUndefinedNames(unittest.TestCase):
    def test_every_name_a_function_uses_exists(self):
        problems = [p for f in FILES for p in missing(f)]
        self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()
