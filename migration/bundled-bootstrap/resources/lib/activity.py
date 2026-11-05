"""Activity pill (owner-approved mockups, docs/design/activity-indicator-mockups.html).

Kodi's background progress box (DialogExtendedProgressBar, window 10151; add-ons open it with DialogProgressBG) is
shared by Kodi itself (add-on update checks and installs, library scans, file operations, the TV guide),
Elementum, Elementum Burst, Umbrella, TMDb Helper and Skin Variables. Kodi shows one job at a time (heading 30,
text 31, progress 32) and switches every 2 s. That box is drawn invisible by the skin (activity_page.py); the
bootstrap service reads it here, keeps every job it has seen, rewrites each one in plain words and publishes them
as Home window properties (Activity.*) for the pill (Custom_1187_Activity.xml) and the Activity sheet.

Elementum downloads come from its engine instead (title, %, speed, pause) and the Google Drive upload from
driveupload, so the pill shows them even between Kodi's turns. Nothing here raises into the service.
"""
import re,time

PREFIX='Activity.'
ROWS=6                      # rows on the Activity sheet (Activity.<n>.*)
WINDOW=10151                # Kodi's WINDOW_DIALOG_EXT_PROGRESS
HEADER,TEXT,PROGRESS=30,31,32
# App tiles: (icon in Fuse's extras/icons, tile colour, ring colour).
APPS={'elementum':('magnet.png','FF1F6FEB','FF0A84FF'),'burst':('fire-flame-curved.png','FFFF6B00','FFFF9F0A'),
      'umbrella':('umbrella.png','FF7D3CFF','FFBF5AF2'),'library':('book.png','FF2A6CDF','FF0A84FF'),
      'addon':('puzzle-piece.png','FFFF9F0A','FFFF9F0A'),'tmdb':('film.png','FF01B4E4','FF64D2FF'),
      'skin':('layer-group.png','FF636366','FFAEAEB2'),'drive':('cloud-arrow-up.png','FF1A9E5C','FF30D158'),
      'files':('copy.png','FF0A84FF','FF0A84FF'),'update':('arrows-rotate.png','FF636366','FFAEAEB2'),
      'tv':('satellite-dish.png','FF5E5CE6','FF5E5CE6'),'other':('circle-info.png','FF636366','FFAEAEB2')}
# Switches in the bootstrap's settings (category Activity): which jobs may show the pill.
GROUPS={'elementum':'activity_elementum','burst':'activity_burst','umbrella':'activity_umbrella','library':'activity_library',
        'addon':'activity_addons','quiet':'activity_quiet','drive':'activity_elementum','other':''}
DONE_FOR=4.0                # seconds a finished job stays as a green check

TAG=re.compile(r'\[/?(?:COLOR|B|I|UPPERCASE|LOWERCASE|CAPITALIZE|LIGHT)[^\]]*\]',re.I)
RATE=r'[\d.]+\s*[kKMGT]?i?B/s'
ELEMENTUM_LINE=re.compile(r'^(?P<name>.+?) - (?P<down>%s) - (?P<up>%s)(?: - (?P<pct>\d+)%%)?$'%(RATE,RATE))
YEAR=re.compile(r'^(?P<title>.+?)[ ._\-(\[]+(?P<year>(?:19|20)\d\d)(?:[ ._\-)\]]|$)')
QUALITY=re.compile(r'(2160p|1080p|720p|576p|480p|4k|uhd)',re.I)
EPISODE=re.compile(r'^(?P<title>.+?)[ ._\-]+S(?P<s>\d{1,2})E(?P<e>\d{1,3})',re.I)

def clean(text):
 text=TAG.sub('',str(text or '')).replace('[CR]',' · ')
 return re.sub(r'\s+',' ',text).strip(' ·')

def words(name):
 """Release-name words as a title: dots and underscores to spaces, CAPS to Title Case."""
 t=re.sub(r'[._]+',' ',name).strip(' -')
 return t.title() if t.isupper() or t.islower() else t

