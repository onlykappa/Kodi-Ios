"""Settings › Google Drive › AI Upscale test (measurement build, DEC-039).

Lists the prepared 720p/1080p videos on Google Drive, asks which one and how long, and leaves the request for the
preparation queue (upscale_measure.py). Nothing is uploaded: the copy is counted and the numbers go to kodi.log.
"""
import os
import sys

import xbmc
import xbmcgui
import xbmcvfs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
import notices
import picture
import prepare_downloads
import upscale_measure

HEADING = 'AI Upscale test'
CHOICES = (
    ('Whole video, best AI engine', ('auto',), 0),
    ('First 5 minutes, best AI engine', ('auto',), 5),
    ('First 3 minutes with each engine (compare)', ('ai-video', 'ai-image', 'ai-fast', 'lanczos'), 3),
)


def main():
    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()
    if upscale_measure.pending(profile):
        dialog.ok(HEADING, 'A test is already waiting. It starts between conversions; its result goes to Notifications and kodi.log.')
        return
    found = upscale_measure.candidates(prepare_downloads.load(profile))
    if not found:
        dialog.ok(HEADING, 'No prepared 720p or 1080p video on Google Drive yet. Download one, let it finish preparing, then try again.')
        return
    found = found[:40]
    rows = ['%s · %s · %d min' % (row['name'], picture.LABELS[picture.level(row['width'], row['height'])]
                                   if picture.level(row['width'], row['height']) >= 0 else '%dp' % row['height'],
                                   round(row['duration'] / 60)) for row in found]
    pick = dialog.select(HEADING, rows)
    if pick < 0:
        return
    how = dialog.select('%s · upscale to 4K UHD' % HEADING, [label for label, _, _ in CHOICES])
    if how < 0:
        return
    label, engines, minutes = CHOICES[how]
    upscale_measure.request(profile, found[pick], '4K UHD', engines, minutes)
    xbmc.log('Kodi iOS upscale measurement: requested %s (%s)' % (found[pick]['name'], label), xbmc.LOGINFO)
    notices.add(profile, 'info', 'AI Upscale test queued', 'Starts between conversions. Keep Kodi open and the phone plugged in; results go to Notifications and the log.')
    dialog.notification(HEADING, 'Queued: starts between conversions', xbmcgui.NOTIFICATION_INFO, 4000)


if __name__ == '__main__':
    main()
