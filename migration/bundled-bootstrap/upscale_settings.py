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
                g = next((g for g in self.groups if g['key'] == action[5:]), None)
                if g is None:
                    return
                sizes = up.show_sizes(g)
                pick = dialog.select('%s · AI Upscale' % g['title'], sizes)
                if pick < 0:
                    return
                picture.save(profile, up.set_show(settings, g, sizes[pick]))
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

    page = Page('IOSSkinList.xml', HERE, 'Default', '1080i')
    page.doModal()
    del page


if __name__ == '__main__':
    run()