def release(name):
 """('Inception (2010)', '1080p') from 'Inception.2010.PROPER.BLURAY.1080p...' (best effort, never empty)."""
 name=clean(name).rstrip('.').rstrip()
 if name.endswith('...'):name=name[:-3]
 q=QUALITY.search(name);quality=('4K' if q and q.group(1).lower() in ('2160p','4k','uhd') else q.group(1).lower()) if q else ''
 m=EPISODE.match(name)
 if m:return '%s · S%d E%d'%(words(m.group('title')),int(m.group('s')),int(m.group('e'))),quality
 m=YEAR.match(name)
 if m:return '%s (%s)'%(words(m.group('title')),m.group('year')),quality
 return words(name) or 'Download',quality

def classify(heading,text,percent=None):
 """One of Kodi's box lines -> {key, app, group, title, sub, pct (None: spinner), drop, problem, download}.
 `drop`: not shown (Elementum's Total line); `problem`: a message for Notifications instead of the pill."""
 h=clean(heading);t=clean(text);pct=None if percent is None or percent<0 else max(0,min(100,int(round(percent))))
 job={'key':'%s|%s'%(h,t),'app':'other','group':'other','title':h or 'Working','sub':t,'pct':pct,'drop':False,'problem':'','download':''}
 low=h.lower()
 if 'burst' in low:
  job.update(app='burst',group='burst',key='burst|'+('errors' if 'error' in low else 'search'))
  if 'error' in low:job.update(drop=True,problem=t or 'Some torrent sites did not answer');return job
  m=re.search(r'(\d+) providers? left',t)
  if t.lower().startswith('syncing cookies'):job.update(group='quiet',title='Updating torrent site cookies',sub='Elementum Burst')
  elif m:job.update(title='Searching torrent sites',sub='%s site%s left'%(m.group(1),'' if m.group(1)=='1' else 's'))
  elif t.lower().startswith('1 provider'):job.update(title='Searching torrent sites',sub='1 site left')
  else:job.update(title='Searching torrent sites',sub='Starting')
  return job
 if low.startswith('elementum'):
  job.update(app='elementum',group='elementum')
  if t.lower().startswith('total -') or t.lower().startswith('total d/l'):job.update(drop=True,key='elementum|total');return job
  m=ELEMENTUM_LINE.match(t)
  if m:
   title,quality=release(m.group('name'))
   if m.group('pct') and pct is None:pct=int(m.group('pct'))
   job.update(key='elementum|dl|'+m.group('name')[:24],title=title,pct=pct,download=m.group('name'),
              sub=' · '.join(x for x in (quality,m.group('down').replace('kB','KB')) if x))
   return job
  plain={'resolving torrent files':('Getting the torrent ready','Reading its files'),'scraping trackers':('Finding peers','Asking trackers'),
         'resolving magnet link':('Getting the torrent ready','Opening the magnet link'),'uploading file to pastebin':('Uploading the log','Elementum')}
  for start,(title,sub) in plain.items():
   if t.lower().startswith(start):job.update(key='elementum|'+start,title=title,sub=sub);return job
  job.update(key='elementum|'+t[:24],title='Elementum',sub=t);return job
 if re.search(r'\b4K:\s*\d+',t) and re.search(r'1080p:\s*\d+',t) or 'preparing sources' in t.lower() or 'checking providers' in t.lower():
  counts=' · '.join('%s %s'%(q,n) for q,n in re.findall(r'\b(4K|1080p|720p|SD):\s*(\d+)',t) if n!='0')
  left=re.search(r'(\d+)\s+(?:providers?\s+)?remaining|remaining[^\d]*(\d+)',t,re.I)
  rest=(left.group(1) or left.group(2)) if left else ''
  sub=' · '.join(x for x in (counts or ('Preparing' if 'preparing' in t.lower() else 'Checking providers'),
                             '%s providers left'%rest if rest else '') if x)
  job.update(key='umbrella|sources',app='umbrella',group='umbrella',title='Finding sources'+(' · '+h if h and h.lower()!='umbrella' else ''),sub=sub)
  return job
 if t.lower().startswith('resolving...') and h:
  job.update(key='umbrella|resolve',app='umbrella',group='umbrella',title='Getting ready to play',sub=t[len('resolving...'):].strip() or h);return job
 if low in ('torbox','offcloud','real-debrid','alldebrid','premiumize'):
  job.update(key='umbrella|'+low,app='umbrella',group='umbrella',title=h,sub=t);return job
 if low=='umbrella':
  job.update(key='umbrella|'+t[:24],app='umbrella',group='umbrella',title='Syncing watched status' if t else 'Umbrella',sub=t);return job
 if low.startswith('checking for add-on updates'):
  job.update(key='kodi|updates',app='update',group='quiet',title='Checking for add-on updates',sub='Kodi',pct=None);return job
 m=re.match(r'^installing (.+?)\.*$',h,re.I)
 if m:
  steps={'downloading add-on':'Downloading','verifying downloaded add-on':'Verifying','checking dependencies':'Checking dependencies'}
  step=next((v for k,v in steps.items() if t.lower().startswith(k)),t)
  job.update(key='install|'+m.group(1),app='addon',group='addon',title='Installing '+m.group(1),
             sub=step+(' %d%%'%pct if pct and step=='Downloading' else ''));return job
 if re.match(r'^scanning (movies|tv shows|music videos|for new content)|^preparing\.\.\.$|^compressing database|^cleaning',h,re.I) or low=='scanning for new content':
  job.update(key='kodi|library',app='library',group='library',title='Updating library',sub=t if t and not t.lower().startswith('scanning') else 'Looking for new videos')
  return job
 if low in ('copy','move','delete','new folder'):
  job.update(key='kodi|files|'+low,app='files',group='other',title={'copy':'Copying','move':'Moving','delete':'Deleting','new folder':'Creating a folder'}[low],
             sub=t);return job
 if low.startswith('importing guide'):
  job.update(key='kodi|epg',app='tv',group='library',title='Loading the TV guide',sub=t or 'Live TV');return job
 if low.startswith('tmdbhelper library'):
  job.update(key='tmdb|library',app='tmdb',group='library',title='Adding to your library',sub=t or 'TMDb Helper');return job
 if low.startswith('tmdbhelper'):
  job.update(key='tmdb|'+low,app='tmdb',group='quiet',title='Updating TMDb Helper',sub=t);return job
 if low.startswith('skin variables') or low.startswith('skin viewtypes') or low.startswith('skin shortcuts'):
  job.update(key='skin',app='skin',group='quiet',title='Setting up views',sub='Arctic Fuse');return job
 return job

