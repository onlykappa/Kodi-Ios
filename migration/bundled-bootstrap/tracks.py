"""Video controls › Subtitles (CC) and Audio (waveform): the owner-approved menus (mockup
docs/design/player-subtitles-audio-mockups.html, round 2) instead of Kodi's settings dialogs.

RunScript(service.kodi.ios.bootstrap,tracks,subtitles|audio) opens 1080i/IOSTrackMenu.xml (pages.track_menu) over the
video. Tap a track to switch (the menu closes and a notice says what is on). Subtitles has Download and apply: one tap
finds subtitles for this video in the owner's language on Podnapisi, downloads and turns them on (track_menu.py). More
holds Choose another (the other results), Add from a file and Use for all videos. Timing and Volume boost use Kodi's
own subtitle delay, audio delay and volume amplification."""
import json
import os
import sys
import threading
import time
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import track_menu as tm
import subtitle_match as sm

BACK = (9, 10, 92, 110)
CLOSE, MORE, CTA, LIST, T_MINUS, T_PLUS, B_MINUS, B_PLUS = 9500, 9501, 9510, 9310, 9401, 9402, 9403, 9404
# The Subtitles drawer (owner, 2026-11-16): its own list and timing buttons; holding a track opens a menu (Find another / Remove).
SUBS_LIST, T_MINUS_S, T_PLUS_S = 9312, 9405, 9406
HOLD_FIND, HOLD_REMOVE, HOLD_SCRIM, SURE_SCRIM, SURE_CANCEL, SURE_REMOVE = 9601, 9602, 9690, 9691, 9611, 9612
LONG = (101, 117, 10)   # a long press on the phone arrives as 101 / 117, and as 10 (Back) first; see favourites_page.onAction
SUBS_ROWS = 5
SPEED_LIST = 9311   # board 02: Playback speed's own six-row list
BACK_LINK = 9502    # board 02: the sub-page's back link in the header (owner log 89a98e5b: named BACK, it
                    # replaced the back actions above and every key press in the menu raised a TypeError)
FIELDS = ['subtitles', 'currentsubtitle', 'subtitleenabled', 'audiostreams', 'currentaudiostream']
UA = 'KodiIOS/1.0'



def continue_known(it, read, now=time.time):
    """What Continue Watching knows about the video it started (show, season, episode, year, TMDb id), when Kodi's own item lacks them and the title agrees.
    Owner, build 639 log 9f7b4ab2: an Umbrella episode played as 'Episode 8' with no show, so SubDL was asked for 'Episode 8' with no season or episode and
    returned some other show's subtitle. {} when nothing agrees."""
    try:
        data = json.loads(read('special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json') or '{}')
        entry = (data.get('items') or {}).get(data.get('current')) or {}
        if not entry or now() - float(entry.get('played') or 0) > 6 * 3600:
            return {}
        names = {str(it.get('title') or '').lower(), str(it.get('showtitle') or '').lower(), str(it.get('label') or '').lower()} - {''}
        mine = {str(entry.get('title') or '').lower(), str(entry.get('tvshowtitle') or '').lower()} - {''}
        if not names & mine:
            return {}
        movie = entry.get('kind') == 'movie'
        return {'kind': 'movie' if movie else 'episode', 'title': entry.get('title') or '', 'show': '' if movie else entry.get('tvshowtitle') or '',
                'season': entry.get('season'), 'episode': entry.get('episode'), 'year': entry.get('year') or None, 'tmdb': entry.get('tmdb_id') or None}
    except Exception:
        return {}

def external(stream):
    """True for a subtitle file Kodi was handed (its stream name ends '(External)'): a download or a file the viewer added."""
    return str(stream.get('name') or '').rstrip().endswith('(External)')


def external_file(folder, name):
    """The file this app downloaded for Kodi's '<crc> (External)' stream (the file is '<crc>.<lang>.<ext>'), or None."""
    import glob
    stem = str(name or '').replace('(External)', '').strip()
    if not stem.isdigit():
        return None
    found = sorted(glob.glob(os.path.join(folder, stem + '.*')))
    return found[0] if found else None


def rpc(xbmc, method, params=None):
    answer = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}})))
    return answer.get('result')


def player_id(xbmc):
    for p in rpc(xbmc, 'Player.GetActivePlayers') or []:
        if p.get('type') == 'video':
            return p['playerid']
    return None


def subtitle_language(xbmc):
    """The owner's subtitle download language (Kodi › Subtitles › Languages to download), as ('en', 'English')."""
    try:
        names = (rpc(xbmc, 'Settings.GetSettingValue', {'setting': 'subtitles.languages'}) or {}).get('value') or []
        name = names[0] if names else 'English'
    except Exception:
        name = 'English'
    code = ''
    try:
        code = xbmc.convertLanguage(name, xbmc.ISO_639_1)
    except Exception:
        pass
    return (code or 'en'), tm.language_name(code or 'en', name)


def http_get(url, headers=None):
    # Roadmap 2.13: the owner's DNS refuses the subtitle site; doh_fetch retries through DNS over HTTPS.
    import doh_fetch
    return doh_fetch.get(url, dict({'Accept': 'application/json', 'User-Agent': UA}, **(headers or {})))


def redact(text):
    import re
    return re.sub(r'(?i)(api[_-]?key=|Api-Key[\'"]?: ?[\'"]?|Bearer )[^&\s\'",)]+', r'\1…', str(text))


def http_post(url, body, headers=None):
    import urllib.request
    req = urllib.request.Request(url, data=body, headers=dict({'User-Agent': UA}, **(headers or {})), method='POST')
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def keys_folder(xbmcvfs):
    return xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')


