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
