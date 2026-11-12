#!/usr/bin/env python3
"""Roadmap 3.4: smoke checks in a real Kodi (the desktop Kodi rig) before an IPA is requested.

For each page the owner meets (pickers and the resume question, the show page, Settings pages, Notifications,
Accounts, Transfers, Library status, the track menus ...) this opens it in the running rig and checks, automatically:
  1. the page's own window opened (the service's `ui open` diagnostic line, or the sheet's log line);
  2. Kodi's log gained no script traceback, XML-load error, expression error or missing-window message while it opened
     and closed (a short list of known harmless lines is allowed and named below);
  3. the screenshot is not blank (the picture has contrast: a window that opened but drew nothing fails).
It writes KODI_RIG_HOME/smoke/report.json and prints one line per check; the exit status is 1 when any check fails.

Evidence class: desktop Kodi rig (APPLE-UI-POLICY §9). It proves the pages load and draw without errors in real Kodi.
It does not prove layout against the mockups (use kodi_rig.py boards for that), touch, the SF font, the native tab bar,
AirPlay or anything on the phone. Run it after `kodi_rig.py setup` (once), before dispatching import-review:

  python3 -B scripts/rig_smoke.py            # start the rig if needed, sync this checkout, run every check
  python3 -B scripts/rig_smoke.py --list
  python3 -B scripts/rig_smoke.py notifications watch_sheet     # only these

Screenshots stay in KODI_RIG_HOME/smoke (they can show artwork) and never go into Git."""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

# Lines that mean a page is broken. Matched against the Kodi log text written while a check ran.
BAD = (
    (re.compile(r'Traceback \(most recent call last\)'), 'Python traceback'),
    (re.compile(r'EXCEPTION|Exception in|Unhandled exception', re.I), 'exception'),
    (re.compile(r'Error parsing (boolean )?expression|Skin Variable.*error', re.I), 'skin expression error'),
    (re.compile(r'XML File for Window is missing|Window id does not exist|Error loading window|Failed to load window', re.I), 'window did not load'),
    (re.compile(r'error <general>: .*(Kodi iOS|bootstrap|plugin\.video\.kodi\.ios\.watch)', re.I), 'app error line'),
    (re.compile(r'CScriptRunner: .*(failed|error|could not)|Failed to start script', re.I), 'script did not run'),
)
# Known harmless lines, each with the reason (roadmap 2.16 / 2.14: Kodi's remembered view control hidden on some pages).
ALLOWED = (
    (re.compile(r"Control \d+ in window \d+ has been asked to focus, but it can't"), 'ISSUE 2.14/2.16: focus request on a hidden control'),
    (re.compile(r'GetDirectory - Error getting plugin://plugin\.video\.kodi\.ios\.watch/\?action=cached'), 'rig has no cached listing copies'),
    (re.compile(r'(Trakt|trakt).*(auth|sign)', re.I), 'rig only: Trakt sign-in prompt'),
    (re.compile(r'GetDirectory - Error getting plugin://plugin\.video\.themoviedb\.helper/'), 'rig only: Home rows that need a Trakt sign-in'),
    (re.compile(r'Previous line repeats'), 'log folding'),
)
BLANK_STDDEV = 0.012     # ImageMagick's standard deviation (0-1) of a screenshot; a window that drew nothing is below this
SETTLE = 6.0


def scan(text):
    """[(label, line)] for the lines of text that show a broken page and are not allowed."""
    found = []
    for line in text.splitlines():
        for pattern, label in BAD:
            if pattern.search(line) and not any(ok.search(line) for ok, _ in ALLOWED):
                found.append((label, line.strip()[:240]))
                break
    return found


def blank(stddev):
    return stddev is None or stddev < BLANK_STDDEV


# name -> how to open it and what proves it opened. page: RunScript(service.kodi.ios.bootstrap, *page);
# script: RunScript(<file>, *args) of a helper in scripts/; builtin: any Kodi builtin. expect: a log fragment that must appear.
CHECKS = (
    {'name': 'notifications', 'page': ['notifications'], 'expect': '"page":"notifications"'},
    {'name': 'accounts', 'page': ['accounts_page'], 'expect': '"page":"accounts_page"'},
    {'name': 'profiles', 'page': ['profiles_page'], 'expect': '"page":"profiles_page"'},
    {'name': 'favourites', 'page': ['favourites_page'], 'expect': '"page":"favourites_page"'},
    {'name': 'settings_search', 'page': ['settings_search'], 'expect': '"page":"settings_search"'},
    {'name': 'settings_player', 'page': ['section_page', 'player'], 'expect': '"page":"section_page"'},
    {'name': 'skin_settings', 'page': ['skin_settings_page'], 'expect': '"page":"skin_settings_page"'},
    {'name': 'navigation_menu', 'page': ['navigation_menu'], 'expect': '"page":"navigation_menu"'},
    {'name': 'activity', 'page': ['activity_page'], 'expect': '"page":"activity_page"'},
    {'name': 'library_status', 'page': ['library_status'], 'expect': '"page":"library_status"'},
    {'name': 'transfers', 'page': ['transfers'], 'expect': '"page":"transfers"'},
    {'name': 'queue', 'page': ['tool_pages', 'queue'], 'expect': '"page":"tool_pages"'},
    {'name': 'history', 'page': ['tool_pages', 'history'], 'expect': '"page":"tool_pages"'},
    {'name': 'airplay_settings', 'page': ['airplay_settings'], 'expect': '"page":"airplay_settings"'},
    # The approved sheets (watch menu, resume question, quality picker): board 13-15 style, opened as the add-ons open them.
    {'name': 'watch_sheet', 'script': ['rig_smoke_sheet.py', 'watch'], 'expect': 'rig smoke: sheet watch opened'},
    {'name': 'resume_sheet', 'script': ['rig_smoke_sheet.py', 'resume'], 'expect': 'rig smoke: sheet resume opened'},
    {'name': 'quality_sheet', 'script': ['rig_smoke_sheet.py', 'quality'], 'expect': 'rig smoke: sheet quality opened'},
    # The show page: the Library's show listing in Kodi's video window (empty in the rig: no Drive, which is the empty state).
    {'name': 'show_page', 'builtin': 'ActivateWindow(videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=tv&show=Smoke&merge=1,return)',
     'expect': 'Kodi iOS Library:'},
    {'name': 'movies_page', 'builtin': 'ActivateWindow(videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=movie,return)',
     'expect': 'Kodi iOS Library:'},
)
NOT_COVERED = (
    'the track menus (Subtitles, Audio, Speed) and the video controls: they open over a playing video, which the rig does not play',
    'the Download/Stream flow after a real Umbrella or Elementum search (needs add-ons and accounts)',
    'anything on the phone: touch, the SF font, the native tab bar, safe areas, AirPlay, Drive',
)


