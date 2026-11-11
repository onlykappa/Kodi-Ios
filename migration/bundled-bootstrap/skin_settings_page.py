"""RunScript(service.kodi.ios.bootstrap,skin_settings_page[,<section>]): Skin Settings (Arctic Fuse's settings) as
portrait pages. With no section: the sections as rows (the section page, IOSSection.xml); with one: that section's
entries as a list (IOSSkinList.xml). The entries, their values and levels come from Fuse's own
Includes_SkinSettings.xml (skin_settings.py), so they are always what Fuse offers. Owner-approved mockup boards 5-6."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import section_rows as sr
import skin_settings as ss

BACK = (9, 10, 92, 110)
ROW_BASE = 9600
INCLUDES = 'special://skin/1080i/Includes_SkinSettings.xml'


def entries_by_include(xbmcvfs):
    handle = xbmcvfs.File(INCLUDES)
    try:
        return ss.parse(handle.read())
    finally:
        handle.close()


def run(section=None):
    import xbmc
    import xbmcgui
    import xbmcvfs

    test = xbmc.getCondVisibility
    text = lambda s: (xbmc.getInfoLabel(s) if '$' in s else s) if s else ''
    level = ss.level_from(xbmc.getInfoLabel('Skin.String(Skin.SettingsLevel)'))
    groups = entries_by_include(xbmcvfs)

    if section is None:
        def build():
            lvl = ss.level_from(xbmc.getInfoLabel('Skin.String(Skin.SettingsLevel)'))
            rows = []
            for index, name, include, icon, tint in ss.SECTIONS:
                shown = [e for e in ss.visible_entries(groups.get(include, []), lvl, test) if e['kind'] != 'title']
                if shown:
                    rows.append({'id': str(index), 'name': name, 'sub': '%d settings' % len(shown), 'icon': icon, 'tint': tint})
            # Fuse shows more settings at Advanced and Expert; this row cycles Standard > Advanced > Expert.
            rows.append({'id': 'level', 'name': 'Settings Level', 'sub': '%s · tap to show %s' % (ss.LEVEL_NAMES[lvl], 'more' if lvl < 3 else 'fewer'),
                         'icon': 'sliders.png', 'tint': sr.SILVER})
            props = {'title': 'Skin Settings', 'foot': 'Arctic Fuse 3. Settings Level decides how many settings each section shows.',
                     'rows': str(max(1, min(len(rows), sr.MAX_ROWS)))}
            for n in range(1, sr.MAX_ROWS + 1):
                r = rows[n - 1] if n <= len(rows) else {}
                for key in ('name', 'sub', 'icon', 'tint'):
                    props['sec.%d.%s' % (n, key)] = r.get(key, '')
            return rows, props

        class Landing(xbmcgui.WindowXMLDialog):
            def onInit(self):
                self.refresh()

            def refresh(self):
                self.rows, props = build()
                for key, value in props.items():
                    self.setProperty(key, value)

            def onAction(self, action):
                if action.getId() in BACK:
                    self.close()

            def onClick(self, control):
                if control == 9001:
                    self.close()
                elif ROW_BASE < control <= ROW_BASE + len(self.rows):
                    chosen = self.rows[control - ROW_BASE - 1]
                    if chosen['id'] == 'level':
                        lvl = ss.level_from(xbmc.getInfoLabel('Skin.String(Skin.SettingsLevel)'))
                        xbmc.executebuiltin('Skin.SetString(Skin.SettingsLevel,%d)' % (lvl % 3 + 1))
                        xbmc.sleep(200)
                        self.refresh()
                    else:
                        xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,skin_settings_page,%s)' % chosen['id'])

        page = Landing('IOSSection.xml', HERE, 'Default', '1080i')
        page.doModal()
        del page
        return

    chosen = next((s for s in ss.SECTIONS if str(s[0]) == str(section)), None)
    if chosen is None:
        return
    _, name, include, _, _ = chosen

    class Listing(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.setProperty('title', name)
            self.fill()

        def current(self):
            return ss.visible_entries(groups.get(include, []), ss.level_from(xbmc.getInfoLabel('Skin.String(Skin.SettingsLevel)')), test)

        def fill(self, keep=None):
            self.entries = self.current()
            items = []
            for e in self.entries:
                item = xbmcgui.ListItem(text(e['label']))
                item.setProperty('kind', e['kind'])
                item.setProperty('label', text(e['label']))
                item.setProperty('value', text(e['value']) if e['kind'] == 'button' else '')
                item.setProperty('on', 'true' if e['kind'] == 'switch' and e['selected'] and test(e['selected']) else '')
                items.append(item)
            lst = self.getControl(9310)
            lst.reset()
            lst.addItems(items)
            if keep is not None and keep < len(items):
                lst.selectItem(keep)
            else:
                first = next((i for i, e in enumerate(self.entries) if e['kind'] != 'title'), 0)
                lst.selectItem(first)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
            elif control == 9310:
                n = self.getControl(9310).getSelectedPosition()
                if 0 <= n < len(self.entries) and self.entries[n]['kind'] != 'title':
                    for action in ss.click_actions(self.entries[n], test):
                        xbmc.executebuiltin(action)
                    xbmc.sleep(250)
                    self.fill(keep=n)

    page = Listing('IOSSkinList.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else None)
