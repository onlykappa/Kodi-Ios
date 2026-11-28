"""Run inside the desktop Kodi rig by rig_smoke.py (RunScript): opens the Deck's "Choose a version" page the way Elementum and Umbrella do, with
sample versions, and waits until the smoke runner closes it (Input.Back). ISSUE-500: with the Wi-Fi speed known the page carries the speed in the
subtitle, a line per version and a MAY BUFFER badge; without it the page is as before.

usage (inside Kodi): RunScript(/path/to/rig_smoke_deck.py, wifi|plain)"""
import os
import sys
import types

import xbmc

name = sys.argv[1] if len(sys.argv) > 1 else 'wifi'
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
folder = os.path.join(root, 'migration', 'deck-picker')
sys.path.insert(0, folder)
# The Elementum parts the page needs, stood in for (the page is Kodi's own window class)
module = types.ModuleType('elementum')
module.addon = types.SimpleNamespace(ADDON_PATH=folder)
module.dialog = types.SimpleNamespace(ACTION_PARENT_DIR=9, KEY_NAV_BACK=92, ACTION_PREVIOUS_MENU=10)
sys.modules.update({'elementum': module, 'elementum.addon': module.addon, 'elementum.dialog': module.dialog})
import deck_picker as dp

dp.MODE[0] = u'stream'
dp.RUNTIME[0] = 3300.0                    # a 55 minute episode
dp.WIFI[0] = 14.0 if name == 'wifi' else 0.0
dp.LIMIT[0] = 9.8 if name == 'wifi' else 0.0


def item(n, size, seeds, tags):
    return {'name': 'War.S01E04.2160p.WEB-DL.%s' % tags, 'tags_text': tags, 'providers': ['AllDebrid', 'Torrentio'], 'quality': '4k', 'seeds': seeds,
            'size': size, 'icon': '', 'idx': n}


items = [item(0, 6.75, 20, 'DV.HDR.H265.Atmos'), item(1, 2.05, 9, 'H265.10bit.DDP5.1'), item(2, 21.0, 12, 'DV.HDR.H265.Atmos'), item(3, 5.35, 8, 'HDR.H265')]
dp._CONTEXT['exp'] = None
shown = dp.pick(items, 10)
rows = dp.build_rows(shown)
xbmc.log('Kodi iOS rig smoke: deck %s opened (%s)' % (name, ' | '.join('%s/%s' % (r['badge'], r.get('fit', '')) for r in rows)), xbmc.LOGINFO)
dp.choose_source(u'WAR', rows, dp.quality_label(shown[0]['quality']), dp.count_label(len(shown), len(shown)))
xbmc.log('Kodi iOS rig smoke: deck %s closed' % name, xbmc.LOGINFO)
