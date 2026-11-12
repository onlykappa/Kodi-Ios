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

    def test_kodis_ffmpeg_skips_mkv_attachment_data(self):
        """Roadmap 1B.1: the depends build patches its FFmpeg so an MKV's fonts/covers are not read before playing."""
        make = self.section('tools/depends/target/ffmpeg/Makefile')
        self.assertIn('+\tcd $(PLATFORM); patch -p1 -i ../kodi-ios-mkv-skip-attachments.patch', make)
        self.assertIn('kodi-ios-mkv-skip-attachments.patch\n', make.split('+DEPS = ')[1])
        ff = self.section('tools/depends/target/ffmpeg/kodi-ios-mkv-skip-attachments.patch')
        self.assertIn('++    { MATROSKA_ID_FILEDATA,     EBML_NONE },', ff)
        self.assertIn('+--- a/libavformat/matroskadec.c', ff)
        # the embedded patch is the same change the AirPlay FFmpeg uses
        airplay = (Path(__file__).resolve().parents[1] / 'migration/airplay-ios/ffmpeg-mkv-skip-attachments.patch').read_text()
        embedded = ''.join(l[1:] + '\n' for l in ff.split('@@ -0,0 +1,', 1)[1].splitlines()[1:])
        self.assertEqual(embedded, airplay)

    def test_build_script_rebuilds_a_cached_ffmpeg_once(self):
        script = (Path(__file__).resolve().parents[1] / 'migration/ios-portrait/build-kodi-ios.sh').read_text()
        self.assertIn('.ffmpeg-mkv-skip-', script)
        self.assertIn('rm -f "$DEPS/.depends-built"', script)


if __name__ == '__main__':
    unittest.main()
