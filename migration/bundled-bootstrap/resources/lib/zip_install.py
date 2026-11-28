"""Install an add-on from a zip file (owner-approved docs/design/addon-install-mockups.html, frames 1 to 3, 6 and 7).

Replaces Kodi's file browser for "Install from zip file": the zips Kodi can see are listed (Share/AirDrop's Inbox and the
Kodi folder in the Files app), one is read (its name, version, kind and what it needs), and on a yes it is unpacked into the
add-ons folder; Kodi is told (UpdateLocalAddons, EnableAddon) and installs whatever it still needs from the repositories.
Pure apart from the file reads, so it is host-tested (scripts/test_zip_install.py)."""
import os
import time
import zipfile
import xml.etree.ElementTree as ET

LIMIT = 8
KINDS = {'xbmc.service': 'Service', 'xbmc.python.script': 'Program add-on', 'xbmc.python.module': 'Add-on library',
         'xbmc.addon.repository': 'Repository', 'xbmc.gui.skin': 'Skin', 'kodi.context.item': 'Context menu add-on',
         'xbmc.python.lyrics': 'Lyrics add-on', 'xbmc.python.weather': 'Weather add-on', 'xbmc.metadata.scraper.movies': 'Scraper'}
PROVIDES = {'video': 'Video add-on', 'audio': 'Music add-on', 'image': 'Picture add-on', 'executable': 'Program add-on', 'game': 'Game add-on'}


def find_zips(folders, limit=LIMIT):
    """[{path, name, size, mtime, where}] newest first. folders: [(folder, where)]; top level only, no deeper."""
    found = []
    for folder, where in folders:
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        for name in names:
            path = os.path.join(folder, name)
            if name.lower().endswith('.zip') and os.path.isfile(path):
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                found.append({'path': path, 'name': name, 'size': stat.st_size, 'mtime': stat.st_mtime, 'where': where})
    found.sort(key=lambda item: item['mtime'], reverse=True)
    return found[:limit]


def size_text(size):
    size = float(size or 0)
    if size < 1024:
        return '%d bytes' % size
    if size < 1024 * 1024:
        return '%d KB' % round(size / 1024)
    return '%.1f MB' % (size / 1024 / 1024)


def when_text(mtime, now=None):
    now = now if now is not None else time.time()
    day = time.localtime(mtime), time.localtime(now)
    if time.strftime('%Y%j', day[0]) == time.strftime('%Y%j', day[1]):
        return 'Today'
    if time.strftime('%Y%j', day[0]) == time.strftime('%Y%j', time.localtime(now - 86400)):
        return 'Yesterday'
    return time.strftime('%d %b', day[0]).lstrip('0')


def kind_of(root):
    for ext in root.findall('extension'):
        point = ext.get('point', '')
        if point == 'xbmc.python.pluginsource':
            provides = (ext.findtext('provides') or '').split()
            for key in provides:
                if key in PROVIDES:
                    return PROVIDES[key]
            return 'Add-on'
        if point in KINDS:
            return KINDS[point]
    return 'Add-on'


def inspect(path):
    """What the zip holds: {ok, id, name, version, kind, requires:[ids], optional:[ids], folder} or {ok: False, reason}."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            tops = {n.split('/')[0] for n in names if n and not n.startswith(('/', '__MACOSX'))}
            manifests = [n for n in names if n.count('/') == 1 and n.endswith('/addon.xml')]
            if len(tops) != 1 or len(manifests) != 1:
                return {'ok': False, 'reason': 'This zip is not a single add-on.'}
            if any(n.startswith('/') or '..' in n.replace('\\', '/').split('/') for n in names):
                return {'ok': False, 'reason': 'This zip has unsafe file names.'}
            root = ET.fromstring(z.read(manifests[0]))
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError):
        return {'ok': False, 'reason': 'This file could not be read as an add-on zip.'}
    folder = manifests[0].split('/')[0]
    if root.tag != 'addon' or not root.get('id') or root.get('id') != folder:
        return {'ok': False, 'reason': 'This zip is not a Kodi add-on (its id does not match its folder).'}
    requires = [i.get('addon') for i in root.findall('requires/import') if i.get('addon') and i.get('optional') != 'true']
    optional = [i.get('addon') for i in root.findall('requires/import') if i.get('addon') and i.get('optional') == 'true']
    return {'ok': True, 'id': root.get('id'), 'name': root.get('name') or root.get('id'), 'version': root.get('version') or '',
            'kind': kind_of(root), 'requires': requires, 'optional': optional, 'folder': folder}


def missing(requires, installed):
    """The add-ons a zip needs that are not installed yet (Kodi's own xbmc.* and kodi.* are always there)."""
    have = set(installed or ())
    return [r for r in requires if not r.startswith(('xbmc.', 'kodi.')) and r not in have]


def describe(info):
    return ('Version %s · %s' % (info['version'], info['kind'])) if info.get('version') else info['kind']


def unpack(path, folder, dest):
    """Unpack one add-on's folder from the zip into `dest` (the add-ons folder); never outside it."""
    base = os.path.realpath(dest)
    with zipfile.ZipFile(path) as z:
        for entry in z.infolist():
            if not entry.filename.startswith(folder + '/'):
                continue
            target = os.path.realpath(os.path.join(base, entry.filename))
            inside = os.path.join(base, folder)
            if target != inside and not target.startswith(inside + os.sep):
                raise ValueError('unsafe path in zip')
            if entry.filename.endswith('/'):
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(entry) as src, open(target, 'wb') as out:
                out.write(src.read())
    return os.path.join(base, folder)
