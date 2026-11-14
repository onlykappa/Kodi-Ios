"""Elementum Burst errors from Kodi's background progress box, to Notifications (ISSUE-287).

The activity pill used to read Kodi's background box (drawn invisible by skin_textures.hidden_box) and pass Burst's
"errors" lines to Notifications. The pill is gone (owner: "I use Library status or the notification tray"); this keeps
only that report. Pure apart from read(), so it is host-tested.
"""
import re

WINDOW=10151   # Kodi's DialogExtendedProgressBar
HEADER,TEXT=30,31
TAG=re.compile(r'\[/?(?:COLOR|B|I|UPPERCASE|LOWERCASE|CAPITALIZE)[^\]]*\]',re.I)


def clean(text):
 text=TAG.sub('',str(text or '')).replace('[CR]',' · ')
 return re.sub(r'\s+',' ',text).strip(' ·')


def burst_problem(heading,text):
 """The Notifications text for a Burst error line, else ''."""
 h=clean(heading).lower()
 if 'burst' in h and 'error' in h:return clean(text) or 'Some torrent sites did not answer'
 return ''


def read_box(xbmc,xbmcgui):
 """(heading, text) from Kodi's box while it is up, else None."""
 if not xbmc.getCondVisibility('Window.IsVisible(%d)'%WINDOW):return None
 try:
  w=xbmcgui.Window(WINDOW);heading=w.getControl(HEADER).getLabel();text=w.getControl(TEXT).getLabel()
 except Exception:
  heading=xbmc.getInfoLabel('Control.GetLabel(%d)'%HEADER);text=xbmc.getInfoLabel('Control.GetLabel(%d)'%TEXT)
 return (heading,text) if heading or text else None


def watch(read,report,wait,interval=1.0):
 """Report each Burst error once per appearance of the box. read() -> (heading, text) or None; report(text);
 wait(s) -> True to stop."""
 seen=set()
 while not wait(interval):
  try:
   box=read()
   if not box:
    seen.clear();continue
   problem=burst_problem(*box)
   if problem and problem not in seen:
    seen.add(problem);report(problem)
  except Exception:
   pass
