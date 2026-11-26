"""Peer-to-peer start-up, seeder and health rules (roadmap step 19). Plain Python.

rank() orders verified torrent candidates for direct streaming (seeders first, a size a phone can start quickly, the quality the person asked
for); stream_best() tries them one at a time, each with a bounded wait and a visible "Waiting for peers" state, records each swarm in the shared
source health so a dead one is not retried until its cooldown ends, stops on cancel, and gives a typed outcome when nothing starts.
"""
import time

import direct_stream
import source_contract

MIN_SEEDERS = 2            # one lonely seeder rarely sustains a stream start
MAX_STREAM_BYTES = 30 << 30
FIRST_WAIT = 90
NEXT_WAIT = 60
TOTAL_WAIT = 240           # the whole direct attempt, however many swarms
MAX_TRIES = 3
QUALITY_ORDER = {'4k': 0, '2160p': 0, '1080p': 1, '720p': 2, '480p': 3, 'sd': 4}
STATUS = 'KodiIOS.DirectStream.Status'


def key(candidate):
    return 'swarm:' + str(candidate.get('torrent_hash') or '').lower()


def viable(candidate):
    size = float(candidate.get('size') or 0)
    return int(candidate.get('seeders') or 0) >= MIN_SEEDERS and (size <= MAX_STREAM_BYTES or not size) and bool(candidate.get('torrent_hash'))


def rank(candidates, wanted_quality='', health=None):
    """Viable candidates, swarms in cooldown left out, best first: asked-for quality, then seeders (capped so a huge count does not beat a sane size), then smaller."""
    out = [c for c in candidates if viable(c) and (health is None or health.state(key(c)) != 'cooldown')]
    return sorted(out, key=lambda c: (str(c.get('quality') or '').lower() != str(wanted_quality or '').lower() if wanted_quality else 0,
                                      QUALITY_ORDER.get(str(c.get('quality') or '').lower(), 5), -min(int(c.get('seeders') or 0), 200), float(c.get('size') or 0)))


def status_text(elapsed, wait):
    left = max(0, int(wait - elapsed))
    return 'Waiting for peers · %d s' % left


def stream_best(candidates, request, playback, home, gate, health=None, force=False, cancel=None, wanted_quality='', clock=time.monotonic, show=None):
    """-> (candidate, 'playing'). Raises Outcome: empty (nothing viable), canceled, refused (prompt declined), timeout/offline (every try failed)."""
    ranked = rank(candidates, wanted_quality, health)[:MAX_TRIES]
    if not ranked:
        raise source_contract.Outcome(source_contract.EMPTY)
    began, last, asked = clock(), None, False
    for number, candidate in enumerate(ranked):
        left = TOTAL_WAIT - (clock() - began)
        if left <= 5:
            break
        if cancel and cancel():
            raise source_contract.Outcome(source_contract.CANCELED)
        wait = min(FIRST_WAIT if number == 0 else NEXT_WAIT, left)
        if show:
            show(status_text(0, wait), 0)
        try:
            result = direct_stream.stream(candidate, request, playback, home, (lambda: None) if asked else gate, health=None, force=force, cancel=cancel, wait=wait,
                                          tick=(lambda elapsed, wait=wait: show(status_text(elapsed, wait), int(min(100, 100 * elapsed / wait)))) if show else None)
            asked = True
        except source_contract.Outcome as outcome:
            if outcome.kind in (source_contract.CANCELED, source_contract.REFUSED):
                raise                               # the person said no: never advance on a cancel or a declined prompt
            asked = asked or outcome.kind == source_contract.TIMEOUT
            last = outcome
            if health is not None and outcome.kind != source_contract.UNSUPPORTED:
                health.record(key(candidate), outcome.kind)
            continue
        if health is not None:
            health.record(key(candidate), source_contract.OK)
        if show:
            show('')
        return candidate, result
    if show:
        show('')
    raise last or source_contract.Outcome(source_contract.TIMEOUT)
