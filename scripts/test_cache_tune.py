"""Roadmap 1B.3: Kodi's cache read factor follows the connection (Wi-Fi x10, cellular x4) and never overrides the owner."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import cache_tune as ct
import open_timing as ot


class FakeKodi(object):
    def __init__(self, value):
        self.value, self.sets = value, []

    def executeJSONRPC(self, text):
        call = json.loads(text)
        if call['method'] == 'Settings.GetSettingValue':
            return json.dumps({'result': {'value': self.value}})
        self.value = call['params']['value']
        self.sets.append(call['params'])
        return '{}'


class Tuning(unittest.TestCase):
    def apply(self, kodi, kind, folder, logs=None):
        return ct.apply(kodi, folder, (logs if logs is not None else []).append, kind=kind)

    def test_interface_names_are_classified(self):
        self.assertEqual([ct.kind_of(n) for n in ('en0', 'pdp_ip0', 'pdp_ip3', 'utun2', 'lo0', '', None)],
                         ['wifi', 'cellular', 'cellular', 'other', 'other', 'other', 'other'])

    def test_the_link_comes_from_the_interface_that_owns_the_local_address(self):
        table = [('lo0', '127.0.0.1'), ('pdp_ip0', '10.20.30.40'), ('en0', '192.168.1.5'), ('en0', 'fe80::1')]
        self.assertEqual(ct.link_kind('192.168.1.5', table), 'wifi')
        self.assertEqual(ct.link_kind('10.20.30.40', table), 'cellular')
        self.assertEqual(ct.link_kind('8.8.8.8', table), 'other')
        self.assertEqual(ct.link_kind('', []), 'other')

    def test_real_interface_table_reads_on_this_host(self):
        names = [name for name, _ in ct.interfaces()]
        self.assertTrue(names)               # at least the loopback
        self.assertIn('127.0.0.1', [a for _, a in ct.interfaces()])

    def test_cellular_gets_4x_and_wifi_goes_back_to_10x(self):
        with tempfile.TemporaryDirectory() as folder:
            kodi, logs = FakeKodi(1000), []
            self.assertEqual(self.apply(kodi, 'cellular', folder, logs), 400)
            self.assertEqual(kodi.sets, [{'setting': 'filecache.readfactor', 'value': 400}])
            self.assertIn('4.0x for cellular', logs[0])
            self.assertEqual(self.apply(kodi, 'cellular', folder, logs), 400)
            self.assertEqual(len(kodi.sets), 1)                 # nothing to change the second time
            self.assertEqual(self.apply(kodi, 'wifi', folder, logs), 1000)
            self.assertEqual(kodi.value, 1000)

    def test_a_value_the_owner_chose_is_left_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            kodi = FakeKodi(250)        # 2.5x chosen in Kodi's settings
            self.assertIsNone(self.apply(kodi, 'cellular', folder))
            self.assertEqual(kodi.sets, [])
            kodi = FakeKodi(1000)
            self.apply(kodi, 'cellular', folder)
            kodi.value = 700            # the owner changes it after we set 400
            self.assertIsNone(self.apply(kodi, 'wifi', folder))
            self.assertEqual(kodi.value, 700)

    def test_unreadable_setting_changes_nothing(self):
        class Broken(FakeKodi):
            def executeJSONRPC(self, text):
                return 'not json'
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(self.apply(Broken(0), 'cellular', folder))


class Hook(unittest.TestCase):
    def test_on_open_runs_once_per_new_mark_before_the_picture(self):
        props, calls, ticks = {}, [], iter(range(6))

        class Home(object):
            def getProperty(self, name):
                return props.get(name, '')

            def setProperty(self, name, value):
                props[name] = value

            def clearProperty(self, name):
                props.pop(name, None)

        def wait(seconds):
            step = next(ticks)
            if step == 0:
                ot.mark(Home(), 'library', now=100.0)
            if step == 3:
                ot.mark(Home(), 'library', now=105.0)
            return step >= 5
        ot.watch(Home(), lambda: False, lambda text: None, wait, on_open=lambda: calls.append(1))
        self.assertEqual(len(calls), 2)       # two different marks, each seen several times, each announced once

    def test_a_failing_hook_never_stops_the_timing(self):
        props = {}

        class Home(object):
            def getProperty(self, name):
                return props.get(name, '')

            def clearProperty(self, name):
                props.pop(name, None)
        props[ot.PROPERTY] = json.dumps({'t': 1.0, 'via': 'library'})
        logs = []

        def boom():
            raise RuntimeError('synthetic')
        ot.watch(Home(), lambda: True, logs.append, lambda s: True, on_open=boom)
        self.assertTrue(any('open timing' in line for line in logs))


if __name__ == '__main__':
    unittest.main()
