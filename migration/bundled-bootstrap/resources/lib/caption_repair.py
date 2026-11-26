"""Prepared copies whose subtitle cues have no length are made again once the converter can give them one (owner, build 639 log 9f7b4ab2: every Lanterns episode came
up on an embedded subtitle that reports "on" and draws nothing, subtitle memory turned it off three times; build 634 log f75957fe found the cause: the converter
wrote each text cue with a length of 0 s).

The converter that gives a cue its reading time is KodiAirPlay r72 (kr_prepare.c). When the installed framework is r72 or newer, the library's check of a prepared,
fragmented MP4 also looks at its subtitle tracks (mp4_tracks.probe, a few small ranges through the app's own proxy); a copy with zero-length cues takes the same
re-package path as a copy in an older layout (prepare_downloads: fast_open False, repack). Each copy is tried once per framework revision, so a converter that did
not fix it cannot make the library repack the same file again and again. Nothing here runs before r72, and nothing is read from a file that is not a fragmented MP4."""
import json
import os
import re

FIXED_FROM = 72
REASON = 'caption_lengths'


def revision(build_json=None):
    """The AirPlay framework's revision number this build carries (0 when unknown): build.json 'frameworks' -> 'airplay' -> 'tag' 'kodi-airplay-r72'."""
    path = build_json or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'build.json')
    try:
        with open(path, encoding='utf-8') as handle:
            tag = str((((json.load(handle).get('frameworks') or {}).get('airplay')) or {}).get('tag') or '')
        found = re.search(r'-r(\d+)$', tag)
        return int(found.group(1)) if found else 0
    except (OSError, ValueError, AttributeError):
        return 0


def due(url, key, tried, installed=None, probe=None):
    """True when the prepared copy at `url` has zero-length subtitle cues, the converter can fix that, and this copy has not been tried at this revision.
    `tried` is the library's {key: revision} record (changed here when a repack is asked for)."""
    installed = revision() if installed is None else installed
    if installed < FIXED_FROM or int(tried.get(key) or 0) >= installed:
        return False
    if probe is None:
        import mp4_tracks
        probe = mp4_tracks.probe
    try:
        found = probe(url)
    except Exception:
        return False
    if not found or not any(t.get('zero_length') for t in found.get('tracks') or ()):
        return False
    tried[key] = installed
    return True


def carry(prior, probe):
    """ISSUE-486 (owner log 0d8c75c0: Iron Man showed "preparing", 18 s later was "kept unchanged", no notice, never made again):
    due() answers True once per copy (it records the try), so the second look, when the video is opened to be made, found
    nothing to do and dropped the repack the first look had asked for. A repack the caption check asked for stays asked."""
    if (prior or {}).get('layout_reason') == REASON and prior.get('fast_open') is False and probe.get('fast_open') is not False:
        probe.update(fast_open=False, layout_reason=REASON)
    return probe
