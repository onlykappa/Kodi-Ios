"""The question before a torrent starts on Elementum's own engine (owner-approved mockup docs/design/torrent-warning-mockup.html, 2026-11-23).

Almost everything goes through AllDebrid (elementum_cloud.route consumes every selected torrent), so this is a safety net at the one place this app's code hands a request
to the engine itself. It says what would happen, says whether a VPN looks active (a hint from vpn_hint, never a guarantee), and makes Cancel the default."""
import vpn_hint

HEADING = 'Download this torrent directly?'
HEAD = 'This one is not coming through AllDebrid. It would download from other people over BitTorrent, and they can see '
STATUS = {
    'direct': ('No VPN detected', 'your IP address. Turn your VPN on first.', 'Download anyway'),
    'unknown': ('Cannot tell if a VPN is on', 'your IP address, unless a VPN is on. Turn your VPN on first.', 'Download anyway'),
    'tunnel': ('A VPN looks active. Not verified: keep your VPN\'s kill switch on', 'the address your VPN gives them.', 'Download'),
}
DECLINED = ('Not downloaded', 'Nothing was started. Pick another source to use AllDebrid.')


def message(found):
    """(text for the dialog, the button that goes on) for a vpn_hint look."""
    status, tail, yes = STATUS[found['state']]
    return '%s%s\n\n[B]%s[/B]' % (HEAD, tail, status), yes


def ask(found, dialog, log=lambda text: None):
    """True when the person chose to go on. `dialog` is xbmcgui.Dialog(): yesno(heading, message, nolabel, yeslabel). Cancel is the first, safe choice."""
    text, yes = message(found)
    log('torrent prompt: asked (%s)' % vpn_hint.line(found))
    answer = bool(dialog.yesno(HEADING, text, nolabel='Cancel', yeslabel=yes))
    log('torrent prompt: %s' % ('the person chose to download directly' if answer else 'cancelled; nothing started'))
    return answer
