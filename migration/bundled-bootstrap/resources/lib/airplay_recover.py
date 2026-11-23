"""A cast that sits still is restarted once, then the person is told (owner, 2026-11-23, logs 72c1c0ac / 7f62ba9c).

The log showed Apple's player waiting at 1101.4 s with the TV receiving about 0.2 MB/s. The app noticed (`buffering_without_progress`, three times) and did nothing for
2 min 40 s until the TV dropped; a second start a minute later worked in 5 s at 2-9 MB/s. So: when the TV is connected, should be playing, and its position has not moved for
STALL seconds, the stream is started again from where the TV was (one restart per cast); if that stalls too, one clear message instead of a silent spinner.

Pure rules; the phone's actions are injected (airplay.restart, a notice)."""
import time

STALL = 25.0     # seconds the position may stay still while the TV is waiting to play
GRACE = 30.0     # after a restart: how long it has to start moving again before it counts as stuck again
HEALTHY = 60.0   # moving this long after a restart: the restart worked, a later stall may be restarted once more
TEXT = 'The TV is not receiving the video fast enough. Move closer to the router or put the Apple TV on Ethernet, then try Play on TV again.'
MOVED = 0.25     # seconds of position that count as movement


class Recover:
    def __init__(self, restart, tell, log=lambda text: None, now=time.monotonic):
        self.restart, self.tell, self.log, self.now = restart, tell, log, now
        self.reset()

    def reset(self):
        self.generation = None
        self.position = None
        self.still_since = None
        self.restarted_at = None
        self.moving_since = None
        self.told = False
        self.restarts = 0

    def observe(self, player):
        """One look at Apple's player (the health sample's `player` dict). Returns 'restart', 'tell' or None."""
        now = self.now()
        if not player or not player.get('generation'):
            return None
        if not player.get('active') or not player.get('external'):
            # not connected to a TV (or not casting): nothing to watch; a fresh cast starts clean
            self.still_since = None
            if not player.get('active'):
                self.reset()
            return None
        # A restart starts a new generation: the same cast, so the counters stay; a different cast starts clean once it has been idle.
        self.generation = player.get('generation')
        position = float(player.get('position') or 0)
        if self.position is None or abs(position - self.position) > MOVED:
            self.position = position
            self.still_since = now
            self.moving_since = self.moving_since or now
            if self.restarts and self.moving_since is not None and now - self.moving_since >= HEALTHY:
                self.restarts, self.told, self.restarted_at = 0, False, None   # it works: the next stall may be restarted again
            return None
        self.moving_since = None
        waiting = player.get('time_control') == 2 or player.get('buffer_empty')
        if not waiting or (player.get('rate') or 0) <= 0:   # paused on the TV, or playing: not a stall
            self.still_since = now
            return None
        if self.still_since is None:
            self.still_since = now
        limit = GRACE if self.restarts else STALL   # after a restart the stream gets GRACE seconds to start moving
        stuck = now - self.still_since
        if stuck < limit:
            return None
        if self.restarts == 0:
            self.restarts += 1
            self.restarted_at = now
            self.still_since = now
            self.moving_since = None
            self.log('airplay recover: the TV has not moved for %d s at %.1f s; starting the stream again' % (stuck, position))
            return 'restart' if self.restart(position) else self._tell(position, stuck, restart_failed=True)
        return self._tell(position, stuck)

    def _tell(self, position, stuck, restart_failed=False):
        if self.told:
            return None
        self.told = True
        self.log('airplay recover: still not moving at %.1f s after %d s%s; the person is told' % (position, stuck, ' (the stream could not be restarted)' if restart_failed else ''))
        self.tell(position)
        return 'tell'
