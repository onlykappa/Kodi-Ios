"""Exercise the staged native parent-row decision with its actual patched condition."""
import re,shutil,subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ParentNavigation(unittest.TestCase):
 def test_downloaded_show_hides_parent_without_changing_other_video_folders(self):
  patch=(ROOT/'migration/ios-portrait/kodi-21.3-portrait.patch').read_text()
  section=patch.split('diff --git a/xbmc/windows/GUIMediaWindow.cpp b/xbmc/windows/GUIMediaWindow.cpp\n',1)[1]
  fragment='\n'.join(line[1:] for line in section.splitlines() if line.startswith(('+',' ')) and not line.startswith('+++'))
  start=fragment.index('if (GetID() == 10025');end=fragment.index('bHideParent = true;',start)+len('bHideParent = true;')
  condition=fragment[start:end]
  compiler=shutil.which('c++')
  self.assertIsNotNone(compiler,'A C++ compiler is required for native behavior verification')
  source='''#include <cassert>
#include <string>
struct Value { std::string text; std::string asString() const { return text; } };
struct Items { std::string downloaded; Value GetProperty(const std::string&) const { return {downloaded}; } };
struct Window {
 int id; int GetID() const { return id; }
 bool hidesParent(const Items& items, bool originalHide) const {
  bool bHideParent = originalHide;
  CONDITION
  return bHideParent;
 }
};
int main() {
 assert(Window{10025}.hidesParent(Items{"true"},false));
 assert(!Window{10025}.hidesParent(Items{""},false));
 assert(!Window{10025}.hidesParent(Items{"false"},false));
 assert(!Window{10002}.hidesParent(Items{"true"},false));
 assert(Window{10025}.hidesParent(Items{""},true));
 assert(Window{10002}.hidesParent(Items{"true"},true));
}
'''.replace('CONDITION',condition)
  with tempfile.TemporaryDirectory() as tmp:
   cpp=Path(tmp)/'parent.cpp';binary=Path(tmp)/'parent';cpp.write_text(source)
   subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
   subprocess.run([str(binary)],check=True,capture_output=True,text=True)

if __name__=='__main__':unittest.main()
