"""The Crew's "new version" window as a portrait sheet (owner-approved docs/design/addon-install-mockups.html frame 8).

The Crew draws its version announcement in its own landscape window (script.thecrew.artwork, skins/<skin>/1080i/
VersionAnnouncement.xml: 1920 x 1080), which sat squeezed in the middle of the phone. This replaces that file, in every skin
of the artwork add-on, with a dark bottom sheet: the title, the version, up to three highlight lines, the beta note when
it applies, and Close (103, the white capsule), View changelog (101) and Beta info (102). The Crew sets the window's
properties (version, announcement_type, highlight1-3, show_alpha_warning) and handles the three buttons; none of that changes.

As with loop_notice.py: pictures are laid out in portrait units inside a zoomed group, text and buttons in the window's
own units (Kodi draws a font at one size; a non-uniform zoom squashes it). Only the exact pinned files are replaced (the
artwork add-on's version and each original file's SHA-256 are checked); the service re-checks every 20 seconds. The QR code
some Crew windows show is not part of this one and is not drawn."""
import hashlib
import os

ADDON = 'script.thecrew.artwork'
VERSION = '3.2.0'
SKINS = ('stylish', 'thecrew', 'modern')
RELATIVE = os.path.join('resources', 'skins', '%s', '1080i', 'VersionAnnouncement.xml')
ORIGINAL_SHA256 = {
    'stylish': 'bca0da0d375ec34628399fdaf2909f318e7bc493cd5a5628952f1d7d3c966be3',
    'thecrew': '73a86d7808566c38197dbeb98d3e93edd34fa8d0a945033d6c49b21a32aaaf65',
    'modern': 'bca0da0d375ec34628399fdaf2909f318e7bc493cd5a5628952f1d7d3c966be3',
}
MARK = 'Kodi-iOS notice sheet r1 (crew)'
MEDIA = 'special://skin/extras/portrait/'
W, H = 1080, 2090              # the portrait skin's canvas
CW, CH = 1920, 1080            # this window's own canvas
SX, SY = W / float(CW), H / float(CH)
SHEET_X, SHEET_W, SHEET_Y, SHEET_H = 27, 1026, 800, 1250
PAD = 60


