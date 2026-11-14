"""Measured piece throughput and one-second samples. Rates are bytes/s; histories never imply byte progress."""
import math

WINDOW = 30.0
SAMPLES = 60
QUIET = 60.0


class Pieces:
    """Time-weighted rolling average of acknowledged bytes / actual request duration (including the first piece)."""
    def __init__(self):
        self.pieces = []

    def observe(self, advanced, elapsed, now, piece_bytes=None):
        if elapsed <= 0 or advanced < 0:
            return
        self.pieces.append((float(now), float(advanced), float(elapsed), int(piece_bytes or advanced)))
        self.pieces = [p for p in self.pieces if now - p[0] <= WINDOW][-60:]

    def fields(self, now):
        recent = [p for p in self.pieces if now - p[0] <= QUIET]
        if not recent:
            return {'rate_own': 0.0, 'measured_at': 0.0, 'piece_bytes': 0, 'piece_seconds': 0.0}
        return {'rate_own': sum(p[1] for p in recent) / sum(p[2] for p in recent),
                'measured_at': recent[-1][0], 'piece_bytes': recent[-1][3], 'piece_seconds': recent[-1][2]}


class History:
    """Sample the latest measured rate once per second. After a scheduler gap start a new segment, never invent samples.
    Each lane is a worker identity, not its title or its screen position. A reused lane starts a new history.
    """
    def __init__(self):
        self.lanes = {}
        self.total = []
        self.last = None

    def restore(self, state):
        self.lanes = {j['lane_id']: list(j.get('speed_history') or [])
                      for j in state.get('jobs', []) if j.get('lane_id')}
        self.total = list((state.get('upload') or {}).get('speed_history') or [])
        self.last = self.total[-1][0] if self.total else None

    def sample(self, state, now):
        stamp = math.floor(now)
        if self.last is not None and stamp < self.last:
            self.lanes.clear(); self.total.clear()
        append = self.last != stamp
        seen, total_rate = set(), 0.0
        for j in state.get('jobs') or []:
            if j.get('kind') not in ('copy', 'upload'):
                continue
            identity = str(j.get('key') or j.get('job') or j.get('id') or j.get('name') or j['title'])
            seen.add(identity)
            rate = float(j.get('rate') or 0) if j.get('state') in ('running', 'slowed') else 0.0
            measured = float(j.get('measured_at') or 0)
            if measured and now - measured > QUIET:
                rate = 0.0
            points = self.lanes.setdefault(identity, [])
            if append:
                points.append([stamp, rate]); del points[:-SAMPLES]
            remaining = (max(0.0, float(j.get('upload_total') or 0) - float(j.get('out_bytes') or 0))
                         if j.get('ready_copy') else
                         max(0.0, float(j.get('total') or 0) - float(j.get('confirmed_bytes', j.get('sent') or 0))))
            j.update(rate=rate, speed_mb_s=rate / 1048576.0, speed_history=list(points),
                     eta_s=remaining / rate if rate else 0.0,
                     progress_pct=float(j.get('pct') or 0), lane_id=identity)
            total_rate += rate
        self.lanes = {k: v for k, v in self.lanes.items() if k in seen}
        if append:
            self.total.append([stamp, total_rate]); del self.total[:-SAMPLES]
        self.last = stamp
        state['upload'] = {'rate': total_rate, 'speed_mb_s': total_rate / 1048576.0,
                           'speed_history': list(self.total), 'lane_count': len(seen),
                           'eta_s': float(state.get('copy_left') or 0) / total_rate if total_rate else 0.0,
                           'lanes': [{k: j.get(k) for k in ('lane_id', 'key', 'title', 'speed_mb_s', 'rate', 'eta_s',
                                                          'progress_pct', 'sent', 'total', 'piece_bytes', 'piece_seconds',
                                                          'measured_at', 'speed_history')}
                                     for j in state.get('jobs') or [] if j.get('lane_id') in seen]}
        return state


def phone_uploads(profile):
    """Actual uploader telemetry, read without the notification store or its independent estimates."""
    import json
    import os
    import time
    target = os.path.join(str(profile), 'addon_data/service.kodi.ios.bootstrap/drive-uploads.json')
    try:
        with open(target, encoding='utf-8') as handle:
            current = (json.load(handle) or {}).get('current') or {}
    except (OSError, ValueError):
        return []
    if not current.get('total'):
        return []
    import drivelibrary
    return [dict(current, title=drivelibrary.display_title(current.get('name', '')),
                 progress=100.0 * float(current.get('sent') or 0) / current['total'],
                 rate=float(current.get('rate_own') or 0) if time.time() - float(current.get('updated') or 0) <= QUIET else 0.0)]
