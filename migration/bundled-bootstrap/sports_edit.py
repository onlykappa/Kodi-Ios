"""Sports › Edit: which leagues show (owner-approved board B, docs/design/sports-redesign-mockups.html).

Two steps on the app's choice sheet: the sports (with how many leagues are on), then one sport's leagues with a switch each and
its real logo. Every flip is saved at once (sports_filter), so closing the sheet any way keeps the choice. `edit()` returns True when the
choice changed, so the page that opened it draws itself again.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import choice_sheet
import sports_filter as sf


def edit(rows, profile, logos=None, choose=choice_sheet.choose):
    """Run the sheets over `rows` (the provider's every league). Returns True when the choice changed."""
    before = sf.load(profile)
    off = set(before)
    while True:
        spec = sf.sports_spec(rows, off)
        answer = choose(spec)
        sports = [s for s, _ in sf.sports_of(rows)][:8]
        if answer == len(spec['rows']) and spec.get('link'):      # "Turn every league on"
            off = sf.all_on()
            sf.save(profile, off)
            continue
        if not 0 <= answer < len(sports):
            break                                                   # Done, Back or the swipe: the choice is already saved
        spec2, codes = sf.leagues_spec(rows, off, sports[answer], logos)

        def flip(index, codes=codes):
            nonlocal off
            off = sf.toggled(off, codes[index])
            sf.save(profile, off)
            return codes[index] not in off
        choose(spec2, toggle=flip)
    return sf.load(profile) != before


def run(args=()):
    import xbmc
    import xbmcvfs
    import sports_logos
    import sports_provider
    profile = xbmcvfs.translatePath('special://profile/')
    try:
        rows = sports_provider.get().all_leagues()
    except Exception as error:
        xbmc.log('Kodi iOS Sports: edit could not list leagues: %s' % type(error).__name__, xbmc.LOGWARNING)
        return False
    logos = sports_logos.paths(profile, [r['code'] for r in rows])
    return edit(rows, profile, logos)


if __name__ == '__main__':
    run(sys.argv[1:])
