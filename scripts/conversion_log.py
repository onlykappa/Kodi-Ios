#!/usr/bin/env python3
"""Roadmap 1G.2: read the live-conversion lines of an owner's kodi.log and say whether the 70 % of real time target holds.

The native remuxer (kr_remux.c) logs, for AirPlay's converted video,
  compat: segment N converted in MS ms (P% of realtime) via ROUTE, source I/O MS ms, ...
for the first three segments of a session and for every later segment slower than 70 %. So in a log:
  - no line after the third one means every later segment finished within 70 % of real time (the target);
  - each later line is a miss, with its route (hardware HDR / GPU / CPU + decoder) and its source read time.
Failed or stopped segments appear as 'compat: segment N failed|stopped after MS ms'.

usage: conversion_log.py kodi.log [--target 70]     (the log stays outside Git; nothing is printed but numbers)"""
import argparse
import re
import statistics
import sys

DONE = re.compile(r'compat: segment (\d+) converted in (\d+) ms \((\d+)% of realtime\) via (.+?), source I/O (\d+) ms')
FAIL = re.compile(r'compat: segment (\d+) (failed|stopped) after (\d+) ms, source I/O (\d+) ms')


def parse(lines):
    """[(kind, segment, ms, percent, route, io_ms)] in log order; kind is 'done' or 'failed' / 'stopped'."""
    out = []
    for line in lines:
        m = DONE.search(line)
        if m:
            out.append(('done', int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5))))
            continue
        m = FAIL.search(line)
        if m:
            out.append((m.group(2), int(m.group(1)), int(m.group(3)), None, '', int(m.group(4))))
    return out


def summarize(events, target=70):
    done = [e for e in events if e[0] == 'done']
    later = done[3:]
    routes = {}
    for _, _, _, pct, route, io in done:
        routes.setdefault(route, []).append((pct, io))
    misses = [e for e in later if e[3] > target]
    if not done:
        verdict = 'no conversion lines'
    elif misses:
        verdict = '%d segments after the first three were slower than %d %% of real time; worst %d %%' % (len(misses), target, max(e[3] for e in misses))
    else:
        verdict = 'no segment after the first three was slower than %d %% of real time' % target
    return {
        'converted': len(done),
        'failed': len([e for e in events if e[0] != 'done']),
        'first_three_pct': [e[3] for e in done[:3]],
        'slow_after_first_three': [(e[1], e[3], e[4]) for e in later if e[3] > target],
        'median_pct': statistics.median([e[3] for e in done]) if done else None,
        'routes': {route: {'segments': len(v), 'median_pct': statistics.median(p for p, _ in v), 'median_io_ms': statistics.median(i for _, i in v)}
                   for route, v in routes.items()},
        'verdict': verdict,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('log')
    parser.add_argument('--target', type=int, default=70)
    args = parser.parse_args(argv)
    with open(args.log, encoding='utf-8', errors='replace') as f:
        summary = summarize(parse(f), args.target)
    for key, value in summary.items():
        print('%-24s %s' % (key, value))
    return 0 if summary['converted'] and not summary['slow_after_first_three'] and not summary['failed'] else 1


if __name__ == '__main__':
    sys.exit(main())
