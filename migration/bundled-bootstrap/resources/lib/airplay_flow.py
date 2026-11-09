"""Play on TV over AirPlay: one card over the paused video from pressing Play on TV until the TV plays, or a problem
with buttons that fix it (owner-approved mockups, 2026-11-08: https://claude.ai/artifact/6rg8jopnvJRVKRUotRgNZM,
boards 1, 2, 3, 5 and 6). It replaces Kodi's generic progress box and OK alerts (owner: "these are uglyy").

- stage_view(stage): the three steps (open the movie, choose your TV, connect and play), which one runs, the bar.
- problem_view(kind, ...): what happened in plain words and the buttons that help (Try again, Pause uploads and try
  again, Open Settings, Keep watching here, Cancel). Each button returns an action word to cast.send_airplay.
- page(): 1080i/IOSAirPlayFlow.xml on Fuse's landscape canvas (Play on TV happens over the video), with Fuse's fonts
  like IOSPlayOnTV.xml. Board 4 (the phone as a remote while the TV plays) needs native pause/seek; not here yet.
- make(xbmc, xbmcgui): the window class; its bar is set through live_window.Guard (ISSUE-123).
"""
WINDOW = 'IOSAirPlayFlow.xml'
CLOSE, B1, B2, B3, LINK, BAR = 9500, 9701, 9702, 9703, 9705, 9710
STAGES = ('opening', 'waiting_tv', 'connecting')
STEPS = (('Opening the movie', 'reading its index'), ('Choose your TV', 'in the AirPlay list'),
         ('Connect and play', ''))
ACTIVE = {'opening': ('Opening the movie', 'reading its index'),
          'waiting_tv': ('Choose your TV', 'in the AirPlay list'),
          'connecting': ('Waiting for the TV to start playing', 'up to 15 s')}
DONE = ('Movie opened', 'TV chosen', '')
BAR_PCT = {'opening': 22, 'waiting_tv': 48, 'connecting': 74}
FOOT = {'opening': 'Usually a few seconds. Your downloads keep going, slower.',
        'waiting_tv': 'The TV and this iPhone must be on the same Wi-Fi.',
        'connecting': 'Kodi keeps playing here until the TV starts.'}
TITLES = {'opening': 'Play on TV', 'waiting_tv': 'Choose your TV', 'connecting': 'Connecting to your TV'}


def stage_view(stage, title='', quality='', skipped=(), converting=False):
    """Window properties for a running stage. `skipped`: stages this attempt never needs (a direct link opens nothing)."""
    stage = stage if stage in STAGES else 'opening'
    now = STAGES.index(stage)
    props = {'mode': 'steps', 'title': TITLES[stage], 'sub': ' · '.join(x for x in (title, quality) if x),
             'foot': FOOT[stage], 'bar': str(BAR_PCT[stage]), 'b1.label': '', 'b2.label': '', 'b3.label': '',
             'link.label': '', 'cancel.label': 'Cancel'}
    for n, name in enumerate(STAGES):
        state = 'active' if n == now else 'done' if n < now or name in skipped else 'todo'
        label, note = (ACTIVE[name] if state == 'active' else (DONE[n], '') if state == 'done' else STEPS[n])
        if state == 'todo':
            note = ''
        props.update({'step%d.state' % n: state, 'step%d.label' % n: label, 'step%d.note' % n: note,
                      'step%d.number' % n: str(n + 1) if state == 'todo' else ''})
    if converting and stage == 'opening':
        # r36: the TV took the sound only; the picture is being converted to H.264 for it.
        props.update({'title': 'Converting the picture for your TV', 'step0.label': 'Converting the picture to H.264',
                      'step0.note': 'your TV cannot show it as it is', 'foot': 'Kodi keeps playing here until the TV starts.'})
    return props


def busy_words(model):
    """'Interstellar is uploading to Google Drive at 0.3 MB/s' from the status model, or '' when nothing moves."""
    for job in (model or {}).get('jobs') or []:
        if job.get('state') in ('running', 'slowed') and job.get('kind') in ('conv', 'repack', 'copy', 'upload', 'down'):
            rate = float(job.get('rate') or 0)
            what = 'is downloading' if job.get('kind') == 'down' else 'is uploading to Google Drive'
            return '%s %s%s' % (job.get('title') or 'A video', what, ' at %.1f MB/s' % (rate / 1048576) if rate else '')
    return ''


