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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import track_menu as tm

BACK = (9, 10, 92, 110)
CLOSE, MORE, CTA, LIST, T_MINUS, T_PLUS, B_MINUS, B_PLUS = 9500, 9501, 9510, 9310, 9401, 9402, 9403, 9404
SPEED_LIST = 9311   # board 02: Playback speed's own six-row list
BACK_LINK = 9502    # board 02: the sub-page's back link in the header (owner log 89a98e5b: named BACK, it
                    # replaced the back actions above and every key press in the menu raised a TypeError)
FIELDS = ['subtitles', 'currentsubtitle', 'subtitleenabled', 'audiostreams', 'currentaudiostream']
UA = 'KodiIOS/1.0'


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


def http_post(url, body, headers=None):
    import urllib.request
    req = urllib.request.Request(url, data=body, headers=dict({'User-Agent': UA}, **(headers or {})), method='POST')
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def keys_folder(xbmcvfs):
    return xbmcvfs.translatePath('special://profile/addon_data/service.kodi.ios.bootstrap/')


def ask_keys(xbmcgui, xbmcvfs, log):
    """More › Subtitle keys: the free SubDL key and/or OpenSubtitles key (and account), saved only on the phone."""
    import subtitle_sources as ss
    folder = keys_folder(xbmcvfs)
    keys = ss.load_keys(folder)
    d = xbmcgui.Dialog()
    labels = ['SubDL key (subdl.com, free)', 'OpenSubtitles key (opensubtitles.com, free)',
              'OpenSubtitles username (optional)', 'OpenSubtitles password (optional)']
    while True:
        rows = ['%s: %s' % (label, 'set' if keys[k] else 'not set') for label, k in zip(labels, ss.KEY_NAMES)]
        pick = d.select('Subtitle keys', rows)
        if pick < 0:
            break
        k = ss.KEY_NAMES[pick]
        hidden = k == 'opensubtitles_password'
        value = d.input(labels[pick], '' if hidden else keys[k], type=xbmcgui.INPUT_ALPHANUM,
                        option=xbmcgui.ALPHANUM_HIDE_INPUT if hidden else 0)
        keys[k] = value.strip()
        ss.save_keys(folder, keys)
        log('subtitle keys: %s %s' % (k, 'set' if keys[k] else 'cleared'))   # never the value
    return keys


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
    log = lambda m: xbmc.log('Kodi iOS tracks: ' + m, xbmc.LOGINFO)
    lang, lang_name = subtitle_language(xbmc)
    folder = xbmcvfs.translatePath('special://temp/kodiios-subtitles/')

    class Menu(xbmcgui.WindowXMLDialog):
        closed = False

        def close(self):
            # Roadmap B.8: a search or download thread could still set a property after the menu closed
            # ("EXCEPTION: Window id does not exist"); those updates are skipped once it is closed.
            self.closed = True
            xbmcgui.WindowXMLDialog.close(self)

        def setProperty(self, key, value):
            if not self.closed:
                xbmcgui.WindowXMLDialog.setProperty(self, key, value)

        def onInit(self):
            self.rows, self.results, self.added = [], [], set()
            self.page = 'tracks'
            self.setProperty('mode', mode)
            self.setProperty('title', {'subtitles': 'Subtitles', 'speed': 'Playback speed'}.get(mode, 'Audio'))
            self.state('idle')
            self.fill()
            self.timing()
            # Roadmap 2.14: the list is empty until fill(), so the window opens on Close and moves here once filled.
            self.setFocusId(SPEED_LIST if mode == 'speed' else LIST)

        def missing(self, name):
            # Nothing found or no answer while no subtitle key is saved: say how to add one (Podnapisi is gone).
            return 'nokey' if keys_tag(xbmcvfs) == 'NOT SET' else name

        def state(self, name):
            self.setProperty('cta_state', 'busy' if name in ('search', 'download') else 'error' if name == 'nokey' else name)
            self.setProperty('cta', tm.cta(name, lang_name))
            self.setProperty('hint', tm.note(name, lang_name) or
                             {'idle': 'Finds %s subtitles for this video' % lang_name, 'search': 'Matching this exact version of the video',
                              'download': 'Matching this exact version of the video', 'done': 'Wrong one? More › Choose another'}.get(name, ''))

        def fill(self, focus_on=True):
            if self.closed:
                return
            p = {} if mode == 'speed' else (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': FIELDS}) or {})
            page = getattr(self, 'page', 'tracks')
            if mode == 'speed':
                self.rows = tm.speed_rows(xbmc.getInfoLabel('Player.PlaySpeed'))
            elif mode == 'subtitles' and page == 'more':
                self.rows = tm.more_rows(len(self.results), self.always_on(), keys_tag(xbmcvfs))
            elif mode == 'subtitles' and page == 'choose':
                self.rows = tm.result_rows(self.results)
            elif mode == 'subtitles':
                cur = (p.get('currentsubtitle') or {}).get('index')
                subs = [dict(s, downloaded=s.get('index') in self.added) for s in p.get('subtitles') or []]
                self.rows = tm.subtitle_rows(subs, cur, p.get('subtitleenabled'))
            else:
                self.rows = tm.audio_rows(p.get('audiostreams'), (p.get('currentaudiostream') or {}).get('index'))
            items = []
            for n, r in enumerate(self.rows):
                li = xbmcgui.ListItem(r['label'])
                li.setProperty('tag', r['tag'])
                li.setProperty('on', 'true' if r['on'] else '')
                li.setProperty('new', 'true' if r['tag'] == 'NEW' else '')
                li.setProperty('sep', 'true' if n < len(self.rows) - 1 else '')
                items.append(li)
            self.setProperty('rows', str(max(1, min(6 if mode == 'speed' else 3, len(self.rows)))))   # the cards and the menu fit the rows shown
            lst = self.getControl(SPEED_LIST if mode == 'speed' else LIST)
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
            self.fill()
            xbmc.sleep(300)
            self.close()
            xbmcgui.Dialog().notification(said, '', xbmcgui.NOTIFICATION_INFO, 2000, False)

        def item(self):
            it = rpc(xbmc, 'Player.GetItem', {'playerid': pid, 'properties': ['title', 'showtitle', 'year', 'season', 'episode', 'file', 'uniqueid']}) or {}
            return it.get('item') or {}

        def search(self):
            it = self.item()
            show = it.get('showtitle')
            season, episode = it.get('season'), it.get('episode')
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
            tmdb = (it.get('uniqueid') or {}).get('tmdb') if not ep[0] else None
            log('search %s %r %s S%sE%s via %s' % (lang, title, year, ep[0], ep[1], ', '.join(ss.sources(keys))))
            return ss.find(http_get, keys, lang, title, year, ep[0], ep[1], name, tmdb, log=lambda m: log('subtitles ' + m))

        def apply(self, result):
            import subtitle_sources as ss
            ep = getattr(self, 'episode', (None, None))
            got = ss.fetch(http_get, http_post, ss.load_keys(keys_folder(xbmcvfs)), result, ep[0], ep[1])
            if not got:
                raise ValueError('no subtitle file in the download')
            name, data = got
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, '%s.%s.%s' % (result['id'], lang, name.rsplit('.', 1)[-1].lower()))
            with open(path, 'wb') as f:
                f.write(data)
            before = {s.get('index') for s in (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []}
            xbmc.Player().setSubtitles(path)
            xbmc.sleep(400)
            after = (rpc(xbmc, 'Player.GetProperties', {'playerid': pid, 'properties': ['subtitles']}) or {}).get('subtitles') or []
            self.added |= {s.get('index') for s in after} - before
            log('applied %s (%d bytes)' % (result['id'], len(data)))

        def download_and_apply(self, result=None):
            try:
                if result is None:
                    self.state('search')
                    self.results = self.search()
                    if not self.results:
                        self.state(self.missing('none'))
                        log('nothing found')
                        return
                    result = self.results[0]
                self.state('download')
                self.apply(result)
                self.state('done')
                self.fill()
                xbmcgui.Dialog().notification('%s subtitles on' % lang_name, '', xbmcgui.NOTIFICATION_INFO, 2000, False)
            except Exception as error:
                log('download and apply failed: %s: %s' % (type(error).__name__, error))
                self.state(self.missing('error'))

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
            self.setProperty('back', {'more': '\u2039 Subtitles', 'choose': '\u2039 More'}.get(page, ''))
            self.fill()
            self.setFocusId(LIST)

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
            elif what == 'file':
                path = xbmcgui.Dialog().browse(1, 'Add subtitles', 'files', '.srt|.ass|.ssa|.vtt|.sub')
                if path:
                    xbmc.Player().setSubtitles(path)
                    xbmc.sleep(400)
                    self.more('tracks')
            elif what == 'keys':
                ask_keys(xbmcgui, xbmcvfs, log)
                self.results = []
                self.more('more')
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
            subs = [dict(x, downloaded=x.get('index') in self.added) for x in p.get('subtitles') or []]
            return subs, (p.get('currentsubtitle') or {}).get('index'), p.get('subtitleenabled')

        def onClick(self, control):
            if control == CLOSE:
                self.close()
            elif control == BACK_LINK:   # the sub-page's back link: Choose another -> More -> the tracks
                self.more('more' if self.page == 'choose' else 'tracks')
            elif control in (LIST, SPEED_LIST):
                n = self.getControl(control).getSelectedPosition()
                if 0 <= n < len(self.rows):
                    self.pick(n)
            elif control == CTA:
                if self.getProperty('cta_state') != 'busy':
                    threading.Thread(target=self.download_and_apply, daemon=True).start()
            elif control == MORE:
                self.more()
            elif control in (T_MINUS, T_PLUS):
                step = 'SubtitleDelay' if mode == 'subtitles' else 'AudioDelay'
                xbmc.executebuiltin('Action(%s%s)' % (step, 'Minus' if control == T_MINUS else 'Plus'))
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
            if action.getId() in BACK:
                self.close()

    home = HERE
    menu = Menu('IOSTrackMenu.xml', home, 'Default', '1080i')
    menu.doModal()
    del menu


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('subtitles', 'audio', 'speed') else 'subtitles')
