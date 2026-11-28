"""Add-on Updates, pure logic (no Kodi): the add-ons Kodi lists as outdated, the line that says when the check last ran,
and the stamp that remembers it. addon_updates.py (the page) reads Kodi through JSON-RPC and draws the result.

Kodi's list is its own directory addons://outdated/ (AddonsDirectory.cpp): one file per outdated add-on, plus the
entries "Update all" and "Allow updates" that are not add-ons."""
import json

LISTING = 'addons://outdated/'
SPECIAL = ('update_all', 'update_allowed')


def updates(files):
    """[{'id', 'name', 'icon'}] for the add-ons in a Files.GetDirectory 'files' list, in Kodi's order."""
    out = []
    for item in files or []:
        path = str(item.get('file') or '')
        if not path.startswith(LISTING):
            continue
        add_on = path[len(LISTING):].strip('/')
        if not add_on or add_on in SPECIAL:
            continue
        out.append({'id': add_on, 'name': str(item.get('label') or add_on), 'icon': str(item.get('thumbnail') or '')})
    return out


def ids_from_listing(entries):
    """Add-on ids from the names Kodi's own listing gives back (xbmcvfs.listdir of addons://outdated/: bare ids, or whole paths), in Kodi's order, without the
    "Update all" / "Allow updates" entries. ISSUE-496 (owner screenshot IMG_0740, build 792): the page asked JSON-RPC Files.GetDirectory, which Kodi 21.3 refuses for
    addons://outdated/ (CFileUtils::RemoteAccessAllowed lists only a few paths, among the add-on ones only addons://sources), so the list was never readable."""
    out = []
    for entry in entries or []:
        text = str(entry or '').strip()
        if text.startswith(LISTING):
            text = text[len(LISTING):]
        add_on = text.strip('/').rsplit('/', 1)[-1]
        if add_on and add_on not in SPECIAL and add_on not in out:
            out.append(add_on)
    return out


# ISSUE-499: the app's own patched copies (pinned_addons.PATCHED). A repository update would replace them with copies without the fixes.
PINNED = ('plugin.googledrive', 'script.module.clouddrive.common', 'plugin.video.elementum', 'script.elementum.burst')


def rows(ids, details):
    """[{'id','name','icon','version'}] for the outdated ids; `details` is Addons.GetAddons' list ({'addonid','name','thumbnail','version'}). An id Kodi does not describe shows its id."""
    known = {str(d.get('addonid') or ''): d for d in details or []}
    out = []
    for add_on in ids:
        d = known.get(add_on) or {}
        pinned = add_on in PINNED
        out.append({'id': add_on, 'pinned': pinned, 'name': str(d.get('name') or add_on) + (' (kept by the app)' if pinned else ''), 'icon': str(d.get('thumbnail') or ''), 'version': str(d.get('version') or '')})
    return out


def ago(seconds):
    """'just now', '1 minute ago', '3 hours ago', '2 days ago'."""
    seconds = max(0, int(seconds))
    for size, unit in ((86400, 'day'), (3600, 'hour'), (60, 'minute')):
        if seconds >= size:
            n = seconds // size
            return '%d %s%s ago' % (n, unit, '' if n == 1 else 's')
    return 'just now'


def status(stamp, now, count, failed=False):
    """The line under the page title (board 12). stamp: when Check Now last ran (epoch seconds), or None if it never has.
    count: outdated add-ons shown; failed: Kodi's list could not be read."""
    if failed:
        return "Could not read Kodi's add-on list. Tap Check Now to try again."
    if stamp is None:
        when = 'Not checked from here yet' if count else 'Tap Check Now to look for updates'
    else:
        when = 'Checked %s' % ago(now - stamp)
    if count:
        return when + '. Tap an add-on to update it.'
    return when + '. Add-ons update on their own when a new version is out.'


def parse_stamp(text):
    """Epoch seconds from the stamp file, or None when it is missing or unreadable."""
    try:
        return float(json.loads(text)['checked'])
    except Exception:
        return None


def stamp_text(now):
    return json.dumps({'checked': int(now)})
