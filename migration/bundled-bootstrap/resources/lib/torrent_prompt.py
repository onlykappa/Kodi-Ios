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
# The same question for a stream from peers (step 18): the wording says Stream, not Download.
STREAM_HEADING = 'Stream this torrent directly?'
STREAM_HEAD = 'This streams from other people, and they can see '
STREAM_TAIL = {'direct': 'your IP address.', 'unknown': 'your IP address, unless a VPN is on.', 'tunnel': 'the address your VPN gives them.'}   # short: Kodi\'s question box shows about three lines
STREAM_YES = {'direct': 'Stream anyway', 'unknown': 'Stream anyway', 'tunnel': 'Stream'}
STREAM_DECLINED = ('Not streamed', 'Nothing was started. Try again when AllDebrid answers.')


def message(found, stream=False):
    """(text for the dialog, the button that goes on) for a vpn_hint look."""
    status, tail, yes = STATUS[found['state']]
    if stream:
        return '%s%s\n\n[B]%s[/B]' % (STREAM_HEAD, STREAM_TAIL[found['state']], status), STREAM_YES[found['state']]
    return '%s%s\n\n[B]%s[/B]' % (HEAD, tail, status), yes


def ask(found, dialog, log=lambda text: None, stream=False):
    """True when the person chose to go on. `dialog` is xbmcgui.Dialog(): yesno(heading, message, nolabel, yeslabel). Cancel is the first, safe choice."""
    text, yes = message(found, stream)
    log('torrent prompt: asked (%s)%s' % (vpn_hint.line(found), ' to stream' if stream else ''))
    answer = bool(dialog.yesno(STREAM_HEADING if stream else HEADING, text, nolabel='Cancel', yeslabel=yes))
    log('torrent prompt: %s' % (('the person chose to %s directly' % ('stream' if stream else 'download')) if answer else 'cancelled; nothing started'))
    return answer
