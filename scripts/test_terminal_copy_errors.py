"""Stop permanent copy failures immediately; keep transient and expired-session recovery available."""
import json
import io
import importlib.util
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import copy_errors as ce
import debrid_drive
import driveupload
import library_index


class Classification(unittest.TestCase):
    def test_terminal_notice_does_not_offer_an_unhelpful_retry(self):
        import notice_help
        model = notice_help.explain({'kind':'problem', 'title':"Couldn't download to Google Drive",
            'text':'Show · S1 E1: The refreshed download is a different file'})
        self.assertIn('different file', model['happened'])
        self.assertNotIn('retry_copies', [action for _, _, action in model['fixes']])

    def test_identity_and_integrity_mismatches_are_terminal(self):
        for text in ('The refreshed download is a different file', 'Google Drive has a different size for Episode.mkv',
                     'Invalid completed upload receipt', 'Invalid Drive confirmed position',
                     'Prepared video did not preserve resolution/HDR'):
            self.assertTrue(ce.is_terminal(RuntimeError(text)), text)
            self.assertTrue(ce.is_terminal('RuntimeError: ' + text), text)

    def test_http_rate_limits_and_server_errors_remain_retryable(self):
        for status in (408, 409, 425, 429, 500, 502, 503, 504):
            error = ce.http_error('Drive upload', status)
            self.assertFalse(ce.is_terminal(error))
            self.assertTrue(ce.is_retryable(error))
        for reason in ('rateLimitExceeded', 'userRateLimitExceeded', 'downloadQuotaExceeded'):
            error = ce.http_error('Drive upload', 403, json.dumps({'error': {'errors': [{'reason': reason}]}}).encode())
            self.assertFalse(ce.is_terminal(error), reason)
            self.assertTrue(ce.is_retryable(error), reason)

    def test_http_permission_storage_and_bad_input_need_owner_action(self):
        for status in (400, 405, 413, 415, 422):
            error = ce.http_error('Drive upload start', status)
            self.assertTrue(ce.is_terminal(error))
            self.assertFalse(ce.is_retryable(error))
        # ISSUE-298: sign-in, folder access and a full Drive wait for the owner; they never retire the copy.
        for status in (401, 403):
            error = ce.http_error('Drive upload start', status)
            self.assertTrue(ce.needs_owner(error));self.assertFalse(ce.is_terminal(error))
        error = ce.http_error('Drive upload', 403, {'error': {'errors': [{'reason': 'storageQuotaExceeded'}]}})
        self.assertIn('Free up space', str(error))
        self.assertTrue(ce.needs_owner(error));self.assertFalse(ce.is_terminal(error))
        # A saved source/AllDebrid text with an HTTP 4xx is not Drive's answer: never retired by the 4xx rule.
        self.assertFalse(ce.is_terminal('RuntimeError: AllDebrid HTTP 404 on the link'))
        self.assertTrue(ce.is_terminal('PermanentCopyError: Drive verification: HTTP 404. gone'))

    def test_expired_upload_session_can_restart(self):
        for status in (404, 410):
            error = ce.http_error('Drive upload', status)
            self.assertTrue(error.restart_session)
            self.assertTrue(ce.is_retryable(error))
            self.assertFalse(ce.is_terminal(error))
            self.assertTrue(ce.is_terminal(ce.http_error('Drive verification', status)))

    def test_incomplete_confirmations_and_metadata_wait_are_not_terminal(self):
        for text in ('Drive did not confirm the upload', 'The download stopped before the end; it will carry on',
                     'Waiting for TMDb to say where season 2 starts', 'Drive upload: HTTP 503'):
            self.assertFalse(ce.is_terminal(RuntimeError(text)), text)
        # HTTP 200 with no Location is an incomplete response, not proof the source is invalid.
        self.assertTrue(ce.is_retryable(ce.http_error('Drive upload start', 200)))

    def test_sign_in_needs_owner_but_a_busy_refresh_does_not(self):
        SignedOut = type('SignedOut', (RuntimeError,), {})
        RefreshBusy = type('RefreshBusy', (RuntimeError,), {})
        self.assertFalse(ce.is_terminal(SignedOut('Please sign in again')))   # ISSUE-298: waits for the owner
        self.assertTrue(ce.needs_owner(SignedOut('Please sign in again')))
        self.assertFalse(ce.is_terminal(RefreshBusy('Waiting for sign-in server')))
        self.assertTrue(ce.is_retryable(RefreshBusy('Waiting for sign-in server')))

    def test_http_body_is_not_copied_into_the_problem(self):
        error = ce.http_error('Drive upload', 403, {'error': {'message': 'private://SECRET', 'errors': [{'reason': 'forbidden'}]}})
        self.assertNotIn('SECRET', str(error))
        self.assertIn('refused access', str(error))


