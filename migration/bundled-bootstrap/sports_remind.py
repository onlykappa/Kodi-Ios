"""Sports › Remind me (owner mockup page 7): the sheet that asks what to be reminded about (sports_remind_page.py draws it).

Two switches, "When a source is ready" and "15 minutes before it starts"; the white "Turn on reminder" saves, "Cancel" leaves things as they
were. When a reminder already exists the sheet opens with its switches (each flip saved at once), a white "Done" and a red "Turn reminder off".
`ask()` returns the saved record, None when it was turned off, or False when nothing changed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import sports_model as sm
import sports_reminders as sr


def spec(game, existing, on_source, before, offset, now=None):
    start = int(game.get('start') or 0)
    rows = [{'label': 'When a source is ready', 'detail': 'Then Play appears here', 'switch': on_source, 'tint': 'FF0A84FF', 'glyph': 'play.png'},
            {'label': '15 minutes before it starts', 'detail': '%s at %s' % (sm.day_label(start - sr.BEFORE, int(now) if now else start - sr.BEFORE, offset), sm.clock_text(start - sr.BEFORE, offset)),
             'switch': before,
             'tint': 'FFFF9F0A', 'glyph': 'clock.png'}]
    return {'heading': 'Remind me about %s' % sr.title_of(game), 'sub': 'A notification on this phone. It opens this game.',
            'rows': rows, 'link': 'Turn reminder off' if existing else 'Turn on reminder', 'button': 'Done' if existing else 'Cancel',
            'primary': 'button' if existing else 'link'}   # which of the two is the white capsule: Done (existing) or Turn on reminder (new)


def window_props(spec):
    """The sheet window's properties for a spec (pure; the tests read them without Kodi)."""
    props = {'heading': spec['heading'], 'sub': spec['sub'], 'mode': 'new' if spec.get('primary') == 'link' else 'existing'}
    for n, row in enumerate(spec['rows'], 1):
        props.update({'row.%d.label' % n: row['label'], 'row.%d.detail' % n: row['detail'], 'row.%d.on' % n: 'on' if row['switch'] else 'off'})
    return props


def answer_for(control, spec):
    """The answer a tapped control gives, in the choice-sheet contract ask() uses: the link row is len(rows), Cancel / Done / Back is -1."""
    import sports_remind_page as page
    link = len(spec['rows'])
    if spec.get('primary') == 'link':
        return link if control == page.PRIMARY else -1
    return link if control == page.SECONDARY_OFF else -1


def choose_window(spec, toggle=None):
    """Show the sheet and return the answer (a switch flips in place through `toggle`)."""
    import xbmcgui
    import xbmcvfs
    import sports_remind_page as page
    result = {'answer': -1}

    class Sheet(xbmcgui.WindowXMLDialog):
        def onInit(self):
            for key, value in window_props(spec).items():
                self.setProperty(key, value)
            self.setFocusId(page.PRIMARY if spec.get('primary') == 'link' else page.DONE)

        def onClick(self, control):
            if control in (page.ROW1, page.ROW2):
                n = 1 if control == page.ROW1 else 2
                if toggle is not None:
                    self.setProperty('row.%d.on' % n, 'on' if toggle(n - 1) else 'off')
            elif control in (page.PRIMARY, page.DONE, page.SECONDARY, page.SECONDARY_OFF):
                result['answer'] = answer_for(control, spec)
                self.close()

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 110):
                self.close()

    try:
        sheet = Sheet(page.WINDOW, HERE, 'Default', '1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'), 'portrait') + '/')
        sheet = Sheet(page.WINDOW, HERE, 'Default', '1080i')
    sheet.doModal()
    del sheet
    return result['answer']


def ask(game, profile, choose=None, now=None):
    """Run the sheet. A new reminder is saved by 'Turn on reminder' (Cancel leaves things as they were); an existing one saves every flip
    at once. Returns the saved record, None when the reminder was turned off, False when nothing changed."""
    import time
    choose = choose or choose_window
    offset = sm.device_offset(int(now or time.time()))
    existing = sr.get(profile, game['id'])
    state = {'on_source': existing['on_source'] if existing else True, 'before': existing['before'] if existing else True}

    def flip(index):
        key = 'on_source' if index == 0 else 'before'
        state[key] = not state[key]
        if existing:
            sr.set_reminder(profile, game, state['on_source'], state['before'])
        return state[key]
    answer = choose(spec(game, existing, state['on_source'], state['before'], offset, now or time.time()), toggle=flip)
    link = 2
    if existing:
        if answer == link:
            sr.set_reminder(profile, game, False, False)
            return None
        return sr.get(profile, game['id']) if sr.get(profile, game['id']) != existing else False
    if answer == link:
        return sr.set_reminder(profile, game, state['on_source'], state['before'])
    return False
