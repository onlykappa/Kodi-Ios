"""Execute the production seek-completion body against controlled native objects.

This tests callback policy, not AVPlayer readiness or an AirPlay receiver.
"""
import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='darwin','requires macOS Foundation')
class Recovery(unittest.TestCase):
 def test_actual_completion_ownership_and_interruption(self):
  source=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  begin=source.index('if(generation!=atomic_load(&playGeneration) || player.currentItem!=seekItem')
  end=source.index('\n                            });',begin)
  body=source[begin:end]
  harness=r'''
#import <Foundation/Foundation.h>
#include <stdatomic.h>
#include <stdio.h>
static atomic_uint playGeneration;
static atomic_int playbackActive;
static void playerNote(NSString *message) {}
@interface ControlledPlayer : NSObject
@property(nonatomic,strong) NSObject *currentItem;
@property(nonatomic) int plays;
- (void)play;
@end
@implementation ControlledPlayer
- (void)play { self.plays++; }
@end
int main(void) { @autoreleasepool {
 for(int scenario=0;scenario<5;scenario++) {
  unsigned generation=10;
  atomic_store(&playGeneration,scenario==1?11:10);
  atomic_store(&playbackActive,scenario==3?0:1);
  ControlledPlayer *player=[ControlledPlayer new];
  NSObject *seekItem=[NSObject new];
  player.currentItem=scenario==2?[NSObject new]:seekItem;
  BOOL done=scenario!=4;
  __block int recoveryDeadline=30;
  void (^completion)(void)=^{ BODY };
  completion();
  int expected=scenario==0;
  if(player.plays!=expected || recoveryDeadline!=(expected?0:30))return 10+scenario;
 }
 printf("5 production completion scenarios passed\n");
 return 0;
}}
'''.replace('BODY',body)
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'recovery.m';path.write_text(harness)
   binary=Path(temp)/'recovery'
   subprocess.run(['xcrun','clang','-fobjc-arc','-fblocks',str(path),'-framework','Foundation','-o',str(binary)],check=True)
   subprocess.run([str(binary)],check=True)

if __name__=='__main__':unittest.main()
