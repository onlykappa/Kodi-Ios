"""ISSUE-294: C1 exact folding, N2 durable bounded timeline and Q2 progressive exact episode coverage, no layouts."""
import copy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'migration/bundled-bootstrap/resources/lib')]
import notice_help
import notice_models
import season_check
import season_sheet
import season_sources


class Notices(unittest.TestCase):
    def test_fold_exact_matches_without_mutating_store(self):
        items = [{'id': 'old', 'time': 1, 'kind': 'problem', 'title': 'Copy stopped', 'text': 'No reply', 'count': 21, 'read': False},
                 {'id': 'new', 'time': 2, 'kind': 'problem', 'title': 'Copy stopped', 'text': 'No reply', 'count': 21, 'read': True},
                 {'id': 'different', 'time': 3, 'kind': 'info', 'title': 'Copy stopped', 'text': 'No reply'},
                 {'id': 'long', 'time': 4, 'kind': 'info', 'title': 'Long', 'text': 'A long message. ' * 12}]
        before = copy.deepcopy(items)
        folded = notice_help.folded(items)
        self.assertEqual(items, before)
        row = next(r for r in folded if r['id'] == 'new')
        self.assertEqual((row['count'], row['lines'], row['unread'], row['ids']), (2, 2, True, ['new', 'old']))
        self.assertEqual(folded[0]['lines'], 3)
        self.assertEqual(len(folded), 3)

    def test_three_real_steps_survive_reload_and_multi_episode_starts_fold(self):
        with tempfile.TemporaryDirectory() as profile:
            base = {'batch': 'fixture-season', 'title': 'Sample Show', 'season': '3'}
            for n in range(1, 4):
                notice_models.record_step(profile, dict(base, hash='fixture-%d' % n, episode=str(n)), 'copying',
                                          '1 episode started copying', 1000 + n)
            notice_models.record_step(profile, base, 'problem', 'AllDebrid stopped answering', 1120)
            notice_models.record_step(profile, base, 'retry', 'Tries again in 5 min', 1420)
            item = {'group': 'fixture-season', 'kind': 'problem', 'title': "Couldn't download to Google Drive", 'text': 'No reply'}
            model = notice_help.detail_model(item, profile=profile)
            timeline = model['timeline']
            self.assertEqual([s['text'] for s in timeline], ['3 episodes started copying', 'AllDebrid stopped answering', 'Tries again in 5 min'])
            self.assertEqual([s['colour_kind'] for s in timeline], ['blue', 'orange', 'orange'])
            self.assertEqual(timeline[0]['at'], 1001)
            self.assertRegex(timeline[0]['time'], r'^\d{2}:\d{2}$')
            notice_models.record_step(profile, base, 'problem', 'Still no reply', 1720)
            self.assertEqual(len(notice_help.detail_model(item, profile=profile)['timeline']), 3)
            self.assertEqual(notice_help.detail_model(item, profile=profile)['timeline'][0]['text'], '3 episodes started copying')

    def test_pack_files_and_single_episode_notices_find_their_steps(self):
        with tempfile.TemporaryDirectory() as profile:
            job = {'hash': 'pack', 'title': 'Sample Show', 'kind': 'season', 'season': '3', 'batch': 'pack-batch'}
            for n in range(1, 4):
                notice_models.record_step(profile, dict(job, timeline_file='S03E%02d.mkv' % n), 'copying', 'Copy started', 1000+n)
            row = notice_help.detail_model({'group': 'pack-batch'}, profile=profile)
            self.assertEqual(row['timeline'][0]['text'], '3 episodes started copying')
            job = dict(job, kind='episode', episode='1', batch='')
            notice_models.record_step(profile, job, 'copying', 'Copy started', 1100)
            self.assertTrue(notice_help.detail_model({'text': 'Sample Show · S3 E1'}, profile=profile)['timeline'])

    def test_copier_produces_timeline_without_touching_notice_store(self):
        import debrid_drive
        with tempfile.TemporaryDirectory() as profile:
            debrid_drive.queue(profile, {'id': 'f' * 40, 'name': 'Sample.S01E01.mkv'}, 'episode', 'Sample', season='1', episode='1')
            state = debrid_drive.load(profile)
            state['jobs'][0].update(status='copying', magnet='fixture', batch='fixture-batch',
                files=[{'path':'Sample.S01E01.mkv', 'size':3, 'link':'fixture', 'done':False, 'session':{}}])
            debrid_drive.save(profile, state)
            def fail(*args, **kwargs): raise ConnectionError('AllDebrid stopped answering')
            api = types.SimpleNamespace(unlock=lambda _: ('https://example.invalid/file', 'Sample.S01E01.mkv', 3))
            drive = types.SimpleNamespace(folder=lambda _: 'fixture-folder', upload_stream=fail)
            debrid_drive.step(profile, api, drive, clock=lambda: 1000)
            model = notice_help.detail_model({'group':'fixture-batch'}, profile=profile)
            self.assertEqual([s['kind'] for s in model['timeline']], ['copying','problem','retry'])
            self.assertIn('Tries again', model['timeline'][-1]['text'])
            self.assertFalse((Path(profile) / 'addon_data/service.kodi.ios.bootstrap/notices.json').exists())

    def test_no_invented_times_and_explicit_timeline_is_exposed_by_explain(self):
        self.assertEqual(notice_help.explain({'text': 'Waiting'})['timeline'], [])
        item = {'timeline': [{'at': 1000, 'kind': 'retry', 'text': 'Tries again in 5 min'}]}
        self.assertEqual(notice_help.explain(item)['timeline'][0]['kind'], 'retry')
        records = [{'time': n, 'text': 'Step %d' % n, 'level': 'info'} for n in range(1000, 1005)]
        self.assertEqual([s['at'] for s in notice_help.detail_model({}, records)['timeline']], [1000, 1003, 1004])


