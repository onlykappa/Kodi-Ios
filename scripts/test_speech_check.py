"""ISSUE-347 (owner: "match subtitle check needs to be added"): subtitles are checked against the words the phone hears
in the video (Apple's speech recognition, on the phone only). The native sound reading is covered by the C host
tests (test_speech_sound); this covers the matching, the timing fix, the download flow and the framework calls."""
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB))
import speech_check as sc  # noqa: E402
import subtitle_match as sm  # noqa: E402

VOCAB = ('river lantern tunnel grandfather money sunrise rope downstairs carefully matters house built never coming '
         'quiet kitchen letter window horses winter bridge garden secret doctor village captain train morning station '
         'music market island ocean mountain forest candle mirror stairs promise brother sister mother father').split()


def scene(offset=0.0, seed=1, lines=40):
    """(SRT bytes, recognizer JSON): speech `offset` seconds after its cues."""
    rnd = random.Random(seed)
    text = [' '.join(rnd.choice(VOCAB) for _ in range(6)) for _ in range(lines)]
    srt, words, t = [], [], 100.0
    for i, line in enumerate(text):
        srt.append('%d\n%s --> %s\n<i>%s</i>\n' % (i + 1, sc._fmt_srt(t), sc._fmt_srt(t + 2.5), line))
        words += [{'w': w.capitalize(), 't': t + .3 + .35 * k + offset, 'd': .25} for k, w in enumerate(line.split())]
        t += 4 + rnd.random() * 3
    return '\n'.join(srt).encode(), {'status': 'ok', 'words': words}


class Matching(unittest.TestCase):
    def test_words_are_normalised(self):
        self.assertEqual(sc.words_of("<i>The River's {\\an8}COLD</i> and I"), ['rivers', 'cold'])

    def test_srt_vtt_and_ass_cues(self):
        data, _ = scene(lines=3)
        cues = sc.cues(data, 'a.srt')
        self.assertEqual(len(cues), 3)
        self.assertAlmostEqual(cues[0][0], 100.0)
        vtt = 'WEBVTT\n\n00:01:40.000 --> 00:01:42.500\nHello river\n'
        self.assertEqual(sc.cues(vtt, 'a.vtt'), [(100.0, 102.5, {'hello', 'river'})])
        ass = ('[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
               'Dialogue: 0,0:01:40.00,0:01:42.50,Default,,0,0,0,,{\\bord4}Hello, river\\Nlantern\n')
        self.assertEqual(sc.cues(ass, 'a.ass'), [(100.0, 102.5, {'hello', 'river', 'lantern'})])

    def test_in_time_it_fits(self):
        data, said = scene()
        fit = sc.compare(sc.heard(said), sc.cues(data, 'a.srt'))
        self.assertEqual(sc.verdict(fit), ('fits', 0.0))

    def test_out_of_time_it_is_shifted_and_then_fits(self):
        for offset in (3.0, -7.5, 25.0):
            data, said = scene(offset)
            spoken = sc.heard(said)
            how, seconds = sc.verdict(sc.compare(spoken, sc.cues(data, 'a.srt')))
            self.assertEqual(how, 'shift')
            self.assertAlmostEqual(seconds, offset, delta=.25)
            moved = sc.shift_file(data, 'a.srt', seconds)
            self.assertEqual(sc.verdict(sc.compare(spoken, sc.cues(moved, 'a.srt')))[0], 'fits')

    def test_another_films_subtitle_is_a_mismatch(self):
        _, said = scene(seed=1)
        other = '\n'.join('%d\n%s --> %s\nSpaceship engines failing number %d\n' % (i, sc._fmt_srt(100 + 4 * i), sc._fmt_srt(102 + 4 * i), i)
                          for i in range(60))
        self.assertEqual(sc.verdict(sc.compare(sc.heard(said), sc.cues(other, 'b.srt')))[0], 'mismatch')

    def test_a_recognizer_that_gets_half_the_words_still_fits(self):
        data, said = scene(4.0)
        rnd = random.Random(7)
        said['words'] = [dict(w, w='mumble') if rnd.random() < .5 else w for w in said['words']]
        how, seconds = sc.verdict(sc.compare(sc.heard(said), sc.cues(data, 'a.srt')))
        self.assertEqual(how, 'shift')
        self.assertAlmostEqual(seconds, 4.0, delta=.25)

    def test_too_few_words_make_no_claim(self):
        data, said = scene()
        said['words'] = said['words'][:5]
        self.assertIsNone(sc.compare(sc.heard(said), sc.cues(data, 'a.srt')))
        self.assertEqual(sc.verdict(None), ('unknown', 0.0))

    def test_repeating_lines_do_not_give_a_timing(self):
        line = 'river lantern tunnel grandfather money sunrise'
        srt = '\n'.join('%d\n%s --> %s\n%s\n' % (i, sc._fmt_srt(100 + 8 * i), sc._fmt_srt(102.5 + 8 * i), line) for i in range(20))
        said = {'words': [{'w': w, 't': 103 + 8 * i + .3 * k, 'd': .2} for i in range(20) for k, w in enumerate(line.split())]}
        fit = sc.compare(sc.heard(said), sc.cues(srt, 'a.srt'))
        self.assertFalse(fit['confident'])
        self.assertNotEqual(sc.verdict(fit)[0], 'shift')


