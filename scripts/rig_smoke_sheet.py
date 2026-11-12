"""Run inside the desktop Kodi rig by rig_smoke.py (RunScript with this file's path): opens the choice sheet the way the
watch menu and the resume question do, with sample rows, and waits until the smoke runner closes it (Input.Back).

usage (inside Kodi): RunScript(/path/to/rig_smoke_sheet.py, watch|resume|quality)"""
import os
import sys

import xbmc
import xbmcaddon
import xbmcvfs

here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
sys.path.insert(0, os.path.join(here, 'resources', 'lib'))
import choice_sheet

SPECS = {
    'watch': {'badge': 'MOVIE · 2014', 'art_title': 'Sample Film', 'heading': 'Sample Film', 'sub': 'How would you like to watch?',
              'rows': [{'label': 'Download', 'detail': 'Saved to Google Drive · watch any time'},
                       {'label': 'Stream', 'detail': 'Plays now from your AllDebrid account'}]},
    'resume': {'heading': 'Sample Film', 'rows': [{'label': 'Continue from 0:42:10', 'detail': 'Where you stopped'},
                                                   {'label': 'Start from beginning', 'detail': ''}]},
    'quality': {'heading': 'Sample Film', 'sub': 'Pick a quality · 25 versions found',
                'rows': [{'label': '4K', 'detail': '3 versions', 'tag': 'BEST', 'tag_kind': 'best', 'cover': 90},
                         {'label': '1080p', 'detail': '12 versions', 'cover': 60},
                         {'label': '720p', 'detail': '10 versions', 'cover': 30}],
                'link': 'Show All 25 Links', 'foot': 'Your choice is remembered for this title.'},
}

name = sys.argv[1] if len(sys.argv) > 1 else 'watch'
xbmc.log('Kodi iOS rig smoke: sheet %s opened' % name, xbmc.LOGINFO)
answer = choice_sheet.choose(SPECS.get(name, SPECS['watch']), path=here)
xbmc.log('Kodi iOS rig smoke: sheet %s answered %s' % (name, answer), xbmc.LOGINFO)