def xml():
    """The replacement VersionAnnouncement.xml."""
    image = lambda x, y, w, h, texture, color, border='', extra='': (
        '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
        '<texture%s colordiffuse="%s">%s%s</texture>%s</control>') % (
        x, y, w, h, ' border="%s"' % border if border else '', color, MEDIA, texture, extra)
    win = lambda v, scale: '%.1f' % (v / scale)
    inner_w = SHEET_W - 2 * PAD
    close_y = SHEET_Y + 900
    second_y = close_y + 128 + 24
    half = (inner_w - 24) // 2
    card_y = SHEET_Y + 250
    alert_y = card_y + 440 + 30
    pictures = (
        image(0, 0, W, H, 'white.png', '99000000') +
        image(SHEET_X, SHEET_Y, SHEET_W, SHEET_H, 'alert.png', 'FFFFFFFF', '40') +
        image((W - 108) // 2, SHEET_Y + 22, 108, 10, 'pill_96.png', '4DEBEBF5', '5') +
        image(SHEET_X + PAD, card_y, inner_w, 440, 'round_s.png', 'FF1C1C1E', '26') +
        image(SHEET_X + PAD, close_y, inner_w, 128, 'pill_128.png', 'FFFFFFFF', '64') +
        image(SHEET_X + PAD, close_y, inner_w, 128, 'pill_128.png', 'FFD1D1D6', '64', '<visible>Control.HasFocus(103)</visible>') +
        image(SHEET_X + PAD, second_y, half, 128, 'pill_128.png', 'FF3A3A3C', '64') +
        image(SHEET_X + PAD + half + 24, second_y, half, 128, 'pill_128.png', 'FF3A3A3C', '64'))
    label = lambda x, y, w, h, text, font, color, align='left', extra='': (
        '<control type="label"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font><textcolor>%s</textcolor>'
        '<align>%s</align><aligny>center</aligny><label>%s</label><scroll>false</scroll>%s</control>') % (
        win(x, SX), win(y, SY), win(w, SX), win(h, SY), font, color, align, text, extra)
    textbox = lambda x, y, w, h, text, font, color, extra='': (
        '<control type="textbox"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>%s</font><textcolor>%s</textcolor>'
        '<align>left</align><autoscroll>false</autoscroll><label>%s</label>%s</control>') % (
        win(x, SX), win(y, SY), win(w, SX), win(h, SY), font, color, text, extra)
    button = lambda id, x, y, w, text, color: (
        '<control type="button" id="%d"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><label>%s</label><font>p_btn</font>'
        '<textcolor>%s</textcolor><focusedcolor>%s</focusedcolor><align>center</align><aligny>center</aligny><texturefocus /><texturenofocus />'
        '<onup>103</onup><ondown>103</ondown></control>') % (id, win(x, SX), win(y, SY), win(w, SX), win(128, SY), text, color, color)
    highlights = ''.join(
        textbox(SHEET_X + PAD + 40, card_y + 30 + n * 135, inner_w - 80, 120, '$INFO[Window().Property(highlight%d)]' % (n + 1), 'p_sub', 'FFF2F2F7',
                '<visible>!String.IsEmpty(Window().Property(highlight%d))</visible>' % (n + 1)) for n in range(3))
    alert = textbox(SHEET_X + PAD, alert_y, inner_w, 190,
                    'INFO: This is a beta version for testing. Most features are stable, but some bugs may exist. Please report any issues on GitHub.',
                    'p_foot', 'FFFFB340', '<visible>String.IsEqual(Window().Property(show_alpha_warning),true)</visible>')
    controls = (
        label(SHEET_X + PAD, SHEET_Y + 70, inner_w, 90, 'The Crew', 'p_h2', 'FFFFFFFF') +
        label(SHEET_X + PAD, SHEET_Y + 150, inner_w, 70, '$INFO[Window().Property(announcement_type)] · v$INFO[Window().Property(version)]', 'p_foot', 'FFAEAEB2') +
        highlights + alert +
        # Close (103) is the white capsule; its label sits over it.
        '<control type="button" id="103"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><label>Close</label><font>p_btn</font>'
        '<textcolor>FF000000</textcolor><focusedcolor>FF000000</focusedcolor><align>center</align><aligny>center</aligny><texturefocus /><texturenofocus />'
        '<onup>101</onup><ondown>101</ondown></control>' % (win(SHEET_X + PAD, SX), win(close_y, SY), win(inner_w, SX), win(128, SY)) +
        button(101, SHEET_X + PAD, second_y, half, 'View changelog', 'FFFFFFFF').replace('<onup>103</onup><ondown>103</ondown>', '<onup>103</onup><ondown>103</ondown><onright>102</onright>') +
        button(102, SHEET_X + PAD + half + 24, second_y, half, 'Beta info', 'FFFFFFFF').replace('<onup>103</onup><ondown>103</ondown>', '<onup>103</onup><ondown>103</ondown><onleft>101</onleft>'))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- %s -->\n<window>\n\t<defaultcontrol always="true">103</defaultcontrol>\n'
            '\t<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>\n'
            '\t<animation effect="fade" start="100" end="0" time="120">WindowClose</animation>\n\t<controls>\n'
            '\t\t<control type="group"><left>0</left><top>0</top><width>%d</width><height>%d</height>\n'
            '\t\t\t<animation effect="zoom" start="0,0,%d,%d" end="0,0,%d,%d" time="0" condition="true">Conditional</animation>\n'
            '\t\t\t%s\n\t\t</control>\n\t\t%s\n\t</controls>\n</window>\n') % (MARK, W, H, W, H, CW, CH, pictures, controls)


def addon_version(addon_xml):
    import re
    found = re.search(r'<addon[^>]*\sversion="([^"]+)"', addon_xml or '')
    return found.group(1) if found else ''


def hook(addon_dir):
    """Replace the window in each skin of the pinned artwork add-on; returns the skins changed."""
    try:
        with open(os.path.join(addon_dir, 'addon.xml'), encoding='utf-8', errors='replace') as f:
            if addon_version(f.read()) != VERSION:
                return []
    except OSError:
        return []
    changed = []
    for skin in SKINS:
        path = os.path.join(addon_dir, RELATIVE % skin)
        try:
            with open(path, 'rb') as f:
                current = f.read()
        except OSError:
            continue
        if MARK.encode() in current or hashlib.sha256(current).hexdigest() != ORIGINAL_SHA256[skin]:
            continue
        temporary = path + '.tmp'
        with open(temporary, 'wb') as f:
            f.write(xml().encode('utf-8'))
        os.replace(temporary, path)
        changed.append(skin)
    return changed


def watch(addon_dir, wait, log, every=20):
    """Keep the window replaced while Kodi runs: `addon_dir()` gives the artwork add-on's folder ('' when it is not installed)."""
    while True:
        try:
            folder = addon_dir()
            changed = hook(folder) if folder else []
            if changed:
                log('crew: version window restyled (%s)' % ', '.join(changed))
        except Exception as error:
            log('crew: version window check failed (%s)' % type(error).__name__)
        if wait(every):
            return
