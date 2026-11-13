"""End-to-end check of the season download system (owner, build 328: "before u push ipa ensure the show download system
fully works"). The real queue, copy lanes, retries, naming, duplicate and Drive checks and the status cards run against
a fake AllDebrid and a fake Google Drive that speaks Drive's HTTP (resumable uploads, folders, moves, Trash), with the
owner's situation from builds 319-328:

- a complete-series pack named by absolute number ("Naruto Shippuden Episode 006 ….mkv", no S01E06) and its 32
  episode jobs queued by an old build with the info-hash as title;
- episode 2 already on Drive in a hash-named folder; episode 6 queued again from two other torrents;
- a slow link: pieces time out with part of them kept, Drive keeps bytes late, a connection drops;
- a conversion running beside the copies; the app closed in the middle (a stale copy card left behind).

Nothing here is the phone: AllDebrid, Drive and iOS are simulated (docs/design/APPLE-UI-POLICY.md §9 evidence classes).
"""
import hashlib, json, os, random, re, sys, tempfile, unittest, urllib.parse
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import debrid_drive, driveupload, transfer_control, work_state  # noqa: E402

SHOW = 'Naruto Shippūden'
TMDB = '31910'
PACK = 'ee34425d5595f37297bc8c94dab3184c02d43daf'
OLD2 = '3c90db2e05217cc29aef549b4' + '0' * 15
ALT6 = ('6a' * 20, '6b' * 20)
PIECE = 256 * 1024


