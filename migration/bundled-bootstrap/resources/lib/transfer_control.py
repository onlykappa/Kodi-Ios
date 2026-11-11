"""Pause and cancel from a long press on a transfer card in Notifications (owner, build 186: "if i hold down on the
conversation tab in the notifications it like closes the notification it should give the option to pause or cancel the
conversation, download or transfer").

The page and the service are different Kodi scripts, so a choice is a small file the service reads:
  paused-conv  the conversion holds where it is (the same hold as a playing video) and no new one starts
  paused-up    uploads to Google Drive (phone files and AllDebrid copies) stop at the next piece; Drive keeps what it
               confirmed, so Resume continues from there
  cancel-up    AllDebrid copies to drop (one info hash per line); the job ends as Cancelled
A cancelled conversion is Keep as it is (prepare_downloads 'keep'); Elementum downloads use its own pause and delete.
"""
import os,time
from pathlib import Path

KINDS=('conv','up')

def folder(profile):return Path(profile)/'addon_data/service.kodi.ios.bootstrap'

def paused(profile,kind):
 try:return (folder(profile)/('paused-'+kind)).exists()
 except OSError:return False

def set_paused(profile,kind,on,now=None,why='you'):
 """why: 'you' (the owner's Pause, kept until Resume) or 'airplay' (Pause and retry over AirPlay: lifted on its own
 when AirPlay is over, release_airplay)."""
 if kind not in KINDS:raise ValueError(kind)
 path=folder(profile)/('paused-'+kind)
 if on:
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text('%s %s'%(now if now is not None else time.time(),why))
 else:
  try:path.unlink()
  except FileNotFoundError:pass

def reason(profile,kind):
 """Why kind is paused: 'you', 'airplay', or '' when it runs. Files from before build 224 hold only a time: 'you'."""
 try:text=(folder(profile)/('paused-'+kind)).read_text().split()
 except OSError:return ''
 return text[1] if len(text)>1 else 'you'

# Build 224 (owner: "downloading ... its currently completely broken"; build-223 log 27f59dcd: uploads_paused true in
# all 122 snapshots over two hours, four AllDebrid downloads waiting): AirPlay's "Pause and retry" paused uploads and
# conversion "until resumed in Library status" and nothing ever resumed them.
AIRPLAY_GRACE=120   # seconds after AirPlay stops before its pause is lifted

def release_airplay(profile,airplay_busy,now=None,quiet_since=None):
 """Lift pauses that AirPlay's Pause and retry set once AirPlay is over. quiet_since: a one-item list the caller
 keeps (when AirPlay was last seen busy). Returns the kinds resumed."""
 now=time.time() if now is None else now
 if airplay_busy:
  if quiet_since is not None:quiet_since[:]=[None]
  return []
 if quiet_since is not None:
  if not quiet_since or quiet_since[0] is None:quiet_since[:]=[now];return []
  if now-quiet_since[0]<AIRPLAY_GRACE:return []
 done=[k for k in KINDS if reason(profile,k)=='airplay']
 for k in done:set_paused(profile,k,False)
 return done

RESET='pause-reset-224'
def reset_once(profile):
 """Build 224, once: lift every pause carried over from earlier builds (the owner did not know uploads were paused).
 Returns the kinds resumed ([] on later starts or when nothing was paused)."""
 marker=folder(profile)/RESET
 if marker.exists():return []
 done=[k for k in KINDS if paused(profile,k)]
 for k in done:set_paused(profile,k,False)
 try:marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(str(time.time()))
 except OSError:pass
 return done

def cancel_copy(profile,info_hash):
 path=folder(profile)/'cancel-up';path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'a',encoding='utf-8') as handle:handle.write(str(info_hash).lower()+'\n')

def cancelled_copies(profile):
 try:return {line.strip() for line in (folder(profile)/'cancel-up').read_text(encoding='utf-8').splitlines() if line.strip()}
 except OSError:return set()

def clear_cancelled(profile,info_hash):
 left=cancelled_copies(profile)-{str(info_hash).lower()}
 path=folder(profile)/'cancel-up'
 try:
  if left:path.write_text(''.join(h+'\n' for h in sorted(left)),encoding='utf-8')
  else:path.unlink()
 except OSError:pass

def menu(kind,item,up_paused=False,conv_paused=False):
 """The long-press choices for a card: [(label, action)].
 kind 'down' (an Elementum download: item has 'paused'), 'up' (the Drive upload: item has 'source'), 'conv'."""
 if kind=='down':
  return [('Resume download' if item.get('paused') else 'Pause download','toggle'),('Cancel download','cancel'),('Show speed','speed')]
 if kind=='up':
  rows=[('Resume uploads' if up_paused else 'Pause uploads','toggle')]
  if item.get('source')=='debrid' and item.get('hash'):rows.append(('Cancel this download','cancel'))
  return rows+[('Show speed','speed')]
 if kind=='conv':
  rows=[('Resume converting' if conv_paused else 'Pause converting','toggle')]
  if item.get('id'):rows.append(('Cancel conversion','cancel'))
  return rows+[('Show speed','speed')]
 return []

def card_of(control,slots=4):
 """Which transfer card a control id is: ('up',0), ('conv',0), ('down',n) or None."""
 if control==9432:return ('up',0)
 if control==9433:return ('conv',0)
 if 9436<=control<=9435+slots:return ('down',control-9436)
 return None