def load_rig():
    spec = importlib.util.spec_from_file_location('kodi_rig', ROOT / 'scripts/kodi_rig.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stddev(path):
    """ImageMagick's standard deviation of the picture (0-1), or None when it cannot be read."""
    try:
        out = subprocess.run(['convert', str(path), '-colorspace', 'Gray', '-format', '%[fx:standard_deviation]', 'info:'],
                             capture_output=True, text=True, timeout=30)
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class Runner(object):
    def __init__(self, rig):
        self.rig = rig
        self.log = rig.HOME / '.kodi/temp/kodi.log'
        self.out = rig.RIG / 'smoke'
        self.out.mkdir(parents=True, exist_ok=True)

    def ensure_running(self):
        try:
            self.rig.rpc('JSONRPC.Ping')
        except Exception:
            self.rig.start(argparse.Namespace())
        self.rig.sync(None)
        # The rig only: Home asks about Trakt first; two Backs clear it before a page opens (docs/design/KODI-RIG.md).
        for _ in range(2):
            self.back()
        time.sleep(1)

    def back(self):
        try:
            self.rig.rpc('Input.Back')
        except Exception:
            pass

    def offset(self):
        try:
            return self.log.stat().st_size
        except OSError:
            return 0

    def since(self, offset):
        try:
            with open(self.log, 'rb') as f:
                f.seek(0, 2)
                if f.tell() < offset:       # Kodi restarted and started a new log: everything in it is new
                    offset = 0
                f.seek(offset)
                return f.read().decode('utf-8', 'replace')
        except OSError:
            return ''

    def open(self, check):
        if 'page' in check:
            self.rig.open_page(argparse.Namespace(page=check['page']), settle=0)
        elif 'script' in check:
            script = str(ROOT / 'scripts' / check['script'][0])
            args = ','.join([script] + check['script'][1:])
            self.rig.run_builtins('RunScript(%s)' % args)
        else:
            self.rig.run_builtins(check['builtin'])

    def close(self):
        self.rig.run_builtins('Dialog.Close(all,true)')
        for _ in range(3):      # script windows close with Back, not Dialog.Close (docs/design/KODI-RIG.md)
            self.back()
            time.sleep(0.5)

    def run(self, check, settle=SETTLE):
        start = self.offset()
        problems = []
        try:
            self.open(check)
            time.sleep(settle)
            picture = self.rig.shot('smoke-' + check['name'])
            spread = stddev(picture)
            if blank(spread):
                problems.append('blank picture (contrast %s)' % ('unreadable' if spread is None else '%.4f' % spread))
        except Exception as error:      # Kodi not answering is a failed check, not a crash of the runner
            problems.append('rig error: %s' % error)
            spread = None
        finally:
            try:
                self.close()
                time.sleep(1.0)
            except Exception:
                pass
        text = self.since(start)
        if check.get('expect') and check['expect'] not in text:
            problems.append('did not open: no log line with %r' % check['expect'])
        problems += ['%s: %s' % item for item in scan(text)]
        return {'name': check['name'], 'ok': not problems, 'problems': problems, 'contrast': spread}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('names', nargs='*', help='only these checks')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--settle', type=float, default=SETTLE, help='seconds each page gets to draw')
    args = parser.parse_args(argv)
    if args.list:
        for check in CHECKS:
            print(check['name'])
        print('not covered:')
        for line in NOT_COVERED:
            print(' -', line)
        return 0
    chosen = [c for c in CHECKS if not args.names or c['name'] in args.names]
    unknown = set(args.names) - {c['name'] for c in CHECKS}
    if unknown:
        print('unknown check:', ', '.join(sorted(unknown)))
        return 2
    runner = Runner(load_rig())
    runner.ensure_running()
    results = []
    for check in chosen:
        result = runner.run(check, args.settle)
        results.append(result)
        print('%-4s %-16s %s' % ('ok' if result['ok'] else 'FAIL', result['name'], '; '.join(result['problems'])))
    report = {'results': results, 'not_covered': list(NOT_COVERED), 'evidence': 'desktop Kodi rig, not the iPhone'}
    (runner.out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    failed = [r['name'] for r in results if not r['ok']]
    print('%d of %d checks passed%s' % (len(results) - len(failed), len(results), '; failed: ' + ', '.join(failed) if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
