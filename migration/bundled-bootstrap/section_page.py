"""RunScript(service.kodi.ios.bootstrap,section_page,<section>): Settings › Interface / Player / Media / Services /
System / PVR / Games as a page of category rows (portrait/IOSSection.xml; owner-approved mockup board 1). Tapping a row
opens Kodi's own settings window on that category. section_rows.py has the words and icons."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import section_rows as sr

BACK = (9, 10, 92, 110)
ROW_BASE = 9600


def rpc(xbmc, method, params=None):
    answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    return answer.get('result')


def run(section):
    import xbmc
    import xbmcgui
    if section not in sr.SECTIONS:
        return
    title, window, _ = sr.SECTIONS[section]
    categories = (rpc(xbmc, 'Settings.GetCategories', {'section': section, 'level': 'standard'}) or {}).get('categories') or []
    settings_of = lambda cat: (rpc(xbmc, 'Settings.GetSettings', {'level': 'standard', 'filter': {'section': section, 'category': cat}}) or {}).get('settings') or []
    rows = sr.rows(categories, settings_of)

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.setProperty('title', title)
            for key, value in sr.properties(section, rows).items():
                self.setProperty(key, value)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
            elif ROW_BASE < control <= ROW_BASE + len(rows):
                chosen = rows[control - ROW_BASE - 1]
                self.close()
                # Opened from a row: the page shows just that category (its chip row is hidden), titled with its name.
                home = xbmcgui.Window(10000)
                home.setProperty('KodiIOS.CategoryPage', chosen['name'])
                home.setProperty('KodiIOS.CategorySection', section)
                xbmc.executebuiltin('ActivateWindow(%s,%s)' % (window, chosen['id']))

    page = Page('IOSSection.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else '')
