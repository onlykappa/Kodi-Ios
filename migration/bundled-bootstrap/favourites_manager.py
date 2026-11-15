"""Settings › Favourites: the Favourites manager (owner-approved boards K1-K8, docs/design/favourites-manager-mockups.html).

Owner (build 486): "when I'm in settings and click on favorites it goes to the library favorites; it needs to open its own
page to manage imports". The landing page (K1) shows the counts, what needs a look after an import, each imported list and
the tools; K2-K5 are its pages, and K7/K8 pick a title by its poster. The poster grid (favourites_page.py) stays the
Library's place to browse and play.

What each page holds is favourites_manager_model.py (pure); the windows are favourites_manager_page.py."""
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import favourites_import as fi
import favourites_manager_model as model
import favourites_manager_page as page

BACK_ACTIONS = (9, 10, 92, 110)
DETAILS_TIMEOUT = 6


def slot_properties(rows, before=()):
    """ISSUE-325: window properties for the page's slots: r.N.kind/label/label2/thumb and every row property. Every
    property the last page set (`before`) that this one does not is emptied, so no count or chip is left behind and unused
    slots hide (their kind is empty)."""
    out = {key: '' for key in before}
    for n, r in enumerate(rows[:page.SLOTS]):
        out['r.%d.label' % n] = str(r.get('label', ''))
        out['r.%d.label2' % n] = str(r.get('label2', ''))
        out['r.%d.thumb' % n] = str(r.get('thumb', ''))
        for k, v in r.items():
            if k not in ('label', 'label2', 'thumb', 'action'):
                out['r.%d.%s' % (n, k)] = str(v)
    return out


