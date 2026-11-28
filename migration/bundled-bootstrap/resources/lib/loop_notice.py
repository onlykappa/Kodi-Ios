"""The Loop's own notice window as a portrait sheet (owner, 2026-11-27: "you can touch it", and it needed to look cleaner).

The Loop opens its messages (first-run notice, news) in its own window, resources/skins/Default/720p/notify.xml: a 1280x720
layout with a translucent white card, white text and a picture of the word "close". Stretched over the portrait screen
that was an almost blank white sheet with a tiny "OK" (owner's build 766 screenshot, ISSUE-504).

This replaces that one file with a bottom sheet in the project's style: a dim backdrop, a dark sheet, the text, a thin scroll
bar for a long text and a white OK capsule. The control ids the add-on drives stay: 300 (the text, paged by 301), 301 (scroll
bar) and 302 (OK, the add-on closes on it). The layout is written in the portrait skin's 1080 x 2090 units and zoomed onto the
window's own 1280 x 720 canvas, so it is not stretched (the technique the portrait wrappers use for landscape windows).

Only the exact file of the pinned version is replaced: the add-on's version and the original file's SHA-256 are both checked,
so another version (or a file someone else changed) is left alone. The service checks every 20 seconds, which also catches an
install or update that happens while Kodi runs; Kodi reads the window file when the window opens.
"""
import hashlib
import os

ADDON = 'plugin.video.the-loop'
VERSION = '8.4'
RELATIVE = os.path.join('resources', 'skins', 'Default', '720p', 'notify.xml')
ORIGINAL_SHA256 = 'c8cdfc8910216129eb244c9f64f537412e52aabf33d123593e7a97f15bce9467'
MARK = 'Kodi-iOS notice sheet r1'
MEDIA = 'special://skin/extras/portrait/'
W, H = 1080, 2090          # the portrait skin's canvas
SHEET_X, SHEET_W = 27, 1026
SHEET_Y, SHEET_H = 900, 1150
PAD = 60
OK_H = 128


SX, SY = 1080 / 1280.0, 2090 / 720.0   # screen units per window unit of the add-on's 1280 x 720 layout (it is stretched)


def xml():
    """The replacement notify.xml.

    Pictures are laid out in portrait units inside one group zoomed onto the window's canvas (so a rounded corner stays round);
    text and the OK button are laid out in the window's own units, because Kodi draws a font at one uniform size and a zoom
    that is not uniform would squash it (found in the desktop rig).
    """
    text_x, text_w = SHEET_X + PAD, SHEET_W - 2 * PAD - 30
    ok_y = SHEET_Y + SHEET_H - 48 - OK_H
    text_y, text_h = SHEET_Y + 60, ok_y - 40 - (SHEET_Y + 60)
    image = lambda x, y, w, h, texture, color, border='': (
        '<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
        '<texture%s colordiffuse="%s">%s%s</texture></control>') % (
        x, y, w, h, ' border="%s"' % border if border else '', color, MEDIA, texture)
    window = lambda v, scale: '%.1f' % (v / scale)
    pictures = (
        image(0, 0, W, H, 'white.png', '99000000') +
        image(SHEET_X, SHEET_Y, SHEET_W, SHEET_H, 'alert.png', 'FFFFFFFF', '40') +
        image((W - 108) // 2, SHEET_Y + 22, 108, 10, 'pill_96.png', '4DEBEBF5', '5') +   # grabber
        image(text_x, ok_y, SHEET_W - 2 * PAD, OK_H, 'pill_128.png', 'FFFFFFFF', '64') +   # the OK capsule, under its label
        image(text_x, ok_y, SHEET_W - 2 * PAD, OK_H, 'pill_128.png', 'FFD1D1D6', '64').replace(
            '</control>', '<visible>Control.HasFocus(302)</visible></control>'))   # a little darker while pressed
    scroll = ('<control type="scrollbar" id="301"><left>%s</left><top>%s</top><width>%s</width><height>%s</height>'
              '<texturesliderbackground /><texturesliderbar colordiffuse="66FFFFFF">%sdot.png</texturesliderbar>'
              '<texturesliderbarfocus colordiffuse="99FFFFFF">%sdot.png</texturesliderbarfocus>'
              '<textureslidernib /><textureslidernibfocus /><orientation>vertical</orientation><showonepage>false</showonepage>'
              '<onleft>302</onleft><onright>302</onright></control>') % (
        window(SHEET_X + SHEET_W - 40, SX), window(text_y, SY), window(10, SX), window(text_h, SY), MEDIA, MEDIA)
    text = ('<control type="textbox" id="300"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><font>p_sub</font>'
            '<align>left</align><aligny>top</aligny><textcolor>FFF2F2F7</textcolor><pagecontrol>301</pagecontrol></control>') % (
        window(text_x, SX), window(text_y, SY), window(text_w, SX), window(text_h, SY))
    ok = ('<control type="button" id="302"><left>%s</left><top>%s</top><width>%s</width><height>%s</height><label>OK</label>'
          '<font>p_btn</font><textcolor>FF000000</textcolor><focusedcolor>FF000000</focusedcolor><align>center</align>'
          '<aligny>center</aligny><texturefocus /><texturenofocus />'
          '<onleft>301</onleft><onright>301</onright><onup>300</onup></control>') % (
        window(text_x, SX), window(ok_y, SY), window(SHEET_W - 2 * PAD, SX), window(OK_H, SY))
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!-- %s -->\n<window>\n\t<defaultcontrol always="true">302</defaultcontrol>\n'
            '\t<animation effect="fade" start="0" end="100" time="180">WindowOpen</animation>\n'
            '\t<animation effect="fade" start="100" end="0" time="120">WindowClose</animation>\n\t<controls>\n'
            '\t\t<control type="group"><left>0</left><top>0</top><width>%d</width><height>%d</height>\n'
            '\t\t\t<animation effect="zoom" start="0,0,%d,%d" end="0,0,1280,720" time="0" condition="true">Conditional</animation>\n'
            '\t\t\t%s\n\t\t</control>\n\t\t%s\n\t\t%s\n\t\t%s\n\t</controls>\n</window>\n') % (
        MARK, W, H, W, H, pictures, text, scroll, ok)


def addon_version(addon_xml):
    import re
    found = re.search(r'<addon[^>]*\sversion="([^"]+)"', addon_xml or '')
    return found.group(1) if found else ''


def hook(addon_dir):
    """Replace the notify window of the pinned Loop at `addon_dir`; True when the file was changed."""
    path = os.path.join(addon_dir, RELATIVE)
    try:
        with open(os.path.join(addon_dir, 'addon.xml'), encoding='utf-8', errors='replace') as f:
            if addon_version(f.read()) != VERSION:
                return False
        with open(path, 'rb') as f:
            current = f.read()
    except OSError:
        return False
    if MARK.encode() in current or hashlib.sha256(current).hexdigest() != ORIGINAL_SHA256:
        return False
    new = xml().encode('utf-8')
    temporary = path + '.tmp'
    with open(temporary, 'wb') as f:
        f.write(new)
    os.replace(temporary, path)
    return True


def watch(addon_dir, wait, log, every=20):
    """Keep the notice replaced while Kodi runs: `addon_dir()` gives the add-on's folder (or '' when it is not installed)."""
    while True:
        try:
            folder = addon_dir()
            if folder and hook(folder):
                log('loop: notice window restyled')
        except Exception as error:
            log('loop: notice check failed (%s)' % type(error).__name__)
        if wait(every):
            return
