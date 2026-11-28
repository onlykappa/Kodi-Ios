"""Run inside the desktop Kodi rig by rig_smoke.py (RunScript): opens One Pace's "Japanese only" alert as ios_onepace.play does (ISSUE-502) and waits
until the smoke runner closes it (Input.Back).

usage (inside Kodi): RunScript(/path/to/rig_smoke_alert.py)"""
import xbmc
import xbmcgui

xbmc.log('Kodi iOS rig smoke: alert japanese opened', xbmc.LOGINFO)
answer = xbmcgui.Dialog().yesnocustom('This episode is Japanese only', 'It plays in Japanese with English subtitles. Do you want to continue?',
                                      "Continue, don't ask again in this arc", nolabel='Cancel', yeslabel='Continue')
xbmc.log('Kodi iOS rig smoke: alert japanese answered %s' % answer, xbmc.LOGINFO)
