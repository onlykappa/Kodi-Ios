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

PATIENCE=180   # roadmap 3.1: seconds iOS may hold the silent audio before the owner is told

def watch(keep,why,wait,log=lambda message:None,every=1,status=lambda:0,idle_every=3,notify=None,clock=None,patience=PATIENCE):
 """Tell the framework every few seconds whether Kodi must stay awake; keep(0) when Kodi closes.

 Roadmap 3.1 (owner logs 9e2568a7, 5331b718: iOS interrupted the silent audio, so downloads and uploads stopped until
 Kodi came back to the screen): every tick while work waits asks the framework again to start the silence (it restarts
 after an interruption as soon as iOS allows). When the audio stays interrupted or failed for `patience` seconds with work
 waiting, notify(title, text) tells the owner once per interruption, and the log says how long it took to recover."""
 import time
 clock=clock or time.monotonic
 last=None;last_status=None;lost_at=None;told=False
 while True:
  try:now=why()
  except Exception:now=''
  # Asked again on every tick while awake: the framework restarts the silence if something stopped it.
  if now or bool(now)!=last:keep(int(bool(now)))
  if bool(now)!=last:
   last=bool(now)
   log('Kodi iOS background: '+('stays awake for '+now if now else 'may sleep (no download or upload)'))
  observed=status()
  if observed!=last_status:
   last_status=observed
   if observed==-1:log('Kodi iOS background: silent audio failed to start; work may pause until Kodi is foregrounded')
   elif observed==-2:log('Kodi iOS background: audio interrupted by iOS; work will resume when allowed')
   elif observed==2:log('Kodi iOS background: silent audio running for queued work')
  if observed in (-1,-2) and now:
   if lost_at is None:lost_at=clock()
   if not told and notify and clock()-lost_at>=patience:
    told=True
    try:notify('Background work paused','iOS took the audio from Kodi (a call or another app), so downloads and uploads wait. They carry on when you open Kodi.')
    except Exception:pass
  elif lost_at is not None and (observed==2 or not now):
   if observed==2 and now:log('Kodi iOS background: silent audio running again after %d s'%int(clock()-lost_at))
   lost_at=None;told=False
  if wait(every if now or observed else idle_every):break   # Roadmap 1E.7: nothing to keep awake for: every 3 s
 if last:keep(0)
