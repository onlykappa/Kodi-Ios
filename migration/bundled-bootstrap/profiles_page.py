"""Settings > Profiles as a portrait page (owner-approved mockup board 09): the profiles as rows (picture or initials, name,
the current one ticked with "Signed in now") and Add Profile in blue, which opens Kodi's own Profiles window. Tapping
another profile loads it with Profiles.LoadProfile; a locked profile asks for its password through Kodi.
The layout is portrait/IOSProfiles.xml, written by portrait.py (settings_page.profiles_page); this fills it."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import profiles_rows as pr

BACK = (9, 10, 92, 110)
ROW_BASE = 9600          # profile n is button 9600+n
ADD = 9609               # Add Profile


def rpc(xbmc, method, params=None):
    answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    return answer.get('result')


def run():
    import xbmc
    import xbmcgui
    profiles = (rpc(xbmc, 'Profiles.GetProfiles', {'properties': ['thumbnail']}) or {}).get('profiles') or []
    rows = pr.entries(profiles, xbmc.getInfoLabel('System.ProfileName'))

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            for key, value in pr.properties(rows).items():
                self.setProperty(key, value)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
            elif control == ADD:
                self.close()
                xbmc.executebuiltin('ActivateWindow(profiles)')
            elif ROW_BASE < control <= ROW_BASE + len(rows):
                name = pr.switch_target(rows, control - ROW_BASE)
                # 'OK' is Kodi's acknowledgement; a refused password leaves the page open.
                if name and rpc(xbmc, 'Profiles.LoadProfile', {'profile': name, 'prompt': True}) == 'OK':
                    self.close()

    page = Page('IOSProfiles.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run()
