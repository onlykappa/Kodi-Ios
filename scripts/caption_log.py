#!/usr/bin/env python3
"""Roadmap 1G.5: say, from an owner's kodi.log, how captions reached (or did not reach) the TV in one Play on TV.

The log shows the whole path, and each stage has its own line:
  Kodi iOS Play on TV: subtitles for AirPlay off | external file | stream N     what Kodi had selected when AirPlay started
  Kodi iOS Play on TV: TV subtitles off | selected                              the same for a Roku / DLNA server
  AirPlay: subtitles: burning source stream N into the converted picture       converted video: burned into the picture
  AirPlay: compat: burning subtitles in (source stream N | external file ...)
  AirPlay: compat: segment N converted ... X subtitle events, Y frames drawn    events found / actually drawn per logged segment
  AirPlay: error: subtitles not burned in: REASON
  AirPlay: prepared: N text subtitle track(s) as WebVTT[, Kodi's on]             a prepared file offers WebVTT captions
  AirPlay: subs: stream N segment M worker result=R elapsed_ms=E; cached | retryable failure
  AirPlay: subs: stream N segment M pending or failed; returning retryable 503

usage: caption_log.py kodi.log      (the log stays outside Git; only counts and one sentence are printed)"""
import re
import sys

SELECTED = re.compile(r'Play on TV: subtitles for AirPlay (off|external file|stream (\d+))')
SERVER = re.compile(r'Play on TV: TV subtitles (off|selected)')
BURN = re.compile(r'subtitles: burning source stream (\d+)|compat: burning subtitles in')
BURN_ERROR = re.compile(r'error: subtitles not burned in: (.+)')
SEGMENT = re.compile(r'compat: segment \d+ converted .*?, (\d+) subtitle events, (\d+) frames drawn')
PREPARED = re.compile(r'prepared: (\d+) text subtitle track\(s\) as WebVTT(, Kodi\'s on)?')
WORKER = re.compile(r'subs: stream (\d+) segment (\d+) worker result=(-?\d+) elapsed_ms=(\d+); (cached|retryable failure)')
PENDING = re.compile(r'subs: stream \d+ segment \d+ pending or failed; returning retryable 503')
NO_CONNECTION = re.compile(r'subs: no subtitle connection')


def analyze(lines):
    """The last Play on TV in the lines, as a dict with a 'verdict' sentence."""
    info = {'selected': None, 'burn': False, 'burn_error': None, 'events': 0, 'drawn': 0, 'segments_logged': 0,
            'webvtt_tracks': 0, 'kodi_on': False, 'cached': 0, 'failed': 0, 'pending_503': 0, 'no_connection': 0, 'slowest_ms': 0}
    for line in lines:
        m = SELECTED.search(line)
        if m:
            info = dict(info, selected=m.group(1) if m.group(1) != 'external file' else 'external file', burn=False, burn_error=None,
                        events=0, drawn=0, segments_logged=0, webvtt_tracks=0, kodi_on=False, cached=0, failed=0,
                        pending_503=0, no_connection=0, slowest_ms=0)   # a new Play on TV starts a new record
            continue
        m = SERVER.search(line)
        if m:
            info['selected'] = 'server ' + m.group(1)
        if BURN.search(line):
            info['burn'] = True
        m = BURN_ERROR.search(line)
        if m:
            info['burn_error'] = m.group(1).strip()
        m = SEGMENT.search(line)
        if m:
            info['segments_logged'] += 1
            info['events'] = max(info['events'], int(m.group(1)))
            info['drawn'] += int(m.group(2))
        m = PREPARED.search(line)
        if m:
            info['webvtt_tracks'] = int(m.group(1))
            info['kodi_on'] = bool(m.group(2))
        m = WORKER.search(line)
        if m:
            info['cached' if m.group(5) == 'cached' else 'failed'] += 1
            info['slowest_ms'] = max(info['slowest_ms'], int(m.group(4)))
        info['pending_503'] += bool(PENDING.search(line))
        info['no_connection'] += bool(NO_CONNECTION.search(line))
    info['verdict'] = verdict(info)
    return info


def verdict(i):
    if i['selected'] is None and not (i['burn'] or i['webvtt_tracks']):
        return 'no Play on TV with a subtitle choice in this log'
    if i['selected'] in ('off', 'server off') and not i['webvtt_tracks']:
        return 'Kodi had subtitles off when Play on TV started, so nothing was burned in and no caption track was offered'
    if i['burn_error']:
        return 'the captions could not be burned into the picture: ' + i['burn_error']
    if i['burn']:
        if i['segments_logged'] and i['events'] == 0:
            return 'burning was on but the converter found no subtitle events in the chosen stream'
        if i['segments_logged'] and i['drawn'] == 0:
            return 'subtitle events were loaded (%d) but no frame had a caption drawn on it in the logged segments' % i['events']
        return 'captions are burned into the picture (%d events, %d frames drawn in the logged segments)' % (i['events'], i['drawn'])
    if i['webvtt_tracks']:
        if i['cached'] == 0 and (i['failed'] or i['pending_503'] or i['no_connection']):
            return 'WebVTT captions were offered but never read: %d failed reads, %d retryable 503s' % (i['failed'], i['pending_503'])
        if i['cached'] == 0:
            return 'WebVTT captions were offered (%d track%s) but the TV asked for none' % (i['webvtt_tracks'], '' if i['webvtt_tracks'] == 1 else 's')
        return 'WebVTT captions served (%d cached, %d failed reads, slowest %d ms)' % (i['cached'], i['failed'], i['slowest_ms'])
    return 'a subtitle was selected (%s) but the log shows neither burning nor WebVTT tracks' % i['selected']


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.splitlines()[0])
        return 2
    with open(argv[0], encoding='utf-8', errors='replace') as f:
        info = analyze(f)
    for key, value in info.items():
        print('%-16s %s' % (key, value))
    return 0


if __name__ == '__main__':
    sys.exit(main())
