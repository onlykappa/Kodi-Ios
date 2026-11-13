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
SUMMARY = 'KodiIOS.UpscaleSummary'


def model(profile):
    import prepare_downloads
    import upscale_cloud
    import drivelibrary
    settings = picture.load(profile)
    data = uq.load(profile)
    groups = up.library(prepare_downloads.load(profile), upscale_cloud.media_lookup(profile, drivelibrary.parse), data)
    return settings, data, groups, up.rows(settings, data, groups, data.get('engine') or {})


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()
    home = xbmcgui.Window(10000)

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.setProperty('title', 'AI Upscale')
            self.fill()

        def fill(self, keep=None):
            self.settings, self.data, self.groups, self.rows = model(profile)
            home.setProperty(SUMMARY, up.summary(self.settings))
            items = []
            for r in self.rows:
                item = xbmcgui.ListItem(r.get('label', ''))
                kind = 'title' if r['kind'] in ('title', 'note') else r['kind']
                for key, value in (('kind', kind), ('label', r.get('label', '')), ('sub', r.get('sub', '')),
                                   ('value', r.get('value', '')), ('on', 'true' if r.get('on') else ''),
                                   ('note', 'true' if r['kind'] == 'note' else '')):
                    item.setProperty(key, value)
                items.append(item)
            lst = self.getControl(9310)
            lst.reset()
            lst.addItems(items)
            lst.selectItem(keep if keep is not None and keep < len(items) else 0)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == 9001:
                self.close()
                return
            if control != 9310:
                return
            n = self.getControl(9310).getSelectedPosition()
            if not 0 <= n < len(self.rows):
                return
            action = self.rows[n].get('action') or ''
            settings = self.settings
            if action.startswith('toggle:'):
                picture.save(profile, up.toggle(settings, action.split(':', 1)[1]))
            elif action == 'size':
                choices = list(picture.LABELS[1:])
                pick = dialog.select('Upscale new downloads to', choices)
                if pick < 0:
                    return
                settings['downloads']['size'] = choices[pick]
                picture.save(profile, settings)
            elif action.startswith('show:'):
                # V3 (board C): the show's own page: size, episodes with their state, make the rest, remove the copies.
                open_show(action[5:])
            elif action == 'model':
                data = uq.load(profile)
                data['model_request'] = True
                uq.save(profile, data)
                dialog.notification('AI Upscale', 'The AI model downloads in the background', xbmcgui.NOTIFICATION_INFO, 3000)
            elif action == 'test':
                xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,upscale_test)')
                return
            else:
                return
            self.fill(keep=n)

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
            elif control == sp.PRIMARY and self.view['primary']:
                picture.save(profile, up.set_show(settings, self.g, self.view['primary_size']))
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
    page = Page('IOSSkinList.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run()