class CopyWorker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name

    def queued(self, count=1):
        for n in range(1, count + 1):
            debrid_drive.queue(self.profile, {'id': str(n) * 40, 'name': 'Show.S01E%02d' % n},
                               'episode', 'Show', season='1', episode=str(n))
        state = debrid_drive.load(self.profile)
        for n, job in enumerate(state['jobs'], 1):
            job.update(status='copying', magnet=str(n), files=[{'path': 'Show.S01E%02d.mkv' % n, 'size': 3,
                                                              'link': str(n), 'done': False, 'session': {}}])
        debrid_drive.save(self.profile, state)
        return types.SimpleNamespace(unlock=lambda link: ('https://source/file', 'Show.S01E%02d.mkv' % int(link), 3))

    def test_terminal_error_never_enters_inline_or_later_retries(self):
        for error in (ce.PermanentCopyError('The refreshed download is a different file'),
                      RuntimeError('Invalid completed upload receipt'), RuntimeError('Invalid Drive confirmed position')):
            with self.subTest(error=str(error)):
                api = self.queued()
                calls, notified, logs = [], [], []

                def upload(*args, **kwargs):
                    calls.append(1)
                    raise error
                drive = types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload)
                debrid_drive.step(self.profile, api, drive, notify=lambda *args: notified.append(args), log=logs.append)
                state = debrid_drive.load(self.profile)
                self.assertEqual((len(calls), state['jobs'][0]['status'], state['jobs'][0]['terminal']), (1, 'failed', True))
                self.assertEqual(state['jobs'][0].get('tries', 0), 0)
                self.assertEqual(len(debrid_drive.problems(state)), 1)
                self.assertIn(str(error), debrid_drive.problems(state)[0]['error'])
                self.assertEqual(notified[0][0], 'problem')
                self.assertFalse(any('trying it again after the others' in line for line in logs))
                debrid_drive.step(self.profile, api, drive)
                self.assertEqual(len(calls), 1)
                debrid_drive.location(self.profile).unlink()

    def test_different_drive_size_is_a_problem_after_one_attempt(self):
        api = self.queued()
        calls = []

        def upload(*args, **kwargs):
            calls.append(1)
            return {'id': 'file', 'size': 4}
        debrid_drive.step(self.profile, api, types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload))
        state = debrid_drive.load(self.profile)
        self.assertEqual((len(calls), state['jobs'][0]['status']), (1, 'failed'))
        self.assertIn('different size', debrid_drive.problems(state)[0]['reason'])
        self.assertEqual(state['jobs'][0]['invalid_drive_id'], 'file')

    def test_signed_out_copy_waits_for_the_owner_and_keeps_its_place(self):
        # ISSUE-298 (review of PR #30): a sign-out retired every queued copy for good.
        api = self.queued()
        def upload(*args, **kwargs):
            raise driveupload.SignedOut('Sign in to Google Drive again')
        drive = types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload)
        wait = debrid_drive.step(self.profile, api, drive, notify=lambda *a: None, log=lambda t: None)
        job = debrid_drive.load(self.profile)['jobs'][0]
        self.assertNotEqual(job['status'], 'failed');self.assertFalse(job.get('terminal'))
        self.assertEqual((wait, job.get('tries', 0)), (ce.OWNER_WAIT, 0))
        self.assertGreater(job['retry_at'], 0)
        self.assertEqual(debrid_drive.problems(debrid_drive.load(self.profile)), [])

    def test_saved_terminal_runtime_error_stops_before_unlock_or_upload(self):
        for text in ('RuntimeError: The refreshed download is a different file',
                     'RuntimeError: Google Drive has a different size for this video'):
            with self.subTest(text=text):
                api = self.queued()
                state = debrid_drive.load(self.profile)
                state['jobs'][0].update(error=text, tries=10)
                debrid_drive.save(self.profile, state)
                calls = []

                def forbidden(*args, **kwargs):
                    calls.append(1)
                    raise AssertionError('Saved terminal failure was retried')
                api.unlock = forbidden
                drive = types.SimpleNamespace(folder=forbidden, upload_stream=forbidden)
                self.assertEqual(debrid_drive.step(self.profile, api, drive), 1)
                self.assertEqual(calls, [])
                state = debrid_drive.load(self.profile)
                self.assertEqual((state['jobs'][0]['status'], state['jobs'][0]['terminal']), ('failed', True))
                self.assertEqual(len(debrid_drive.problems(state)), 1)
                debrid_drive.location(self.profile).unlink()

    def test_saved_transient_runtime_error_still_has_a_recovery_attempt(self):
        for text in ('RuntimeError: Drive upload: HTTP 503', 'ConnectionError: connection reset',
                     'RuntimeError: Drive upload: HTTP 401'):
            with self.subTest(text=text):
                api = self.queued()
                state = debrid_drive.load(self.profile)
                state['jobs'][0].update(error=text)
                debrid_drive.save(self.profile, state)
                calls = []

                def upload(*args, **kwargs):
                    calls.append(1)
                    return {'id': 'complete', 'size': 3}
                debrid_drive.step(self.profile, api, types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload))
                self.assertEqual(calls, [1])
                self.assertEqual(debrid_drive.load(self.profile)['jobs'][0]['status'], 'done')
                debrid_drive.location(self.profile).unlink()

    def test_transient_failure_keeps_session_and_completes_on_next_inline_attempt(self):
        api = self.queued()
        sessions = []

        def upload(source, size, name, parent, session, save, going, progress, **kwargs):
            sessions.append(dict(session))
            if len(sessions) == 1:
                session.update(url='https://upload/session', size=size, confirmed=1)
                save()
                raise ce.http_error('Drive upload', 503)
            progress(size, size)
            return {'id': 'completed', 'size': size}
        debrid_drive.step(self.profile, api, types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload))
        self.assertEqual(debrid_drive.load(self.profile)['jobs'][0]['status'], 'done')
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[1]['confirmed'], 1)

    def test_companion_terminal_failure_is_isolated_and_main_failure_does_not_hide_completed_companion(self):
        for bad_episode in (1, 2):
            with self.subTest(bad_episode=bad_episode):
                api = self.queued(2)
                calls, finished = {}, []

                def upload(source, size, name, *args, **kwargs):
                    calls[name] = calls.get(name, 0) + 1
                    if 'E%02d' % bad_episode in name:
                        raise ce.PermanentCopyError('Google Drive has a different size for this video')
                    return {'id': 'completed', 'size': size}
                debrid_drive.step(self.profile, api, types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload),
                                   on_done=lambda job: finished.append(job['episode']))
                jobs = debrid_drive.load(self.profile)['jobs']
                self.assertEqual([j['status'] for j in jobs], ['failed', 'done'] if bad_episode == 1 else ['done', 'failed'])
                self.assertEqual(list(calls.values()), [1, 1])
                self.assertEqual(finished, [str(3 - bad_episode)])
                debrid_drive.location(self.profile).unlink()

    def test_refreshed_source_identity_is_checked_before_retrying_the_copy(self):
        api = self.queued()
        unlocked = []

        def unlock(link):
            unlocked.append(link)
            return 'https://source/file', 'Show.S01E01.mkv' if len(unlocked) == 1 else 'Other.S01E01.mkv', 3
        api.unlock = unlock
        calls = []

        def upload(source, *args, **kwargs):
            calls.append(1)
            return source(0)

        def expired(url, offset):
            raise urllib.error.HTTPError(url, 403, 'expired', {}, io.BytesIO())
        debrid_drive.step(self.profile, api, types.SimpleNamespace(folder=lambda parts: 'folder', upload_stream=upload), open_url=expired)
        state = debrid_drive.load(self.profile)
        self.assertEqual((len(calls), len(unlocked), state['jobs'][0]['status']), (1, 2, 'failed'))
        self.assertIn('different file', debrid_drive.problems(state)[0]['reason'])

    def test_an_expired_access_token_is_renewed_before_terminal_classification(self):
        tokens, calls = [], []

        def token(rejected=None):
            tokens.append(rejected)
            return 'fresh' if rejected else 'expired'

        def send(method, url, body, headers):
            calls.append(headers['Authorization'])
            return (200, {}, b'{"files": [{"id": "folder"}]}') if headers['Authorization'] == 'Bearer fresh' else (401, {}, b'{}')
        drive = driveupload.Drive(token, send)
        self.assertEqual(drive.folder(['Kodi Downloads']), 'folder')
        self.assertEqual(tokens, [None, 'expired'])
        self.assertEqual(calls, ['Bearer expired', 'Bearer fresh'])

    def test_actual_native_receipt_and_confirmed_position_are_terminal(self):
        for answer in ((200, {}, b'{"id":"wrong-size","size":"9"}'), (308, {'Range': 'bytes=0-9'}, b'')):
            drive = driveupload.Drive(lambda rejected=None: 'token', None)
            with self.assertRaises(ce.PermanentCopyError) as caught:
                drive._native_stream(lambda *args, **kwargs: answer, 3, {'url': 'https://upload/session'}, 0,
                                     lambda: None, lambda: True, lambda *args: None, lambda *args: None)
            self.assertEqual(caught.exception.invalid_drive_id, 'wrong-size' if answer[0] == 200 else '')

    def test_completed_resume_receipt_and_malformed_ranges_do_not_loop(self):
        for body in (b'{}', b'{"id":"file","size":"wrong"}', b'not JSON'):
            drive = driveupload.Drive(lambda rejected=None: 'token', lambda *args: (200, {}, body))
            with self.assertRaises(ce.PermanentCopyError):
                drive.upload_stream(lambda offset: io.BytesIO(b'abc'), 3, 'video.mkv', 'folder',
                                    {'url': 'https://upload/session', 'size': 3}, lambda: None)
        for value in ('invalid', 'bytes=10-20', 'bytes=0--1', 'bytes=0-10'):
            with self.assertRaises(ce.PermanentCopyError):
                driveupload._next_offset({'Range': value}, 3)

    def test_prepared_resolution_mismatch_is_not_hidden_by_plain_copy_fallback(self):
        from test_debrid_ready import Native, Stream
        from test_drive_prepare import Drive
        import debrid_ready
        drive, native, stream = Drive(), Native(), Stream()
        probe = native.probe

        def mismatched(url):
            info = probe(url)
            if info.get('ready'):
                info['width'] = 640
            return info
        native.probe = mismatched
        queue = types.SimpleNamespace(native=native, stream=stream, drive=drive,
                                      layout_probe=lambda *args: {'fast_open': False})
        with self.assertRaises(ce.PermanentCopyError):
            debrid_ready.copy(queue, self.profile, lambda action: action('https://source/video'), 'Show.S01E01.mkv', 1000,
                              'folder', lambda: True, lambda *args: None, 'synthetic')
        self.assertEqual(list(drive.files), ['source'])


