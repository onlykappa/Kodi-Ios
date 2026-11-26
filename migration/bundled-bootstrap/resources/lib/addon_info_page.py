"""portrait/DialogAddonInfo.xml: one portrait page for every add-on (owner-approved docs/design/addon-info-mockups.html,
frames 1-5). Replaces Fuse's landscape dialog squeezed into the phone.

Kodi drives the dialog through fixed control ids and writes their labels and enabled state, so each one stays as a
1x1 invisible button (Fuse does the same). The drawn rows only read their state and press them with SendClick:

    6  Install / Uninstall   (its label is "Uninstall" while the add-on is installed)
    7  Enable / Disable      (its label is "Disable" while the add-on is enabled)
    8  Update                9  Settings        10 Dependencies     12 Open / Run / Use     13 Auto-update   14 Versions

Page: hero (icon, name, author and type, status), one white primary capsule (Update, else Open, else Install) with
Settings beside it, rows for the switches, versions and dependencies, About, the description and what is new (full
text; the whole page scrolls, nothing is cut off) and a red Uninstall at the end.
"""
RADIUS_CARD = 26          # RADIUS: cards and posters (policy 4.4)
ROW = 140
GAP = 14
PAD = 43

UNINSTALL = 'String.IsEqual(Control.GetLabel(6),$LOCALIZE[24037])'
INSTALLED = UNINSTALL
ENABLED = 'String.IsEqual(Control.GetLabel(7),$LOCALIZE[24021])'
UPDATE = 'Control.IsEnabled(8)'
HAS_DATE = '!String.IsEmpty(ListItem.AddonLastUpdated) | !String.IsEmpty(ListItem.AddonInstallDate)'
VERSION = '$INFO[ListItem.AddonVersion]'


def spacer(h, visible=''):
    return '<control type="image"><height>%d</height>%s<texture /></control>' % (h, '<visible>%s</visible>' % visible if visible else '')


def carrier(id):
    """The real control Kodi writes its label and state into: 1x1, drawn as nothing."""
    return ('<control type="button" id="%d"><left>0</left><top>0</top><width>1</width><height>1</height><label></label>'
            '<texturefocus /><texturenofocus /></control>') % id


