"""The AllDebrid key, kept in the app's own profile so removing or breaking Umbrella does not take it away.

Umbrella stays the place you sign in: its setting `alldebridtoken` is read first, so a fresh sign-in or a new key is picked up at once.
Every successful read is mirrored into the app's profile (alldebrid.token, owner-only file); when Umbrella is missing, disabled or
empty, that copy is used. The key lives only in the phone's profile folder: never in the repository, the IPA, a log or a diagnostic.
"""
import os
import tempfile

NAME = 'alldebrid.token'
OWN = 'alldebrid.own'          # present when the key was obtained by the app's own sign-in: it then wins over Umbrella's setting
UMBRELLA = 'plugin.video.umbrella'
SETTING = 'alldebridtoken'


def _path(profile=None):
    if profile is None:
        try:
            import xbmcvfs
            profile = xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')
        except Exception:
            return ''                         # no Kodi (or no profile): the mirror is simply off
    return os.path.join(str(profile), NAME)


def _umbrella():
    try:
        import xbmcaddon
        return (xbmcaddon.Addon(UMBRELLA).getSetting(SETTING) or '').strip()
    except Exception:
        return ''


def _read(path):
    if not path:
        return ''
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read().strip()
    except OSError:
        return ''


def _write(path, token):
    if not path:
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.token-')
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(token)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return True
    except OSError:
        return False


def save_own(token, profile=None):
    """Store a key from the app's own sign-in (owner-only file plus a marker that it outranks Umbrella's setting)."""
    path = _path(profile)
    token = str(token or '').strip()
    if not path or not token or not _write(path, token):
        return False
    return _write(os.path.join(os.path.dirname(path), OWN), '1')


def clear(profile=None):
    """Sign out: remove the stored key and the marker (Umbrella's own setting is never touched)."""
    path = _path(profile)
    if not path:
        return False
    for name in (path, os.path.join(os.path.dirname(path), OWN)):
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        except OSError:
            return False
    return True


def own(profile=None):
    path = _path(profile)
    return bool(path) and os.path.exists(os.path.join(os.path.dirname(path), OWN)) and bool(_read(path))


def get(profile=None, umbrella=None):
    """The current AllDebrid key, or ''. `umbrella` is a function returning Umbrella's setting (tests pass one)."""
    path = _path(profile)
    if own(profile):
        return _read(path)               # the app's own sign-in outranks Umbrella's setting
    live = (umbrella or _umbrella)()
    if live:
        if _read(path) != live:
            _write(path, live)               # mirror a new or changed sign-in
        return live
    return _read(path)


def has(profile=None, umbrella=None):
    return bool(get(profile, umbrella))
