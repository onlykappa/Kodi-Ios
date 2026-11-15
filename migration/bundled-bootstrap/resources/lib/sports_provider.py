"""The one door the Sports pages use to reach sports data (DEC-057).

Pages call get() and play(); they never talk to an add-on. get() returns a provider with the methods listed in sports_model.py.
Real data only: with no setting, get() is the real provider. Until The Loop's provider lands that has no source, so every call raises
SportsUnavailable and the pages say "Can't load ... right now" (the sample games must never reach a phone as if they were real).
For building and looking at pages in the desktop Kodi rig and in tests, set KODI_IOS_SPORTS=sample (the approved boards' sample
data), =quiet (nothing live: the grey Live Now tile) or =down (every call fails).
"""
import os

import sports_model

_provider = [None]


def get():
    mode = os.environ.get('KODI_IOS_SPORTS', '')
    if mode == 'down':
        return sports_model.Sample(fail=True)
    if mode == 'quiet':
        return sports_model.Sample(offset=sports_model.device_offset(), quiet=True)
    if mode == 'sample':
        if _provider[0] is None:
            _provider[0] = sports_model.Sample(offset=sports_model.device_offset())
        return _provider[0]
    return real()


def real():
    """The providers of the add-ons on this phone, combined (DEC-055). The Loop's lands next; until then there is no source."""
    return sports_model.Sample(fail=True)


def reset():
    """Forget the cached provider (tests)."""
    _provider[0] = None


def play(source, log=lambda message: None):
    """Play a source at once (what a tap on a source line does). The sample provider only logs; the real one hands source['play'] to
    Kodi's player."""
    log('sports: play %s from %s (%s, %s)' % (source.get('id'), source.get('addon'), source.get('quality'), source.get('language')))
    return source.get('play')
