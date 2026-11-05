"""Compile and exercise the changed native startup branches, extracted from the shipped Kodi patch.

This is a host branch test with protocol/log stubs, not an iOS executable build or a full ActiveAE integration test.
"""
import shutil,subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATCH=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()

def additions(path):
 section=next(s for s in PATCH.split('diff --git ') if s.startswith('a/'+path+' '))
 return '\n'.join(line[1:] for line in section.splitlines() if line.startswith('+') and not line.startswith('+++'))

class NativeStartup(unittest.TestCase):
 def compile_run(self,body,ios=False):
  compiler=shutil.which('c++')
  if not compiler:self.skipTest('C++ compiler unavailable')
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'check.cpp';out=Path(d)/'check';src.write_text(body)
   built=subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',*(['-DTARGET_DARWIN_IOS'] if ios else []),str(src),'-o',str(out)],capture_output=True,text=True)
   self.assertEqual(built.returncode,0,built.stderr)
   subprocess.run([str(out)],check=True,capture_output=True)
 def audio(self,ios):
  code=additions('xbmc/cores/AudioEngine/Engines/ActiveAE/ActiveAE.cpp')
  self.assertIn('Suspended handles INIT first',code)
  self.compile_run('''#include <cassert>
struct CActiveAEControlProtocol { enum {INIT=0, ACC=1}; };
struct Message { int replies=0; void Reply(int s) { assert(s==CActiveAEControlProtocol::ACC); ++replies; } };
int unhandled=0;
void configured(int signal, Message *msg) { (void)msg; switch(signal) {
'''+code+'''
default: ++unhandled; break;
} }
int main() { Message m;
#if defined(TARGET_DARWIN_IOS)
configured(0,&m); configured(0,&m); assert(m.replies==2); assert(unhandled==0);
#else
configured(0,&m); assert(unhandled==1); assert(m.replies==0);
#endif
int before=unhandled; configured(123,&m); assert(unhandled==before+1);
}
''',ios)
 def test_repeated_ios_resume_gets_an_acknowledgement(self):self.audio(True)
 def test_other_platforms_keep_their_existing_protocol(self):self.audio(False)
 def test_forward_reference_is_debug_but_invalid_schema_still_warns(self):
  code=additions('xbmc/interfaces/json-rpc/JSONServiceDescription.cpp')
  self.compile_run('''#include <cassert>
#include <string>
enum { LOGWARNING=2, LOGDEBUG=0 };
struct CLog { static int level; template<class... T> static void Log(int l,T...) { level=l; } }; int CLog::level=-1;
struct Type { std::string missingReference; };
void report(Type *globalType) { const std::string typeName="test";
'''+code+'''
}
int main() { Type t; report(&t); assert(CLog::level==LOGWARNING);
t.missingReference="Setting.Details.Setting"; report(&t); assert(CLog::level==LOGDEBUG); }
''')

if __name__=='__main__':unittest.main()
