"""Roadmap 2.4/2.5: the Kodi patch drops the "- " sub-setting prefix and sends number/PIN prompts to the iPhone's
keyboard on iOS only (other platforms keep Kodi's behaviour)."""
import unittest
from pathlib import Path

PATCH = (Path(__file__).resolve().parents[1] / 'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()


class KodiPatch(unittest.TestCase):
    def section(self, path):
        start = PATCH.index('diff --git a/%s ' % path)
        end = PATCH.find('\ndiff --git ', start + 1)
        return PATCH[start:end if end > 0 else None]

    def test_sub_settings_have_no_dash_on_ios(self):
        s = self.section('xbmc/settings/dialogs/GUIDialogSettingsBase.cpp')
        self.assertIn('+#if defined(TARGET_DARWIN_EMBEDDED)', s)
        self.assertIn('+    label = indentation + label;', s)

    def test_number_and_pin_prompts_use_the_iphone_keyboard(self):
        s = self.section('xbmc/dialogs/GUIDialogNumeric.cpp')
        self.assertIn('+#include "guilib/GUIKeyboardFactory.h"', s)
        self.assertEqual(s.count('CGUIKeyboardFactory::ShowAndGetInput('), 2)
        self.assertIn('if (c >= \'0\' && c <= \'9\')', s)


if __name__ == '__main__':
    unittest.main()
