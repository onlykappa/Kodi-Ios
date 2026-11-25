"""Text cues with no duration must not be written with a length of 0 s (owner, build 634 log f75957fe: every text cue of The Lanterns' converted tracks was 0 s long,
so Kodi drew none of them). kr_prepare.c gives such a cue its source packet's duration, else a reading time from its text. The helper is compiled and run here when a
C compiler and FFmpeg's headers are installed (not on the CI runner), and the call site is checked as text everywhere."""
import re,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
SRC=Path(__file__).resolve().parents[1]/'migration/airplay-ios/remux/src/kr_prepare.c'
TEXT=SRC.read_text()

class CallSite(unittest.TestCase):
    def test_a_cue_with_no_length_gets_the_packets_duration_or_a_reading_time(self):
        i=TEXT.index('encoded->duration=av_rescale_q(sub.end_display_time-sub.start_display_time')
        block=TEXT[i:i+900]
        self.assertIn('if(encoded->duration<=0)',block);self.assertIn('p->duration>0?av_rescale_q(p->duration,src->time_base,(AVRational){1,1000}):kr_cue_reading_ms(&sub)',block)
        self.assertLess(TEXT.index('int64_t kr_cue_reading_ms(const AVSubtitle *sub) {'),i)   # defined before its use
        self.assertIn('int64_t kr_cue_reading_ms(const AVSubtitle *sub);',(SRC.parent/'kr_prepare.h').read_text())
    def test_the_helper_is_bounded_two_to_seven_seconds(self):
        body=TEXT[TEXT.index('int64_t kr_cue_reading_ms'):];body=body[:body.index('\n}\n')]
        self.assertIn('ms<2000?2000:ms>7000?7000:ms',body)

class Compiled(unittest.TestCase):
    def test_the_helper_gives_the_documented_times(self):
        if not shutil.which('gcc') or not shutil.which('pkg-config') or subprocess.run(['pkg-config','--exists','libavcodec'],capture_output=True).returncode:
            self.skipTest('no C compiler or FFmpeg headers here')
        body=TEXT[TEXT.index('int64_t kr_cue_reading_ms'):];body=body[:body.index('\n}\n')+3]
        main='''
int main(void){
  AVSubtitle s;memset(&s,0,sizeof s);AVSubtitleRect *r[1];AVSubtitleRect rect;memset(&rect,0,sizeof rect);s.num_rects=1;s.rects=r;r[0]=&rect;
  rect.ass=(char*)"0,0,Default,,0,0,0,,Hello";long a=kr_cue_reading_ms(&s);
  rect.ass=(char*)"0,0,Default,,0,0,0,,This is a considerably longer line of dialogue that goes on and on, and on again for quite some time";long b=kr_cue_reading_ms(&s);
  rect.ass=(char*)"0,0,Default,,0,0,0,,A line of about forty characters!!";long c=kr_cue_reading_ms(&s);
  s.num_rects=0;long d=kr_cue_reading_ms(&s);
  printf("%ld %ld %ld %ld\\n",a,b,c,d);return 0;}
'''
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            Path(t,'c.c').write_text('#include <stdio.h>\n#include <string.h>\n#include <stdint.h>\n#include <libavcodec/avcodec.h>\n'+body+main)
            flags=subprocess.run(['pkg-config','--cflags','libavcodec'],capture_output=True,text=True).stdout.split()
            built=subprocess.run(['gcc','-Wno-deprecated-declarations',*flags,str(Path(t,'c.c')),'-o',str(Path(t,'c'))],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            out=subprocess.run([str(Path(t,'c'))],capture_output=True,text=True).stdout.split()
        a,b,c,d=map(int,out);self.assertEqual((a,b,d),(2000,7000,2000));self.assertTrue(2000<c<7000)
if __name__=='__main__':unittest.main()
