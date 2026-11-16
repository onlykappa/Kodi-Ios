"""Sports › Leagues › one league (DEC-056, DEC-057: "a league's page is the approved Live Now cards and the approved Upcoming list, filtered").

The two approved pages already filter by league, so a league opens the one that has something to show: Live Now on that league's chip when
one of its games is live, otherwise Upcoming on that league's chip. The code arrives as the one argument after the page name.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import sports_model as sm  # noqa: E402


def choose(provider, code):
    """'live' when the provider has a live game in the league, else 'upcoming'; any failure also gives 'upcoming' (its error page says why)."""
    try:
        return 'live' if sm.filter_league(provider.live_games(), code) else 'upcoming'
    except Exception:
        return 'upcoming'


def run(args=()):
    code = args[0] if args else ''
    if not re.fullmatch(r'[A-Za-z0-9_-]+', code):
        return
    import sports_provider
    page = choose(sports_provider.get(), code)
    if page == 'live':
        import sports_live
        sports_live.run([code])
    else:
        import sports_upcoming
        sports_upcoming.run([code])


if __name__ == '__main__':
    run(sys.argv[1:])