class Tracker:
 """Every job seen in Kodi's box (it shows one at a time) plus the engine's downloads and the Drive upload."""
 def __init__(self):self.jobs={};self.done={};self.problems=[];self.box_key=None;self.box_pct=None;self.engine={};self.engine_until=-1
 def ttl(self):return max(6.0,2.5*len(self.jobs)+3)
 def see(self,heading,text,percent,now):
  job=classify(heading,text,percent)
  if job['problem']:
   if job['problem'] not in self.problems:self.problems.append(job['problem'])
   return None
  # Kodi's bar is shared by every job it rotates through: a value equal to the one the previous (other) job left
  # there is that job's, unless this job already had it. 0 means "no percentage" except for downloads and installs.
  raw=job['pct'];old=self.jobs.get(job['key'])
  if raw is not None and job['key']!=self.box_key and raw==self.box_pct and not (old and old.get('pct')==raw):job['pct']=None
  if job['pct']==0 and job['app'] not in ('elementum','addon'):job['pct']=None
  self.box_key,self.box_pct=job['key'],raw
  if job['drop']:return None
  job['seen']=now;job['first']=old['first'] if old else now
  self.jobs[job['key']]=job;return job
 def prune(self,now):
  """Forget jobs Kodi has stopped showing; the ones that got to 95% (or installs) flash a green check."""
  for key,job in list(self.jobs.items()):
   if now-job['seen']>self.ttl():
    del self.jobs[key]
    if (job['pct'] or 0)>=95 or job['app']=='addon':self.done[key]=dict(job,until=now+DONE_FOR)
  for key,job in list(self.done.items()):
   if now>job['until']:del self.done[key]
 def current(self,downloads=(),uploads=(),now=None):
  """Jobs to show, in order: engine downloads (they replace Elementum's own lines), Drive upload, the rest."""
  now=time.time() if now is None else now
  out=[]
  for d in downloads:
   title,quality=release(d.get('title',''))
   speed=speed_text(d.get('speed',''))
   out.append({'key':'dl|'+str(d.get('id','')),'app':'elementum','group':'elementum','title':title,'pct':int(d.get('progress') or 0),
               'sub':('Paused · %d%%'%int(d.get('progress') or 0)) if d.get('paused') else ' · '.join(x for x in (quality,speed.replace('  ·  ',' · ')) if x),
               'paused':bool(d.get('paused')),'id':d.get('id',''),'download':d.get('title','')})
  # An engine download that leaves the list near the end has finished: green check (found in the rig: it just vanished).
  now_keys={'dl|'+str(d.get('id','')) for d in downloads}
  for key,job in list(self.engine.items()):
   if key not in now_keys:
    del self.engine[key]
    if (job.get('pct') or 0)>=95:self.done[key]=dict(job,pct=100,paused=False,id='',sub='Downloaded · Saved to Kodi Downloads',until=now+DONE_FOR)
  for job in out:self.engine[job['key']]=job
  for u in uploads:
   out.append({'key':'drive','app':'drive','group':'drive','title':'Uploading to Google Drive','pct':int(u.get('progress') or 0),
               'sub':'%s · %d%%'%(release(u.get('title',''))[0],int(u.get('progress') or 0))})
  # Elementum's own download lines are replaced by the engine's list, and stay ignored for a while after the last
  # engine download (they linger in Kodi's box for a few seconds; found in the tests: "446 KB/s" beside "Downloaded").
  if downloads:self.engine_until=now+15
  engine=bool(downloads) or now<self.engine_until
  for job in sorted(self.jobs.values(),key=lambda j:j['first']):
   if engine and job.get('download'):continue
   out.append(job)
  for job in self.done.values():
   if not any(o['key']==job['key'] for o in out):out.append(dict(job,state='done'))
  return out

