"""The one door the Sports pages use to reach sports data (DEC-057).

Pages call get() and play(); they never talk to an add-on. get() returns a provider with the methods listed in sports_model.py.
Real data only: with no setting, get() is the real provider (ESPN's public scoreboard feed, sports_espn.py); when nothing answers, every call raises
SportsUnavailable and the pages say "Can't load ... right now" (the sample games must never reach a phone as if they were real).
For building and looking at pages in the desktop Kodi rig and in tests, set KODI_IOS_SPORTS=sample (the approved boards' sample
data), =quiet (nothing live: the grey Live Now tile) or =down (every call fails).
"""
import os

import sports_model

_provider = [None]
_real = [None]


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
    """The provider the phone uses: JetExtractors' scrapers for the games and their streams (DEC-061). ESPN's feed (sports_espn.py, DEC-059/060) stays
    in the app and is used with KODI_IOS_SPORTS=espn."""
    if _real[0] is None:
        if os.environ.get('KODI_IOS_SPORTS', '') == 'espn':
            import sports_espn
            _real[0] = sports_espn.EspnProvider()
        else:
            import sports_jet
            import sports_scores
            _real[0] = sports_jet.JetProvider(remote=True, score_loader=sports_scores.fetch_live)   # a page's thread cannot call JetExtractors: its script does (ISSUE-365)
    return _real[0]


def reset():
    """Forget the cached provider (tests)."""
    _provider[0] = None
    _real[0] = None


def play(source, log=lambda message: None):
    """Play a source at once (what a tap on a source line does). The sample provider only logs; the real one hands source['play'] to
    Kodi's player."""
    log('sports: play %s from %s (%s, %s)' % (source.get('id'), source.get('addon'), source.get('quality'), source.get('language')))
    if os.environ.get('KODI_IOS_SPORTS', '') in ('', 'jet') and str(source.get('play') or '').startswith('{'):
        import sports_jet
        return sports_jet.play_request(source, log)
    return source.get('play')
