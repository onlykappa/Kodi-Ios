"""Build 232 (owner log eabc204b): `import airplay` inside drive_uploads made `airplay` local to the whole function, so
its earlier use raised UnboundLocalError and the upload and AllDebrid copy thread never ran. No function in the
service may import a name it also uses before that import."""
import ast,unittest
from pathlib import Path

SERVICE=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/service.py'

class Scoping(unittest.TestCase):
    def test_no_name_used_before_its_local_import(self):
        tree=ast.parse(SERVICE.read_text(encoding='utf-8'))
        problems=[]
        for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
            imports={}
            for stmt in ast.walk(fn):
                if isinstance(stmt,(ast.Import,ast.ImportFrom)) and _owner(fn,stmt):
                    for alias in stmt.names:
                        name=(alias.asname or alias.name).split('.')[0]
                        imports.setdefault(name,stmt.lineno)
            for node in ast.walk(fn):
                if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Load) and node.id in imports and node.lineno<imports[node.id] and _owner(fn,node):
                    problems.append('%s: %s used at line %d, imported at %d'%(fn.name,node.id,node.lineno,imports[node.id]))
        self.assertEqual(problems,[])

def _owner(fn,target):
    """True when target belongs to fn itself, not to a nested function."""
    stack=[(fn,True)]
    while stack:
        node,mine=stack.pop()
        for child in ast.iter_child_nodes(node):
            if child is target:return mine
            nested=isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda))
            stack.append((child,mine and not nested))
    return False

if __name__=='__main__':unittest.main()
