"""One-time reset of a changed screen calibration. Kodi has no API for overscan, so this drives its own
calibration window: Kodi asks for confirmation, resets the current resolution and saves on close."""
import json,re,xml.etree.ElementTree as ET
from pathlib import Path
REVISION='calibration-reset-r1'

def changed(guisettings):
 """True when any saved resolution has an overscan other than Kodi's default (0,0 to full width/height)."""
 try:root=ET.parse(guisettings).getroot()
 except (OSError,ET.ParseError):return False
 for res in root.iter('resolution'):
  scan=res.find('overscan')
  if scan is None:continue
  value=lambda name:int(float(scan.findtext(name) or 0))
  if value('left') or value('top'):return True
  size=re.search(r'(\d{3,5})x(\d{3,5})',res.findtext('description') or '')
  if size and (value('right'),value('bottom'))!=(int(size.group(1)),int(size.group(2))):return True
 return False

def reset(builtin,visible,wait):
 builtin('ActivateWindow(screencalibration)')
 for _ in range(20):
  if visible('Window.IsActive(screencalibration)'):break
  if wait(0.25):return 'ABORTED'
 builtin('Action(resetcalibration)')
 # Kodi's own Yes/No dialog; leave the window only once it is answered so the reset is saved.
 for _ in range(4*120):
  if wait(0.25):return 'ABORTED'
  if not visible('Window.IsVisible(yesnodialog)'):break
 if visible('Window.IsActive(screencalibration)'):builtin('Action(Back)')
 return 'OFFERED'

def reset_once(profile,builtin,visible,wait):
 state=Path(profile)/'addon_data/service.kodi.ios.bootstrap';marker=state/'calibration-reset.json'
 if marker.exists():return 'DONE BEFORE'
 result='NOT NEEDED'
 if changed(Path(profile)/'guisettings.xml'):
  result=reset(builtin,visible,wait)
  if result=='ABORTED':return result
 state.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'revision':REVISION,'result':result})+'\n')
 return result
