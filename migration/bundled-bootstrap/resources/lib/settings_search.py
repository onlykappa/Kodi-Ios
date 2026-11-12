"""Search Settings, the index: every setting the search can find, as (label, breadcrumb, action). Page rows come from
settings_page.py, and every visible setting in Kodi's own settings.xml (special://xbmc/system/settings/settings.xml).
The matching is settings_find.py; the page is settings_search.py at the add-on root."""
import xml.etree.ElementTree as ET
import settings_find

KODI_SETTINGS='special://xbmc/system/settings/settings.xml'
# Kodi settings section id -> the window that shows it (the same windows the Settings rows open).
SECTIONS={'system':'systemsettings','player':'playersettings','media':'mediasettings','interface':'interfacesettings',
          'services':'servicesettings'}   # no PVR & Live TV or Games: not in the app (owner, 2026-11-12)
HIDDEN_LEVEL=4   # Kodi's internal settings, never shown in its own pages

def page_entries(settings_page):
 """[(label, section, actions)] for every row of Settings, Customisation and Library."""
 out=[(r[1],'Settings',r[2]) for group in settings_page.ROOT for r in group]
 out+=[(r[1],settings_find.crumb('Customisation',title),r[2]) for title,rows,_ in settings_page.CUSTOM for r in rows]
 out+=[(r[1],settings_find.crumb('Library',title),r[2]) for title,rows,_ in settings_page.LIBRARY for r in rows]
 return out

def kodi_entries(xml_text,localize):
 """[(label, 'Section › Category', action)] for each visible setting in Kodi's settings.xml; localize(id) -> text."""
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
   where=settings_find.crumb(text(section),text(category))
   action='ActivateWindow(%s,%s)'%(window,category.get('id'))
   out.append((text(category),text(section),action))
   for setting in category.iter('setting'):
    level=setting.findtext('level')
    if level and level.strip().isdigit() and int(level)>=HIDDEN_LEVEL:continue
    label=text(setting)
    if label:out.append((label,where,action))
 return out