def set_key(xbmcgui, xbmcvfs, name, log):
    """Subtitles › More › Subtitle keys › a row: the keyboard for that key; saved only on the phone."""
    import subtitle_sources as ss
    folder = keys_folder(xbmcvfs)
    keys = ss.load_keys(folder)
    label = dict(tm.KEY_ROWS).get(name, name)
    hidden = name == 'opensubtitles_password'
    value = xbmcgui.Dialog().input(label, '' if hidden else keys.get(name, ''), type=xbmcgui.INPUT_ALPHANUM,
                                   option=xbmcgui.ALPHANUM_HIDE_INPUT if hidden else 0)
    keys[name] = (value or '').strip()
    ss.save_keys(folder, keys)
    log('subtitle keys: %s %s' % (name, 'set' if keys[name] else 'cleared'))   # never the value


def file_roots(xbmc, xbmcvfs):
    """Where subtitle files are looked for: the app's Documents (Files app), its Inbox (AirDrop / Share), Kodi Downloads,
    Elementum's folder, and the folder of the video playing when it is on the phone."""
    from pathlib import Path
    home = Path(xbmcvfs.translatePath('special://home/'))
    docs = next((p for p in (home, *home.parents) if p.name == 'Documents'), home.parent)
    roots = [str(docs / 'Inbox'), str(docs / 'Kodi Downloads'), str(docs / 'Elementum Download'), str(docs)]
    playing = xbmc.getInfoLabel('Player.Folderpath')
    if playing.startswith('/'):
        roots.insert(0, playing)
    return [r for r in roots if os.path.isdir(r)]


def keys_tag(xbmcvfs):
    import subtitle_sources as ss
    keys = ss.load_keys(keys_folder(xbmcvfs))
    names = [n for n, k in (('SubDL', 'subdl'), ('OpenSubtitles', 'opensubtitles')) if keys[k]]
    return ' + '.join(names).upper() if names else 'NOT SET'


