#!/usr/bin/env python3
"""Roadmap 1G.6: read an owner's kodi.log of a long AirPlay session and say when and how it ended.

While a TV plays, the service writes `Kodi iOS diagnostic {...}` lines (airplay_diagnostics.py): playback_progress
every 30 s with the native player (position, buffer, error, stop reason), the network phase and the source counters
(HTTP requests, retries, errors, last status, read error); playback_ended; and unexpected_stop with the last twelve
samples. This script builds the timeline from them so a one-hour stop can be attributed instead of guessed:

  - how long the session ran (first to last line) and the position the TV reached;
  - the last HTTP status and read error from the source, and whether the retry/error counters rose in the last minutes;
  - whether the stop came near 3600 s (a Drive access token lasts one hour) or after a gap with no lines (the phone was
    suspended);
  - the stop reason and Apple's error code, if the service captured one.
usage: stop_log.py kodi.log      (the log stays outside Git; only numbers and one sentence are printed)"""
import datetime
import json
import re
import sys

STAMP = re.compile(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})(?:\.(\d+))?')
EVENT = re.compile(r'Kodi iOS diagnostic (\{.*\})\s*$')
HOUR = 3600
HOUR_WINDOW = 180        # a stop within 3 minutes of an hour matches a one-hour lifetime
SUSPENSION_GAP = 75      # progress lines are 30 s apart; this long without one means the app was not running


def stamp(line):
    m = STAMP.match(line)
    if not m:
        return None
    return datetime.datetime.strptime(m.group(1) + ' ' + m.group(2), '%Y-%m-%d %H:%M:%S').timestamp() + float('0.' + (m.group(3) or '0'))


def events(lines):
    """[(time, record)] for the airplay diagnostic lines."""
    out, last = [], None
    for line in lines:
        at = stamp(line)
        last = at if at is not None else last
        m = EVENT.search(line)
        if not m:
            continue
        try:
            record = json.loads(m.group(1))
        except ValueError:
            continue
        if record.get('component') == 'airplay':
            out.append((at if at is not None else last, record))
    return out


def analyze(lines):
    rows = events(lines)
    progress = [(t, r) for t, r in rows if r.get('event') == 'playback_progress' and t is not None]
    stops = [(t, r) for t, r in rows if r.get('event') in ('unexpected_stop', 'playback_ended')]
    if not progress and not stops:
        return {'verdict': 'no AirPlay diagnostic lines in this log (needs a build with the stop evidence, and AirPlay playing)'}
    generation = (stops[-1][1].get('generation') if stops else progress[-1][1].get('player', {}).get('generation'))
    mine = [(t, r) for t, r in progress if r.get('player', {}).get('generation') == generation] or progress
    first, last = mine[0][0], mine[-1][0]
    info = {'session_s': round(last - first), 'progress_lines': len(mine), 'last_position_s': mine[-1][1].get('player', {}).get('position'),
            'duration_s': mine[-1][1].get('player', {}).get('duration')}
    gaps = [round(b[0] - a[0]) for a, b in zip(mine, mine[1:]) if b[0] - a[0] > SUSPENSION_GAP]
    info['gaps_s'] = gaps
    source = [r.get('source', {}) for _, r in mine]
    tail = source[-6:]
    info['last_status'] = source[-1].get('last_status')
    info['read_error'] = source[-1].get('read_error') or ''
    for key in ('http_errors', 'http_retries'):
        info[key + '_last_3min'] = (tail[-1].get(key, 0) - tail[0].get(key, 0)) if len(tail) > 1 else 0
    stop = stops[-1][1] if stops else {}
    info['stop'] = stop.get('reason') or stop.get('event') or ''
    recent = [row.get('player', {}) for row in stop.get('recent') or []]
    info['stop_reason_code'] = (recent[-1].get('stop_reason') if recent else mine[-1][1].get('player', {}).get('stop_reason'))
    info['error'] = '%s %s' % ((recent[-1] if recent else {}).get('error_domain', ''), (recent[-1] if recent else {}).get('error_code', '')) if recent else ''
    info['verdict'] = verdict(info, stops[-1][0] - first if stops else info['session_s'])
    return info


def verdict(i, elapsed):
    near_hour = abs(elapsed - HOUR) <= HOUR_WINDOW
    status = i.get('last_status')
    if not i.get('stop'):
        return 'no stop in this log; the session ran %d s%s' % (i['session_s'], ' and the phone was away for %s s' % i['gaps_s'] if i['gaps_s'] else '')
    if i['stop'] == 'playback_ended':
        return 'the TV ended playback normally after %d s' % elapsed
    if i['gaps_s'] and i['gaps_s'][-1] > SUSPENSION_GAP and i['session_s'] - sum(i['gaps_s']) > 0 and i['gaps_s'][-1] >= 120:
        return 'the app had no diagnostic lines for %d s before the stop: the phone was suspended or locked' % i['gaps_s'][-1]
    if status in (401, 403) or 'expired' in str(i['read_error']).lower():
        return ('the source answered %s near the one-hour mark (%d s): an expired Drive token or debrid link' % (status, elapsed)) if near_hour \
            else 'the source answered %s at %d s: a rejected token or link' % (status, elapsed)
    if status in (404, 410):
        return 'the source answered %s: the file or link is gone' % status
    if i['read_error'] or i['http_errors_last_3min'] or i['http_retries_last_3min']:
        return 'the source was failing before the stop (%d errors, %d retries in the last minutes, read error %r): the network or the host' % (
            i['http_errors_last_3min'], i['http_retries_last_3min'], i['read_error'])
    if near_hour:
        return 'stopped %d s in, about an hour, with healthy source reads: look at the receiver side (reason %s, error %s)' % (elapsed, i['stop'], i['error'].strip() or 'none')
    return 'stopped %d s in (%s, error %s) with healthy source reads: the receiver or the player ended it' % (elapsed, i['stop'], i['error'].strip() or 'none')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.splitlines()[0])
        return 2
    with open(argv[0], encoding='utf-8', errors='replace') as f:
        info = analyze(f)
    for key, value in info.items():
        print('%-24s %s' % (key, value))
    return 0


if __name__ == '__main__':
    sys.exit(main())