class Shifting(unittest.TestCase):
    def test_srt_vtt_ass(self):
        self.assertIn(b'00:01:43,250 --> 00:01:45,750', sc.shift_file(b'1\n00:01:40,000 --> 00:01:42,500\nHi\n', 'a.srt', 3.25))
        self.assertIn('00:01:36.000 --> 00:01:38.500', sc.shift_file('WEBVTT\n\n00:01:40.000 --> 00:01:42.500\nHi\n', 'a.vtt', -4))
        ass = 'Dialogue: 0,0:01:40.00,0:01:42.50,Default,,0,0,0,,Hi, there, friend\n'
        self.assertEqual(sc.shift_file(ass, 'a.ass', 1.5), 'Dialogue: 0,0:01:41.50,0:01:44.00,Default,,0,0,0,,Hi, there, friend\n')

    def test_never_before_zero(self):
        self.assertIn(b'00:00:00,000 --> 00:00:01,000', sc.shift_file(b'1\n00:00:02,000 --> 00:00:05,000\nHi\n', 'a.srt', -4))


class Download(unittest.TestCase):
    video = {'duration': 3000, 'language': 'en', 'season': None, 'episode': None}

    def test_a_mismatch_is_skipped_and_the_next_one_is_shifted_into_time(self):
        good, said = scene(2.0, lines=60)
        wrong = '\n'.join('%d\n%s --> %s\nSpaceship engines failing number %d\n' % (i + 1, sc._fmt_srt(100 + 4 * i), sc._fmt_srt(102 + 4 * i), i)
                          for i in range(400)).encode()
        filler = b''.join(b'%d\n%s --> %s\nfiller line\n\n' % (900 + i, sc._fmt_srt(400 + 6 * i).encode(), sc._fmt_srt(402 + 6 * i).encode()) for i in range(400))
        results = [{'source': 'subdl', 'id': 'wrong', 'filename': 'Film.2020.srt'},
                   {'source': 'subdl', 'id': 'good', 'filename': 'Film.2020.srt'}]
        files = {'wrong': wrong, 'good': good + b'\n' + filler}
        video = dict(self.video, heard=sc.heard(said))
        result, name, data = sm.choose_download(results, lambda r: ('Film.2020.srt', files[r['id']]), video)
        self.assertEqual(result['id'], 'good')
        self.assertEqual(result['match_speech'], 'shift')
        self.assertAlmostEqual(result['match_speech_shift'], 2.0, delta=.25)
        self.assertEqual(results[0]['match_speech'], 'mismatch')
        self.assertEqual(results[0]['match_reason'], 'Words do not match the speech')
        self.assertEqual(sc.verdict(sc.compare(video['heard'], sc.cues(data, name)))[0], 'fits')

    def test_without_heard_words_nothing_changes(self):
        good, _ = scene(lines=60)
        filler = b''.join(b'%d\n%s --> %s\nfiller line\n\n' % (900 + i, sc._fmt_srt(400 + 6 * i).encode(), sc._fmt_srt(402 + 6 * i).encode()) for i in range(400))
        result, _, data = sm.choose_download([{'source': 's', 'id': 1}], lambda r: ('a.srt', good + b'\n' + filler), self.video)
        self.assertNotIn('match_speech', result)
        self.assertEqual(data, good + b'\n' + filler)