def speed_text(text):
 """notices.downloads' '0.4 MB/s  ·  5h 49m' as '446 KB/s · 5h 49m left' ('Waiting for peers' unchanged)."""
 parts=[x.strip() for x in str(text or '').split('·') if x.strip()]
 if not parts:return ''
 m=re.match(r'^([\d.]+)\s*MB/s$',parts[0])
 if m and float(m.group(1))<1:parts[0]='%d KB/s'%round(float(m.group(1))*1024)
 if len(parts)>1 and not parts[1].endswith('left'):parts[1]+=' left'
 return ' · '.join(parts)

def allowed(job,setting,playing=False):
 """Whether this job may show the pill (the owner's switches; quiet jobs never over video)."""
 if not setting('activity_show',True):return False
 if playing and (not setting('activity_video',True) or job['group']=='quiet'):return False
 name=GROUPS.get(job['group'],'')
 return setting(name,job['group']!='quiet') if name else True

def ring_name(pct):
 """Texture for a ring filled to the nearest 5% (activity_page.textures draws ring_00..ring_20)."""
 return 'ring_%02d.png'%max(0,min(20,int(round((pct or 0)/5.0))))

def properties(jobs,count_hidden=0):
 """Home window properties for the pill and the sheet. `jobs`: what may show, in order."""
 props={PREFIX+k:'' for k in ('Show','Count','Title','Sub','Icon','Tint','Ring','RingTint','Pct','State','Pause','PauseId','Stack','Running')}
 for n in range(1,5):props.update({PREFIX+'S%d.Icon'%n:'',PREFIX+'S%d.Tint'%n:''})
 for n in range(1,ROWS+1):
  for k in ('Title','Sub','Icon','Tint','Bar','Pct','State','Pause','Id'):props[PREFIX+'%d.%s'%(n,k)]=''
 props[PREFIX+'Running']=str(len(jobs)+count_hidden) if jobs or count_hidden else ''
 if not jobs:return props
 def state(j):
  if j.get('state')=='done':return 'done'
  if j.get('paused'):return 'paused'
  return 'spin' if j.get('pct') is None else 'progress'
 for n,j in enumerate(jobs[:ROWS],1):
  icon,tile,ring=APPS.get(j['app'],APPS['other'])
  props.update({PREFIX+'%d.Title'%n:j['title'],PREFIX+'%d.Sub'%n:j.get('sub',''),PREFIX+'%d.Icon'%n:icon,PREFIX+'%d.Tint'%n:tile,
                PREFIX+'%d.Bar'%n:'FF30D158' if state(j)=='done' else ('FF8E8E93' if j.get('paused') else ring),
                PREFIX+'%d.Pct'%n:'' if j.get('pct') is None else str(j['pct']),PREFIX+'%d.State'%n:state(j),
                PREFIX+'%d.Pause'%n:('resume' if j.get('paused') else 'pause') if j.get('id') else '',PREFIX+'%d.Id'%n:str(j.get('id',''))})
 first=jobs[0];icon,tile,ring=APPS.get(first['app'],APPS['other'])
 props.update({PREFIX+'Show':'true',PREFIX+'Count':str(len(jobs)),PREFIX+'Icon':icon,PREFIX+'Tint':tile})
 if len(jobs)==1:
  st=state(first)
  props.update({PREFIX+'Title':first['title'],PREFIX+'Sub':first.get('sub',''),PREFIX+'State':st,
                PREFIX+'Pct':'' if first.get('pct') is None else str(first['pct']),
                PREFIX+'Ring':ring_name(100 if st=='done' else first.get('pct')),
                PREFIX+'RingTint':'FF30D158' if st=='done' else ('FF8E8E93' if st=='paused' else ring),
                PREFIX+'Pause':('resume' if first.get('paused') else 'pause') if first.get('id') else '',PREFIX+'PauseId':str(first.get('id',''))})
 else:
  sized=[j for j in jobs if j.get('pct') is not None and j.get('state')!='done']
  lead=max(sized,key=lambda j:j['pct']) if sized else first
  avg=int(sum(j['pct'] for j in sized)/len(sized)) if sized else None
  props.update({PREFIX+'Title':'%d running'%len(jobs),PREFIX+'Stack':'true',PREFIX+'State':'spin' if avg is None else 'progress',
                PREFIX+'Sub':'%s%s'%(lead['title'],' · %d%%'%lead['pct'] if lead.get('pct') is not None else ''),
                PREFIX+'Pct':'' if avg is None else str(avg),PREFIX+'Ring':ring_name(avg),PREFIX+'RingTint':'FF0A84FF'})
  for n,j in enumerate(jobs[:4],1):
   icon,tile,_=APPS.get(j['app'],APPS['other'])
   props.update({PREFIX+'S%d.Icon'%n:icon,PREFIX+'S%d.Tint'%n:tile})
 return props

