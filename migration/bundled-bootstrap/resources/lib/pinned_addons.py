"""ISSUE-267 (owner log b98d5fc2, build 421: "it seems frozen waiting for AllDebrid"): Kodi's own add-on updater installed
plugin.googledrive 1.6.13 and script.module.clouddrive.common 1.5.20 from the official repository into
special://home/addons. Those copies shadow the patched ones the app ships (scripts/build_customized_ipa.py patches them:
tls_context, timeouts, the iPhone sign-in), so the service's copy thread failed at "import tls_context" and no AllDebrid
copy or Drive upload ran at all.

The add-ons the build patches must stay the app's own copies:
- block_updates(): Kodi's per-add-on rule "don't update automatically" (Addons DB, update_rules, rule 1) for each.
- restore(): a home copy with another version than the bundled one is moved aside (special://temp/shadowed-addons), so
  Kodi loads the bundled, patched copy again after it rescans its add-ons (UpdateLocalAddons).
A home copy of the same version (the desktop rig copies every add-on there) is left alone.
"""
import os
import re
import shutil
import time

PATCHED = ('plugin.googledrive', 'script.module.clouddrive.common', 'plugin.video.elementum', 'script.elementum.burst')
NO_AUTO_UPDATE = 1   # Kodi's AddonUpdateRule::USER_DISABLED_AUTO_UPDATE


def version(folder):
    try:
        with open(os.path.join(str(folder), 'addon.xml'), encoding='utf-8', errors='replace') as f:
            head = f.read(4096)
    except OSError:
        return ''
    m = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', head)
    return m.group(1) if m else ''


def shadowed(home_addons, bundled_addons, ids=PATCHED):
    """[(id, home version, bundled version)] of the patched add-ons a different home copy hides."""
    out = []
    for addon in ids:
        mine, theirs = version(os.path.join(str(bundled_addons), addon)), version(os.path.join(str(home_addons), addon))
        if mine and theirs and mine != theirs:
            out.append((addon, theirs, mine))
    return out


def restore(home_addons, bundled_addons, aside, ids=PATCHED, log=lambda text: None, now=None):
    """Move the shadowing home copies aside. Returns [(id, home version, bundled version)] moved."""
    moved = []
    for addon, theirs, mine in shadowed(home_addons, bundled_addons, ids):
        source = os.path.join(str(home_addons), addon)
        target = os.path.join(str(aside), '%s-%s-%d' % (addon, theirs, int(time.time() if now is None else now)))
        try:
            os.makedirs(str(aside), exist_ok=True)
            shutil.move(source, target)
        except OSError as error:
            log('Kodi iOS add-ons: %s %s could not be moved aside (%s)' % (addon, theirs, type(error).__name__))
            continue
        log('Kodi iOS add-ons: %s %s from a repository update hid the app\'s patched %s; it was moved aside' % (addon, theirs, mine))
        moved.append((addon, theirs, mine))
    return moved


def block_updates(database, ids=PATCHED, log=lambda text: None):
    """Kodi's "don't update automatically" rule for each patched add-on. Returns the ids newly blocked."""
    try:
        import sqlite3
    except Exception:
        log('Kodi iOS add-ons: no sqlite3, automatic updates of the patched add-ons are not blocked')
        return []
    added = []
    try:
        db = sqlite3.connect(str(database), timeout=5)
        try:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'update_rules' not in tables:
                return []
            for addon in ids:
                if not db.execute('SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?', (addon, NO_AUTO_UPDATE)).fetchone():
                    db.execute('INSERT INTO update_rules (addonID, updateRule) VALUES (?, ?)', (addon, NO_AUTO_UPDATE))
                    added.append(addon)
            db.commit()
        finally:
            db.close()
    except Exception as error:
        log('Kodi iOS add-ons: update rules not written (%s)' % type(error).__name__)
        return []
    if added:
        log('Kodi iOS add-ons: automatic updates blocked for %s (the app ships patched copies)' % ', '.join(added))
    return added


def addons_database(database_folder):
    """The newest Addons<NN>.db in special://database (Kodi 21: Addons33.db)."""
    try:
        names = [n for n in os.listdir(str(database_folder)) if re.match(r'Addons\d+\.db$', n)]
    except OSError:
        return ''
    return os.path.join(str(database_folder), max(names, key=lambda n: int(re.findall(r'\d+', n)[0]))) if names else ''


def use_clouddrive(xbmcaddon=None, xbmcvfs=None):
    """ISSUE-270 (owner log 4e5fb2dd, build 424: after restore() moved the repository copy aside, Library lists and the Drive
    proxy failed every 10 s with "No module named 'clouddrive.common.remote'" until a restart): the clouddrive library is
    loaded from the app's patched copy. Modules already loaded from another (or a moved) folder are dropped, stale path
    entries removed, and the bundled copy put first. Returns its folder."""
    import sys
    if xbmcaddon is None:
        import xbmcaddon
    if xbmcvfs is None:
        import xbmcvfs
    bundled = xbmcvfs.translatePath('special://xbmc/addons/script.module.clouddrive.common/')
    if os.path.isfile(os.path.join(bundled, 'addon.xml')):
        path = bundled
    else:
        path = xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
    root = os.path.normpath(path)
    for name, module in list(sys.modules.items()):
        if name == 'clouddrive' or name.startswith('clouddrive.'):
            files = [getattr(module, '__file__', '') or ''] + list(getattr(module, '__path__', []) or [])
            if any(f and (not os.path.exists(f) or not os.path.normpath(f).startswith(root)) for f in files):
                del sys.modules[name]
    sys.path[:] = [p for p in sys.path if not (str(p).rstrip('/').endswith('script.module.clouddrive.common')
                                               and os.path.normpath(str(p)) != root)]
    if path not in sys.path:
        sys.path.insert(0, path)
    return path
