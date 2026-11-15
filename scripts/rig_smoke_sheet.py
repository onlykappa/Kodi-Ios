"""Run inside the desktop Kodi rig by rig_smoke.py (RunScript with this file's path): opens the choice sheet the way the
watch menu and the resume question do, with sample rows, and waits until the smoke runner closes it (Input.Back).

usage (inside Kodi): RunScript(/path/to/rig_smoke_sheet.py, watch|resume|quality|bell)"""
import os
import sys

import xbmc
import xbmcaddon
import xbmcvfs

here = xbmcaddon.Addon('service.kodi.ios.bootstrap').getAddonInfo('path')
sys.path.insert(0, os.path.join(here, 'resources', 'lib'))
import anticipated
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
    'bell': {'heading': 'New episodes \u00b7 Black Clover', 'sub': 'Next: Season 5 \u00b7 Episode 1 \u00b7 Fri 21 Nov',
             'rows': anticipated.rows({'alert': True, 'auto': False, 'on': True}), 'button': 'Done',
             'foot': 'Switch on only Alert to be told without downloading anything.'},
}

name = sys.argv[1] if len(sys.argv) > 1 else 'watch'
xbmc.log('Kodi iOS rig smoke: sheet %s opened' % name, xbmc.LOGINFO)
state = [True, False]


def flip(index):
    """The bell sheet's switches flip in place (G3), as anticipated_bell.py does with the saved choice."""
    state[index] = not state[index]
    return state[index]


answer = choice_sheet.choose(SPECS.get(name, SPECS['watch']), path=here, toggle=flip if name == 'bell' else None)
xbmc.log('Kodi iOS rig smoke: sheet %s answered %s' % (name, answer), xbmc.LOGINFO)