class FakeLib:
    def __init__(self, answers, allowed=1):
        self.answers, self.allowed, self.calls = list(answers), allowed, []
        lib = self

        class Fn:
            def __init__(self, fn):
                self.fn = fn

            def __call__(self, *a):
                return self.fn(*a)
        self.kodi_speech_authorize = Fn(lambda seconds: lib.allowed)
        self.kodi_speech_words = Fn(self._words)

    def _words(self, url, audio, start, seconds, budget, locale, out, size):
        self.calls.append((url, audio, start, seconds, budget, locale))
        data = json.dumps(self.answers.pop(0)).encode()
        out.value = data
        return len(data)


class Listening(unittest.TestCase):
    def test_only_for_sound_in_the_subtitle_language(self):
        self.assertTrue(sc.wanted({'language': 'en'}, 'eng'))
        self.assertFalse(sc.wanted({'language': 'en'}, 'jpn'))
        self.assertFalse(sc.wanted({'language': 'en'}, ''))

    def test_two_stretches_away_from_the_ends(self):
        self.assertEqual(sc.places(3000), [900.0, 1800.0])
        self.assertEqual(sc.places(30), [])

    def test_an_older_framework_or_no_permission_hears_nothing(self):
        self.assertEqual(sc.listen(object(), 'u', 0, 'en', 3000), [])
        lib = FakeLib([], allowed=0)
        self.assertEqual(sc.listen(lib, 'u', 0, 'en', 3000), [])
        self.assertEqual(lib.calls, [])

    def test_words_from_both_stretches_on_the_on_device_recognizer(self):
        lib = FakeLib([{'status': 'ok', 'words': [{'w': 'Lantern', 't': 900.5, 'd': .4}]},
                       {'status': 'ok', 'words': [{'w': 'river', 't': 1801.0, 'd': .2}]}])
        heard = sc.listen(lib, 'http://127.0.0.1:1/v.mkv|User-Agent=x', 1, 'en', 3000)
        self.assertEqual(heard, [(900.7, 'lantern'), (1801.1, 'river')])
        self.assertEqual(lib.calls[0][0], b'http://127.0.0.1:1/v.mkv')   # Kodi's header suffix is not part of the link
        self.assertEqual((lib.calls[0][1], lib.calls[0][4], lib.calls[0][5]), (1, sc.BYTE_BUDGET, b'en-US'))

    def test_a_place_with_no_sound_is_read_again_with_a_bigger_budget_and_a_third_place_is_tried(self):   # build 639 log 9f7b4ab2: 4K Drive episode, 'less than a second of sound'
        quiet = {'status': 'no_sound', 'why': 'speech sample: less than a second of sound'}
        lib = FakeLib([quiet, quiet, quiet, quiet, {'status': 'ok', 'words': [{'w': 'lantern', 't': 1350.0, 'd': .4}]}])
        heard = sc.listen(lib, 'u', 0, 'en', 3000)
        self.assertEqual(heard, [(1350.2, 'lantern')])
        self.assertEqual([c[4] for c in lib.calls], [sc.BYTE_BUDGET, sc.BYTE_BUDGET * sc.RETRY_BUDGET] * 2 + [sc.BYTE_BUDGET * sc.RETRY_BUDGET])
        self.assertEqual([c[2] for c in lib.calls], [900.0, 900.0, 1800.0, 1800.0, 1350.0])
        lib = FakeLib([quiet, {'status': 'ok', 'words': [{'w': 'river', 't': 900.0, 'd': .2}]}, {'status': 'ok', 'words': []}])
        sc.listen(lib, 'u', 0, 'en', 3000);self.assertEqual(len(lib.calls), 3)   # a retry that hears something is kept; no third place once words are heard

    def test_a_language_the_phone_cannot_recognise_stops_at_once(self):
        lib = FakeLib([{'status': 'not_on_device', 'why': 'no'}, {'status': 'ok', 'words': []}])
        self.assertEqual(sc.listen(lib, 'u', 0, 'en', 3000), [])
        self.assertEqual(len(lib.calls), 1)


