"""Keep Kodi running after it leaves the screen while an Elementum download or a Google Drive upload has work.

iOS suspends an app a few seconds after you switch away or lock the phone, so downloads and uploads stopped until
Kodi was on screen again. An app that plays sound keeps running: KodiAirPlay.framework (r3, kodi_background_keep)
plays silence, mixed with other apps' sound so your music is not interrupted, from the moment Kodi leaves the screen
until the work is done or Kodi comes back. With no work it does nothing and iOS suspends Kodi as before. Swiping
Kodi away in the app switcher still ends everything."""
import os

def reason(downloads,uploads,waiting):
 """Why Kodi must stay awake, or '' when it may sleep. downloads: notices.downloads() cards; uploads:
 notices.uploads() cards; waiting: whether finished videos wait for the next Google Drive upload."""
 running=[d for d in downloads if not d.get('paused')]
 if running:return '%d Elementum download%s'%(len(running),'' if len(running)==1 else 's')
 if uploads:return 'Google Drive upload'
 if waiting:return 'videos waiting for Google Drive'
 return ''

def videos_waiting(root):
 """Any kept video in Kodi Downloads (Movies / TV Shows) that the Drive uploader has not taken yet."""
 for section in ('Movies','TV Shows'):
  for _,_,files in os.walk(os.path.join(root,section)):
   if any(not f.startswith('.') and f.lower().endswith(('.mkv','.mp4','.m4v','.avi','.mov','.webm','.ts')) for f in files):return True
 return False

def watch(keep,why,wait,log=lambda message:None,every=5):
 """Tell the framework every few seconds whether Kodi must stay awake; keep(0) when Kodi closes."""
 last=None
 while not wait(every):
  try:now=why()
  except Exception:now=''
  # Asked again on every tick while awake: the framework restarts the silence if something stopped it.
  if now or bool(now)!=last:keep(int(bool(now)))
  if bool(now)!=last:
   last=bool(now)
   log('Kodi iOS background: '+('stays awake for '+now if now else 'may sleep (no download or upload)'))
 if last:keep(0)