def run():
    import xbmc
    import xbmcgui
    import xbmcvfs
    import favourites_import_page as fip
    import favourites_match as fm
    import favourites_page as fp
    import favourites_rows as fr

    profile = xbmcvfs.translatePath('special://profile/')
    dialog = xbmcgui.Dialog()

    def lookup():
        """TMDb search through TMDb Helper's key, or None (with a message) when TMDb Helper is not there."""
        import source_match
        key = source_match.tmdb_key()
        if not key:
            dialog.ok(fip.TITLE, 'TMDb Helper is needed to look titles up, and it is not available right now.')
            return None, None
        return fip.tmdb_search(key), key

    def details(key, choices):
        """TMDb's details for each choice (genres, seasons), fetched together, so the picker can say what each one is."""
        import json
        import urllib.request
        out, threads = {}, []

        def one(c):
            try:
                url = '%s/%s/%s?api_key=%s' % (fip.TMDB, 'tv' if c['kind'] == 'tv' else 'movie', c['tmdb'], key)
                with urllib.request.urlopen(url, timeout=DETAILS_TIMEOUT) as response:
                    out['%s:%s' % (c['kind'], c['tmdb'])] = json.loads(response.read(512 * 1024))
            except Exception:
                pass
        for c in choices:
            t = threading.Thread(target=one, args=(c,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(DETAILS_TIMEOUT + 1)
        return out

    class Pick(xbmcgui.WindowXMLDialog):
        """K7 / K8: returns the tapped poster's index, 'other' (Search Another Name), 'search' (the field), 'skip' or None."""
        def setup(self, spec):
            self.spec, self.answer = spec, None

        def onInit(self):
            for k in ('back', 'title', 'sub', 'search', 'query', 'other'):
                self.setProperty(k, str(self.spec.get(k) or ''))
            items = []
            for c in self.spec['cells']:
                li = xbmcgui.ListItem(c['label'], c['label2'])
                li.setArt({'poster': c['poster'], 'thumb': c['poster']})
                li.setProperty('best', c['best'])
                items.append(li)
            for ident in (page.GRID, page.GRID + 1):
                try:
                    grid = self.getControl(ident)
                    grid.reset()
                    grid.addItems(items)
                except Exception:
                    pass
            try:
                self.setFocusId(page.GRID + 1 if self.spec.get('search') else page.GRID)
            except Exception:
                pass

        def onClick(self, control):
            if control in (page.GRID, page.GRID + 1):
                self.answer = self.getControl(control).getSelectedPosition()
            elif control == page.OTHER:
                self.answer = 'other'
            elif control == page.SEARCH:
                self.answer = 'search'
            elif control == page.SKIP:
                self.answer = 'skip'
            else:
                return
            self.close()

        def onAction(self, action):
            if action.getId() in BACK_ACTIONS:
                self.close()

    def show_pick(spec):
        window = Pick(page.PICK, HERE, 'Default', '1080i')
        window.setup(spec)
        window.doModal()
        answer = window.answer
        del window
        return answer

    def add_choice(choice, entry, report):
        new, _ = fi.add(profile, [dict(choice, rank=entry.get('rank') or 0, watched=entry.get('watched', 0))], report.get('list') or '')
        report['added'] = int(report.get('added') or 0) + len(new)

    def search_pick(name, line, entry, report):
        """K8: the name searched as written; the field changes the spelling. True when a title was added."""
        search, key = lookup()
        if not search:
            return False
        query = name
        while True:
            try:
                found = [r for r in search(query) if r.get('media_type') in ('tv', 'movie')][:9]
            except Exception:
                found = []
            choices = [c for c in (fm.candidate(r) for r in found) if c]
            for c, r in zip(choices, found):
                c.update(genre_ids=r.get('genre_ids') or [], origin_country=r.get('origin_country') or [],
                         original_language=r.get('original_language') or '')
            answer = show_pick(model.picker(name, line, choices, details(key, choices), search=query, mode='search'))
            if isinstance(answer, int) and 0 <= answer < len(choices):
                add_choice(choices[answer], entry, report)
                return True
            if answer == 'search':
                query = (dialog.input('Search for “%s”' % name, defaultt=query, type=xbmcgui.INPUT_ALPHANUM) or '').strip() or query
                continue
            return answer == 'skip' and None

    def answer_question(n, report):
        """K7 for one question. Returns 'done' (picked or skipped: it leaves the report), or None (Back: it stays)."""
        questions = report.get('questions') or []
        if not 0 <= n < len(questions):
            return None
        q = questions[n]
        entry, choices = q['entry'], q.get('choices') or []
        _, key = lookup()
        answer = show_pick(model.picker(entry.get('title', ''), entry.get('line', ''), choices,
                                        details(key, choices) if key else {}, mode='ask'))
        if isinstance(answer, int) and 0 <= answer < len(choices):
            add_choice(choices[answer], entry, report)
        elif answer == 'other':
            if not search_pick(entry.get('title', ''), entry.get('line', ''), entry, report):
                return None
        elif answer != 'skip':
            return None
        questions.pop(n)
        fi.save_report_data(profile, report)
        return 'done'

    def retry(indexes, report):
        """K3 Not checked: look the names up again. A match is added; several matches become a question; no match stays."""
        search, _ = lookup()
        if not search:
            return
        missing = report.get('missing') or []
        keep = []
        bar = xbmcgui.DialogProgress()
        bar.create(fip.TITLE, 'Looking up titles again')
        try:
            for k, m in enumerate(missing):
                if k not in indexes:
                    keep.append(m)
                    continue
                bar.update(int(100 * len(keep) / max(1, len(missing))), m.get('title', ''))
                result = fm.run([{'title': m['title'], 'rank': m.get('rank') or 0, 'line': m.get('line'), 'watched': m.get('watched', 0)}], search)
                if result['matched']:
                    add_choice(result['matched'][0], m, report)
                elif result['questions']:
                    report.setdefault('questions', []).append(result['questions'][0])
                else:
                    keep.append(dict(result['missing'][0], line=m.get('line'), rank=m.get('rank')) if result['missing'] else m)
        finally:
            bar.close()
        report['missing'] = keep
        fi.save_report_data(profile, report)

    class Manage(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if not hasattr(self, 'stack'):
                self.stack = [('landing', None)]
            self.render()

        def build(self):
            name, arg = self.stack[-1]
            report = fi.load_report(profile) or {}
            data = fi.load(profile)
            if name == 'landing':
                shown, sort = fp.read(xbmc, xbmcvfs)
                own = len(fr.entries((fp.rpc(xbmc, 'Favourites.GetFavourites', {'properties': fr.READ}) or {}).get('favourites') or []))
                return model.landing(shown, data['items'], report, own, fi.sort_label(sort))
            if name == 'ask':
                return model.questions_page(report)
            if name == 'missing':
                return model.missing_page(report, failed=bool(arg))
            if name == 'dups':
                return model.duplicates_page(report)
            if name == 'list':
                list_name, view = arg
                return model.list_page(list_name, data['items'], report, view)
            return model.landing([], [], {}, 0, '')

        def render(self):
            spec = self.spec = self.build()
            for k in ('back', 'title', 'sub'):
                self.setProperty(k, str(spec.get(k) or ''))
            seg = spec.get('seg') or []
            self.setProperty('seg.count', str(len(seg)) if seg else '')
            self.setProperty('seg.on', str(spec.get('seg_on') or 1))
            for n in range(1, 4):
                self.setProperty('seg.%d' % n, seg[n - 1] if n <= len(seg) else '')
            # ISSUE-325: the page is a column of slots (favourites_manager_page.SLOTS), one per row, filled from properties.
            props = slot_properties(spec['rows'], getattr(self, 'slot_keys', ()))
            for key, value in props.items():
                self.setProperty(key, value)
            self.slot_keys = [k for k, v in props.items() if v]
            if len(spec['rows']) > page.SLOTS:
                xbmc.log('Kodi iOS favourites manager: %d rows, %d shown' % (len(spec['rows']), page.SLOTS), xbmc.LOGWARNING)

        def go(self, name, arg=None):
            self.stack.append((name, arg))
            self.render()

        def back(self):
            if len(self.stack) > 1:
                self.stack.pop()
                self.render()
            else:
                self.close()

        def onAction(self, action):
            if action.getId() in BACK_ACTIONS:
                self.back()

        def onClick(self, control):
            if control == page.BACK:
                self.back()
                return
            if page.SEG <= control < page.SEG + 3:
                n = control - page.SEG
                name, arg = self.stack[-1]
                if name == 'missing':
                    self.stack[-1] = ('missing', n == 1)
                elif name == 'list':
                    self.stack[-1] = ('list', (arg[0], ('all', 'added', 'need')[n]))
                self.render()
                return
            if not page.ROW_TAP <= control < page.ROW_TAP + page.SLOTS:
                return
            position = control - page.ROW_TAP
            rows = self.spec['rows']
            if 0 <= position < len(rows) and rows[position].get('action'):
                self.act(rows[position]['action'])

        def act(self, action):
            report = fi.load_report(profile) or {}
            if action in ('ask', 'dups'):
                self.go(action)
            elif action == 'missing':
                failed = report.get('missing') or []
                self.go('missing', bool(failed) and all(m.get('failed') for m in failed))
            elif action.startswith('list:'):
                self.go('list', (action[5:], 'all'))
            elif action == 'grid':
                fp.run()
            elif action == 'import':
                fip.run_import(xbmc, xbmcgui, profile)
            elif action == 'sort':
                rows = [{'label': label, 'detail': detail} for key, label, detail in fi.SORTS]
                choice = fip.pick(xbmcgui, {'heading': 'Sort Favourites', 'rows': rows})
                if 0 <= choice < len(fi.SORTS):
                    fi.set_sort(profile, fi.SORTS[choice][0])
            elif action.startswith('ask:'):
                answer_question(int(action[4:]), report)
            elif action == 'ask_all':
                while report.get('questions') and answer_question(0, report) == 'done':
                    report = fi.load_report(profile) or {}
            elif action.startswith('search:'):
                n = int(action[7:])
                missing = report.get('missing') or []
                if 0 <= n < len(missing):
                    m = missing[n]
                    if search_pick(m.get('title', ''), m.get('line', ''), m, report) is not False:
                        missing.pop(n)
                        fi.save_report_data(profile, report)
            elif action.startswith('retry:'):
                retry({int(action[6:])}, report)
            elif action == 'retry_all':
                retry({k for k, m in enumerate(report.get('missing') or []) if m.get('failed')}, report)
            elif action == 'skip_all':
                report['missing'] = [m for m in report.get('missing') or [] if m.get('failed')]
                fi.save_report_data(profile, report)
            elif action.startswith('open:'):
                _, kind, tmdb = action.split(':', 2)
                item = next((i for i in fi.load(profile)['items'] if i.get('kind') == kind and str(i.get('tmdb')) == tmdb), None)
                if item:
                    self.close()
                    fip.open_item(xbmc, xbmcgui, xbmcvfs, fr.imported_entry(item))
                    return
            elif action == 'remove_list':
                name = self.stack[-1][1][0]
                titles = [i for i in fi.load(profile)['items'] if (i.get('list') or 'Imported list') == name]
                choice = fip.pick(xbmcgui, {'heading': 'Remove “%s”?' % name,
                                            'sub': 'Its %d title%s leave Favourites. Favourites added by hand, and anything you '
                                                   'downloaded, stay.' % (len(titles), '' if len(titles) == 1 else 's'),
                                            'rows': [{'label': 'Remove List and Its %d Title%s' % (len(titles), '' if len(titles) == 1 else 's'),
                                                      'glyph': 'trash.png', 'tint': 'FFFF453A'}]})
                if choice == 0:
                    data = fi.load(profile)
                    data['items'] = [i for i in data['items'] if (i.get('list') or 'Imported list') != name]
                    fi.save(profile, data)
                    self.stack.pop()
            self.render()

    window = Manage(page.MANAGE, HERE, 'Default', '1080i')
    # start=ask|missing|dups|list:<name> opens that page over the landing page (Notifications links, the rig).
    start = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a).get('start', '')
    window.stack = [('landing', None)]
    if start in ('ask', 'missing', 'dups'):
        window.stack.append((start, None))
    elif start.startswith('list:'):
        window.stack.append(('list', (start[5:], 'all')))
    window.doModal()
    del window


if __name__ == '__main__':
    run()