class Quality(unittest.TestCase):
    def test_each_answer_changes_exact_quality_counts_and_pending(self):
        survey = season_check.Survey([1, 2, 3])
        survey.record(1, {'qualities': ['1080p', '720p']})
        model = survey.model()
        self.assertEqual([r['found'] for r in model['qualities']], [0, 1, 1])
        self.assertEqual(model['pending'], 2)
        self.assertEqual(model['checking_qualities'], ['4k', '1080p', '720p'])
        props = season_sheet.checking_props('Sample', 3, 3, [1, 2, 3], 1, {'coverage': model})
        self.assertEqual(props['check.quality.2.text'], '1 of 3 episodes found')
        self.assertNotIn('Looking at', ' '.join(props.values()))
        survey.record(2, {'qualities': ['480p']})  # does not claim an exact 720p match
        survey.record(3, {})  # an empty error response is unknown, never proof a quality doesn't exist
        model = survey.model()
        self.assertEqual([r['found'] for r in model['qualities']], [0, 1, 1])
        self.assertEqual(model['checking_qualities'], [])
        self.assertEqual(model['unknown'], 1)
        self.assertTrue(all(r['state'] == 'incomplete' for r in model['qualities']))

    def test_builder_publishes_answers_before_finish_and_checks_entire_season(self):
        seen, called = [], []
        def choose(gui, title, season, count, check, wait):
            check(lambda done, states: seen.append(states['coverage']), lambda: False)
            return None  # reading data does not queue anything
        def search(episode, purpose, quality):
            called.append((episode, purpose))
            return {'qualities': ['1080p'] if episode % 2 else ['720p']}
        xbmc = types.SimpleNamespace(Monitor=lambda: types.SimpleNamespace(waitForAbort=lambda _: False))
        with tempfile.TemporaryDirectory() as profile, patch.object(season_sheet, 'pick_quality', side_effect=choose):
            result = season_sources._build(xbmc, None, None, None, profile, 'fixture', 'Sample', 3,
                                          list(range(1, 6)), set(), {}, search)
        self.assertEqual(result, [])
        self.assertEqual(called, [(n, 'scan') for n in range(1, 6)])
        self.assertTrue(any(m['completed'] == 1 and m['pending'] == 4 for m in seen))
        self.assertEqual([r['found'] for r in seen[-1]['qualities']], [0, 3, 2])
        self.assertEqual(seen[-1]['pending'], 0)


if __name__ == '__main__': unittest.main()