class PhoneUploads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name
        self.state_path = Path(self.profile) / 'addon_data/service.kodi.ios.bootstrap/drive-uploads.json'
        self.state_path.parent.mkdir(parents=True)
        self.path = Path(self.profile) / 'phone' / 'Show.S01E05.mkv'
        self.path.parent.mkdir()
        self.path.write_bytes(b'video')
        self.calls, self.fail, self.notified = [], True, []

        def upload(path, parent, sessions, save, *args, **kwargs):
            self.calls.append(path)
            if self.fail:
                raise ce.http_error('Drive upload', 403)
            return {'id': 'complete', 'size': Path(path).stat().st_size}
        self.drive = types.SimpleNamespace(folder=lambda parts: 'folder', upload=upload)

    def run_pass(self):
        with patch.object(driveupload, 'pending', return_value=[(str(self.path), ['Kodi Downloads', 'TV Shows', 'Show'])]):
            return driveupload.run_once(str(self.path.parent), self.drive, str(self.state_path), lambda text: None,
                                        delete_after=False, notify=lambda *args: self.notified.append(args))

    def test_unchanged_file_stops_after_one_attempt_and_matches_shared_problems(self):
        self.assertEqual(self.run_pass(), 0)
        self.assertEqual(self.run_pass(), 0)
        self.assertEqual(self.calls, [str(self.path)])
        self.assertEqual(len(self.notified), 1)
        self.assertTrue(self.path.exists())
        saved = json.loads(self.state_path.read_text())
        self.assertEqual(saved['failures'][str(self.path)]['fp'], list(driveupload.fingerprint(self.path)))
        debrid = debrid_drive.load(self.profile)
        problems = debrid_drive.problems(debrid)
        self.assertEqual((len(problems), problems[0]['source'], problems[0]['terminal']), (1, 'phone', True))
        index = library_index.refresh(self.profile)
        self.assertEqual(library_index.counts(index)['problems'], 1)
        self.assertEqual(index['videos'][0]['reason'], problems[0]['error'])
        self.assertEqual(index['videos'][0]['episode'], 5)

    def test_changed_fingerprint_clears_old_problem_and_allows_fresh_upload(self):
        self.run_pass()
        self.path.write_bytes(b'a changed video')
        self.fail = False
        self.assertEqual(self.run_pass(), 1)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(debrid_drive.problems(debrid_drive.load(self.profile)), [])
        self.assertEqual(json.loads(self.state_path.read_text())['failures'], {})
        self.assertTrue(self.path.exists())

    def test_manual_retry_wakes_phone_uploader_without_sending_a_synthetic_hash_to_alldebrid(self):
        self.run_pass()
        problems = debrid_drive.problems(debrid_drive.load(self.profile))
        self.assertEqual(debrid_drive.retry_failed(self.profile, only={problems[0]['key']}), 1)
        self.assertEqual(debrid_drive.load(self.profile)['jobs'], [])

        def forbidden(*args):
            raise AssertionError('A phone upload was sent to AllDebrid')
        self.assertIsNone(debrid_drive.step(self.profile, types.SimpleNamespace(add=forbidden), self.drive))
        self.fail = False
        self.assertEqual(self.run_pass(), 1)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(json.loads(self.state_path.read_text())['failures'], {})

    def test_one_phone_problem_does_not_hold_other_files(self):
        good = self.path.with_name('Show.S01E06.mkv')
        good.write_bytes(b'good video')
        upload = self.drive.upload

        def mixed(path, *args, **kwargs):
            if path == str(good):
                self.calls.append(path)
                return {'id': 'complete', 'size': good.stat().st_size}
            return upload(path, *args, **kwargs)
        self.drive.upload = mixed
        with patch.object(driveupload, 'pending', return_value=[(str(p), ['Kodi Downloads']) for p in (self.path, good)]):
            count = driveupload.run_once(str(self.path.parent), self.drive, str(self.state_path), lambda text: None, delete_after=False)
        self.assertEqual(count, 1)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(good.exists())

    def assert_invalid_upload(self):
        state = debrid_drive.load(self.profile)
        problem = debrid_drive.problems(state)[0]
        self.assertEqual(state['jobs'][0]['invalid_drive_id'], 'invalid-upload')
        bad = {'id': 'invalid-upload', 'name': self.path.name, 'size': 5}
        index = library_index.build([bad], {}, state)
        self.assertEqual(index['videos'][0]['state'], library_index.PROBLEM)
        self.assertEqual(index['videos'][0]['problem_key'], problem['key'])
        self.assertEqual(index['videos'][0]['reason'], problem['error'])
        self.assertEqual(library_index.counts(index)['problems'], 1)
        spec = importlib.util.spec_from_file_location('terminal_copy_problems', ROOT / 'migration/bundled-bootstrap/copy_problems.py')
        copy_problems = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy_problems)
        self.assertEqual(len(copy_problems.from_index(self.profile, [problem], index)), 1)
        import problem_ignore
        ignored = {problem['key']: problem_ignore.signature(problem)}
        hidden = library_index.build([bad], {}, state, ignored=ignored)
        self.assertTrue(hidden['videos'][0]['hidden'])
        self.assertEqual(library_index.counts(hidden)['hidden'], 1)
        # Another verified version wins, regardless of which Drive file is listed first.
        good = dict(bad, id='known-good')
        for listing in ([bad, good], [good, bad]):
            index = library_index.build(listing, {}, state)
            self.assertEqual((index['videos'][0]['id'], index['videos'][0]['state']), ('known-good', library_index.READY))
            self.assertEqual(index['duplicates'], ['invalid-upload'])
            self.assertEqual(copy_problems.from_index(self.profile, [problem], index), [])
        self.assertTrue(self.path.exists())

    def test_wrong_size_upload_present_on_drive_stays_a_problem(self):
        self.drive.upload = lambda *args, **kwargs: {'id': 'invalid-upload', 'size': 99}
        self.run_pass()
        self.assert_invalid_upload()

    def test_wrong_checksum_upload_present_on_drive_stays_a_problem(self):
        self.drive.upload = lambda *args, **kwargs: {'id': 'invalid-upload', 'size': self.path.stat().st_size}
        with patch.object(driveupload, 'pending', return_value=[(str(self.path), ['Kodi Downloads'])]), patch.object(driveupload, 'confirmed', return_value=False):
            driveupload.run_once(str(self.path.parent), self.drive, str(self.state_path), lambda text: None, delete_after=True)
        self.assert_invalid_upload()

    def test_permission_error_does_not_mark_a_preexisting_good_copy_invalid(self):
        self.run_pass()
        state = debrid_drive.load(self.profile)
        self.assertNotIn('invalid_drive_id', state['jobs'][0])
        index = library_index.build([{'id': 'known-good', 'name': self.path.name, 'size': 5}], {}, state)
        self.assertEqual(index['videos'][0]['state'], library_index.READY)


if __name__ == '__main__':
    unittest.main()
