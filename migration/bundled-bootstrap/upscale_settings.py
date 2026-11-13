"""RunScript(service.kodi.ios.bootstrap,upscale_settings): Settings › AI Upscale (ai-upscale-settings-mockups.html,
approved DEC-042). The rows come from upscale_page.rows; the window is the Skin Settings list (IOSSkinList.xml)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import picture
import upscale_page as up
import upscale_queue as uq

BACK = (9, 10, 92, 110)
LONG = (101, 117)   # right click, context menu: a long press
SUMMARY = 'KodiIOS.UpscaleSummary'


def model(profile):
    import prepare_downloads
    import upscale_cloud
    import drivelibrary
    settings = picture.load(profile)
    data = uq.preview(profile, uq.load(profile))   # ISSUE-228: a cancel shows at once, before the service applies it
    groups = up.library(prepare_downloads.load(profile), upscale_cloud.media_lookup(profile, drivelibrary.parse), data)
    return settings, data, groups, up.rows(settings, data, groups, data.get('engine') or {})


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()
    home = xbmcgui.Window(10000)

    import upscale_main_page as mp
    import transfer_artwork
    import drivelibrary

    art = drivelibrary.load_json(transfer_artwork.cache_path(profile), {})

    def poster(name):
        try:
            return transfer_artwork.describe(name, art)['poster'] if name else ''
        except Exception:
            return ''

    def window(cls, xml):
        try:
            return cls(xml, HERE, 'Default', '1080i')
        except RuntimeError:
            import xbmcvfs as _v
            _v.listdir(os.path.join(_v.translatePath('special://skin/'), 'portrait') + '/')   # a page added while Kodi runs
            return cls(xml, HERE, 'Default', '1080i')

    def pos(n, count):
        return 'only' if count == 1 else 'first' if n == 0 else 'last' if n == count - 1 else 'mid'

    class Page(xbmcgui.WindowXMLDialog):
        """DEC-044 board A: the AI Upscale page (upscale_main_page.page)."""
        def onInit(self):
            self.stop = False
            self.fill()
            import threading
            threading.Thread(target=self.loop, daemon=True).start()

        def loop(self):
            monitor = xbmc.Monitor()
            while not self.stop and not monitor.waitForAbort(2):
                try:
                    self.fill()
                except Exception:
                    pass

        def fill(self):
            self.settings, self.data, self.groups, _ = model(profile)
            home.setProperty(SUMMARY, up.summary(self.settings))
            v = up.main_view(self.settings, self.data, self.groups, self.data.get('engine') or {}, uq.paused(profile))
            self.view = v
            props = {}
            card = v['making'] or {}
            props.update({'making.title': card.get('title', ''), 'making.line': card.get('line', ''),
                          'making.pct': str(card.get('pct', 0)), 'making.tint': '4DEBEBF5' if card.get('grey') else 'FF0A84FF',
                          'making.paused': 'true' if card.get('paused') else '', 'making.poster': poster(card.get('name'))})
            nexts = v['next']
            props['next.head'] = ('UP NEXT · %d' % len(nexts)) if nexts else ''
            shown = nexts[:mp.NEXT_SLOTS]
            for n in range(mp.NEXT_SLOTS):
                r = shown[n] if n < len(shown) else {}
                k = 'next.%d.' % n
                props.update({k + 'title': r.get('title', ''), k + 'sub': r.get('line', ''), k + 'poster': poster(r.get('name')),
                              k + 'pos': ('first' if n == 0 else 'mid') if r and len(nexts) > len(shown) else (pos(n, len(shown)) if r else '')})
            props['all.label'] = 'Show all %d' % len(nexts) if len(nexts) > len(shown) else ''
            props['all.pos'] = 'last'
            shows = v['shows'][:mp.SHOW_SLOTS]
            for n in range(mp.SHOW_SLOTS):
                r = shows[n] if n < len(shows) else {}
                k = 'show.%d.' % n
                props.update({k + 'title': r.get('title', ''), k + 'sub': r.get('sub', ''), k + 'value': r.get('value', ''),
                              k + 'poster': poster(r.get('name')), k + 'pos': pos(n, len(shows)) if r else ''})
            props['shows.note'] = '' if shows else 'No prepared 720p or 1080p download on Google Drive yet.'
            props.update({'set.new.on': 'true' if v['prepare'] else '', 'set.new.pos': 'first', 'set.size.value': v['size'],
                          'set.size.pos': 'mid', 'set.charge.on': 'true' if v['only_charging'] else '', 'set.charge.pos': 'last',
                          'engine.title': v['engine']['title'], 'engine.sub': v['engine']['sub'], 'engine.pos': 'only',
                          'space.title': 'AI copies on Google Drive', 'space.sub': v['space'], 'space.pos': 'only',
                          'cancelall': 'true' if v['can_cancel_all'] else ''})
            for key, value in props.items():
                if self.getProperty(key) != value:
                    self.setProperty(key, value)

        def close(self):
            self.stop = True
            xbmcgui.WindowXMLDialog.close(self)

        def hold_menu(self):
            """ISSUE-228 (owner: "if I hold down on a movie that is downloading it closes out the setting, I want the option to
            cancel it instead of only pausing"): a long press is a right click, which Kodi turns into "previous menu" and
            closed the page. On the copy being made it now opens Pause / Resume, Cancel This Copy and Cancel All Upscaling; on
            an Up next row, Make Next / Remove. False when nothing is held (a real back then closes the page)."""
            focus = self.getFocusId()
            card = self.view['making'] or {}
            if focus in (mp.MAKING, mp.MAKING_PAUSE) and card:
                labels = ['Resume' if card.get('paused') else 'Pause', 'Cancel This Copy', 'Cancel All Upscaling']
                pick = dialog.contextmenu(labels)
                if pick == 0:
                    uq.set_paused(profile, not card.get('paused'))
                elif pick == 1 and dialog.yesno('Cancel this copy?', '%s stops and leaves Up next. The original video stays as it is.'
                                                % card.get('title', 'This copy'), nolabel='Keep Making It', yeslabel='Cancel Copy'):
                    uq.cancel(profile, [card['key']])
                elif pick == 2:
                    self.cancel_all()
                self.fill()
                return True
            if mp.NEXT <= focus < mp.NEXT + mp.NEXT_SLOTS and focus - mp.NEXT < len(self.view['next']):
                row_menu(self.view['next'], focus - mp.NEXT)
                self.fill()
                return True
            return False

        def cancel_all(self):
            card = self.view['making'] or {}
            waiting = len(self.view['next']) + (0 if card.get('running') or not card else 1)
            if dialog.yesno('Cancel all upscaling?', 'The copy being made stops and %d waiting leave Up next. Copies already made '
                            'stay, and the original videos are not touched.' % max(0, waiting),
                            nolabel='Keep Making Them', yeslabel='Cancel All'):
                uq.cancel_all(profile)

        def onAction(self, action):
            import time
            code = action.getId()
            if code in LONG or code == 10:
                if time.time() - getattr(self, 'menu_done', 0) < 1.5:   # one long press can arrive as both actions
                    return
                if self.hold_menu():
                    self.menu_done = time.time()
                    return
            if code in BACK:
                self.close()

        def onClick(self, control):
            settings = self.settings
            card = self.view['making'] or {}
            if control == mp.BACK:
                self.close()
                return
            if control == mp.MAKING_PAUSE and card:
                uq.set_paused(profile, not card.get('paused'))
            elif control == mp.MAKING and card:
                open_copy(card['key'])
            elif control in (mp.EDIT, mp.SHOW_ALL):
                open_edit()
            elif mp.NEXT <= control < mp.NEXT + mp.NEXT_SLOTS:
                n = control - mp.NEXT
                if n < len(self.view['next']):
                    row_menu(self.view['next'], n)
            elif mp.SHOW <= control < mp.SHOW + mp.SHOW_SLOTS:
                n = control - mp.SHOW
                if n < len(self.view['shows']):
                    open_show(self.view['shows'][n]['key'])
            elif control == mp.NEW:
                picture.save(profile, up.toggle(settings, 'prepare'))
            elif control == mp.CHARGE:
                picture.save(profile, up.toggle(settings, 'only_charging'))
            elif control == mp.SIZE:
                choices = list(picture.LABELS[1:])
                pick = dialog.select('Upscale new downloads to', choices)
                if pick < 0:
                    return
                settings['downloads']['size'] = choices[pick]
                picture.save(profile, settings)
            elif control == mp.ENGINE:
                if self.view['engine']['action'] == 'model':
                    data = uq.load(profile)
                    data['model_request'] = True
                    uq.save(profile, data)
                    dialog.notification('AI Upscale', 'The AI model downloads in the background', xbmcgui.NOTIFICATION_INFO, 3000)
                else:
                    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,upscale_test)')
                    return
            elif control == mp.SPACE:
                xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,library_manager,freeup)')
                return
            elif control == mp.CANCEL_ALL:
                self.cancel_all()
            else:
                return
            self.fill()

    def row_menu(rows, n):
        """A tap on an Up next row: what can be done with that copy."""
        labels = ['Make Next', 'Remove From Up Next']
        pick = dialog.contextmenu(labels)
        if pick == 0:
            order = [r['key'] for r in rows]
            order.insert(0, order.pop(n))
            uq.reorder(profile, order)
        elif pick == 1 and dialog.yesno('Remove from Up next?', '%s will not be upscaled. The original stays as it is.' % rows[n]['title'],
                                        nolabel='Keep', yeslabel='Remove'):
            uq.cancel(profile, [rows[n]['key']])

    class Copy(xbmcgui.WindowXMLDialog):
        """DEC-044 board B1: the copy being made, with Pause / Cancel Copy."""
        def onInit(self):
            self.draw()

        def draw(self):
            settings, data, groups, _ = model(profile)
            up.main_view(settings, data, groups, data.get('engine') or {})   # fills names saved without one
            device = {}
            v = up.copy_sheet(data, self.key, uq.paused(profile), device)
            props = {'title': v['title'], 'sub': v['sub'], 'device': v['device'], 'pct': str(v['pct']),
                     'tint': '4DEBEBF5' if v['grey'] else 'FF0A84FF', 'stats': v['stats'], 'left': v['left'], 'pause': v['pause'],
                     'poster': poster(v['name'])}
            for n, (state, label) in enumerate(v['stages']):
                props['stage%d.state' % n] = state
                props['stage%d.label' % n] = label
                props['stage%d.tint' % n] = 'FFFFFFFF' if state != 'next' else '99EBEBF5'
            for key, value in props.items():
                self.setProperty(key, value)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control in (mp.SHEET_CLOSE, mp.SHEET_DIM):
                self.close()
            elif control == mp.SHEET_PAUSE:
                uq.set_paused(profile, not uq.paused(profile))
                self.draw()
            elif control == mp.SHEET_CANCEL:
                title = self.getProperty('title')
                if dialog.yesno('Cancel this copy?', '%s stops and leaves Up next. The original video stays as it is.' % title,
                                nolabel='Keep Making It', yeslabel='Cancel Copy'):
                    uq.cancel(profile, [self.key])
                    self.close()

    def open_copy(key):
        sheet = window(Copy, mp.SHEET)
        sheet.key = key
        sheet.doModal()
        del sheet

    class Edit(xbmcgui.WindowXMLDialog):
        """DEC-044 board B2: Up next › Edit (– removes, ≡ moves; Kodi cannot drag rows)."""
        def onInit(self):
            self.draw()

        def draw(self):
            settings, data, groups, _ = model(profile)
            up.main_view(settings, data, groups, data.get('engine') or {})   # fills names saved without one
            card = up.making(data, uq.paused(profile))
            self.rows = up.next_rows(data, card['key'] if card and card.get('running') else None)
            props = {'heading': 'Up next', 'foot': 'A removed copy is not made again until you choose the show\'s size again. '
                                                   'Tap the lines on the right to move a copy.' if self.rows else '',
                     'removeall': 'Remove All From Up Next' if self.rows else '', 'empty': '' if self.rows else 'Nothing waiting.'}
            for n in range(mp.EDIT_SLOTS):
                r = self.rows[n] if n < len(self.rows) else {}
                k = 'row.%d.' % n
                props.update({k + 'title': r.get('title', ''), k + 'sub': r.get('line', ''), k + 'poster': poster(r.get('name')),
                              k + 'pos': pos(n, min(len(self.rows), mp.EDIT_SLOTS)) if r else ''})
            for key, value in props.items():
                self.setProperty(key, value)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def order(self, keys):
            uq.reorder(profile, keys)
            data = uq.load(profile)
            if uq.apply_control(profile, data, keep=True):   # shown at once; the service would apply it on its next pass too
                uq.save(profile, data)

        def onClick(self, control):
            keys = [r['key'] for r in self.rows]
            if control in (mp.BACK, mp.DONE):
                self.close()
                return
            if mp.REMOVE <= control < mp.REMOVE + mp.EDIT_SLOTS and control - mp.REMOVE < len(keys):
                n = control - mp.REMOVE
                if not dialog.yesno('Remove from Up next?', '%s will not be upscaled. The original stays as it is.' % self.rows[n]['title'],
                                    nolabel='Keep', yeslabel='Remove'):
                    return
                uq.cancel(profile, [keys[n]])
                data = uq.load(profile)
                if uq.apply_control(profile, data, keep=True):
                    uq.save(profile, data)
            elif mp.MOVE <= control < mp.MOVE + mp.EDIT_SLOTS and control - mp.MOVE < len(keys):
                n = control - mp.MOVE
                pick = dialog.contextmenu(['Move to Top', 'Move Up', 'Move Down'])
                if pick < 0:
                    return
                k = keys.pop(n)
                keys.insert(0 if pick == 0 else max(0, n - 1) if pick == 1 else min(len(keys), n + 1), k)
                self.order(keys)
            elif control == mp.REMOVE_ALL and keys:
                if not dialog.yesno('Remove all from Up next?', '%d copies will not be made. The originals stay as they are.' % len(keys),
                                    nolabel='Keep', yeslabel='Remove All'):
                    return
                uq.cancel(profile, keys)
                data = uq.load(profile)
                if uq.apply_control(profile, data, keep=True):
                    uq.save(profile, data)
            else:
                return
            self.draw()

    def open_edit():
        page = window(Edit, mp.EDIT_WINDOW)
        page.doModal()
        del page

    import upscale_show_page as sp

    class Show(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.draw()

        def group(self):
            _, _, groups, _ = model(profile)
            return next((g for g in groups if g['key'] == self.key), None)

        def draw(self):
            self.g = self.group()
            if self.g is None:
                self.close()
                return
            settings = picture.load(profile)
            self.view = up.show_view(settings, self.g)
            v = self.view
            props = {'title': v['title'], 'sub': v['sub'], 'chosen': v['chosen'], 'primary': v['primary'], 'remove': v['remove'],
                     'note': v['note'], 'what': 'movie' if self.g['kind'] == 'movie' else 'show',
                     'episodes.title': 'EPISODES' if self.g['kind'] != 'movie' else ''}
            for n in range(sp.SEGS):
                label = v['choices'][n] if n < len(v['choices']) else ''
                props['seg.%d' % n] = up.short(label) if label else ''
                props['seg.%d.tint' % n] = 'FF0A84FF' if label and label == v['chosen'] else 'FF2C2C2E'
            rows = v['rows'][:sp.SLOTS] if self.g['kind'] != 'movie' else []
            for n in range(sp.SLOTS):
                r = rows[n] if n < len(rows) else {}
                props['ep.%d.title' % n] = r.get('title', '')
                props['ep.%d.line' % n] = r.get('line', '')
                props['ep.%d.chip' % n] = r.get('chip', '')
                props['ep.%d.tone' % n] = r.get('tone', '')
                props['ep.%d.pos' % n] = ('only' if len(rows) == 1 else 'first' if n == 0 else 'last' if n == len(rows) - 1 else 'mid') if r else ''
            for key, value in props.items():
                self.setProperty(key, str(value))

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            settings = picture.load(profile)
            if control == sp.BACK:
                self.close()
                return
            if sp.SEG <= control < sp.SEG + sp.SEGS and control - sp.SEG < len(self.view['choices']):
                picture.save(profile, up.set_show(settings, self.g, self.view['choices'][control - sp.SEG]))
                uq.save(profile, uq.revive(uq.load(profile), self.g['videos']))   # DEC-044: chosen again, cancelled copies may be made
            elif control == sp.PRIMARY and self.view['primary']:
                picture.save(profile, up.set_show(settings, self.g, self.view['primary_size']))
                uq.save(profile, uq.revive(uq.load(profile), self.g['videos']))   # DEC-044: chosen again, cancelled copies may be made
                dialog.notification('AI Upscale', 'Copies are made in the background, one at a time', xbmcgui.NOTIFICATION_INFO, 3000)
            elif control == sp.REMOVE and self.view['remove']:
                if not dialog.yesno('Remove the copies?', 'The upscaled copies of %s go to Google Drive\'s Trash, where they stay for '
                                    '30 days. The originals are not touched, and this show is set to Off.' % self.view['title'],
                                    nolabel='Cancel', yeslabel='Remove'):
                    return
                settings, data = up.remove_copies(settings, uq.load(profile), self.g)
                picture.save(profile, settings)
                uq.save(profile, data)
            else:
                return
            self.draw()

    def open_show(key):
        try:
            sheet = Show(sp.WINDOW, HERE, 'Default', '1080i')
        except RuntimeError:
            import xbmcvfs as _v
            _v.listdir(os.path.join(_v.translatePath('special://skin/'), 'portrait') + '/')   # a page added while Kodi runs
            sheet = Show(sp.WINDOW, HERE, 'Default', '1080i')
        sheet.key = key
        sheet.doModal()
        del sheet

    direct = next((a[5:] for a in sys.argv[1:] if a.startswith('show=')), '')
    if direct:   # RunScript(service.kodi.ios.bootstrap,upscale_settings,show=KEY): straight to one show's page
        open_show(direct)
        return
    page = window(Page, mp.WINDOW)
    page.doModal()
    del page


if __name__ == '__main__':
    run()
