"""Sports as its own source capability (roadmap step 10): which listing is THIS game, and may it be started now. No Kodi imports.

ESPN supplies the game's identity (id, league, teams, start, state, score); a source listing (Crew's walk, an independent embed
page) supplies streams. A listing is used only when it is one unique, current match: same league, same two teams, start within
sports_merge.SAME_GAME_WITHIN, and the game neither finished nor stale. Two different matching listings are ambiguous and rejected
(never "closest wins"). A live source handle expires quickly (LIVE_TTL) and is never written down: persistable() carries no link or
play request. Native Crew handling stays as it is: `launch` is the existing sports_provider.play hand-off.
"""
import threading
import time

import source_contract
import sports_merge

LIVE_TTL = 300             # a listing older than this is re-asked, never played
MAX_LIVE_AGE = 8 * 3600    # ESPN says live but it began over 8 h ago: its state is stale
MAX_UPCOMING_LATE = 3 * 3600  # ESPN says upcoming but the start passed over 3 h ago
EARLY = 24 * 3600          # a source more than a day before the game is not for this game
SAME_LISTING = 120         # two matching listings whose starts differ by less than this are one listing seen twice
PERSIST = ('id', 'addon', 'quality', 'language', 'also')


def status(game, now=None):
    """'live' | 'upcoming' | 'stale' from ESPN's own state and start; unknown states are stale (never guess)."""
    now = time.time() if now is None else now
    start = game.get('start') or 0
    state = game.get('state')
    if state == 'live':
        return 'live' if start and now - start <= MAX_LIVE_AGE else 'stale'
    if state == 'upcoming':
        return 'upcoming' if start and now - start <= MAX_UPCOMING_LATE and start - now <= EARLY else 'stale'
    return 'stale'


def unique_match(game, listings, now=None):
    """-> listing. Raises Outcome(empty) for none, Outcome(unsupported) for stale or ambiguous."""
    now = time.time() if now is None else now
    if status(game, now) == 'stale':
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    found = [x for x in listings if x.get('sources') and sports_merge.same_game(game, x)]
    if not found:
        raise source_contract.Outcome(source_contract.EMPTY)
    if len(found) > 1:
        first = found[0]
        for other in found[1:]:
            twin = abs((first.get('start') or 0) - (other.get('start') or 0)) < SAME_LISTING
            if not twin:
                raise source_contract.Outcome(source_contract.UNSUPPORTED)       # a doubleheader or a lookalike: never guess
        merged = list(first['sources'])
        seen = {s.get('id') for s in merged}
        for other in found[1:]:
            merged.extend(s for s in other['sources'] if s.get('id') not in seen)
        return dict(first, sources=merged)
    return found[0]


def fresh(listed_at, now=None):
    now = time.time() if now is None else now
    return listed_at is not None and 0 <= now - listed_at <= LIVE_TTL


def persistable(game, source):
    """What may be saved or logged about a chosen live source: ids and labels only, never its play request or a link."""
    out = {'game': game.get('id')}
    out.update({k: source[k] for k in PERSIST if k in source})
    return out


class Launcher:
    """One live start at a time per game: a second tap while one is opening does nothing."""
    def __init__(self):
        self.lock = threading.Lock()
        self.opening = set()

    def start(self, game, listings, listed_at, launch, now=None, cancel=None, current=None, source_id=None, health=None):
        """Returns the persistable record of what was started. Raises Outcome: empty, unsupported (stale/ambiguous), expired, canceled."""
        now = time.time() if now is None else now
        key = game.get('id') or ''
        with self.lock:
            if key in self.opening:
                raise source_contract.Outcome(source_contract.UNSUPPORTED)
            self.opening.add(key)
        try:
            listing = unique_match(game, listings, now)
            if not fresh(listed_at, now):
                raise source_contract.Outcome(source_contract.EXPIRED)
            sources = listing['sources']
            if health is not None and not source_id:      # a family cooling down goes behind the others, never away
                cool = [x for x in sources if health.state('sports:' + str(x.get('addon', '')).split(' ')[0].lower()) == 'cooldown']
                sources = [x for x in sources if x not in cool] + cool
            source = next((s for s in sources if s.get('id') == source_id), None) if source_id else sources[0]
            if source is None:
                raise source_contract.Outcome(source_contract.UNSUPPORTED)
            if cancel and cancel():
                raise source_contract.Outcome(source_contract.CANCELED)
            if current is not None:                    # ESPN, asked again just before starting: a game that ended meanwhile is stale
                latest = current(key)
                if latest is None or status(latest, now) == 'stale':
                    raise source_contract.Outcome(source_contract.UNSUPPORTED)
            family = 'sports:' + str(source.get('addon', '')).split(' ')[0].lower()
            try:
                launch(source)
            except Exception as error:
                if health is not None:
                    health.record(family, source_contract.classify(error))
                raise
            return persistable(game, source)       # a successful start is recorded by the router once the picture really moves
        finally:
            with self.lock:
                self.opening.discard(key)


def independent_resolver(address, resolve, now=time.time, verify=None):
    """For Playback.start_resolved: ask the embed resolver for a fresh playlist right now, then fetch its chain. Typed failures only."""
    import fresh_resolve

    def go():
        try:
            url, headers = resolve(address)
        except RuntimeError:
            raise source_contract.Outcome(source_contract.EMPTY)           # the resolver's own "no verified HLS stream available"
        except Exception as error:
            raise source_contract.Outcome(source_contract.classify(error))
        resolved = fresh_resolve.Resolved(url, headers, now(), ttl=LIVE_TTL)
        (verify or fresh_resolve.verify_chain)(resolved)
        return resolved
    return go


def start_independent(game, address, playback, resolve, now=None, cancel=None, current=None, verify=None, health=None):
    """Game -> fresh embed playlist -> player, with the same stale, cancel and duplicate rules as native Crew starts."""
    now = time.time() if now is None else now
    if status(game, now) == 'stale':
        raise source_contract.Outcome(source_contract.UNSUPPORTED)
    if cancel and cancel():
        raise source_contract.Outcome(source_contract.CANCELED)
    if current is not None:
        latest = current(game.get('id') or '')
        if latest is None or status(latest, now) == 'stale':
            raise source_contract.Outcome(source_contract.UNSUPPORTED)
    try:
        result = playback.start_resolved((game.get('id') or '', 'independent'), independent_resolver(address, resolve, verify=verify), cancel=cancel)
    except source_contract.Outcome as outcome:
        if health is not None:
            health.record('sports:independent', outcome.kind)       # canceled is ignored by Health.record
        raise
    if health is not None and result == 'playing':
        health.record('sports:independent', source_contract.OK)
    return result
