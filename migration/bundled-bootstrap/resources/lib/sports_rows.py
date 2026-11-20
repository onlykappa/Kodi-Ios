"""One game row's window properties (owner-approved mockup docs/design/sports-list-rows.html, 2026-11-20).

The row is the Apple Sports layout: each team is its logo with its short name and its record under it, the league tag and the
start time sit in the middle. Used by the hub's Up next and by Upcoming (and so the league pages). Pure: crest files are looked up
in the dict the caller got from sports_logos.crests().

A game with no second side (a golf tournament, a race weekend) has no two teams to draw, so it gets form 2: its title (wrapped) with the
tag and time on the right. The property that picks the form is still called "lines" (row.N.lines / next.N.lines).
"""
import sports_model as sm

NAME_MAX = 16   # characters that fit under a logo at 13 pt (policy 4.2): a longer club name falls back to its code, never cut
FORMS = (1, 2)
KEYS = ('clock', 'tag', 'lines', 'title', 'pos', 'away.name', 'away.rec', 'away.logo', 'home.name', 'home.rec', 'home.logo')   # every property a row sets


def team_name(team, fighter=False):
    """The short name under the logo: ESPN's short name (a fighter: the last name), else the full name. Over NAME_MAX it is the code, never cut."""
    name = str(team.get('name') or '').strip()
    if fighter:
        name = name.split(' ')[-1]
    else:
        name = str(team.get('short') or name).strip()
    if not name or len(name) > NAME_MAX:
        name = str(team.get('code') or name[:NAME_MAX])
    return name


def crest_url(team):
    """The small (96 px) crest address for a team, or ''."""
    import sports_logos
    return sports_logos.small(team.get('crest'))


def crest_urls(games):
    return [u for g in games for u in (crest_url(g['away']), crest_url(g['home'])) if u]


def row_props(game, now, offset, crests=None, pos=''):
    """{suffix: value} for one row; '' values for no game."""
    if not game:
        return {}
    crests = crests or {}
    two = bool(game['home'].get('name')) and bool(game['away'].get('name'))
    out = {'clock': sm.clock_text(game['start'], offset), 'tag': game['league'], 'lines': '1' if two else '2',
           'title': game.get('title') or sm.versus(game), 'pos': pos}
    for side in ('away', 'home'):
        team = game[side]
        out.update({side + '.name': team_name(team, game.get('sport') == 'Combat sports') if two else '', side + '.rec': str(team.get('record') or '') if two else '',
                    side + '.logo': crests.get(crest_url(team), '') if two else ''})
    return out
