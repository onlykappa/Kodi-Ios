"""Which Sports pages exist: RunScript(service.kodi.ios.bootstrap,<name>) runs the recovery script for a name default.py does not
know, so a tile or button only starts a page that is in default.PAGES."""
import importlib.util
import os


def available(route, root=None):
    """True when `route` is a page this add-on has (default.PAGES)."""
    root = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    spec = importlib.util.spec_from_file_location('kodi_ios_default', os.path.join(root, 'default.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return route in module.PAGES