def card_row(p, id, y_label, kind, visible, click, first_in_card=False, glyph='', tint='', value='', switch='', red=False,
             nav=''):
    """One 140-unit card: a tappable row (press SendClick(real id)). kind 'chevron' | 'switch' | 'plain'."""
    w = p.WIDTH - 2 * p.SIDE
    color = 'FFFF453A' if red else p.WHITE
    x = PAD
    body = p.surface(0, 0, w, ROW, 'round_s.png', p.SURFACE, RADIUS_CARD)
    btn = ('<control type="button" id="%d"><left>0</left><top>0</top><width>%d</width><height>%d</height><label></label>'
           '<texturefocus border="26" colordiffuse="1FFFFFFF">%sround_s.png</texturefocus><texturenofocus />'
           '<onclick>%s</onclick>%s</control>') % (id, w, ROW, p.MEDIA, click, nav)
    if glyph:
        body_icon = (p.surface(PAD, (ROW - 84) // 2, 84, 84, 'tile84.png', 'FF0F0F10', 24) +
                     p.icon(PAD + 9, (ROW - 66) // 2, 66, glyph, tint))
        x = PAD + 84 + 34
    else:
        body_icon = ''
    align = 'center' if red else 'left'
    lab = p.label(x if not red else 0, 0, (w - x - 220) if not red else w, ROW, y_label, 'p_body', color, align)
    right = ''
    if value:
        right += p.label(w - 520 - 60, 0, 520, ROW, value, 'p_foot', p.GREY, 'right')
    if kind == 'chevron':
        right += p.icon(w - PAD - 20, (ROW - 34) // 2, 34, 'chevron-right.png', p.DIM)
    elif kind == 'switch':
        on = switch
        right += (p.image(w - PAD - 130, (ROW - 58) // 2, 130, 58, p.MEDIA + 'toggle_on.png', p.WHITE, '<visible>%s</visible>' % on) +
                  p.image(w - PAD - 130, (ROW - 58) // 2, 130, 58, p.MEDIA + 'toggle_off.png', p.WHITE, '<visible>![%s]</visible>' % on))
    return ('<control type="group"><width>%d</width><height>%d</height><visible>%s</visible>' % (p.WIDTH, ROW + GAP, visible) +
            '<control type="group"><left>%d</left>%s%s%s%s%s</control></control>' % (p.SIDE, body, body_icon, lab, right, btn))


def info_card(p, rows, visible=''):
    """About: label left, value right, in one rounded card (rows = [(label, info)])."""
    w = p.WIDTH - 2 * p.SIDE
    h = ROW * len(rows)
    inner = ''
    for i, (name, info) in enumerate(rows):
        y = i * ROW
        if i:
            inner += p.image(PAD, y, w - PAD, 2, p.MEDIA + 'white.png', p.SEP)
        inner += (p.label(PAD, y, 300, ROW, name, 'p_body', p.WHITE) +
                  p.label(PAD + 300, y, w - 2 * PAD - 300, ROW, info, 'p_body', p.GREY, 'right', '<scroll>false</scroll>'))
    return ('<control type="group"><width>%d</width><height>%d</height>%s' % (p.WIDTH, h + GAP, '<visible>%s</visible>' % visible if visible else '') +
            '<control type="group"><left>%d</left>' % p.SIDE + p.surface(0, 0, w, h, 'round_s.png', p.SURFACE, RADIUS_CARD) + inner + '</control></control>')


def text_block(p, heading, info, visible=''):
    """A heading and its full text: grows with the text, so the page (not a box) scrolls."""
    w = p.WIDTH - 2 * p.SIDE
    vis = '<visible>%s</visible>' % visible if visible else ''
    head = ('<control type="group"><width>%d</width><height>80</height>%s' % (p.WIDTH, vis) +
            p.label(p.SIDE + 20, 0, w - 40, 70, heading, 'p_h3', p.GREY) + '</control>')
    body = ('<control type="textbox"><left>%d</left><width>%d</width><height>auto</height><font>p_sub</font>'
            '<textcolor>FFD1D1D6</textcolor><align>left</align><autoscroll>false</autoscroll><label>%s</label>%s</control>') % (
        p.SIDE + 20, w - 40, p.e(info), vis)
    return head + body + spacer(40, visible)


def page_body(p):
    w = p.WIDTH - 2 * p.SIDE
    M = p.MEDIA
    status = lambda cond, text, color: p.label(0, 0, p.WIDTH, 60, text, 'p_foot_b', color, 'center', '<visible>%s</visible>' % cond)
    st = (status('![%s]' % INSTALLED, 'Not installed · v%s' % VERSION, p.GREY) +
          status('%s + %s' % (INSTALLED, UPDATE), 'Update available · v%s' % VERSION, p.ACCENT) +
          status('%s + ![%s] + %s' % (INSTALLED, UPDATE, ENABLED), 'Enabled · v%s' % VERSION, p.GREY) +
          status('%s + ![%s] + ![%s]' % (INSTALLED, UPDATE, ENABLED), 'Disabled · v%s' % VERSION, p.GREY))
    tile = 256
    hero = ('<control type="group"><width>%d</width><height>640</height>' % p.WIDTH +
            p.surface((p.WIDTH - tile) // 2, 0, tile, tile, 'tile100.png', 'FF0F0F10', 56) +
            p.image((p.WIDTH - tile) // 2 + 20, 20, tile - 40, tile - 40, '$INFO[ListItem.Icon]', p.WHITE, '', '>keep') +
            p.label(p.SIDE, 290, w, 150, '[B]$INFO[ListItem.Label][/B]', 'p_h2', p.WHITE, 'center',
                    '<wrapmultiline>true</wrapmultiline><scroll>false</scroll>') +
            p.label(p.SIDE, 450, w, 56, '$INFO[ListItem.AddonCreator]$INFO[ListItem.AddonType, · ,]', 'p_foot', p.GREY, 'center',
                    '<scroll>false</scroll>') +
            '<control type="group"><top>520</top>' + st + '</control></control>')
    # Primary capsule (Update, else Open, else Install) with Settings beside it.
    cap_h = 128
    both = '%s + Control.IsEnabled(9)' % INSTALLED
    primary = lambda id, text, click, cond, x, wd, style: p.pill_button(
        id, x, 0, wd, cap_h, text, [('', click)], style, extra='<visible>%s</visible>' % cond)
    open_cond = '![%s] + Control.IsEnabled(12)' % UPDATE
    install_cond = '![%s] + Control.IsEnabled(6) + ![%s]' % (UPDATE, INSTALLED)
    settings_here = 'Control.IsEnabled(9) + [%s | %s]' % (UPDATE, 'Control.IsEnabled(12)')
    half = (w - 20) // 2
    actions = ('<control type="group"><width>%d</width><height>%d</height>' % (p.WIDTH, cap_h + 40) +
               '<control type="group"><left>%d</left><top>20</top>' % p.SIDE +
               # Update: wide when alone, half with Settings.
               primary(9108, 'Update', 'SendClick(8)', '%s + !Control.IsEnabled(9)' % UPDATE, 0, w, 'primary') +
               primary(9118, 'Update', 'SendClick(8)', '%s + Control.IsEnabled(9)' % UPDATE, 0, half, 'primary') +
               primary(9112, '$INFO[Control.GetLabel(12)]', 'SendClick(12)', '%s + !Control.IsEnabled(9)' % open_cond, 0, w, 'primary') +
               primary(9122, '$INFO[Control.GetLabel(12)]', 'SendClick(12)', '%s + Control.IsEnabled(9)' % open_cond, 0, half, 'primary') +
               primary(9106, 'Install', 'SendClick(6)', install_cond, 0, w, 'primary') +
               primary(9109, 'Settings', 'SendClick(9)', settings_here, half + 20, half, 'glass') +
               primary(9119, 'Settings', 'SendClick(9)', 'Control.IsEnabled(9) + ![%s] + ![Control.IsEnabled(12)] + ![%s]' % (UPDATE, install_cond), 0, w, 'primary') +
               '</control></control>')
    rows = ''
    rows += card_row(p, 9107, 'Enabled', 'switch', 'Control.IsEnabled(7)', 'SendClick(7)', switch=ENABLED)
    rows += ('<control type="group"><width>%d</width><height>%d</height><visible>Control.IsEnabled(13)</visible>' % (p.WIDTH, ROW + GAP) +
             '<control type="group"><left>%d</left>' % p.SIDE + p.surface(0, 0, w, ROW, 'round_s.png', p.SURFACE, RADIUS_CARD) +
             '<control type="radiobutton" id="13"><left>0</left><top>0</top><width>%d</width><height>%d</height>'
             '<label>Update automatically</label><font>p_body</font><textcolor>%s</textcolor><focusedcolor>%s</focusedcolor>'
             '<align>left</align><aligny>center</aligny><textoffsetx>%d</textoffsetx><radioposx>%d</radioposx><radioposy>%d</radioposy>'
             '<radiowidth>130</radiowidth><radioheight>58</radioheight>'
             '<texturefocus border="26" colordiffuse="1FFFFFFF">%sround_s.png</texturefocus><texturenofocus />'
             '<textureradioonfocus>%stoggle_on.png</textureradioonfocus><textureradioonnofocus>%stoggle_on.png</textureradioonnofocus>'
             '<textureradioofffocus>%stoggle_off.png</textureradioofffocus><textureradiooffnofocus>%stoggle_off.png</textureradiooffnofocus>'
             '</control></control></control>') % (w, ROW, p.WHITE, p.WHITE, PAD, w - PAD - 130, (ROW - 58) // 2, M, M, M, M, M)
    rows += card_row(p, 9114, 'Versions', 'chevron', 'Control.IsEnabled(14)', 'SendClick(14)', glyph='code-branch.png', tint=p.ACCENT,
                     value='$INFO[ListItem.AddonVersion]')
    rows += card_row(p, 9110, 'Dependencies', 'chevron', 'Control.IsEnabled(10)', 'SendClick(10)', glyph='dependencies.png', tint='FFBF5AF2')
    rows += card_row(p, 9132, '$INFO[Control.GetLabel(12)]', 'chevron', '%s + Control.IsEnabled(12)' % UPDATE, 'SendClick(12)',
                     glyph='play3.png', tint='FF30D158')
    about = [('Author', '$INFO[ListItem.AddonCreator]'), ('Category', '$INFO[ListItem.AddonType]'), ('Version', VERSION)]
    about_date = about + [('Updated', '$VAR[Label_AddonInfo_LastUpdated]')]
    about_xml = (spacer(30) + '<control type="group"><width>%d</width><height>80</height>' % p.WIDTH +
                 p.label(p.SIDE + 20, 0, w - 40, 70, 'About', 'p_h3', p.GREY) + '</control>' +
                 info_card(p, about_date, HAS_DATE) + info_card(p, about, '![%s]' % HAS_DATE.replace(' | ', '] + ![')))
    uninstall = card_row(p, 9161, 'Uninstall', 'plain', '%s + Control.IsEnabled(6)' % UNINSTALL, 'SendClick(6)', red=True)
    controls = ''.join(carrier(i) for i in (6, 7, 8, 9, 10, 12, 14))
    lst = ('<control type="grouplist" id="9400"><left>0</left><top>0</top><width>%d</width><bottom>0</bottom><orientation>vertical</orientation>'
           '<itemgap>0</itemgap><usecontrolcoords>false</usecontrolcoords>' % p.WIDTH +
           spacer(200) + hero + actions + spacer(30) + rows + about_xml +
           spacer(30) + text_block(p, 'Description', '$INFO[ListItem.AddonDescription]', '!String.IsEmpty(ListItem.AddonDescription)') +
           text_block(p, 'What\'s new', '$INFO[ListItem.AddonNews]', '!String.IsEmpty(ListItem.AddonNews)') +
           spacer(20) + uninstall + spacer(260) + '</control>')
    return controls, lst


def window(p, original):
    """portrait/DialogAddonInfo.xml. Fuse's landscape include is dropped; the dialog keeps its type and Kodi's ids."""
    controls, lst = page_body(p)
    header = p.settings_page.header(p, [('', 'Action(Back)')], [('Add-on', '')], 36, '<ondown>9400</ondown>')
    body = '<controls>' + p.backdrop() + controls + lst + header + '</controls>'
    return p.window('<window type="dialog" />', body, '9001',
                    '<animation effect="fade" start="0" end="100" time="160">WindowOpen</animation>')
