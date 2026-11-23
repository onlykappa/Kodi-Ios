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

    def test_a_turn_is_covered_until_kodi_drew_the_new_size(self):   # ISSUE-411: Home turned and squeezed on leaving a video
        text = PATCH.read_text()
        section = text[text.index('diff --git a/xbmc/platform/darwin/ios/XBMCController.mm'):]
        section = section[:section.index('\ndiff --git ', 10)]
        self.assertIn('+static UIView* s_rotationCover = nil;', section)
        self.assertIn('+    [m_window bringSubviewToFront:s_rotationCover];', section)            # over Kodi and the glass bar
        self.assertIn('+  HideRotationCover(turn, 0.05); // Kodi draws the new layout on its next frame', section)   # after ApplyRotatedScreen
        self.assertIn('+                                 HideRotationCover(turn, 0.6); // limit', section)        # Home within 1 s (owner)
        self.assertIn('+    if (turn != s_rotationTurn || !s_rotationCover || !s_rotationCover.superview)', section)  # a newer turn keeps its cover

    def test_a_pages_inertia_answer_is_not_overwritten_by_the_window_under(self):   # ISSUE-424: flicks did nothing on Python dialog pages
        text = PATCH.read_text()
        section = text[text.index('diff --git a/xbmc/guilib/GUIWindow.cpp'):]
        section = section[:section.index('\ndiff --git ', 10)]
        self.assertIn('+      int* answered = static_cast<int*>(message.GetPointer());', section)
        self.assertIn('+      if (answered && *answered != EVENT_RESULT_UNHANDLED)\n+        return true;', section)   # an accepted answer stays
        self.assertIn('+      delete answered;', section)                                                         # a replaced one is freed
        self.assertLess(section.index('return true;'), section.index('OnMouseAction(action);\n+      delete answered'))

    def test_the_lock_names_the_new_build_and_this_patch(self):
        lock = json.loads(LOCK.read_text())
        self.assertEqual(lock['build_tag'], 'kodi-ios-portrait-r36')   # r36's patch is ready; executable_release stays r35 until it is built
        self.assertEqual(lock['patch_sha256'], hashlib.sha256(PATCH.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
