"""Sports › Remind me (owner-approved board C, C2): the sheet that asks what to be reminded about.

Two switches on the app's choice sheet, "When a source is ready" and "15 minutes before it starts"; "Turn on reminder" saves,
Cancel leaves things as they were. When a reminder already exists the sheet opens with its switches and "Update reminder", plus
"Turn reminder off". `ask()` returns the saved record, None when it was turned off, or False when cancelled.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import choice_sheet
import sports_model as sm
import sports_reminders as sr


def spec(game, existing, on_source, before, offset):
    start = int(game.get('start') or 0)
    rows = [{'label': 'When a source is ready', 'detail': 'Then Play appears on the game', 'switch': on_source, 'tint': 'FF0A84FF', 'glyph': 'play.png'},
            {'label': '15 minutes before it starts', 'detail': 'At %s' % sm.clock_text(start - sr.BEFORE, offset), 'switch': before,
             'tint': 'FFFF9F0A', 'glyph': 'clock.png'}]
    return {'heading': 'Remind me about %s' % sr.title_of(game), 'sub': 'A notification on this phone. It opens this game.',
            'rows': rows, 'link': 'Turn reminder off' if existing else 'Turn on reminder', 'button': 'Done' if existing else 'Cancel',
            'foot': 'Reminders arrive while Kodi is closed; iOS may deliver them a little late.'}


def ask(game, profile, choose=choice_sheet.choose, now=None):
    """Run the sheet. A new reminder is saved by 'Turn on reminder' (Cancel leaves things as they were); an existing one saves every flip
    at once. Returns the saved record, None when the reminder was turned off, False when nothing changed."""
    import time
    offset = sm.device_offset(int(now or time.time()))
    existing = sr.get(profile, game['id'])
    state = {'on_source': existing['on_source'] if existing else True, 'before': existing['before'] if existing else True}

    def flip(index):
        key = 'on_source' if index == 0 else 'before'
        state[key] = not state[key]
        if existing:
            sr.set_reminder(profile, game, state['on_source'], state['before'])
        return state[key]
    answer = choose(spec(game, existing, state['on_source'], state['before'], offset), toggle=flip)
    link = 2
    if existing:
        if answer == link:
            sr.set_reminder(profile, game, False, False)
            return None
        return sr.get(profile, game['id']) if sr.get(profile, game['id']) != existing else False
    if answer == link:
        return sr.set_reminder(profile, game, state['on_source'], state['before'])
    return False
