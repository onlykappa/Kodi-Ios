"""What one source row of the game page says (owner mockup docs/design/sports-game-sources-mockup.html, 2026-11-28): up to three picture chips (size, frame rate, bitrate), a
coloured dot and one status line. Chips and dot come from what was measured when the page opened (sports_probe, our own sites), from what this phone saw when the source last
played (sports_stream_health: `seen`), or from the size the add-on reported; Crew's and The Loop's links cannot be measured ahead and say so. Pure functions (no Kodi)."""
import re

import sports_probe

SHARP = 1080          # the size chip is green from here up (mockup: chip.q)
SLOW = 1.5            # a stream that downloads slower than 1.5x real time will stall


def ago(then, now):
    """'just now', '5 min ago', '2 h ago', 'yesterday', '3 days ago'."""
    seconds = max(0, now - then)
    if seconds < 90:
        return 'just now'
    if seconds < 3600:
        return '%d min ago' % (seconds // 60)
    if seconds < 86400:
        return '%d h ago' % (seconds // 3600)
    days = int(seconds // 86400)
    return 'yesterday' if days == 1 else '%d days ago' % days


def _height(text):
    found = re.search(r'(\d{3,4})\s*p', str(text or ''), re.I)
    return int(found.group(1)) if found else 0


def chips(source, probe=None):
    """([chip texts], sharp) for a source: measured first, then this phone's memory, then the add-on's own size."""
    seen = source.get('seen') or {}
    probe = probe if (probe or {}).get('ok') else {}
    height = probe.get('height') or seen.get('height') or _height(source.get('quality'))
    fps = probe.get('fps') or seen.get('fps') or 0
    kbps = probe.get('kbps') or seen.get('kbps') or 0
    out = []
    if height:
        out.append('%dp' % height)
    elif str(source.get('quality') or '').strip():
        out.append(str(source['quality']).strip()[:8])
    if fps:
        out.append('%d fps' % fps)
    if kbps:
        out.append('%.1f Mbps' % (kbps / 1000.0))
    return out[:3], height >= SHARP


def status(source, probe, now):
    """(dot, text): dot is 'g' (worked / answering), 'o' (checking, slow or shaky), 'r' (failed lately), 'n' (nothing known)."""
    seen = source.get('seen') or {}
    own = bool(sports_probe.own_name(str(source.get('play') or '')))
    history = ''
    if seen.get('ok'):
        history = 'Worked %d time%s' % (seen['ok'], '' if seen['ok'] == 1 else 's')
        if seen.get('ok_at'):
            history += ', ' + ago(seen['ok_at'], now)
    if seen.get('dead'):
        return 'r', 'Failed lately' + ((' · ' + history.lower()) if history else '')
    if own:
        if probe is None:
            return 'o', 'Checking…'
        if not probe.get('ok'):
            return 'o', "Didn't answer just now" + ((' · ' + history.lower()) if history else '')
        speed = probe.get('speed') or 0
        if speed and speed < SLOW:
            return 'o', 'Answering, but slowly (%.1fx real time)' % speed + ((' · ' + history.lower()) if history else '')
        return 'g', 'Stream found and answering' + ((' · ' + history.lower()) if history else '')
    if history:
        return ('o' if seen.get('fail') and seen.get('fail_at', 0) > seen.get('ok_at', 0) else 'g'), history
    return 'n', 'Checked when played'


def view(source, now):
    """{'chips': [...], 'sharp': bool, 'dot': 'g'|'o'|'r'|'n', 'status': text} for one row."""
    play = str(source.get('play') or '')
    probe = sports_probe.cached(play) if sports_probe.own_name(play) else None
    texts, sharp = chips(source, probe)
    dot, text = status(source, probe, now)
    return {'chips': texts, 'sharp': sharp, 'dot': dot, 'status': text}


def header(sources, now):
    """The Sources heading's right side: 'Checking…' while our own sites are being looked at, then 'Checked 12 s ago'; '' when there is nothing of ours to check."""
    plays = [str(s.get('play') or '') for s in sources if sports_probe.own_name(str(s.get('play') or ''))]
    if not plays:
        return ''
    found = [sports_probe.cached(p) for p in plays]
    if any(f is None for f in found):
        return 'Checking…'
    newest = max(sports_probe.checked_at(p) or 0 for p in plays)
    age = max(0, int(now - newest)) if newest else 0
    return 'Checked just now' if age < 15 else 'Checked %s' % (('%d s ago' % age) if age < 90 else ago(newest, now))
