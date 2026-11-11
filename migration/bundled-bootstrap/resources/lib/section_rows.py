"""Section pages (Settings › Interface, Player, Media, Services, System, PVR & Live TV, Games): each section's
categories as rows with an icon tile, a name and what is set now. Pure logic; section_page.py reads Kodi (JSON-RPC)
and draws it into portrait/IOSSection.xml (settings_page.section_page).

Owner-approved mockup: docs/design/settings-pages-mockups.html, board 1."""

BLUE, PURPLE, GREEN, ORANGE, RED, TEAL, PINK, SILVER = 'FF0A84FF', 'FFBF5AF2', 'FF30D158', 'FFFF9F0A', 'FFFF453A', 'FF64D2FF', 'FFFF375F', 'FF8E8E93'

# section id -> (page title, Kodi window, footer)
SECTIONS = {
    'interface': ('Interface', 'interfacesettings', "Each row shows its current setting, so most of the time you don't need to open it."),
    'player': ('Player', 'playersettings', 'How videos, music and pictures play, and which languages and subtitles they use.'),
    'media': ('Media', 'mediasettings', 'Libraries, sources and how Kodi lists your files.'),
    'services': ('Services', 'servicesettings', 'How this iPhone appears to other devices, and the remotes that can control it.'),
    'system': ('System', 'systemsettings', 'Display, sound, input and the rest of how Kodi runs on this iPhone.'),
    'pvr': ('PVR & Live TV', 'pvrsettings', 'Live TV and recording. Needs a PVR add-on.'),
    'games': ('Games', 'gamesettings', 'Gameplay options for the games Kodi can run.'),
}

# category id -> (icon file in the skin's icon folder, tile colour)
ICONS = {
    'skin': ('brush.png', PURPLE), 'regional': ('globe.png', BLUE), 'screensaver': ('display.png', TEAL), 'masterlock': ('shield.png', ORANGE),
    'startupwindow': ('power-off.png', GREEN),
    'videoplayer': ('film.png', BLUE), 'musicplayer': ('music.png', PINK), 'discs': ('compact-disc.png', SILVER),
    'pictures': ('image.png', ORANGE), 'language': ('language.png', TEAL), 'subtitles': ('closed-captioning.png', GREEN),
    'library': ('folder.png', BLUE), 'filelists': ('list.png', SILVER), 'video': ('clapperboard.png', PURPLE), 'music': ('music.png', PINK),
    'general': ('gear.png', SILVER), 'control': ('tower-broadcast.png', BLUE), 'weather': ('cloud-sun.png', TEAL),
    'display': ('desktop.png', BLUE), 'audio': ('volume-high.png', ORANGE), 'input': ('keyboard.png', SILVER), 'network': ('wifi.png', TEAL),
    'powermanagement': ('bolt.png', GREEN), 'addons': ('puzzle-piece.png', PURPLE), 'logging': ('file-lines.png', SILVER),
    'pvrmanager': ('gear.png', SILVER), 'pvrmenu': ('tv.png', BLUE), 'epg': ('book-open.png', PURPLE), 'pvrplayback': ('circle-play.png', GREEN),
    'pvrrecord': ('video.png', RED), 'pvrreminders': ('clock.png', ORANGE),
    'gamesgeneral': ('gamepad.png', PINK), 'gamesachievements': ('trophy.png', ORANGE),
}
DEFAULT_ICON = ('gear.png', SILVER)
MAX_ROWS = 9
SUMMARY_PARTS = 2   # settings named in a row's second line

# Words Kodi's settings show that read better short.
PLAIN = {'default': 'Default', 'true': 'On', 'false': 'Off'}


def icon_for(category_id):
    return ICONS.get(category_id, DEFAULT_ICON)


def value_text(setting):
    """A setting (Settings.GetSettings entry) as the words its row would show, or ''. Only values that mean something
    on their own count: a named option ("Skin default"), an add-on or a text value. On/Off, bare numbers and actions
    say nothing without the setting's name, so they are left out."""
    kind = setting.get('type')
    value = setting.get('value')
    for option in setting.get('options') or []:
        if option.get('value') == value:
            return str(option.get('label') or '')
    if kind in ('addon', 'string') and isinstance(value, str):
        text = PLAIN.get(value, value)
        looks_like_id = ' ' not in text and '.' in text and text == text.lower()   # skin.arctic.fuse.3, resource.language.en_gb
        return text if text and len(text) <= 28 and '/' not in text and not looks_like_id and text.lower() not in ('on', 'off', 'none') else ''
    return ''


def summary(settings):
    """'Arctic Fuse 3 · Skin default' from the first few settings of a category that have a meaningful value, or
    '12 settings' when none does."""
    parts = []
    for s in settings or []:
        text = value_text(s)
        if text and text not in parts:
            parts.append(text)
        if len(parts) >= SUMMARY_PARTS:
            break
    if parts:
        return ' · '.join(parts)
    n = sum(1 for s in settings or [] if s.get('type') != 'action' or s.get('label'))
    return '%d setting%s' % (n, '' if n == 1 else 's') if n else ''


def rows(categories, settings_of):
    """[{'id', 'name', 'sub', 'icon', 'tint'}] for a section. categories: Settings.GetCategories entries;
    settings_of(category_id) -> that category's Settings.GetSettings entries."""
    out = []
    for c in (categories or [])[:MAX_ROWS]:
        icon, tint = icon_for(c.get('id'))
        try:
            sub = summary(settings_of(c['id']))
        except Exception:
            sub = ''
        out.append({'id': c['id'], 'name': str(c.get('label') or c['id']), 'sub': sub, 'icon': icon, 'tint': tint})
    return out


def properties(section, rows_):
    """Window properties for IOSSection.xml."""
    title, _, foot = SECTIONS[section]
    props = {'title': title, 'foot': foot, 'rows': str(max(1, min(len(rows_), MAX_ROWS)))}
    for n in range(1, MAX_ROWS + 1):
        r = rows_[n - 1] if n <= len(rows_) else {}
        for key in ('name', 'sub', 'icon', 'tint'):
            props['sec.%d.%s' % (n, key)] = r.get(key, '')
    return props