def problem_view(kind, title='', reason='', busy='', settings=False):
    """Window properties for a problem (boards 5 and 6). kind: startup_timeout, slow_source, unreachable, selection_timeout,
    failed, mirroring. Buttons carry their action in '<b>.action'."""
    props = {'mode': 'problem', 'sub': title, 'foot': '', 'bar': '0', 'cancel.label': '', 'check1': '', 'check1.note': '',
             'check2': '', 'b1.label': '', 'b2.label': '', 'b3.label': '', 'link.label': '',
             'b1.action': '', 'b2.action': '', 'b3.action': '', 'link.action': ''}

    def buttons(*pairs, link=None):
        for n, pair in enumerate(pairs, 1):
            props['b%d.label' % n], props['b%d.action' % n] = pair
        if link:
            props['link.label'], props['link.action'] = link

    if kind == 'startup_timeout':
        props.update(title='The movie took too long to open', icon='clock.png')
        if busy:
            props['text'] = 'Your internet is busy: %s. The TV was never asked to connect, so your Wi-Fi and settings are fine.' % busy
            buttons(('Pause uploads and try again', 'pause_retry'), ('Try again', 'retry'), link=('Keep watching here', 'watch'))
        else:
            props['text'] = 'Opening it over your connection took longer than a minute. The TV was never asked to connect, so your Wi-Fi and settings are fine.'
            buttons(('Try again', 'retry'), link=('Keep watching here', 'watch'))
    elif kind == 'unreachable':
        props.update(title="Your TV can't reach this iPhone", icon='wifi.png',
                     text="The movie was ready, but the TV couldn't connect to it.",
                     check1='Local Network is on for Kodi', check2='The TV and this iPhone are on the same Wi-Fi')
        props['check1.note'] = 'Settings › Kodi'
        if settings:
            buttons(('Open Settings', 'settings'), ('Try again', 'retry'), ('Cancel', 'watch'))
        else:
            buttons(('Try again', 'retry'), ('Cancel', 'watch'))
    elif kind == 'slow_source':
        # r38 (owner, build 201: "port the wifi card"; uploads keep going in the background, so no pause button).
        props.update(title='The movie took too long to load', icon='wifi.png')
        props['text'] = ("The TV connected, but reading the movie from Drive took too long for playback to start.%s "
                         "Try again to reconnect to the movie." % (' %s at the same time.' % busy if busy else ''))
        buttons(('Try again', 'retry'), link=('Keep watching here', 'watch'))
    elif kind == 'selection_timeout':
        props.update(title='No TV was chosen', icon='tv.png', text='Choose a TV in the AirPlay list to play there.')
        buttons(('Try again', 'retry'), link=('Keep watching here', 'watch'))
    elif kind == 'mirroring':
        props.update(title="AirPlay can't send this video", icon='tv.png', text=reason)
        buttons(('OK', 'watch'))
    else:
        props.update(title="AirPlay couldn't play this", icon='triangle-exclamation.png', text=reason or 'The TV did not answer.')
        buttons(('Try again', 'retry'), link=('Keep watching here', 'watch'))
    props['size'] = 'long' if props['check1'] else 'mid' if props['link.label'] else 'short'
    return props


# --- layout (Fuse 1920x1080 landscape canvas; 1 pt of the approved boards = 2.687 units) ---------------------------
W, PAD = 1500, 54
MEDIA, ICONS = 'special://skin/extras/portrait/', 'special://skin/extras/icons/'
GREEN, BLUE, GREY, WHITE, SURF2, SURF3, SURF1 = 'FF30D158', 'FF0A84FF', '99EBEBF5', 'FFFFFFFF', 'FF2C2C2E', 'FF48484A', 'FF1C1C1E'
HEIGHTS = {'steps': 770, 'short': 560, 'mid': 680, 'long': 820}


def _p(key):
    return '$INFO[Window().Property(%s)]' % key


def _has(key):
    return '!String.IsEmpty(Window().Property(%s))' % key


def _is(key, value):
    return 'String.IsEqual(Window().Property(%s),%s)' % (key, value)


def _img(x, y, w, h, tex, color=WHITE, extra='', border=''):
    return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<texture%s colordiffuse="%s">%s</texture>%s</control>'
            % (x, y, w, h, ' border="%s"' % border if border else '', color, tex, extra))


def _lab(x, y, w, h, text, font, color=WHITE, align='left', extra=''):
    return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font>'
            '<textcolor>%s</textcolor><align>%s</align><aligny>center</aligny><scroll>false</scroll><label>%s</label>%s</control>'
            % (x, y, w, h, font, color, align, text, extra))


def _box(x, y, w, h, text, font, color=GREY):
    return ('<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>%d</height><font>%s</font>'
            '<textcolor>%s</textcolor><autoscroll>false</autoscroll><label>%s</label></control>' % (x, y, w, h, font, color, text))


