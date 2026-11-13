"""RunScript(service.kodi.ios.bootstrap,copy_problems): Settings › Library › Download problems (ISSUE-198).

The AllDebrid → Google Drive copies that ended, each with its reason, and two actions: Retry All (they go back in
line, carrying on from what Drive confirmed) and Clear (they leave the list). Network trouble no longer ends a copy;
what is listed here is a source problem (AllDebrid could not give the file) or a cancel."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))
import debrid_drive

WORDS = {'network': 'Network', 'source': 'Source', 'cancelled': 'Cancelled'}


def rows(found):
    """The list's lines: actions first, then each copy as 'Title · reason'."""
    out = []
    retryable = [p for p in found if p['kind'] != 'cancelled']
    if retryable:
        out.append(('retry', 'Retry All (%d)' % len(retryable)))
    if found:
        out.append(('clear', 'Clear All (%d)' % len(found)))
    for p in found:
        out.append(('item', '%s · %s: %s' % (p['title'], WORDS.get(p['kind'], 'Problem'), p['reason'])))
    return out


def run():
    import xbmcgui
    import xbmcvfs
    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()
    found = debrid_drive.problems(debrid_drive.load(profile))
    if not found:
        dialog.ok('Download problems', 'No download has a problem. Copies that lose the network wait and carry on by themselves.')
        return
    lines = rows(found)
    pick = dialog.select('Download problems', [text for _, text in lines])
    if pick < 0:
        return
    what = lines[pick][0]
    if what == 'retry':
        n = debrid_drive.retry_failed(profile)
        dialog.notification('Download problems', '%d back in line' % n, xbmcgui.NOTIFICATION_INFO, 3000)
    elif what == 'clear':
        if dialog.yesno('Clear all?', 'These downloads leave the list. Nothing on Google Drive is deleted.', nolabel='Cancel', yeslabel='Clear'):
            n = debrid_drive.clear_failed(profile)
            dialog.notification('Download problems', '%d cleared' % n, xbmcgui.NOTIFICATION_INFO, 3000)


if __name__ == '__main__':
    run()