def read_box(xbmc,xbmcgui):
 """(heading, text, percent or None) from Kodi's box while it is up, else None."""
 if not xbmc.getCondVisibility('Window.IsVisible(%d)'%WINDOW):return None
 try:
  w=xbmcgui.Window(WINDOW)
  def text_of(control):
   return w.getControl(control).getLabel()   # buttons in activity_skin.hidden_box: read from Kodi, not cached
  heading=text_of(HEADER);text=text_of(TEXT)
  # Kodi only moves the bar for jobs that report a percentage and never resets it between jobs, so this may be
  # the previous job's value: Tracker.see decides whether it belongs to this job.
  pct=w.getControl(PROGRESS).getPercent()
 except Exception:
  heading=xbmc.getInfoLabel('Control.GetLabel(%d)'%HEADER);text=xbmc.getInfoLabel('Control.GetLabel(%d)'%TEXT);pct=None
 if not heading and not text:return None
 return heading,text,pct

def watch(read,downloads,uploads,setting,playing,publish,report,wait,interval=0.5,clock=time.time):
 """The service loop. read() -> (heading, text, pct) or None; downloads()/uploads() -> lists (notices.py);
 setting(id, default) -> bool; playing() -> bool; publish(props); report(problem text) -> None; wait(s) -> True to stop."""
 tracker=Tracker();last={};engine_every=2.0;engine_at=0;dl=[];up=[]
 while not wait(interval):
  try:
   now=clock()
   seen=read()
   if seen:tracker.see(seen[0],seen[1],seen[2],now)
   while tracker.problems:report(tracker.problems.pop(0))
   if now-engine_at>=engine_every:
    engine_at=now
    try:dl=downloads() or []
    except Exception:dl=[]
    try:up=uploads() or []
    except Exception:up=[]
   tracker.prune(now)
   jobs=tracker.current(dl,up,now)
   video=playing()
   shown=[j for j in jobs if allowed(j,setting,video)]
   props=properties(shown,len(jobs)-len(shown))
   changed={k:v for k,v in props.items() if last.get(k)!=v}
   if changed:publish(changed);last.update(changed)
  except Exception:
   pass