def _capsule(ident, w, label, primary, cond, extra=''):
    fill, text = (WHITE, 'FF000000') if primary else (SURF3, WHITE)
    return ('<control type="button" id="%d"><width>%d</width><height>129</height><label>%s</label><font>font_main_bold</font>'
            '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturenofocus border="64" colordiffuse="%s">%spill_128.png</texturenofocus>'
            '<texturefocus border="64" colordiffuse="%s">%spill_128.png</texturefocus><visible>%s</visible>%s</control>'
            % (ident, w, label, text, text, fill, MEDIA, 'FFD1D1D6' if primary else 'FF5A5A5E', MEDIA, cond, extra))


def _step(n, y):
    key = 'step%d.' % n
    state = lambda s: '<visible>%s</visible>' % _is(key + 'state', s)
    icon = (_img(PAD, y, 65, 65, MEDIA + 'dot.png', GREEN, state('done')) +
            _img(PAD + 8, y + 8, 50, 50, ICONS + 'check.png', 'FF000000', state('done')) +
            _img(PAD, y, 65, 65, MEDIA + 'ring.png', BLUE, state('active') +
                 '<animation effect="rotate" end="-360" center="auto" time="900" loop="true" reversible="false" condition="true">Conditional</animation>') +
            _img(PAD, y, 65, 65, MEDIA + 'ring.png', '4DEBEBF5', state('todo')) +
            _lab(PAD, y, 65, 65, _p(key + 'number'), 'font_mini_bold', GREY, 'center', state('todo')))
    label = (_lab(PAD + 97, y, W - 2 * PAD - 97 - 330, 65, _p(key + 'label'), 'font_main_bold', WHITE, 'left', state('active')) +
             _lab(PAD + 97, y, W - 2 * PAD - 97 - 330, 65, _p(key + 'label'), 'font_main', GREY, 'left',
                  '<visible>!%s</visible>' % _is(key + 'state', 'active')) +
             _lab(W - PAD - 320, y, 320, 65, _p(key + 'note'), 'font_mini', GREY, 'right'))
    return icon + label


