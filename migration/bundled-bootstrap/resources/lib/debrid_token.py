"""The AllDebrid key, kept in the app's own profile so removing or breaking Umbrella does not take it away.

Umbrella stays the place you sign in: its setting `alldebridtoken` is read first, so a fresh sign-in or a new key is picked up at once.
Every successful read is mirrored into the app's profile (alldebrid.token, owner-only file); when Umbrella is missing, disabled or
empty, that copy is used. The key lives only in the phone's profile folder: never in the repository, the IPA, a log or a diagnostic.
"""
import os
import tempfile

NAME = 'alldebrid.token'
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


def get(profile=None, umbrella=None):
    """The current AllDebrid key, or ''. `umbrella` is a function returning Umbrella's setting (tests pass one)."""
    path = _path(profile)
    live = (umbrella or _umbrella)()
    if live:
        if _read(path) != live:
            _write(path, live)               # mirror a new or changed sign-in
        return live
    return _read(path)


def has(profile=None, umbrella=None):
    return bool(get(profile, umbrella))
