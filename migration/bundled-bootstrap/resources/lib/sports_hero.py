"""The two teams at the top of the game page and of its Info / Standings page (owner mockups pages 6 and 8): each team's colour glows behind its
crest, the short name and the record under it, and between them either the start time ("5:15 PM", "Today · in 2 h 10 min") or, in a live game,
"● LIVE", the score and the clock. Shared by sports_game_page.py and sports_game_facts_page.py; sports_game.py fills the properties."""
import status_ui as u

CREST, NAME_LINE = 230, 57
TEAM_FORMS = range(1, 4)    # lines the short team names take (a long one wraps, never cut)


def hero_height(lines):
    return 180 + CREST + 40 + NAME_LINE * lines + 60 + 70


def event_height(lines):
    """An event with one name (a Grand Prix, a tournament): the crest in the middle, the name under it, then LIVE / the session / the time, all centred."""
    return 450 + NAME_LINE * lines + 20 + 56 + 102 + 51 + 70


EVENT_NAME_WIDTH = 900


def textures(p):
    """A soft round glow (white, fading to nothing): the page tints it with each team's colour."""
    size = 256

    def pixel(x, y):
        d = (((x + .5) / size - .5) ** 2 + ((y + .5) / size - .5) ** 2) ** .5 * 2
        return (255, 255, 255, int(255 * max(0.0, 1 - d) ** 1.1))
    return {'sports_glow.png': p.png(size, size, pixel)}


def hero(p):
    out = ''
    for lines in TEAM_FORMS:
        height = hero_height(lines)
        card = p.image(-300, -40, 1000, height + 80, p.MEDIA + 'sports_glow.png', u.P('away.tint'), aspect='>stretch')
        card += p.image(380, -40, 1000, height + 80, p.MEDIA + 'sports_glow.png', u.P('home.tint'), aspect='>stretch')
        card += u.text(p, p.SIDE, 134, 972, 56, u.P('league'), 'p_foot_b', p.GREY, 'center')
        for side, x in (('away', 90), ('home', 760)):
            side_xml = p.image(x, 200, CREST, CREST, p.MEDIA + 'avatar_s.png', p.SURFACE2, '<visible>' + u.neg(u.has(side + '.crest')) + '</visible>')
            side_xml += p.image(x, 200, CREST, CREST, u.P(side + '.crest'), extra='<visible>' + u.has(side + '.crest') + '</visible>', aspect='>keep', background=True)
            side_xml += u.text(p, x, 200, CREST, CREST, u.P(side + '.code'), 'p_pill', align='center').replace(
                '</control>', '<visible>' + u.neg(u.has(side + '.crest')) + '</visible></control>')
            side_xml += p.textbox(x - 60, 450, CREST + 120, NAME_LINE * lines, u.P(side + '.name'), 'p_h3').replace('<autoscroll>', '<align>center</align><autoscroll>')
            side_xml += u.text(p, x - 60, 450 + NAME_LINE * lines + 6, CREST + 120, 51, u.P(side + '.record'), 'p_foot', p.GREY, 'center')
            # A tournament or a race weekend has a title and no opponent: only the first side is drawn.
            card += '<control type="group"><visible>%s</visible>%s</control>' % (u.has('home.name') if side == 'home' else 'true', side_xml)
        card += u.text(p, 325, 214, 430, 50, '[B]● LIVE[/B]', 'p_foot_b', 'FFFF453A', 'center').replace(
            '</control>', '<visible>' + u.has('game.live') + '</visible></control>')
        card += u.text(p, 325, 270, 430, 94, u.P('clock'), 'p_title', align='center')
        card += u.text(p, 310, 372, 460, 51, u.P('when'), 'p_foot', p.GREY, 'center')
        out += u.group(p, height, card, 'String.IsEqual(Window().Property(hero.lines),%d) + %s' % (lines, u.has('home.name')))
    return out + _event(p)


def _event(p):
    """The same hero for a game with no opponent (owner, 2026-11-27: "f1s page is not optimized for F1. It should have team in center, with logo not on left")."""
    out = ''
    middle = (1080 - CREST) // 2
    for lines in TEAM_FORMS:
        height = event_height(lines)
        card = p.image(40, -40, 1000, height + 80, p.MEDIA + 'sports_glow.png', u.P('away.tint'), aspect='>stretch')
        card += u.text(p, p.SIDE, 134, 972, 56, u.P('league'), 'p_foot_b', p.GREY, 'center')
        card += p.image(middle, 200, CREST, CREST, p.MEDIA + 'avatar_s.png', p.SURFACE2, '<visible>' + u.neg(u.has('away.crest')) + '</visible>')
        card += p.image(middle, 200, CREST, CREST, u.P('away.crest'), extra='<visible>' + u.has('away.crest') + '</visible>', aspect='>keep', background=True)
        card += u.text(p, middle, 200, CREST, CREST, u.P('away.code'), 'p_pill', align='center').replace(
            '</control>', '<visible>' + u.neg(u.has('away.crest')) + '</visible></control>')
        card += p.textbox((1080 - EVENT_NAME_WIDTH) // 2, 450, EVENT_NAME_WIDTH, NAME_LINE * lines, u.P('away.name'), 'p_h3').replace('<autoscroll>', '<align>center</align><autoscroll>')
        below = 450 + NAME_LINE * lines + 20
        live = u.has('game.live')
        card += u.text(p, p.SIDE, below, 972, 50, '[B]● LIVE[/B]', 'p_foot_b', 'FFFF453A', 'center').replace('</control>', '<visible>' + live + '</visible></control>')
        for top, shown in ((below + 56, live), (below, u.neg(live))):   # the session / the time sits under LIVE, or right under the name when it is not live
            card += u.text(p, p.SIDE, top, 972, 94, u.P('clock'), 'p_title', align='center').replace('</control>', '<visible>' + shown + '</visible></control>')
        for top, shown in ((below + 56 + 102, live), (below + 102, u.neg(live))):
            card += u.text(p, 54, top, 972, 51, u.P('when'), 'p_foot', p.GREY, 'center').replace('</control>', '<visible>' + shown + '</visible></control>')
        out += u.group(p, height, card, 'String.IsEqual(Window().Property(hero.lines),%d) + %s' % (lines, u.neg(u.has('home.name'))))
    return out