class Wiring(unittest.TestCase):
    def test_native_and_callers(self):
        native = (ROOT / 'migration/airplay-ios/remux/src/kr_speech.m').read_text()
        self.assertIn('request.requiresOnDeviceRecognition = YES;', native)
        self.assertIn('if (!r.supportsOnDeviceRecognition)', native)
        self.assertIn('kodi_speech_words', native)
        self.assertIn('int kr_speech_pcm(', (ROOT / 'migration/airplay-ios/remux/src/kr_speech.h').read_text())
        self.assertIn('test_speech_sound(', (ROOT / 'migration/airplay-ios/remux/tests/test_remux.c').read_text())
        tracks = (ROOT / 'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertEqual(tracks.count('self.checked_video()'), 2)   # Choose-another (apply) and the check that now runs after Download and apply has put the subtitle on
        self.assertIn('speech_check.for_playing(', (LIB / 'dub_captions.py').read_text())
        self.assertIn("NSSpeechRecognitionUsageDescription", (ROOT / 'scripts/build_customized_ipa.py').read_text())

class Choosing(unittest.TestCase):
    """Build 623 (owner: "download and apply ... they dont match and timing is off"): the first of 13 results was applied and the check could not decide."""
    def test_the_best_supported_of_several_is_kept(self):
        right, said = scene(0.0, seed=1);other, _ = scene(0.0, seed=7);shifted, said2 = scene(6.0, seed=1)
        heard = sc.heard(said)
        self.assertEqual(sc.compare(heard, sc.cues(other, 'o.srt'))['agreement'] < sc.MISMATCH + .1, True)
        best = sc.best_fit(heard, [({'id': 'a'}, 'a.srt', other), ({'id': 'b'}, 'b.srt', right)])
        self.assertEqual((best[0]['id'], best[3]), ('b', 'fits'))
        best = sc.best_fit(sc.heard(said2), [({'id': 'a'}, 'a.srt', other), ({'id': 'c'}, 'c.srt', right)])
        self.assertEqual(best[0]['id'], 'c');self.assertEqual(best[3], 'shift');self.assertAlmostEqual(best[4], 6.0, delta=.6)   # its cues are 6 s early: take that out
    def test_nothing_established_gives_none_and_bad_files_are_skipped(self):
        other, _ = scene(0.0, seed=7);_, said = scene(0.0, seed=1)
        self.assertIsNone(sc.best_fit(sc.heard(said), [({'id': 'a'}, 'a.srt', other), ({'id': 'x'}, 'x.srt', b'not a subtitle')]))
        self.assertIsNone(sc.best_fit([], []));self.assertIsNone(sc.best_fit(sc.heard(said)[:3], [({'id': 'a'}, 'a.srt', scene(0.0, seed=1)[0])]))   # too few words: no claim
    def test_the_verdict_is_worded_for_the_log(self):
        self.assertEqual(sc.describe({}), 'no verdict')
        self.assertEqual(sc.describe({'match_speech': 'unknown', 'match_speech_agreement': .213, 'match_speech_shift': 0.0}), 'unknown (agreement 0.21, shift 0.0 s)')
        self.assertEqual(sc.describe({'match_speech': 'shift', 'match_speech_agreement': None, 'match_speech_shift': -3.5}), 'shift (agreement n/a, shift -3.5 s)')
    def test_the_menu_tries_the_next_results_when_the_check_cannot_decide(self):
        text = (ROOT / 'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn("log('speech check: %d words heard, this subtitle: %s' % (len(heard), speech_check.describe(selected)))", text)
        self.assertIn("selected.get('match_speech') == 'unknown'", text)
        self.assertIn('best = speech_check.best_fit(heard, files)', text)


if __name__ == '__main__':
    unittest.main()
