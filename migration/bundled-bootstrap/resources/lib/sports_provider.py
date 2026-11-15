"""The one door the Sports pages use to reach sports data (DEC-057).

Pages call get() and play(); they never talk to an add-on. get() returns a provider with the methods listed in sports_model.py.
Until the real providers (The Loop first) land, get() returns the sample provider, so every page can be built, tested and looked at
in the desktop Kodi rig. KODI_IOS_SPORTS=sample forces the sample data once real providers exist (rig, tests); KODI_IOS_SPORTS=down
makes every call raise SportsUnavailable (to look at the "can't load" pages).
"""
import os

import sports_model

_provider = [None]


def get():
    mode = os.environ.get('KODI_IOS_SPORTS', '')
    if mode == 'down':
        return sports_model.Sample(fail=True)
    if _provider[0] is None:
        _provider[0] = sports_model.Sample(offset=sports_model.device_offset())
    return _provider[0]


def reset():
    """Forget the cached provider (tests)."""
    _provider[0] = None


def play(source, log=lambda message: None):
    """Play a source at once (what a tap on a source line does). The sample provider only logs; the real one hands source['play'] to
    Kodi's player."""
    log('sports: play %s from %s (%s, %s)' % (source.get('id'), source.get('addon'), source.get('quality'), source.get('language')))
    return source.get('play')
