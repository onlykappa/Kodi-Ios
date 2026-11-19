"""Persist a temporary pause after JetExtractors explicitly refuses access."""
import json
import os
import time
from pathlib import Path

PROPERTY = 'KodiIOS.SportsJetPause'
DURATION = 6 * 60 * 60


def build():
    try:
        data = json.loads((Path(__file__).resolve().parents[2] / 'build.json').read_text())
        return str(data.get('commit') or '') + ':' + str(data.get('build') or '')
    except (OSError, ValueError, AttributeError):
        return 'unknown'


def location():
    import xbmcvfs
    return Path(xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')) / 'sports-jet-pause.json'


class Pause:
    def __init__(self, window=None, path=None, build_id=None, clock=time.time):
        self.window, self.clock = window, clock
        self.build_id = build() if build_id is None else build_id
        self.path = path

    def _path(self):
        return Path(self.path) if self.path is not None else location()

    def active(self):
        try:
            raw = self.window.getProperty(PROPERTY) if self.window else ''
            if not raw:
                raw = self._path().read_text()
            record = json.loads(raw)
            active = record.get('build') == self.build_id and 0 < float(record['until']) - self.clock() <= DURATION
            if active and self.window:
                self.window.setProperty(PROPERTY, raw)
            return active
        except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError):
            return False

    def pause(self):
        raw = json.dumps({'build': self.build_id, 'until': self.clock() + DURATION}, separators=(',', ':'))
        if self.window:
            self.window.setProperty(PROPERTY, raw)
        try:
            path = self._path()
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
            temp.write_text(raw)
            os.replace(temp, path)
        except (OSError, ImportError, AttributeError):
            pass

    def clear(self):
        if self.window:
            self.window.clearProperty(PROPERTY)
        try:
            self._path().unlink(missing_ok=True)
        except (OSError, ImportError, AttributeError):
            pass


def is_refusal(error):
    message = str(error).lower()
    return any(text in message for text in ('user is banned', 'not in whitelist', 'not authorized', 'not authorised', 'unauthorized addon'))
