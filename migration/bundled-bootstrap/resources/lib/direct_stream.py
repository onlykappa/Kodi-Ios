"""Peer-to-peer stream route for when debrid is unavailable (roadmap step 18). Plain Python; Kodi pieces are injected.

The app normally sends a chosen torrent to AllDebrid and Google Drive (elementum_cloud.route intercepts Elementum's /play). Here the person
may instead stream it straight from peers with the bundled Elementum engine, but only when: the candidate is a verified torrent, debrid is
unavailable (debrid_account) or the person asks for it, and they accept the existing torrent prompt (vpn hint, Cancel by default). Nothing
starts silently, a Stream is never turned into a Drive download, and no VPN or network setting is touched. Approval is a one-time, short-lived
grant on the Home window for exactly that info hash; elementum_cloud.route lets that one request through to Elementum's own player.
"""
import json
import time
import urllib.parse

import backup_playback
import debrid_account
import source_contract

PROPERTY = 'KodiIOS.DirectStream'
GRANT_TTL = 120
ELEMENTUM = 'plugin://plugin.video.elementum/play?uri='
WAIT = 90                      # seconds to wait for the first picture from peers (step 19 refines this)


def grant(home, info_hash, now=None):
    now = time.time() if now is None else now
    home.setProperty(PROPERTY, json.dumps({'hash': str(info_hash).lower(), 'until': now + GRANT_TTL}))


def revoke(home):
    try:
        home.clearProperty(PROPERTY)
    except Exception:
        pass


def consume(home, info_hash, now=None):
    """True exactly once for the hash that was approved, within its short life; anything else (or no home window) is False."""
    if home is None:
        return False
    now = time.time() if now is None else now
    try:
        record = json.loads(home.getProperty(PROPERTY) or '{}')
    except (ValueError, TypeError):
        return False
    revoke(home)                                 # one use: a retry must ask again
    return bool(record) and record.get('hash') == str(info_hash).lower() and record.get('until', 0) >= now


def plan(candidate, request, health=None, force=False):
    """-> the info hash to stream. Raises Outcome: unsupported (not a torrent, wrong match, debrid is fine and the person did not ask)."""
    if backup_playback.route_of(candidate) != 'torrent':
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    found = backup_playback.verify_torrent(candidate)
    source_contract.check_usable(dict(candidate, capabilities=candidate.get('capabilities') or source_contract.capabilities(candidate),
                                      expires_at=candidate.get('expires_at') or source_contract.expiry(candidate)), dict(request, purpose='download'))
    import debrid_token
    if not (force or debrid_account.unavailable(health) or not debrid_token.has()):
        raise source_contract.Outcome(source_contract.UNSUPPORTED)      # debrid works: use it, not peers
    return found


def stream(candidate, request, playback, home, gate, health=None, force=False, cancel=None, wait=WAIT, now=None, tick=None):
    """Ask, approve, hand Elementum's play URL to the player. Returns 'playing' / 'duplicate' or raises Outcome (refused if declined, canceled, timeout...)."""
    found = plan(candidate, request, health, force)
    try:
        gate()                                    # the existing torrent prompt; raises when the person declines
    except Exception as error:
        if type(error).__name__ in ('Canceled', 'Cancelled'):
            raise source_contract.Outcome(source_contract.REFUSED)
        raise
    if cancel and cancel():
        raise source_contract.Outcome(source_contract.CANCELED)
    grant(home, found, now)
    url = ELEMENTUM + urllib.parse.quote('magnet:?xt=urn:btih:' + found, safe='')

    def resolve():
        import fresh_resolve
        return fresh_resolve.Resolved(url, {}, time.time(), ttl=GRANT_TTL)
    try:
        return playback.start_resolved(('direct', found), resolve, cancel=cancel, wait=wait, tick=tick)
    except BaseException:
        revoke(home)
        raise
