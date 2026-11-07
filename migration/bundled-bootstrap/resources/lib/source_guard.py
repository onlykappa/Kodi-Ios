"""Checks what a torrent really contains once Elementum knows its name, and stops the wrong film.

Owner (build 156): Fall (2022) in 4K, "the best one", started Fall.2.Deadpoint.2026. The source list was filtered
(source_match), but some sites (YTS look-alikes) label a result from their own catalogue ("Fall 2022 2160p"); the
torrent's real name only arrives with its metadata, after it was chosen. This watches Elementum's torrent list and
checks every torrent added after a source search against the title that search was for (Burst publishes it:
source_match.PROPERTY), once its real name is known. A clear mismatch (another title, year, season or episode) is
removed with its files and explained in Notifications; anything uncertain (no year in the name) is left alone.
"""
import json
import re
import time

import source_match

# Clear mismatches only. For shows, only another show: when several episodes are chosen, each one's search follows
# the last, so a season or episode mismatch may just be the previous episode's torrent.
DECISIVE = {'movie': ('wrong title', 'wrong year', 'an episode, not the film'),
            'show': ('wrong title', 'wrong show year', "another country's show")}
WATCH_FOR = 300        # seconds after it appears: a torrent's name changes from the site's label to its real name
FRESH = 1800           # a search older than this is not what a new torrent was for
HASH = re.compile(r'^(?:[0-9a-f]{40}|[a-z2-7]{32}|magnet:.*)$', re.I)


def identity(window):
    """(expected, published time) from the last source search, or None (never after the owner chose a hidden source)."""
    try:
        data = json.loads(window.getProperty(source_match.PROPERTY) or '{}')
        if not data or data.get('revealed'):
            return None
        return data['exp'], float(data.get('time', 0))
    except Exception:
        return None


class Guard(object):
    def __init__(self, stop, notify, clock=time.time):
        self.stop, self.notify, self.clock = stop, notify, clock
        self.baseline = None          # torrents already there when Kodi started: never ours to judge
        self.first = {}
        self.search = {}              # the search a torrent was started from: the one current when it first appeared
        self.done = set()

    def tick(self, torrents, found):
        """torrents: Elementum's list ([{'id','name',...}]); found: identity() result. Returns the ids stopped."""
        now = self.clock()
        ids = set(str(t.get('id', '')) for t in torrents)
        if self.baseline is None:
            self.baseline = ids
            return []
        stopped = []
        for t in torrents:
            tid = str(t.get('id', ''))
            if not tid or tid in self.baseline or tid in self.done:
                continue
            if tid not in self.first:
                self.first[tid] = now
                if found and found[1] <= now + 5 and now - found[1] < FRESH:
                    self.search[tid] = found
            first = self.first[tid]
            if now - first > WATCH_FOR:
                self.done.add(tid)
                continue
            if tid not in self.search:
                continue                # not started from a recent search: nothing to compare it with
            exp, published = self.search[tid]
            name = (t.get('name') or '').strip()
            if not name or HASH.match(name):
                continue                # metadata not there yet
            ok, reason = source_match.check(name, exp)
            if ok or reason not in DECISIVE['movie' if exp.get('kind', 'movie') == 'movie' else 'show']:
                continue
            self.done.add(tid)
            try:
                self.stop(tid)
            except Exception:
                pass
            wanted = exp.get('titles', [''])[0] + (' (%s)' % exp['year'] if exp.get('year') else '')
            self.notify('Wrong video stopped', '%s is not %s (%s). The download was stopped and removed; '
                        'choose another version.' % (name, wanted, reason))
            stopped.append(tid)
        for tid in list(self.first):
            if tid not in ids:
                self.first.pop(tid, None)
                self.search.pop(tid, None)
        return stopped


def run(window, torrents, stop, notify, wait, interval=2.0):
    """Service loop: every `interval` s while Kodi runs."""
    guard = Guard(stop, notify)
    while not wait(interval):
        try:
            guard.tick(torrents() or [], identity(window))
        except Exception:
            pass
