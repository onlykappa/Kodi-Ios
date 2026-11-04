"""Search Settings (the field at the top of portrait Settings): an index of the Settings page rows plus every Kodi
setting from Kodi's own definition (special://xbmc/system/settings/settings.xml), matched against what was typed.
settings_search.py at the add-on root asks for the text with Kodi's keyboard and lists the matches; picking one runs
its action (a Settings row's own action, or the setting's section window opened at its category)."""
import xml.etree.ElementTree as ET

KODI_SETTINGS='special://xbmc/system/settings/settings.xml'
# Kodi settings section id -> the window that shows it (the same windows the Settings rows open).
SECTIONS={'system':'systemsettings','player':'playersettings','media':'mediasettings','interface':'interfacesettings',
          'services':'servicesettings','pvr':'pvrsettings','games':'gamesettings'}
HIDDEN_LEVEL=4   # Kodi's internal settings, never shown in its own pages

def page_entries(settings_page):
 """[(label, section, actions)] for every row of the portrait Settings home and its Customisation page."""
 out=[(r[1],'Settings',r[2]) for group in settings_page.ROOT for r in group]
 out+=[(r[1],'Customisation'+(' · '+title if title else ''),r[2]) for title,rows,_ in settings_page.CUSTOM for r in rows]
 return out

def kodi_entries(xml_text,localize):
 """[(label, 'Section · Category', action)] for each visible setting in Kodi's settings.xml; localize(id) -> text."""
 try:root=ET.fromstring(xml_text)
 except ET.ParseError:return []
 def text(node):
  value=node.get('label','')
  try:value=localize(int(value)) if value.isdigit() else value
  except Exception:value=''
  return ' '.join(str(value or '').split())
 out=[]
 for section in root.findall('section'):
  window=SECTIONS.get(section.get('id'))
  if not window:continue
  for category in section.findall('category'):
   where='%s · %s'%(text(section),text(category))
   action='ActivateWindow(%s,%s)'%(window,category.get('id'))
   out.append((text(category),text(section),action))
   for setting in category.iter('setting'):
    level=setting.findtext('level')
    if level and level.strip().isdigit() and int(level)>=HIDDEN_LEVEL:continue
    label=text(setting)
    if label:out.append((label,where,action))
 return out

def search(entries,query,limit=60):
 """Entries whose label or section contains every word typed (any case); label matches first, no duplicates."""
 words=str(query or '').lower().split()
 if not words:return []
 first,second,seen=[],[],set()
 for label,where,action in entries:
  key=(label.lower(),where.lower())
  if key in seen:continue
  hay=key[0]+' '+key[1]
  if all(w in hay for w in words):
   seen.add(key);(first if all(w in key[0] for w in words) else second).append((label,where,action))
 return (first+second)[:limit]
