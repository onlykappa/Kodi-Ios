"""Skin Settings as portrait pages (owner-approved mockup docs/design/settings-pages-mockups.html, boards 5-6).

Arctic Fuse's Skin Settings is a landscape window of about 110 entries, each an include in its
Includes_SkinSettings.xml: a Settings_Label (group title) or a Settings_Button (a switch when its control is
radiobutton, otherwise a button with an optional value). This reads those includes, so the portrait pages always show
exactly the settings Fuse has, with the same actions, values and Standard / Advanced / Expert levels. Pure logic;
skin_settings_page.py asks Kodi for the live values."""
import re
import xml.etree.ElementTree as ET

# (index, page name, the Fuse include that holds its entries, icon file, tile colour). Fuse's own order and names
# (Settings_Category_List): Customise, Appearance, Interface, Details, Layout, Behaviour, Other, Dependencies.
BLUE, PURPLE, GREEN, ORANGE, RED, TEAL, SILVER = 'FF0A84FF', 'FFBF5AF2', 'FF30D158', 'FFFF9F0A', 'FFFF453A', 'FF64D2FF', 'FF8E8E93'
SECTIONS = (
    (0, 'Customisation', 'SkinSettings_Items_Menus', 'layer-group.png', BLUE),
    (1, 'Appearance', 'SkinSettings_Items_Appearance', 'palette.png', PURPLE),
    (2, 'Interface', 'SkinSettings_Items_Interface', 'sliders.png', TEAL),
    (3, 'Details', 'SkinSettings_Items_Details', 'circle-info.png', GREEN),
    (4, 'Layout', 'SkinSettings_Items_Viewtypes', 'list.png', ORANGE),
    (5, 'Behaviour', 'SkinSettings_Items_Behaviour', 'circle-play.png', RED),
    (6, 'Other', 'SkinSettings_Items_Other', 'puzzle-piece.png', SILVER),
    (7, 'Dependencies', 'SkinSettings_Items_Dependecies', 'puzzle-piece.png', SILVER),
)
LEVEL_NAMES = {1: 'Standard', 2: 'Advanced', 3: 'Expert'}


def _text(node, name):
    child = node.find(name)
    return (child.text or '').strip() if child is not None else ''


def parse(xml_text):
    """{include name: [entry]} for every SkinSettings_Items_* include. entry: kind 'title' | 'switch' | 'button',
    label, value (an info label for a button's current value), selected (condition, switches), visible (condition),
    level (the Standard/Advanced/Expert level it needs), clicks [(condition, builtin)]."""
    root = ET.fromstring(xml_text)
    out = {}
    for group in root.iter('include'):
        name = group.get('name') or ''
        if not name.startswith('SkinSettings_Items_'):
            continue
        entries = []
        for inc in group.iter('include'):
            content = inc.get('content')
            if content not in ('Settings_Label', 'Settings_Button'):
                continue
            params = {p.get('name'): (p.text or '').strip() for p in inc.findall('param')}
            label = _text(inc, 'label')
            if not label:
                continue
            level = params.get('slevel', '0')
            entry = {'kind': 'title', 'label': label, 'value': '', 'selected': '', 'visible': _text(inc, 'visible'),
                     'level': int(level) if level.isdigit() else 0, 'clicks': []}
            if content == 'Settings_Button':
                entry['kind'] = 'switch' if params.get('control') == 'radiobutton' else 'button'
                entry['value'] = _text(inc, 'label2')
                entry['selected'] = _text(inc, 'selected')
                entry['clicks'] = [(c.get('condition') or '', (c.text or '').strip()) for c in inc.findall('onclick') if (c.text or '').strip()]
            entries.append(entry)
        out[name] = entries
    return out


def visible_entries(entries, level, test):
    """Entries shown at settings `level` (1 Standard, 2 Advanced, 3 Expert), where test(condition) -> bool answers
    Kodi's visibility conditions. A group title with nothing under it is dropped."""
    shown = []
    for e in entries:
        if e['level'] and level < e['level']:
            continue
        if e['visible'] and not test(e['visible']):
            continue
        shown.append(e)
    # a title followed by another title (or by nothing) has no settings under it
    out = []
    for i, e in enumerate(shown):
        if e['kind'] == 'title' and (i + 1 >= len(shown) or shown[i + 1]['kind'] == 'title'):
            continue
        out.append(e)
    return out


def click_actions(entry, test):
    """The builtins a tap runs: every onclick whose condition holds, in order."""
    return [action for cond, action in entry['clicks'] if not cond or test(cond)]


def level_from(text):
    try:
        n = int(str(text).strip())
    except ValueError:
        return 1
    return n if n in LEVEL_NAMES else 1