def blob(name, size):
    seed = hashlib.sha256(name.encode()).digest()
    return (seed * (size // len(seed) + 1))[:size]


class AllDebrid:
    """Torrents by hash: files (path, size, link); unlock gives the source URL."""
    def __init__(self):
        self.torrents = {}
        self.sources = {}

    def add_torrent(self, h, files):
        self.torrents[h] = []
        for path, size in files:
            link = 'L:%s:%s' % (h[:6], path)
            self.sources['https://debrid/' + link] = (os.path.basename(path), blob(path, size))
            self.torrents[h].append((path, size, link))

    def add(self, h):
        return 'm:' + h, True

    def status(self, magnet):
        return 4, 1.0, 'Ready'

    def files(self, magnet):
        return list(self.torrents[magnet[2:]])

    def unlock(self, link):
        name, data = self.sources['https://debrid/' + link]
        return 'https://debrid/' + link, name, len(data)


class DriveServer:
    """Enough of Drive v3 for the copy path: folders, resumable sessions, PATCH moves and Trash, children listing."""
    FOLDER = 'application/vnd.google-apps.folder'

    def __init__(self):
        self.items = {'root': {'name': 'root', 'parents': [], 'mime': self.FOLDER, 'trashed': False}}
        self.sessions = {}
        self.n = 0

    def new_id(self, prefix):
        self.n += 1
        return '%s%d' % (prefix, self.n)

    def mkdir(self, parts):
        parent = 'root'
        for name in parts:
            found = [i for i, it in self.items.items() if it['name'] == name and parent in it['parents'] and it['mime'] == self.FOLDER and not it['trashed']]
            if found:
                parent = found[0]
            else:
                ident = self.new_id('d')
                self.items[ident] = {'name': name, 'parents': [parent], 'mime': self.FOLDER, 'trashed': False}
                parent = ident
        return parent

    def put_file(self, parent, name, data):
        ident = self.new_id('f')
        self.items[ident] = {'name': name, 'parents': [parent], 'mime': 'video/x-matroska', 'trashed': False, 'data': data}
        return ident

    def path(self, ident):
        out = []
        while ident != 'root':
            out.append(self.items[ident]['name'])
            ident = self.items[ident]['parents'][0]
        return '/'.join(reversed(out))

    def videos(self):
        return {i: it for i, it in self.items.items() if it['mime'] != self.FOLDER and not it['trashed']}

    def send(self, method, url, body=None, headers=None):
        headers = headers or {}
        split = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(split.query))
        if url.startswith(driveupload.UPLOAD) and method == 'POST':
            meta = json.loads(body)
            session = 'https://upload/s%d' % len(self.sessions)
            self.sessions[session] = {'name': meta['name'], 'parents': meta['parents'],
                                      'size': int(headers['X-Upload-Content-Length']), 'data': b''}
            return 200, {'Location': session}, b''
        if url in self.sessions and method == 'PUT':
            return self.put(url, body or b'', headers['Content-Range'])
        if url.startswith(driveupload.API) and method == 'GET':
            q = query.get('q', '')
            parent = re.search(r"'([^']+)' in parents", q).group(1)
            named = re.search(r"name='((?:[^'\\]|\\.)*)'", q)
            files = [{'id': i} for i, it in self.items.items() if parent in it['parents'] and not it['trashed']
                     and (not named or it['name'] == named.group(1).replace("\\'", "'").replace('\\\\', '\\'))
                     and (not named or it['mime'] == self.FOLDER)]
            return 200, {}, json.dumps({'files': files}).encode()
        if url.startswith(driveupload.API) and method == 'POST':
            meta = json.loads(body)
            ident = self.new_id('d')
            self.items[ident] = {'name': meta['name'], 'parents': meta['parents'], 'mime': meta['mimeType'], 'trashed': False}
            return 200, {}, json.dumps({'id': ident}).encode()
        if url.startswith(driveupload.API + '/') and method == 'PATCH':
            ident = urllib.parse.unquote(split.path.rsplit('/', 1)[1])
            item = self.items[ident]
            change = json.loads(body or b'{}')
            if change.get('trashed'):
                item['trashed'] = True
            if 'name' in change:
                item['name'] = change['name']
            if query.get('removeParents'):
                item['parents'] = [p for p in item['parents'] if p != query['removeParents']]
            if query.get('addParents'):
                item['parents'].append(query['addParents'])
            return 200, {}, b'{}'
        raise AssertionError('unexpected Drive call %s %s' % (method, url))

    def put(self, url, body, content_range):
        s = self.sessions[url]
        total = int(content_range.rsplit('/', 1)[1])
        if not content_range.startswith('bytes */'):
            a, b = (int(x) for x in content_range[6:].split('/')[0].split('-'))
            if a > len(s['data']):
                return 308, self.range(s), b''
            s['data'] = s['data'][:a] + body
        if len(s['data']) == total:
            if 'id' not in s:
                s['id'] = self.put_file(s['parents'][0], s['name'], s['data'])
            return 200, {}, json.dumps({'id': s['id'], 'size': str(total)}).encode()
        return 308, self.range(s), b''

    @staticmethod
    def range(s):
        return {'Range': 'bytes=0-%d' % (len(s['data']) - 1)} if s['data'] else {}


class SlowLink:
    """The native copier on a bad link: some pieces time out with part kept, some answers are lost after Drive took
    the bytes (late bytes), and a connection sometimes drops before anything is sent."""
    def __init__(self, server, debrid, rng):
        self.server, self.debrid, self.rng = server, debrid, rng
        self.timeouts = self.late = self.drops = self.pieces = 0

    def __call__(self, source, source_headers, target, headers, offset, count, total, timeout):
        self.pieces += 1
        _, data = self.debrid.sources[source]
        roll = self.rng.random()
        if roll < 0.05:
            self.drops += 1
            raise ConnectionError('connection reset')
        if roll < 0.20:   # cut off at the deadline: Drive kept part of the piece
            self.timeouts += 1
            keep = max(1, count // 2)
            self.server.put(target, data[offset:offset + keep], 'bytes %d-%d/%d' % (offset, offset + keep - 1, total))
            raise TimeoutError('piece deadline')
        status, h, body = self.server.put(target, data[offset:offset + count], 'bytes %d-%d/%d' % (offset, offset + count - 1, total))
        if roll < 0.30:   # Drive took the bytes, the answer was lost
            self.late += 1
            raise ConnectionError('response lost')
        return status, h, body


class SeasonDownload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.profile = self.tmp.name
        self.state_dir = os.path.join(self.profile, 'addon_data', 'service.kodi.ios.bootstrap')
        os.makedirs(self.state_dir)
        rng = random.Random(328)
        self.debrid = AllDebrid()
        # The complete-series pack, absolute numbers only, with a sample and a film beside the episodes.
        self.sizes = {n: rng.randrange(3 * PIECE, 7 * PIECE) for n in range(1, 33)}
        pack = [('Naruto Shippuden (001-032)/Naruto Shippuden Episode %03d Title %d.mkv' % (n, n), self.sizes[n]) for n in range(1, 33)]
        pack += [('Naruto Shippuden (001-032)/Sample/sample.mkv', PIECE), ('Naruto Shippuden (001-032)/Movies/The Movie.mkv', 9 * PIECE)]
        self.debrid.add_torrent(PACK, pack)
        self.debrid.add_torrent(OLD2, [('[Sub] Naruto Shippuuden - 002 [1080p].mkv', self.sizes[2])])
        for h in ALT6:
            self.debrid.add_torrent(h, [('Naruto.Shippuden.S01E06.1080p.WEB.%s.mkv' % h[:2], self.sizes[6])])
        self.server = DriveServer()
        # Episode 2 is on Drive already, in a folder named after its torrent's hash (builds before 315).
        hash_folder = self.server.mkdir([debrid_drive.TOP, 'TV Shows', OLD2])
        ep2 = self.server.put_file(hash_folder, '[Sub] Naruto Shippuuden - 002 [1080p].mkv', self.debrid.sources['https://debrid/L:%s:[Sub] Naruto Shippuuden - 002 [1080p].mkv' % OLD2[:6]][1])
        with open(os.path.join(self.state_dir, 'drive-library.json'), 'w') as f:
            json.dump({'tv:': {'entries': [{'id': hash_folder, 'title': OLD2}]},
                       'tv:%s' % hash_folder: {'entries': [{'id': ep2, 'name': '[Sub] Naruto Shippuuden - 002 [1080p].mkv',
                                                            'show': 'Naruto Shippuuden', 'season': '', 'episode': ''}]}}, f)
        # The queue as builds 317-319 left it: 32 episode jobs on the pack named after the hash, and a stale card.
        state = {'jobs': [{'hash': PACK, 'name': PACK, 'title': PACK, 'kind': 'episode', 'season': '1', 'episode': str(n),
                           'episodes': [], 'status': 'new', 'files': [], 'watch_requested': 0, 'added': n, 'show_tmdb': TMDB}
                          for n in range(1, 33)],
                 'current': {'slot': 7, 'name': PACK, 'stage': 'copying', 'sent': 0, 'total': 100, 'updated': 1, 'count': 1}}
        # The download that put episode 2 into the hash folder, finished under build 314.
        state['jobs'].insert(0, {'hash': OLD2, 'name': OLD2, 'title': OLD2, 'kind': 'episode', 'season': '1', 'episode': '2',
                                 'episodes': [], 'status': 'done', 'watch_requested': 0, 'added': 0, 'show_tmdb': TMDB,
                                 'files': [{'path': '[Sub] Naruto Shippuuden - 002 [1080p].mkv', 'size': self.sizes[2], 'done': True,
                                            'drive_id': ep2, 'drive_name': '[Sub] Naruto Shippuuden - 002 [1080p].mkv', 'session': {}}]})
        debrid_drive.save(self.profile, state)
        # Episode 6 asked for again from two other torrents (Build Season, a hand pick).
        for h in ALT6:
            debrid_drive.queue(self.profile, {'id': h, 'name': 'Naruto Shippuden S01E06'}, 'episode', 'Naruto Shippuden',
                               season='1', episode='6', show_tmdb=TMDB)
        self.link = SlowLink(self.server, self.debrid, rng)
        self.drive = driveupload.Drive(lambda *a: 'token', self.server.send)
        self.drive.copy_piece = self.link
        self.link.max = PIECE
        self.clock = [1_000_000.0]
        self.log = []

    def tearDown(self):
        self.tmp.cleanup()

    def cards(self):
        names = {TMDB: SHOW}
        snap = work_state.build({'debrid': debrid_drive.load(self.profile), 'prep': {}, 'show_names': names}, self.clock[0])
        return [j['title'] for j in snap.get('jobs', [])]

    def run_queue(self, steps=400, close_after=None):
        pieces = [0]

        def going():
            pieces[0] += 1
            return close_after is None or pieces[0] < close_after
        titles = []
        for n in range(steps):
            converting = n < 30
            with patch.object(debrid_drive, 'conversion_running', lambda profile, now: converting), \
                 patch.object(debrid_drive, 'show_lookup', lambda profile: (lambda tmdb: SHOW if tmdb == TMDB else '')):
                delay = debrid_drive.step(self.profile, self.debrid, self.drive, keep_going=going, clock=lambda: self.clock[0],
                                          cancelled=lambda: transfer_control.cancelled_copies(self.profile),
                                          forget=lambda h: transfer_control.clear_cancelled(self.profile, h),
                                          log=self.log.append)
            titles += self.cards()
            if delay is None:
                return n, titles
            self.clock[0] += delay
            if close_after is not None and pieces[0] >= close_after:
                return n, titles
        return steps, titles

    def test_a_whole_season_arrives_once_named_after_the_show(self):
        # The app is closed in the middle of the copies, then opened again.
        self.run_queue(steps=3, close_after=40)
        steps, titles = self.run_queue()
        state = debrid_drive.load(self.profile)
        jobs = state['jobs']
        failed = [(j['episode'], j.get('error')) for j in jobs if j['status'] == 'failed']
        self.assertEqual(failed, [], self.log[-20:])
        self.assertTrue(all(j['status'] == 'done' for j in jobs), [(j['episode'], j['status']) for j in jobs])
        # Every episode of the season is on Drive exactly once, byte for byte, in one show folder.
        want = {n: blob('Naruto Shippuden (001-032)/Naruto Shippuden Episode %03d Title %d.mkv' % (n, n), self.sizes[n]) for n in range(1, 33)}
        want[2] = self.debrid.sources['https://debrid/L:%s:[Sub] Naruto Shippuuden - 002 [1080p].mkv' % OLD2[:6]][1]
        on_drive = {}
        for ident, item in self.server.videos().items():
            n = next((k for k, data in want.items() if data == item['data']), None)
            self.assertIsNotNone(n, 'unexpected file %s' % self.server.path(ident))
            on_drive.setdefault(n, []).append(self.server.path(ident))
        self.assertEqual(sorted(on_drive), list(range(1, 33)), 'missing: %s' % sorted(set(range(1, 33)) - set(on_drive)))
        self.assertEqual({n: len(p) for n, p in on_drive.items() if len(p) > 1}, {})       # nothing twice (episodes 2, 6)
        folders = {p.rsplit('/', 1)[0] for paths in on_drive.values() for p in paths}
        self.assertEqual(len(folders), 1, folders)
        folder = folders.pop()
        self.assertFalse(debrid_drive.is_hash(folder.rsplit('/', 1)[1]), folder)
        # No film, no sample from the pack.
        self.assertFalse(any('Movie' in p or 'sample' in p.lower() for paths in on_drive.values() for p in paths))
        # The pages never showed a hash or "Download".
        self.assertFalse([t for t in titles if debrid_drive.is_hash(t.split(' · ')[0]) or t.startswith('Download')], set(titles))
        # The hash-named folder of episode 2 is empty and in the Trash.
        live = [it['name'] for it in self.server.items.values() if it['mime'] == DriveServer.FOLDER and not it['trashed']]
        self.assertNotIn(OLD2, live)
        # The bad link was exercised.
        self.assertGreater(self.link.timeouts + self.link.late + self.link.drops, 15)
        self.assertTrue(self.link.timeouts and self.link.late and self.link.drops)

    def on_drive(self):
        out = {}
        for ident, item in self.server.videos().items():
            out.setdefault(item['data'], []).append(self.server.path(ident))
        return out

    def test_pick_better_versions_replaces_the_waiting_picks(self):
        # Owner (build 328): the waiting episodes get a better version; nothing is copied twice, nothing is lost.
        state = debrid_drive.load(self.profile)
        hashes, episodes = debrid_drive.repick_plan(state, SHOW, TMDB)
        self.assertIn(PACK, hashes)
        self.assertIn((1, 6), episodes)
        for h in hashes:
            transfer_control.cancel_copy(self.profile, h)
        self.run_queue(steps=2)
        left = [j for j in debrid_drive.load(self.profile)['jobs'] if j['hash'] in hashes and j['status'] not in ('done', 'failed')]
        self.assertEqual(left, [])
        # The new picks: one WEB release per episode, named S01Exx.
        for season, n in episodes:
            h = ('%02d' % n) * 20
            self.debrid.add_torrent(h, [('Naruto.Shippuden.S01E%02d.1080p.WEB.x264.mkv' % n, self.sizes[n])])
            debrid_drive.queue(self.profile, {'id': h, 'name': 'Naruto Shippuden S01E%02d' % n}, 'episode', SHOW,
                               season=str(season), episode=str(n), show_tmdb=TMDB)
        self.run_queue()
        copies = self.on_drive()
        for season, n in episodes:
            data = blob('Naruto.Shippuden.S01E%02d.1080p.WEB.x264.mkv' % n, self.sizes[n])
            # Episode 2 is on Drive already (the hash folder's copy): the new pick is not copied again.
            self.assertEqual(len(copies.get(data, [])), 0 if n == 2 else 1, 'episode %d' % n)
        old2 = self.debrid.sources['https://debrid/L:%s:[Sub] Naruto Shippuuden - 002 [1080p].mkv' % OLD2[:6]][1]
        self.assertEqual(len(copies.get(old2, [])), 1)
        self.assertFalse([p for paths in copies.values() for p in paths if 'Movie' in p])

    def test_a_new_build_season_names_and_files_everything(self):
        # From build 315 on, Build Season queues each episode with the show's title and TMDb id.
        debrid_drive.location(self.profile).write_text(json.dumps({'jobs': []}))   # an empty queue (save() merges)
        for n in range(1, 9):
            h = ('%02d' % (40 + n)) * 20
            self.debrid.add_torrent(h, [('Show.S02E%02d.1080p.WEB.mkv' % n, self.sizes[n]), ('Show.S02E%02d.sample.mkv' % n, PIECE)])
            debrid_drive.queue(self.profile, {'id': h, 'name': ''}, 'episode', 'Lanterns', season='2', episode=str(n), show_tmdb='99')
        self.run_queue()
        jobs = debrid_drive.load(self.profile)['jobs']
        self.assertEqual([j['status'] for j in jobs], ['done'] * 8)
        paths = sorted(p for paths in self.on_drive().values() for p in paths if 'Lanterns' in p)
        self.assertEqual(len(paths), 8)
        self.assertTrue(all(p.startswith('Kodi Downloads/TV Shows/Lanterns/') for p in paths), paths)

    def test_season_two_of_an_absolute_pack(self):
        # E12: "Naruto Shippuden Episode 045" is S2E13 (season 1 has 32); before, season 2+ copied nothing.
        debrid_drive.location(self.profile).write_text(json.dumps({'jobs': []}))
        h = 'b2' * 20
        files = [('Naruto Shippuden (001-500)/Season 02/Naruto Shippuden Episode %03d T.mkv' % n, PIECE * 3) for n in range(33, 54)]
        files += [('Naruto Shippuden (001-500)/Season 01/Naruto Shippuden Episode %03d T.mkv' % n, PIECE * 3) for n in (13, 14)]
        self.debrid.add_torrent(h, files)
        for n in (13, 14):
            debrid_drive.queue(self.profile, {'id': h, 'name': 'Naruto Shippuden S02E%02d' % n}, 'episode', SHOW, season='2', episode=str(n), show_tmdb=TMDB)
        with patch.object(debrid_drive, 'offset_lookup', lambda profile: (lambda job: 32 if job.get('season') == '2' else None)):
            self.run_queue()
        names = sorted(p.rsplit('/', 1)[1] for paths in self.on_drive().values() for p in paths if 'S02' in p)
        self.assertEqual(len(names), 2, names)
        self.assertTrue(names[0].endswith('Episode 045 T.mkv') and names[1].endswith('Episode 046 T.mkv'), names)

    def test_season_two_waits_when_tmdb_is_unknown(self):
        debrid_drive.location(self.profile).write_text(json.dumps({'jobs': []}))
        h = 'b3' * 20
        self.debrid.add_torrent(h, [('P/Naruto Shippuden Episode %03d.mkv' % n, PIECE) for n in range(1, 60)])
        debrid_drive.queue(self.profile, {'id': h, 'name': 'x'}, 'episode', SHOW, season='2', episode='1', show_tmdb=TMDB)
        with patch.object(debrid_drive, 'offset_lookup', lambda profile: (lambda job: None)):
            self.run_queue(steps=3)
        job = debrid_drive.load(self.profile)['jobs'][0]
        self.assertNotEqual(job['status'], 'failed')                          # waits, never a wrong file
        self.assertEqual(self.on_drive().get(blob('P/Naruto Shippuden Episode 001.mkv', PIECE), []), [])

    def test_up_next_goes_episode_by_episode(self):
        snap = work_state.build({'debrid': debrid_drive.load(self.profile), 'prep': {}, 'show_names': {TMDB: SHOW}}, self.clock[0])
        numbers = [int(re.search(r'E(\d+)', j['title']).group(1)) for j in snap.get('jobs', []) if re.search(r'E(\d+)', j['title'])]
        self.assertEqual(numbers, sorted(numbers))


if __name__ == '__main__':
    unittest.main()