def run(mode):
    import xbmc
    import xbmcgui
    import xbmcvfs
    pid = player_id(xbmc)
    if pid is None:
        return
    # Owner log 20b1ca76: an error message carried the SubDL key into kodi.log; keys never reach the log.
    log = lambda m: xbmc.log('Kodi iOS tracks: ' + redact(m), xbmc.LOGINFO)
    lang, lang_name = subtitle_language(xbmc)
    folder = xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/subtitles/')   # build 634 log f75957fe: special://temp is emptied at every start, so a download was lost
    LIST_ID = SUBS_LIST if mode == 'subtitles' else LIST   # the drawer has a taller list of its own

    class Menu(xbmcgui.WindowXMLDialog):
        closed = False

        def close(self):
            xbmcgui.Window(10000).clearProperty('KodiIOS.TrackMenu')   # Kodi's own offset slider may show again
            # Roadmap B.8: a search or download thread could still set a property after the menu closed
            # ("EXCEPTION: Window id does not exist"); those updates are skipped once it is closed.
            self.closed = True
            xbmcgui.WindowXMLDialog.close(self)

        def setProperty(self, key, value):
            if not self.closed:
                xbmcgui.WindowXMLDialog.setProperty(self, key, value)

        def onInit(self):
            # Owner (2026-11-12): Timing − / + opened Kodi's "Subtitle offset" slider over the video; the menu's own
            # row shows the value, so the slider is hidden while the menu is open (pages.slider_quiet).
            xbmcgui.Window(10000).setProperty('KodiIOS.TrackMenu', 'open')
            self.rows, self.results, self.added = [], [], set()
            self.track_evidence, self.auto_chosen = {}, False
            self.hidden, self.paths, self.held = set(), {}, None   # removed tracks, files this menu downloaded, the row held
            self.file_tracks, self.names = [], {}   # the subtitle tracks the MP4 itself holds (log_file_tracks), stream names by index
            self.lang, self.lang_name, self.from_hold = lang, lang_name, False
            self.page = 'tracks'
            self.setProperty('mode', mode)
            self.setProperty('title', {'subtitles': 'Subtitles', 'speed': 'Playback speed'}.get(mode, 'Audio'))
            self.state('idle')
            self.fill()
            self.timing()
            # Roadmap 2.14: the list is empty until fill(), so the window opens on Close and moves here once filled.
            self.setFocusId(SPEED_LIST if mode == 'speed' else LIST_ID)

        def missing(self, name):
            # Nothing found or no answer while no subtitle key is saved: say how to add one (Podnapisi is gone).
            return 'nokey' if keys_tag(xbmcvfs) == 'NOT SET' else name

        def state(self, name):
            self.setProperty('cta_state', 'busy' if name in ('search', 'download') else 'error' if name == 'nokey' else name)
            self.setProperty('cta', tm.cta(name, self.lang_name))
            self.setProperty('hint', tm.note(name, self.lang_name) or
                             {'idle': 'Finds %s subtitles for this video' % self.lang_name, 'search': 'Matching this exact version of the video',
                              'download': 'Matching this exact version of the video', 'done': 'Wrong one? More › Choose another'}.get(name, ''))

        def fill(self, focus_on=True):
            if self.closed:
                return
            p = {} if mode == 'speed' else (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': FIELDS}) or {})
            page = getattr(self, 'page', 'tracks')
            if mode == 'speed':
                self.rows = tm.speed_rows(xbmc.getInfoLabel('Player.PlaySpeed'))
            elif mode == 'subtitles' and page == 'more':
                shown = [r for r in tm.subtitle_rows(*self.subtitle_streams()) if r['on'] and r['index'] is not None]
                self.rows = tm.more_rows(len(self.results), self.always_on(), keys_tag(xbmcvfs),
                                         shown[0]['label'] if shown else '', bool(shown and shown[0].get('removable')))
            elif mode == 'subtitles' and page == 'choose':
                self.rows = tm.result_rows(self.results)
            elif mode == 'subtitles' and page == 'keys':
                import subtitle_sources as ss
                self.rows = tm.keys_rows(ss.load_keys(keys_folder(xbmcvfs)))
            elif mode == 'subtitles' and page == 'files':
                self.rows = tm.file_rows(getattr(self, 'files', []))
            elif mode == 'subtitles':
                cur = (p.get('currentsubtitle') or {}).get('index')
                subs = self.with_evidence(p.get('subtitles') or [])
                video = self.video()
                if not self.auto_chosen:
                    self.auto_chosen = True
                    chosen = sm.preferred(tm.pick(subs, video), cur, p.get('subtitleenabled'), video)   # only the streams the menu shows
                    if any(s.get('index') == cur and s.get('downloaded') for s in subs):
                        chosen = cur   # a subtitle the viewer downloaded is never swapped for an embedded one by opening the menu
                    if p.get('subtitleenabled') and chosen != cur:
                        rpc(xbmc, 'Player.SetSubtitle', {'playerid': pid, 'subtitle': chosen if chosen is not None else 'off',
                                                       'enable': chosen is not None})
                        cur = chosen
                        p['subtitleenabled'] = chosen is not None
                if not getattr(self, 'logged_streams', False):
                    self.logged_streams = True   # what Kodi offers for this video, so a log shows why a track is or is not there
                    log('streams: %s' % '; '.join('#%s %s%s%s%s' % (s.get('index'), s.get('language') or '?', ' "%s"' % s['name'] if s.get('name') else '',
                                                                   ' forced' if s.get('isforced') else '', ' sdh' if s.get('isimpaired') else '') for s in (p.get('subtitles') or [])) + ' | on #%s' % cur)
                    threading.Thread(target=self.log_file_tracks, daemon=True).start()
                self.rows = tm.subtitle_rows(subs, cur, p.get('subtitleenabled'), video)
            else:
                self.rows = tm.audio_rows(p.get('audiostreams'), (p.get('currentaudiostream') or {}).get('index'))
            items = []
            for n, r in enumerate(self.rows):
                li = xbmcgui.ListItem(r['label'])
                li.setProperty('tag', r['tag'])
                li.setProperty('on', 'true' if r['on'] else '')
                li.setProperty('new', 'true' if r['tag'] == 'NEW' else '')
                li.setProperty('danger', 'true' if r.get('danger') else '')   # Remove is red
                li.setProperty('sep', 'true' if n < len(self.rows) - 1 else '')
                # Backend evidence for the approved menu; its layout is wired separately.
                for key in ('match_reason', 'match_score', 'match_rejected', 'match_timing_checked', 'match_offset_s'):
                    value = r.get(key)
                    li.setProperty(key, str(value).lower() if isinstance(value, bool) else '' if value is None else str(value))
                items.append(li)
            self.setProperty('rows', str(max(1, min(6 if mode == 'speed' else SUBS_ROWS if mode == 'subtitles' else 3, len(self.rows)))))   # the cards and the menu fit the rows shown
            lst = self.getControl(SPEED_LIST if mode == 'speed' else LIST_ID)
            lst.reset()
            lst.addItems(items)
            if focus_on:
                on = next((n for n, r in enumerate(self.rows) if r['on']), 0)
                lst.selectItem(on)

        def timing(self):
            self.setProperty('timing', tm.seconds_text(xbmc.getInfoLabel('Player.SubtitleDelay' if mode == 'subtitles' else 'Player.AudioDelay'),
                                                       's' if mode == 'subtitles' else 'ms'))
            self.setProperty('boost', tm.boost_text(self.boost_now()))

        def boost_key(self):
            import zlib   # hash() of a str changes between interpreter runs
            return 'KodiIOS.Boost.%08x' % zlib.crc32(xbmc.getInfoLabel('Player.Filenameandpath').encode('utf-8', 'replace'))

        def boost_now(self):
            try:
                return int(xbmcgui.Window(10000).getProperty(self.boost_key()) or 0)
            except ValueError:
                return 0

        def pick(self, n):
            r = self.rows[n]
            if getattr(self, 'page', 'tracks') != 'tracks':
                self.pick_more(r)
                return
            if mode == 'speed':
                answer = rpc(xbmc, 'Player.SetTempo', {'playerid': pid, 'tempo': r['index']})
                said = 'Speed %s' % r['label'] if answer is not None else 'This video cannot change speed'
                log(said)
                self.fill()
                xbmc.sleep(300)
                self.close()
                xbmcgui.Dialog().notification(said, '', xbmcgui.NOTIFICATION_INFO, 2000, False)
                return
            if mode == 'subtitles':
                if r.get('match_rejected'):
                    self.setProperty('hint', r['match_reason'])
                    return
                if r['index'] is None:
                    rpc(xbmc, 'Player.SetSubtitle', {'playerid': pid, 'subtitle': 'off'})
                    said = 'Subtitles off'
                else:
                    rpc(xbmc, 'Player.SetSubtitle', {'playerid': pid, 'subtitle': r['index'], 'enable': True})
                    said = '%s subtitles on' % r['label']
            else:
                rpc(xbmc, 'Player.SetAudioStream', {'playerid': pid, 'stream': r['index']})
                said = 'Audio: %s' % r['label']
            log(said)
            if mode == 'subtitles' and r.get('index') is not None:
                # Build 622 (owner: captions "on" and nothing drawn): what Kodi itself says a moment later, so "on but not drawn" and "never turned on" differ.
                def report():
                    try:
                        xbmc.sleep(2500)
                        got = rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitleenabled', 'currentsubtitle']}) or {}
                        shown = xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled')
                        current = got.get('currentsubtitle') or {}
                        log('Kodi says subtitles enabled=%s (info %s), current #%s %s %s' % (got.get('subtitleenabled'), shown, current.get('index'),
                                                                                           current.get('language') or '?', current.get('name') or ''))
                    except Exception as error:
                        log('subtitle check not read (%s)' % type(error).__name__)
                threading.Thread(target=report, daemon=True).start()
            self.fill()
            xbmc.sleep(300)
            self.close()
            xbmcgui.Dialog().notification(said, '', xbmcgui.NOTIFICATION_INFO, 2000, False)

        def item(self):
            it = rpc(xbmc, 'Player.GetItem', {'playerid': pid, 'properties': ['title', 'showtitle', 'year', 'season', 'episode', 'file', 'uniqueid']}) or {}
            return it.get('item') or {}

        def video(self):
            it = self.item()
            name = os.path.basename(str(it.get('file') or '').split('?')[0].split('|')[0])
            guess = tm.from_release(name) or tm.from_release(it.get('title')) or {}
            try:
                duration = xbmc.Player().getTotalTime()
            except Exception:
                duration = 0
            try:   # ISSUE-339: a dub with the original language's audio beside it
                a = rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['audiostreams', 'currentaudiostream']}) or {}
                dubbed = sm.dubbed(a.get('audiostreams'), a.get('currentaudiostream'), self.lang)
            except Exception:
                dubbed = False
            return {'filename': name, 'duration': duration, 'language': self.lang, 'dubbed': dubbed,
                    'season': it.get('season') if it.get('season') is not None and it['season'] >= 0 else guess.get('season'),
                    'episode': it.get('episode') if it.get('episode') is not None and it['episode'] > 0 else guess.get('episode')}

        def checked_video(self):
            """video() plus the words heard in it (ISSUE-347), for checking a download against the speech."""
            video = self.video()
            try:
                import speech_check
                video['heard'] = speech_check.for_playing(xbmc, xbmcgui, xbmcvfs, video, log)
            except Exception as error:
                log('speech check: skipped (%s)' % type(error).__name__)
            return video

        def with_evidence(self, streams):
            # A track this menu downloaded or added from a file can be removed; one inside the video file cannot.
            # Owner, 2026-11-20 (build 617 log): a downloaded subtitle was forgotten the moment the menu closed (this object is new on every open), so the
            # next open saw it as an ordinary English track, ranked the embedded CC above it and switched Kodi to that, turning the download off. Kodi names
            # every file it was handed "<file> (External)": those are the viewer's, wherever this menu instance learned of them.
            gone = set(filter(None, xbmcgui.Window(10000).getProperty('KodiIOS.SubsRemoved').split('|')))
            embedded = [s for s in streams if not external(s)]
            sized = {}
            if self.file_tracks and len(self.file_tracks) == len(embedded):   # the file's tracks come in the order Kodi numbers its own
                for stream, track in zip(sorted(embedded, key=lambda s: s.get('index') or 0), self.file_tracks):
                    if track.get('samples') is not None:
                        sized[stream.get('index')] = track['samples']
            out = []
            for s in streams:
                index, mine = s.get('index'), external(s)
                self.names[index] = s.get('name') or ''
                if index in self.hidden or (mine and s.get('name') in gone):
                    continue
                extra = {} if index not in sized else {'sample_count': sized[index]}
                out.append(dict(s, downloaded=index in self.added or mine, removable=index in self.added or index in self.track_evidence or mine,
                                **extra, **self.track_evidence.get(index, {})))
            return out

        def played(self, it):
            """What the add-on that started this video knew about it (show, season, episode, year, TMDb id of the show), when Kodi's own item lacks it and the
            title agrees. Owner, build 618 log: a Drive episode searched as 'Trust Fall' with no season or episode, and SubDL found nothing."""
            try:
                known = json.loads(xbmcgui.Window(10000).getProperty('KodiIOS.Playing') or '{}')
                if time.time() - float(known.get('t') or 0) > 6 * 3600:
                    return {}
                names = {str(it.get('title') or '').lower(), str(it.get('showtitle') or '').lower(), str(it.get('label') or '').lower()} - {''}
                if names & {str(known.get('title') or '').lower(), str(known.get('show') or '').lower()}:
                    return known
            except Exception:
                pass
            try:   # a stream Continue Watching follows (Umbrella): Kodi's item says only 'Episode 8' (build 639 log 9f7b4ab2: the search had no show, season or episode)
                def read(path):
                    f = xbmcvfs.File(path)
                    try:
                        return f.read()
                    finally:
                        f.close()
                return continue_known(it, read)
            except Exception:
                return {}
            return {}

        def search(self):
            it = self.item()
            show = it.get('showtitle')
            season, episode = it.get('season'), it.get('episode')
            extra = self.played(it)
            show_tmdb = None
            if extra and extra.get('kind') != 'movie':
                if not show:
                    show = extra.get('show') or None
                try:
                    if season is None or season < 0:
                        season = int(extra.get('season')) if str(extra.get('season') or '').isdigit() else season
                    if episode is None or episode <= 0:
                        episode = int(extra.get('episode')) if str(extra.get('episode') or '').isdigit() else episode
                except (TypeError, ValueError):
                    pass
                show_tmdb = extra.get('tmdb') or None
            elif extra and not it.get('year'):
                it = dict(it, year=extra.get('year') or it.get('year'))
            title = show or it.get('title') or it.get('label') or ''
            name = os.path.basename(str(it.get('file') or '').split('?')[0].split('|')[0])
            # Roadmap B.5 (build 232): a copy played without details searched its file name; read show and episode
            # from the release name ('phony.s01e01.1080p…' -> 'phony', 1, 1) when Kodi has none.
            guess = tm.from_release(title) if not show else None
            year = it.get('year') or None
            if guess:
                title, show, season, episode = guess['title'], guess['title'], guess['season'], guess['episode']
            elif not show:
                movie = tm.movie_from_release(title)
                if movie and (not year or str(year) == str(movie['year']) or title == name):
                    title, year = movie['title'], movie['year']
            ep = (season, episode) if show and (season or -1) >= 0 and (episode or -1) > 0 else (None, None)
            import subtitle_sources as ss
            keys = ss.load_keys(keys_folder(xbmcvfs))
            self.episode = ep
            tmdb = (it.get('uniqueid') or {}).get('tmdb') if not ep[0] else show_tmdb
            log('search %s %r %s S%sE%s via %s' % (self.lang, title, year, ep[0], ep[1], ', '.join(ss.sources(keys))))
            video = self.video()
            return sm.rank(ss.find(http_get, keys, self.lang, title, year, ep[0], ep[1], name, tmdb,
                                   log=lambda m: log('subtitles ' + m), dubbed=video.get('dubbed')), video)

        def fetch_result(self, result):
            import subtitle_sources as ss
            ep = getattr(self, 'episode', (None, None))
            return ss.fetch(http_get, http_post, ss.load_keys(keys_folder(xbmcvfs)), result, ep[0], ep[1])

        def apply(self, result, got=None):
            if got is None:
                result, name, data = sm.choose_download([result], self.fetch_result, self.checked_video())
                got = (name, data)
            name, data = got
            os.makedirs(folder, exist_ok=True)
            # Owner log 20b1ca76: SubDL's id is its download path ('/subtitle/…zip?…'), which made an absolute, missing
            # path; the file is named by a hash of the id.
            path = os.path.join(folder, '%s.%s.%s' % (zlib.crc32(str(result['id']).encode('utf-8')) & 0xffffffff, self.lang,
                                                      name.rsplit('.', 1)[-1].lower()))
            with open(path, 'wb') as f:
                f.write(data)
            before = {s.get('index') for s in (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []}
            xbmc.Player().setSubtitles(path)
            xbmc.sleep(400)
            after = (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []
            added = {s.get('index') for s in after} - before
            self.added |= added
            try:   # this video's subtitle from now on, put back on when it starts again (subtitle_memory.py)
                import subtitle_memory
                subtitle_memory.remember(folder, subtitle_memory.identity(xbmc.getInfoLabel, xbmc.Player().getPlayingFile()), path, name, self.lang)
            except Exception as error:
                log('subtitle memory: not kept (%s)' % type(error).__name__)
            for index in added:
                self.paths[index] = path
                self.track_evidence[index] = {'filename': name, 'cues': sm.cue_times(data, name), 'language': self.lang}
            log('applied %s (%d bytes, speech %s%s)' % (result['id'], len(data), result.get('match_speech') or 'not checked',
                                                        ', shifted %+.1f s' % result['match_speech_shift'] if result.get('match_speech_shift') else ''))

        def download_and_apply(self, result=None):
            try:
                if result is None:
                    self.state('search')
                    self.results = self.search()
                    if not self.results:
                        self.state(self.missing('none'))
                        log('nothing found')
                        return
                self.state('download')
                # Owner, 2026-11-20 (build 616 log): Download and apply took 58 s, nearly all of it listening to two 45 s stretches of the video's
                # sound over Drive (96 MB of a 4K file) for a check that heard 9 words and made no claim. The subtitle that fits the video's length and
                # episode is applied at once; the words check runs afterwards and only then corrects the timing or swaps it.
                candidates = list(self.results if result is None else [result])
                selected, name, data = sm.choose_download(candidates, self.fetch_result, self.video())
                self.apply(selected, (name, data))
                self.state('done')
                self.fill()
                xbmcgui.Dialog().notification('%s subtitles on' % self.lang_name, '', xbmcgui.NOTIFICATION_INFO, 2000, False)
                threading.Thread(target=self.check_by_speech, args=(selected, name, data, candidates, self.lang_name), daemon=True).start()
            except Exception as error:
                log('download and apply failed: %s: %s' % (type(error).__name__, error))
                self.state(self.missing('error'))
                if isinstance(error, sm.Mismatch):
                    self.setProperty('hint', str(error))
            finally:
                self.reset_language()

        def log_file_tracks(self):
            """What kind of subtitle tracks the playing MP4 carries (tx3g text Kodi draws; wvtt, stpp or c608 it may not), read from the first MB of the
            file through the app's own proxy (the playback cache already holds it). One log line, for diagnosis."""
            try:
                url = str(xbmc.Player().getPlayingFile() or '').split('|')[0]
                if not url.startswith('http://127.0.0.1:'):
                    return
                import mp4_tracks
                request = urllib.request.Request(url, headers={'Range': 'bytes=0-1048575'})
                with urllib.request.urlopen(request, timeout=3) as response:
                    head = response.read(1048576)
                    total = int(str(response.headers.get('Content-Range') or '').rpartition('/')[2] or 0)
                self.file_tracks = mp4_tracks.subtitle_tracks(head)
                picture = None
                if self.file_tracks and all(t.get('samples') is None for t in self.file_tracks) and total > 1048576:
                    # A fragmented file counts no samples in its moov: its fragment index (the last bytes) says how many fragments hold each track.
                    try:
                        def get(first, last):
                            with urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % (first, last)}), timeout=3) as r:
                                return r.read(last - first + 2)
                        tail = get(total - 16, total - 1)
                        size = int.from_bytes(tail[-4:], 'big') if tail[-12:-8] == b'mfro' else 0
                        if 24 <= size <= 2 * 1024 * 1024:
                            index = get(total - size, total - 1)
                            mp4_tracks.with_fragment_counts(self.file_tracks, mp4_tracks.fragment_counts(index))
                            spans = mp4_tracks.fragment_spans(index, mp4_tracks.track_timescales(head))   # where the cues sit against the video (ISSUE-424)
                            mp4_tracks.with_spans(self.file_tracks, spans)
                            picture = mp4_tracks.video_span(self.file_tracks, spans)
                            try:   # what the first fragments hold for each subtitle track: text or only blanks, and when (ISSUE-424: the cues exist, so are they readable?)
                                scales = mp4_tracks.track_timescales(head)
                                entries = mp4_tracks.fragment_entries(index, 3)
                                first = next((t['id'] for t in self.file_tracks if len(entries.get(t['id'], ())) > 1), None)
                                cues = {t['id']: [] for t in self.file_tracks}
                                raw = {t['id']: [] for t in self.file_tracks}
                                for when, offset in entries.get(first, ()):
                                    found = mp4_tracks.moof_samples(get(offset, offset + 262143), offset, scales)
                                    for t in self.file_tracks:
                                        cues[t['id']].append('%d s: %s' % (round(when / scales.get(first, 1)), mp4_tracks.cue_summary(found.get(t['id'], []))))
                                        raw[t['id']].extend(found.get(t['id'], []))
                                if first is not None:
                                    log('file subtitle cues: ' + '; '.join('#%s [%s]' % (k, ' | '.join(v)) for k, v in cues.items()))
                                    # Build 634 log f75957fe: every text cue of these tracks has no length, so Kodi reports the track on and draws nothing: such a track
                                    # is left out of the menu like an empty one, and is not shown as "on" (the existing rule below turns subtitles off)
                                    flat = [t['id'] for t in self.file_tracks if mp4_tracks.zero_length(raw[t['id']])]
                                    for t in self.file_tracks:
                                        if t['id'] in flat:
                                            t['samples'] = 0
                                    if flat:
                                        log('file subtitle tracks with cues that have no length (hidden, they would show nothing): %s' % ', '.join('#%s' % i for i in flat))
                            except Exception as error:
                                log('file subtitle cues: not read (%s)' % type(error).__name__)
                    except Exception as error:
                        log('file subtitle tracks: fragment index not read (%s)' % type(error).__name__)
                log('file subtitle tracks: %s' % mp4_tracks.describe(self.file_tracks, picture))
                if any(t.get('samples') is not None and t['samples'] <= 1 for t in self.file_tracks) and not self.closed:
                    self.fill(focus_on=False)   # an empty embedded track is now known: the list drops it
            except Exception as error:
                log('file subtitle tracks: not read (%s)' % type(error).__name__)

        def check_by_speech(self, selected, name, data, candidates, language):
            """After the subtitle is already on: listen to the video (slow, off the page's thread). A clear mismatch swaps it for the next candidate; a shift
            of 0.4 s or more is taken out and the file applied again; too few words to say anything leaves it alone."""
            try:
                video = self.checked_video()
                heard = video.get('heard')
                if not heard:
                    log('speech check: nothing to compare, subtitles kept as applied')
                    return
                import speech_check
                tested = sm.annotate(dict(selected, filename=name, data=data), video)
                fixed, why = speech_check.apply(selected, tested, data, name, heard)
                log('speech check: %d words heard, this subtitle: %s' % (len(heard), speech_check.describe(selected)))
                if not why and selected.get('match_speech') == 'unknown':
                    # The words cannot say whether this subtitle is for this video: try the next few results and keep one the speech supports.
                    others = [r for r in candidates if r.get('id') != selected.get('id')][:3]
                    files = []
                    for other in others:
                        try:
                            files.append(sm.choose_download([other], self.fetch_result, video))
                        except Exception:
                            continue
                    best = speech_check.best_fit(heard, files)
                    if best:
                        selected2, name2, data2, how, seconds = best
                        log('speech check: a better supported subtitle among %d others (%s)' % (len(files), how))
                        if how == 'shift':
                            data2 = speech_check.shift_file(data2, name2, seconds)
                        self.apply(selected2, (name2, data2))
                        xbmcgui.Dialog().notification('Better-matched %s subtitles on' % language, '', xbmcgui.NOTIFICATION_INFO, 3000, False)
                        return
                    log('speech check: none of %d others is better supported; subtitles kept as applied' % len(files))
                if why:
                    others = [r for r in candidates if r.get('id') != selected.get('id')]
                    log('speech check: %s; trying %d other subtitle(s)' % (why, len(others)))
                    selected2, name2, data2 = sm.choose_download(others, self.fetch_result, video)
                    self.apply(selected2, (name2, data2))
                    xbmcgui.Dialog().notification('Better-timed %s subtitles on' % language, '', xbmcgui.NOTIFICATION_INFO, 3000, False)
                elif fixed is not data:
                    self.apply(selected, (name, fixed))
                    xbmcgui.Dialog().notification('%s subtitle timing adjusted' % language, '', xbmcgui.NOTIFICATION_INFO, 3000, False)
            except Exception as error:
                log('speech check: skipped (%s: %s)' % (type(error).__name__, error))

        def always_on(self):
            try:
                cur = (rpc(xbmc, 'Settings.GetSettingValue', {'setting': 'locale.subtitlelanguage'}) or {}).get('value') or ''
            except Exception:
                cur = ''
            return cur not in ('', 'default', 'original', 'none', 'forced_only')

        def more(self, page='more'):
            # Roadmap B.6 (owner, build 232 screenshot): More opened Kodi's select box over the menu. Its choices and
            # the found subtitles are now rows in this list, with a back row on top.
            self.page = page
            # Board 02: a sub-page shows a blue back link in the header instead of the title (pages.track_menu).
            self.setProperty('page', '' if page == 'tracks' else page)
            self.setProperty('back', {'more': '\u2039 Subtitles', 'choose': '\u2039 Subtitles' if self.from_hold else '\u2039 More', 'keys': '\u2039 More', 'files': '\u2039 More'}.get(page, ''))
            self.fill()
            self.setFocusId(LIST_ID)

        def pick_more(self, r):
            what = r['index']
            if what == 'back':
                self.more('tracks')
            elif what == 'more':
                self.more('more')
            elif what == 'choose':
                if not self.results:
                    self.state('search')
                    try:
                        self.results = self.search()
                    except Exception as error:
                        log('search failed: %s' % error)
                        self.state(self.missing('error'))
                        return
                if not self.results:
                    self.state(self.missing('none'))
                    return
                self.state('idle')
                self.more('choose')
            elif what == 'remove':
                shown = [x for x in tm.subtitle_rows(*self.subtitle_streams()) if x['on'] and x['index'] is not None]
                if shown:
                    self.ask_remove(shown[0])
            elif what == 'file':
                self.files = tm.subtitle_files(file_roots(xbmc, xbmcvfs))
                self.more('files')
            elif isinstance(what, str) and what.startswith('sub:'):
                path = self.files[int(what[4:])]
                try:
                    with open(path, 'rb') as source:
                        data = source.read(8 * 1024 * 1024 + 1)
                    if len(data) > 8 * 1024 * 1024:
                        raise sm.Mismatch('Subtitle file is too large to check')
                    evidence = {'filename': os.path.basename(path), 'data': data}
                    match = sm.assess(evidence, self.video())
                    if match['rejected']:
                        raise sm.Mismatch(match['reason'])
                except (OSError, sm.Mismatch) as error:
                    self.setProperty('hint', str(error))
                    return
                before = {s.get('index') for s in (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []}
                xbmc.Player().setSubtitles(path)
                log('subtitle file turned on: %s' % os.path.basename(path))
                xbmc.sleep(400)
                after = (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []
                for stream in after:
                    if stream.get('index') not in before:
                        self.track_evidence[stream['index']] = {'filename': os.path.basename(path), 'cues': sm.cue_times(data, path)}
                self.more('tracks')
            elif what == 'nofiles':
                pass
            elif isinstance(what, str) and what.startswith('key:'):
                set_key(xbmcgui, xbmcvfs, what[4:], log)
                self.results = []
                self.fill()
            elif what == 'keys':
                self.more('keys')
            elif what == 'always':
                tracks_now = [x for x in tm.subtitle_rows(*self.subtitle_streams()) if x['on'] and x['index'] is not None]
                value = 'default' if self.always_on() else (tracks_now[0]['label'] if tracks_now else lang_name)
                rpc(xbmc, 'Settings.SetSettingValue', {'setting': 'locale.subtitlelanguage', 'value': value})
                log('use for all videos: %s' % value)
                self.fill()
            elif isinstance(what, int) and 0 <= what < len(self.results):
                self.page = 'tracks'
                self.setProperty('page', '')   # back to the tracks: the title again, not the back link
                self.setProperty('back', '')
                threading.Thread(target=self.download_and_apply, args=(self.results[what],), daemon=True).start()

        def subtitle_streams(self):
            p = rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': FIELDS}) or {}
            subs = self.with_evidence(p.get('subtitles') or [])
            return subs, (p.get('currentsubtitle') or {}).get('index'), p.get('subtitleenabled')

        def onClick(self, control):
            if control == CLOSE:
                self.close()
            elif control == BACK_LINK:   # the sub-page's back link: Find another -> More -> the tracks (from a hold: straight to the tracks)
                if self.page == 'choose' and self.from_hold:
                    self.reset_language()
                    self.state('idle')
                    self.more('tracks')
                else:
                    self.more('more' if self.page in ('choose', 'keys', 'files') else 'tracks')
            elif control in (HOLD_SCRIM, SURE_SCRIM):
                if control == HOLD_SCRIM:
                    self.end_hold()
            elif control == HOLD_FIND and self.held:
                row = self.held
                self.end_hold()
                threading.Thread(target=self.find_another, args=(row,), daemon=True).start()
            elif control == HOLD_REMOVE and self.held and self.held.get('removable'):   # a track inside the video file is never removed
                self.ask_remove(self.held)
            elif control == SURE_CANCEL:
                self.end_hold()
            elif control == SURE_REMOVE:
                self.do_remove()
            elif control in (LIST_ID, SPEED_LIST):
                n = self.getControl(control).getSelectedPosition()
                if 0 <= n < len(self.rows):
                    self.pick(n)
            elif control == CTA:
                if self.getProperty('cta_state') != 'busy':
                    threading.Thread(target=self.download_and_apply, daemon=True).start()
            elif control == MORE:
                self.more()
            elif control in (T_MINUS, T_PLUS, T_MINUS_S, T_PLUS_S):
                step = 'SubtitleDelay' if mode == 'subtitles' else 'AudioDelay'
                xbmc.executebuiltin('Action(%s%s)' % (step, 'Minus' if control in (T_MINUS, T_MINUS_S) else 'Plus'))
                xbmc.sleep(150)
                self.timing()
            elif control in (B_MINUS, B_PLUS):
                # Roadmap B.2 (owner, build 232: "i tap it and it disappears"): Kodi's own slider popped up over the
                # menu and the row showed no value. 3 dB a tap, Kodi's slider closed at once, the value in the row.
                new, actions = tm.boost_change(self.boost_now(), control == B_PLUS)
                for name in actions:
                    xbmc.executebuiltin('Action(%s)' % name)
                if actions:
                    xbmc.sleep(60)
                    xbmc.executebuiltin('Dialog.Close(slider,true)')
                    self.setFocusId(control)
                xbmcgui.Window(10000).setProperty(self.boost_key(), str(new))
                self.setProperty('boost', tm.boost_text(new))
                log('volume boost %s' % tm.boost_text(new))

        def onAction(self, action):
            code = action.getId()
            if mode == 'subtitles':
                # Holding a track (iOS sends 10, then 101/117): its menu, never Back; the rest of the same press does nothing.
                recent = time.time() - getattr(self, 'menu_done', 0) < 1.5
                if self.getProperty('ctx'):
                    if code in BACK and not recent:
                        self.end_hold()
                    return
                if code in LONG and self.page == 'tracks' and self.getFocusId() == SUBS_LIST:
                    if not recent:
                        n = self.getControl(SUBS_LIST).getSelectedPosition()
                        if 0 <= n < len(self.rows):
                            self.hold(n)
                    self.menu_done = time.time()
                    return
            if code in BACK:
                self.close()

        # --- hold a subtitle (docs/design/subtitles-manage-mockups.html) ---------------------------------------
        def hold(self, n):
            options = tm.hold_options(self.rows[n])
            if not options:
                return   # Off has no menu
            self.held = self.rows[n]
            self.setProperty('ctx.find', options[0])
            self.setProperty('ctx.remove', options[1])
            self.setProperty('ctx.row', str(min(n, SUBS_ROWS - 1)))
            self.setProperty('ctx', '1')
            self.setFocusId(HOLD_FIND)
            self.menu_done = time.time()

        def end_hold(self):
            for key in ('ctx', 'ctx.find', 'ctx.remove', 'sure.title', 'sure.text'):
                self.setProperty(key, '')
            self.setProperty('ctx.row', '0')
            self.held = None
            self.setFocusId(LIST_ID)

        def reset_language(self):
            if self.from_hold:
                self.results = []   # they were found for another language
            self.lang, self.lang_name, self.from_hold = lang, lang_name, False

        def find_another(self, row):
            """Hold > Find another: the other results for this track's language; picking one downloads it, the current one stays until then."""
            code = ''
            try:
                code = xbmc.convertLanguage(row.get('language') or '', xbmc.ISO_639_1)
            except Exception:
                pass
            self.lang, self.lang_name, self.from_hold, self.results = code or lang, row['label'], True, []
            try:
                self.state('search')
                self.results = self.search()
            except Exception as error:
                log('find another failed: %s: %s' % (type(error).__name__, error))
                self.state(self.missing('error'))
                self.reset_language()
                return
            if not self.results:
                self.state(self.missing('none'))
                self.reset_language()
                return
            self.state('idle')
            self.more('choose')

        def ask_remove(self, row):
            title, text = tm.sure_text(row)
            self.held = row
            self.setProperty('sure.title', title)
            self.setProperty('sure.text', text)
            self.setProperty('ctx', 'sure')
            self.setFocusId(SURE_CANCEL)

        def do_remove(self):
            row = self.held
            if not row:
                return
            index = row['index']
            if row.get('on'):
                rpc(xbmc, 'Player.SetSubtitle', {'playerid': pid, 'subtitle': 'off'})
            self.hidden.add(index)
            home_window = xbmcgui.Window(10000)
            home_window.setProperty('KodiIOS.SubsRemoved', '|'.join(filter(None, [home_window.getProperty('KodiIOS.SubsRemoved'), self.names.get(index, '')])))
            path = self.paths.pop(index, None) or external_file(folder, self.names.get(index, ''))
            if path and os.path.dirname(path) == os.path.dirname(os.path.join(folder, 'x')):   # only a file this menu downloaded
                try:
                    os.remove(path)
                except OSError:
                    pass
            try:
                import subtitle_memory
                subtitle_memory.forget(folder, subtitle_memory.identity(xbmc.getInfoLabel, xbmc.Player().getPlayingFile()))
            except Exception:
                pass
            log('removed subtitle %s' % row['label'])
            self.end_hold()
            if self.page != 'tracks':
                self.more('tracks')
            else:
                self.fill()
            xbmcgui.Dialog().notification('%s removed' % row['label'], '', xbmcgui.NOTIFICATION_INFO, 2000, False)

    home = HERE
    menu = Menu('IOSTrackMenu.xml', home, 'Default', '1080i')
    menu.doModal()
    del menu


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('subtitles', 'audio', 'speed') else 'subtitles')
