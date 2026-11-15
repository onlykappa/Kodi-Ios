"""ISSUE-316 (owner: "the flick just sucks" on every page but Home, Movies and TV): Kodi's group list processed every
child on every frame; the hubs' rows are lists that process only what is on screen. The Kodi patch skips group-list
children more than a screen away from the visible part (desktop rig A/B: Favourites 68 -> 83 fps, Notifications 70 ->
88 fps while dragging, Home unchanged)."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'migration/ios-portrait/kodi-21.3-portrait.patch'
LOCK = ROOT / 'migration/ios-portrait/source-lock.json'


class SmoothPages(unittest.TestCase):
    def test_the_patch_skips_far_children(self):
        text = PATCH.read_text()
        section = text[text.index('diff --git a/xbmc/guilib/GUIControlGroupList.cpp'):]
        section = section[:section.index('\ndiff --git ', 10)]
        self.assertIn('+    const bool far = control->IsVisible() && !control->HasFocus() &&', section)
        self.assertIn('+    if (!far)', section)
        self.assertIn('+      control->DoProcess(currentTime, dirtyregions);', section)
        self.assertIn('-    control->DoProcess(currentTime, dirtyregions);', section)

    def test_the_lock_names_the_new_build_and_this_patch(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock['build_tag'], 'kodi-ios-portrait-r33')
        self.assertEqual(lock['patch_sha256'], hashlib.sha256(PATCH.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