def page(close_button):
    steps_body = (
        _img(0, 0, W, HEIGHTS['steps'], MEDIA + 'row_only.png', SURF2, border='43') +
        _img(PAD, PAD, 107, 161, MEDIA + 'white.png', 'FF3A3A3C') +
        _img(PAD, PAD, 107, 161, _p('poster'), WHITE, '<aspectratio>scale</aspectratio>') +
        _lab(PAD + 139, PAD + 20, W - 2 * PAD - 139 - 150, 64, _p('title'), 'font_head_bold') +
        _lab(PAD + 139, PAD + 88, W - 2 * PAD - 139 - 150, 50, _p('sub'), 'font_mini', GREY) +
        ''.join(_step(n, 270 + n * 92) for n in range(3)) +
        '<control type="progress" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>11</height>'
        '<texturebg border="5" colordiffuse="FF3A3A3C">%spill11.png</texturebg><midtexture border="5" colordiffuse="%s">%spill11.png</midtexture>'
        '<lefttexture /><righttexture /><overlaytexture /></control>' % (BAR, PAD, 560, W - 2 * PAD, MEDIA, BLUE, MEDIA) +
        _lab(PAD, 602, W - 2 * PAD - 360, 129, _p('foot'), 'font_mini', GREY) +
        '<control type="group"><left>%d</left><top>602</top>' % (W - PAD - 320) +
        _capsule(9704, 320, _p('cancel.label'), False, _has('cancel.label'), '<onup>%d</onup>' % CLOSE) + '</control>')
    backs = ''.join(_img(0, 0, W, h, MEDIA + 'row_only.png', SURF2, '<visible>%s</visible>' % _is('size', k), '43')
                    for k, h in HEIGHTS.items() if k != 'steps')
    checks = ('<control type="group"><width>%d</width><height>250</height><visible>%s</visible>' % (W, _has('check1')) +
              _img(PAD, 0, W - 2 * PAD, 220, MEDIA + 'row_only.png', SURF1, border='43') +
              ''.join(_img(PAD + 38, 22 + n * 110, 54, 54, MEDIA + 'dot.png', 'FF3A3A3C') +
                      _lab(PAD + 38, 22 + n * 110, 54, 54, '$NUMBER[%d]' % (n + 1), 'font_mini_bold', WHITE, 'center') +
                      _lab(PAD + 120, 0 + n * 110, W - 2 * PAD - 120 - 420, 98, _p('check%d' % (n + 1)), 'font_main') +
                      _lab(W - PAD - 400, 0 + n * 110, 362, 98, _p('check%d.note' % (n + 1)), 'font_mini', GREY, 'right')
                      for n in range(2)) +
              _img(PAD + 120, 108, W - 2 * PAD - 158, 3, MEDIA + 'white.png', '1FEBEBF5') + '</control>')
    row = ('<control type="grouplist" id="9720"><width>%d</width><height>160</height><left>%d</left><orientation>horizontal</orientation>'
           '<itemgap>27</itemgap><usecontrolcoords>true</usecontrolcoords>' % (W - 2 * PAD, PAD) +
           _capsule(B1, 760, _p('b1.label'), True, _has('b1.label')) + _capsule(B2, 300, _p('b2.label'), False, _has('b2.label')) +
           _capsule(B3, 270, _p('b3.label'), False, _has('b3.label')) + '</control>')
    link = ('<control type="group"><width>%d</width><height>129</height><visible>%s</visible>' % (W, _has('link.label')) +
            '<control type="button" id="%d"><left>%d</left><width>%d</width><height>118</height><label>%s</label><font>font_main_bold</font>'
            '<textcolor>FF4FA8FF</textcolor><focusedcolor>FFFFFFFF</focusedcolor><align>center</align><aligny>center</aligny>'
            '<texturefocus border="30" colordiffuse="26FFFFFF">%sround_s.png</texturefocus><texturenofocus /></control></control>'
            % (LINK, PAD, W - 2 * PAD, _p('link.label'), MEDIA))
    problem_body = (
        backs + _img(PAD, PAD, 107, 107, MEDIA + 'r27.png', '2EFF9F0A', border='27') +
        _img(PAD - 10, PAD - 10, 127, 127, ICONS + _p('icon'), 'FFFF9F0A', '<aspectratio>keep</aspectratio>') +
        _lab(PAD + 139, PAD, W - 2 * PAD - 139 - 160, 64, _p('title'), 'font_head_bold') +
        '<control type="grouplist"><left>0</left><top>%d</top><width>%d</width><height>%d</height><orientation>vertical</orientation>'
        '<itemgap>0</itemgap><usecontrolcoords>true</usecontrolcoords>' % (PAD + 72, W, HEIGHTS['long']) +
        '<control type="group"><width>%d</width><height>200</height>%s</control>' % (W, _box(PAD + 139, 0, W - 2 * PAD - 139 - 160, 180, _p('text'), 'font_main')) +
        checks + '<control type="group"><width>%d</width><height>160</height>%s</control>' % (W, row) + link + '</control>')
    body = (
        _img(0, 0, 1920, 1080, MEDIA + 'white.png', '8C000000').replace('<width>1920</width>', '<width>100%</width>') +
        '<control type="group"><centerleft>50%%</centerleft><top>130</top><width>%d</width>' % W +
        '<animation effect="zoom" start="94" end="100" center="auto" time="220" tween="back" easing="out">WindowOpen</animation>'
        '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>'
        '<animation effect="fade" start="100" end="0" time="120">WindowClose</animation>' +
        '<control type="group"><visible>%s</visible>%s</control>' % (_is('mode', 'steps'), steps_body) +
        '<control type="group"><visible>%s</visible>%s</control>' % (_is('mode', 'problem'), problem_body) +
        close_button(CLOSE, W - PAD - 118, 40, size=118) + '</control>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Kodi-iOS player controls: Play on TV flow (owner-approved boards 1-3, 5, 6) -->\n'
            '<window type="dialog"><defaultcontrol always="true">%d</defaultcontrol><controls>%s</controls></window>\n' % (B1, body))


def make(xbmc, xbmcgui):
    """The window class (modeless while the attempt runs; choice() waits for a button)."""
    import live_window

    class Flow(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.guard = live_window.Guard(self)
            self.chosen = ''
            self.props = getattr(self, 'props', {})
            for k, v in self.props.items():
                self.setProperty(k, v)
            try:   # onInit runs on Kodi's side while the window opens: safe without the guard
                self.getControl(BAR).setPercent(float(self.props.get('bar') or 0))
            except Exception:
                pass

        def apply(self, props):
            self.props = dict(getattr(self, 'props', {}), **props)
            for k, v in props.items():
                self.setProperty(k, v)
            if hasattr(self, 'guard'):
                self.guard.percent(BAR, props.get('bar') or 0)
            if props.get('mode') == 'problem':
                try:
                    self.setFocusId(B1)
                except Exception:
                    pass

        def canceled(self):
            return getattr(self, 'chosen', '') in ('cancel', 'watch')

        def onClick(self, control):
            key = {B1: 'b1', B2: 'b2', B3: 'b3', LINK: 'link'}.get(control)
            if key:
                self.chosen = self.props.get(key + '.action') or 'watch'
            elif control in (CLOSE, 9704):
                self.chosen = 'cancel'

        def onAction(self, action):
            if action.getId() in (9, 10, 92, 110):
                self.chosen = 'cancel'

        def choice(self, monitor):
            while not self.chosen and not monitor.waitForAbort(0.15):
                pass
            return self.chosen or 'cancel'

        def finish(self):
            if hasattr(self, 'guard'):
                self.guard.close()
            else:
                self.close()

    return Flow
