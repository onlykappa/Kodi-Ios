"""Readable transfer titles and posters. Rendering is cache-only; optional lookups run off the UI thread."""
import os,re,time
from pathlib import Path
import drivelibrary

def cache_path(profile):return str(Path(profile)/'addon_data/service.kodi.ios.bootstrap/drive-library-art.json')

def identity(name):
 name=os.path.basename(str(name));info=drivelibrary.parse(name)
 season=re.search(r'\bS(\d{1,2})(?:E(\d{1,3}))?\b|\bSeason[ ._-]*(\d+)\b',name,re.I)
 kind='tv' if info['season'] or season else 'movie'
 return kind,info

def cached_poster(kind,info,cache):
 title=info['title'].lower();year=info['year']
 keys=['%s:%s:%s'%(kind,title,year)]
 if year:keys.append('%s:%s:'%(kind,title))
 else:keys+=sorted(k for k in cache if k.startswith('%s:%s:'%(kind,title)))
 for key in keys:
  art=cache.get(key) or {}
  if isinstance(art,dict) and art.get('poster'):return art['poster']
 return ''

def describe(name,cache=None,poster=''):
 kind,info=identity(name);title=info['title'] or 'Video';details=[]
 if kind=='movie' and info['year']:title+=' (%s)'%info['year']
 if info['season']:
  details+=['Season %s'%info['season'],'Episode %s'%info['episode']]
  match=re.search(r'\b(?:S\d{1,2}[ ._-]*E\d{1,3}|\d{1,2}x\d{2,3})\b',str(name),re.I)
  if match:
   text=os.path.splitext(str(name))[0] if drivelibrary.is_video(name) else str(name)
   tail=text[match.end():]
   stop=drivelibrary.STOP.search(tail)
   if stop:tail=tail[:stop.start()]
   episode=re.sub(r'[._]+',' ',tail).strip(' -()')
   if episode and len(episode)<=100:details.append(episode)
 elif kind=='tv':
  match=re.search(r'\b(?:S|Season[ ._-]*)(\d{1,2})\b',str(name),re.I)
  if match:details.append('Season %d'%int(match.group(1)))
 if re.search(r'\b(?:2160p|4k)\b',str(name),re.I):details.append('4K')
 elif re.search(r'\b1080p\b',str(name),re.I):details.append('1080p')
 return {'title':title,'detail':' · '.join(details),'poster':poster or cached_poster(kind,info,cache or {})}

def hydrate(profile,names,key,get,active=lambda:True,attempted=None,max_titles=1):
 """At most one small metadata lookup per pass, including while downloads/uploads run. No Drive listing."""
 if not key or not active():return False
 attempted=attempted if attempted is not None else set()
 path=cache_path(profile);cache=drivelibrary.load_json(path,{});updates={};count=0
 for name in names:
  if not active() or count>=max_titles:break
  kind,info=identity(name);slot='%s:%s:%s'%(kind,info['title'].lower(),info['year'])
  if not info['title'] or slot in attempted or cached_poster(kind,info,cache):continue
  attempted.add(slot);count+=1
  # An earlier empty search is not a poster. Retry once when this page opens, without a busy loop.
  if not cache.get(slot):cache.pop(slot,None)
  art=drivelibrary.artwork(kind,info['title'],info['year'],key,cache,get)
  if art.get('poster'):updates[slot]=art
 if not updates:return False
 latest=drivelibrary.load_json(path,{});latest.update(updates);drivelibrary.save_json(path,latest)
 return True

def preparation_status(current):
 stage=re.sub(r'^Step \d+ of \d+\s*·\s*','',str(current.get('stage') or 'Queued'))
 return '%s · %d%%'%(stage,current.get('progress',0))
