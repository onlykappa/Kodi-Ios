"""Settings › Library › Library status (portrait/IOSLibraryStatus.xml, drawn by resources/lib/library_page.py).

Shows every video in Google Drive › Kodi Downloads: what is ready for Kodi and AirPlay, what is being prepared,
downloaded or uploaded, what waits (and why), and what is kept as it is. Refreshes every two seconds while open.
Check now (top right) asks the service to look at Google Drive again; a row opens that video's details sheet
(portrait/IOSLibraryItem.xml) with what can be done about it (prepare next, try again, keep as it is), which the
service applies on its next pass (prepare_downloads.request)."""
import os,shutil,sys,threading,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import library_page,library_rows,prepare_downloads,tool_windows,transfer_history
p_side=54   # portrait.SIDE: the summary card's left edge

BACK=(9,10,92,110)
# By id: a script started through RunScript(service.kodi.ios.bootstrap,...) runs via default.py's runpy, and Kodi
# cannot tell which add-on an Addon call without an id means (build 159: the page never opened).
ADDON='service.kodi.ios.bootstrap'
FILTER_BASE=9101

def folder_size(path):
 total=0
 for root,_,names in os.walk(str(path)):
  for name in names:
   try:total+=os.path.getsize(os.path.join(root,name))
   except OSError:pass
 return total

def quality_key(height):
 """drivelibrary.quality (2160, 1080...) as the source picker names it ('4k', '1080p'...); '' when unknown."""
 try:height=int(height or 0)
 except (TypeError,ValueError):return ''
 return '4k' if height>=2000 else '1440p' if height>=1400 else '1080p' if height>=1000 else '720p' if height>=700 else '480p' if height>=400 else ''

def snapshot(profile,downloads,uploads):
 """library_view() for the page right now (never raises: an empty library on any error)."""
 # Choices not yet applied by the service show at once (it applies them before its next video).
 import work_state
 # Build 193: "preparing" and its words come from the status model, as on every other page and the bell.
 model=work_state.load(profile)
 state=work_state.align(prepare_downloads.snapshot(profile),model)
 state=prepare_downloads.apply_to(state,prepare_downloads.pending_requests(profile),time.time())
 work=prepare_downloads.location(profile).parent/'preparing-videos'
 import phone_space
 try:free=phone_space.free(str(work if work.exists() else work.parent))
 except OSError:free=None
 view=prepare_downloads.library_view(state,[],[],free,folder_size(work) if work.exists() else 0)
 view=library_rows.with_model(view,model)
 return state,view

def run(args=()):
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 import drivelibrary,notices,transfer_artwork
 profile=xbmcvfs.translatePath('special://profile/');addon=xbmcaddon.Addon(ADDON);dialog=xbmcgui.Dialog()
 here=os.path.dirname(os.path.abspath(__file__))
 # Posters as in the Library: TMDb with TMDb Helper's key, cached; looked up in the background, one at a time.
 try:
  key=drivelibrary.tmdb_key(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path')))
 except Exception:key=''
 import urllib.request
 def get(url):
  with urllib.request.urlopen(url,timeout=8) as response:return response.read(1024*1024)
 cache=drivelibrary.load_json(transfer_artwork.cache_path(profile),{});posters={};asked=set();lock=threading.Lock()
 def poster(row):
  name=row.get('name') or row.get('title') or ''
  cached=transfer_artwork.describe(name,cache)['poster']
  if cached:return cached
  if name in posters or not key:return posters.get(name,'')
  with lock:
   if name in asked:return ''
   asked.add(name)
  def fetch():
   try:
    info=drivelibrary.parse(name)
    posters[name]=drivelibrary.artwork('tv' if info['season'] else 'movie',info['title'],info['year'],key,cache,get).get('poster','')
   except Exception:posters[name]=''
  threading.Thread(target=fetch,daemon=True).start()
  return ''

 class Details(xbmcgui.WindowXMLDialog):
  def setup(self,sheet,row,fresh=None):
   self.sheet,self.row,self.chosen,self.fresh=sheet,row,None,fresh
   self.recovery=''
  def onInit(self):
   self.stop=threading.Event();self.graphs=transfer_history.GraphCache('item')
   self.show(self.sheet)
   if not self.sheet['actions']:
    try:self.setFocusId(9200)
    except Exception:pass
   # Build 177: a moving movie's sheet stays live (speed card, graph, rows) every 2 s while open.
   if self.fresh:threading.Thread(target=self.loop,daemon=True).start()
  def show(self,s):
   for k in ('title','status','tone','quality','sentence'):self.setProperty(k,s.get(k,''))
   for n,(label,tint) in enumerate(s.get('steps',[])):
    self.setProperty('step%d.label'%n,label);self.setProperty('step%d.tint'%n,tint)
    pct=(100 if self.row['state']=='ready' else float(s.get('bar') or 0)) if n==2 else (100 if tint=='FF30D158' else 50)
    # Build 194: Kodi cannot size a progress bar from a window property, so the script sets each step bar.
    try:self.getControl(library_page.STEP_BARS+n).setPercent(pct)
    except Exception:pass
   for k in ('title','text','button'):self.setProperty('need.'+k,s.get('need',{}).get(k,''))
   self.setProperty('poster',poster(self.row))
   self.setProperty('card',s.get('card',''))
   self.setProperty('bar',s.get('bar',''));self.setProperty('bar.tint',s.get('bar_tint',''))
   self.setProperty('facts.n',str(len(s['facts'])))
   for n in range(library_rows.FACTS):
    label,value=s['facts'][n] if n<len(s['facts']) else ('','')
    self.setProperty('fact%d.label'%n,label);self.setProperty('fact%d.value'%n,value)
    self.setProperty('fact%d.tint'%n,'FF30D158' if s.get('tone')=='ok' and n<2 else 'FFFFFFFF')
   for n in range(3):
    label,action=s['actions'][n] if n<len(s['actions']) else ('','')
    self.setProperty('action%d.label'%(n+1),label)
    # "Keep as it is" stays red (it gives up on preparing); the others are ordinary buttons.
    if n:self.setProperty('action%d.colour'%(n+1),'FFFF453A' if action in ('keep','') else 'FFFFFFFF')
   if s.get('card'):self.speed(s)
  def speed(self,s):
   import transfer_history
   history=transfer_history.load(profile)
   j=(history.get('jobs') or {}).get(s['card']) or {}
   points=j.get('points') or [] if j.get('title')==s['title'] else []
   live=s.get('live') or {}
   rate=float(live.get('rate') or 0)
   moving=live.get('state') in ('running','slowed') and rate>0
   props=dict(library_rows.speed_card_text(live,j,self.row.get('size'),s.get('bar')))
   ok=len(points)>1 and any(pt[1]>0 for pt in points)
   import work_state
   folder=os.path.join(xbmcvfs.translatePath('special://skin/'),'extras','portrait','graph')
   props['card.graph']=self.graphs.image(work_state.job_key(live),points,
      live.get('tint_now') or library_rows.DOWN,folder,'special://skin/extras/portrait/graph',
      width=library_page.PLOT_W,height=library_page.GRAPH[3]-54,scale=transfer_history.device_scale(),start=j.get('start'),
      now=points[-1][0] if points else None) if ok else ''
   # No graph yet: the step while it moves, else the model's own line (a stale state reads 'Updating…').
   props['card.wait']='' if ok else ((live.get('step') or 'Measuring…') if live.get('state') in ('running','slowed') else live.get('line','Updating…'))
   if ok:
    labels=transfer_history.graph_labels(points,j.get('start'))
    for k,v in labels.items():
     if isinstance(v,str):props['card.'+k]=v
    try:
     gx,gy,gw,gh=library_page.GRAPH
     self.getControl(library_page.PEAK).setPosition(int(54+gx+min(library_page.PLOT_W-300,max(0,labels['peak_x']*library_page.PLOT_W+8))),gy+round((gh-54)*.2)-52)
    except Exception:pass
   for k,v in props.items():self.setProperty(k,v)
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    try:
     fresh=self.fresh() if self.fresh else None
     if fresh:self.sheet,self.row=fresh
     elif self.fresh:
      self.sheet=dict(self.sheet,live={'state':'stale','line':'Updating…'},status='Updating…',actions=[])
     self.show(self.sheet)
    except Exception as error:xbmc.log('Library status sheet: %s: %s'%(type(error).__name__,error),xbmc.LOGWARNING)
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def onClick(self,control):
   if control==9004 and self.sheet.get('need',{}).get('action'):
    self.recovery=self.sheet['need']['action'];self.finish()
   elif control in (9201,9202,9203) and len(self.sheet['actions'])>control-9201:
    self.chosen=self.sheet['actions'][control-9201];self.finish()
   elif control in (9200,9099):self.finish()
  def finish(self):
   self.stop.set();self.close()

 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.offset=0;self.graphs=transfer_history.GraphCache('spark');self.filter=getattr(self,'filter','all');self.checking=0;self.shown=None;self.view=None
   self.stop=threading.Event();self.busy=threading.Lock()
   self.setProperty('filter',self.filter);self.setProperty('title',library_rows.TITLES.get(self.filter,'Library status'))
   self.refresh(force=True)
   threading.Thread(target=self.loop,daemon=True).start()
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    if self.stop.is_set():break
    try:self.refresh()
    except Exception as error:xbmc.log('Library status: %s'%error,xbmc.LOGWARNING)
  def refresh(self,force=False):
   with self.busy:
    state,view=snapshot(profile,notices.downloads,lambda:notices.uploads(profile))
    if self.checking and (state.get('library') or {}).get('checked',0)>=self.checking:self.checking=0
    if self.checking and time.time()-self.checking>300:self.checking=0
    self.view=view
    props=library_rows.page_properties(view,bool(self.checking))
    for k,v in props.items():self.setProperty(k,v)
    items=library_rows.list_items(view,self.filter)
    self.items=items
    # Build 194: one pool of rows per section (library_page.POOLS), as the approved boards draw them.
    pools=library_rows.pools(items)
    self.pools=pools
    self.setProperty('empty','' if items or (view.get('model') or {}).get('jobs') else 'No downloaded videos here yet.')
    model=view.get('model') or {}
    self.setProperty('queue','true' if model.get('next') else '')
    for k in ('title','text','button'):self.setProperty('need.'+k,(model.get('needs') or [{}])[0].get(k,''))
    import work_state
    conv=work_state.job(model,'conv') or {}
    for k in ('title','line','step','state'):self.setProperty('work.'+k,str(conv.get(k,'')))
    # Board 2: slowed by AirPlay still moves, so the ring keeps the job's colour; paused or stale turns it grey.
    self.setProperty('work.tint',str(conv.get('tint') if conv.get('state')=='slowed' else conv.get('tint_now','')))
    speed,left=library_rows.speed_left(conv)
    self.setProperty('work.speed',speed);self.setProperty('work.left',left)
    self.setProperty('work.metrics',work_state.metrics_line(conv))
    self.setProperty('work.ring',library_rows.ring_name(conv.get('pct')))
    self.setProperty('work.percent','' if conv.get('indeterminate') else '%d%%'%float(conv.get('pct') or 0))
    self.setProperty('work.poster',poster(conv))
    graph=''
    if conv:
     import transfer_history as th
     j=(th.load(profile).get('jobs') or {}).get('conv') or {}
     if j.get('title')==conv.get('title') and len(j.get('points') or [])>1:
      folder=os.path.join(xbmcvfs.translatePath('special://skin/'),'extras','portrait','spark')
      graph=self.graphs.image(work_state.job_key(conv),j['points'],conv['tint_now'],folder,
       'special://skin/extras/portrait/spark',width=438,height=81,scale=th.device_scale(),guides=False)
    self.setProperty('work.graph',graph)
    for key,base,slots,_ in library_page.POOLS:
     rows=pools.get(key,[])
     for n in range(slots):
      i=rows[n] if n<len(rows) else {}
      r=i.get('row',{});iprops=i.get('props',{})
      values=dict(title=i.get('label',''),sub=i.get('label2',''),number=iprops.get('number',''),state=iprops.get('state',''),
                  pos=iprops.get('pos','only'),off=iprops.get('off',''),pct='%d%%'%int(r.get('pct') or 0) if key=='down' and i else '',
                  poster=poster(r) if r and key=='down' else '')
      for k,v in values.items():self.setProperty('%s.%d.%s'%(key,n,k),v)
      if key=='down':
       try:self.getControl(library_page.DOWN_BARS+n).setPercent(float(r.get('pct') or 0))
       except Exception:pass
    # The segmented summary bar: one segment per count, 8-unit gaps (Kodi cannot size these from a property).
    for n,(x,width) in enumerate(library_rows.segments([int(props.get('count.'+k) or 0) for k in ('ready','working','next','kept')],
                                                      library_page.BAR_W,library_page.BAR_GAP)):
     try:
      c=self.getControl(library_page.SEGMENTS+n);c.setPosition(p_side+library_page.BAR_X+x,library_page.BAR_Y);c.setWidth(max(0,width))
      c.setVisible(width>0)
     except Exception:pass
  def set_filter(self,key):
   # A folder (Waiting, Ready, Kept) or a filter: the page's title says which; Back returns to All.
   self.offset=0;self.filter=key;self.setProperty('filter',key);self.setProperty('title',library_rows.TITLES.get(key,'Library status'))
   self.refresh(force=True)
  def finish(self):
   self.stop.set();self.close()
  def go_back(self):
   if getattr(self,'filter','all')!='all':self.set_filter('all')
   else:self.finish()
  def onAction(self,action):
   if action.getId() in BACK:self.go_back()
  def onClick(self,control):
   if control==library_page.BACK:self.go_back()
   elif control==library_page.CHECK:self.check()
   elif control==library_page.EDIT:
    # Waiting › Edit order: the Queue page (▲ ▼); this page shows the new order when it comes back.
    tool_windows.open_queue(profile);self.refresh(force=True)
   elif FILTER_BASE<=control<FILTER_BASE+len(library_page.FILTERS):self.set_filter(library_page.FILTERS[control-FILTER_BASE][0])
   elif control==library_page.NEED:
    need=((self.view.get('model') or {}).get('needs') or [{}])[0]
    if need.get('action'):self.finish();xbmc.executebuiltin(need['action'])
   elif control in (library_page.WORK,library_page.WORK+100):
    import work_state
    conv=work_state.job(self.view.get('model'),'conv')
    if conv:
     row=next((r for r in self.view['rows']['preparing'] if r['title']==conv['title']),None)
     if row:self.open_item({'kind':'row','row':row})
   else:
    for key,base,slots,_ in library_page.POOLS:
     if base<=control<base+slots:
      rows=getattr(self,'pools',{}).get(key,[])
      if control-base<len(rows):self.open_item(rows[control-base])
      break
  def control_for(self,item):
   """The button id that opens this row (its section's pool, library_page.POOLS)."""
   key=lambda i:(i.get('props',{}).get('id'),i.get('title'))
   for name,base,slots,_ in library_page.POOLS:
    rows=[key(r) for r in getattr(self,'pools',{}).get(name,[])]
    if key(item) in rows and rows.index(key(item))<slots:return base+rows.index(key(item))
   return library_page.WORK if item.get('props',{}).get('state')=='preparing' else None
  def check(self):
   if not addon.getSettingBool('prepare_downloads'):
    if not dialog.yesno('Library status','Preparing videos for Kodi and AirPlay is turned off. Turn it on and check now?',
                        nolabel='Cancel',yeslabel='Turn on'):return
    addon.setSettingBool('prepare_downloads',True)
   self.checking=time.time();prepare_downloads.request_check(profile);self.refresh()
  def open_row(self,position):
   items=getattr(self,'items',[])
   if not 0<=position<len(items):return
   self.open_item(items[position])
  def open_item(self,item):
   if item['kind']=='folder':self.set_filter(item['props']['folder']);return
   if item['kind']!='row':return
   try:sheet=Details(library_page.ITEM,here,'Default','1080i')
   except RuntimeError:
    xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')   # a page added while Kodi runs (build 173)
    sheet=Details(library_page.ITEM,here,'Default','1080i')
   wanted=item['row']
   def fresh():
    _,view=snapshot(profile,notices.downloads,lambda:notices.uploads(profile))
    for rows in view['rows'].values():
     for r in rows:
      if r.get('id')==wanted.get('id') and r.get('title')==wanted.get('title'):return library_rows.details(r,view),r
    matches=[r for group in view['rows'].values() for r in group if wanted.get('state')=='preparing' and r.get('state') in ('preparing','ready') and r.get('title')==wanted.get('title')]
    if len(matches)==1:return library_rows.details(matches[0],view),matches[0]
    return None
   sheet.setup(library_rows.details(item['row'],self.view),item['row'],fresh)
   sheet.doModal()
   chosen=sheet.chosen;recovery=sheet.recovery;chosen_row=sheet.row;live=sheet.sheet.get('live') or {}
   if hasattr(sheet,'stop'):sheet.stop.set()
   del sheet
   if recovery:self.finish();xbmc.executebuiltin(recovery);return
   if chosen and chosen[1] in ('play','tv'):
    play(chosen_row,chosen[1]=='tv');return
   if chosen and chosen[1] in ('toggle','cancel'):
    import transfer_control
    kind=live.get('kind')
    action=chosen[1]
    if kind=='down':
     command='resume' if live.get('state')=='paused_by_you' else 'pause'
     if action=='cancel':
      if not dialog.yesno('Cancel download','Stop downloading %s and delete what has downloaded so far?'%live.get('title','this video')):return
      command='cancel'
     if live.get('id') and not notices.engine_action(command,live['id']):
      dialog.notification('Elementum','The download engine did not answer',xbmcgui.NOTIFICATION_WARNING,3000)
    elif action=='toggle':
     channel='conv' if kind in ('conv','repack') else 'up'
     transfer_control.set_paused(profile,channel,not transfer_control.paused(profile,channel))
    elif kind=='copy' and live.get('hash'):
     if dialog.yesno('Cancel download','Stop copying %s from AllDebrid to Google Drive? What has been copied so far is dropped.'%live.get('title','this video')):
      transfer_control.cancel_copy(profile,live['hash'])
    self.refresh(force=True);return
   if chosen and chosen[1]=='quicker':
    find_quicker(item['row']);return
   if chosen and chosen[1]=='now':
    # Owner (build 178): start this one now, over the one converting (which starts over later: no resume yet).
    state=prepare_downloads.load(profile);running=prepare_downloads.running_id(state)
    if running and running!=str(item['row']['id']):
     title=prepare_downloads.drivelibrary.display_title((state.get('current') or {}).get('title',''))
     if not dialog.yesno('Start converting now','Start %s now? %s stops and starts again from the beginning later.'%(item['row']['title'],title),
                         nolabel='Cancel',yeslabel='Start now'):return
   if chosen:
    label,action=chosen
    if not addon.getSettingBool('prepare_downloads'):
     if not dialog.yesno('Library status','Preparing videos for Kodi and AirPlay is turned off. Turn it on so this can happen?',
                         nolabel='Cancel',yeslabel='Turn on'):return
     addon.setSettingBool('prepare_downloads',True)
    prepare_downloads.request(profile,action,item['row']['id'])
    dialog.notification('Library status','%s: %s'%(label,item['row']['title']),xbmcgui.NOTIFICATION_INFO,2500)
    self.refresh(force=True)

 def find_quicker(row):
  """Library status › a movie that must be re-encoded › "Find a version without converting": Elementum's sources for
  the same movie or episode, only those that need no conversion, at the same quality (deck_picker.avoid_request). The
  new copy goes to Drive the usual way; the library keeps it and sends the AV1 copy to the bin (Queue.unique)."""
  try:
   info=drivelibrary.parse(row.get('name') or '')
   found=drivelibrary.artwork('tv' if info['season'] else 'movie',info['title'],info['year'],key,cache,get) if key else {}
  except Exception as error:
   xbmc.log('Library status: TMDb lookup failed: %s'%error,xbmc.LOGWARNING);info,found={},{}
  tmdb=str((found or {}).get('tmdb_id') or '')
  if not tmdb:
   dialog.ok('Find a version without converting','TMDb did not recognise "%s", so its other versions cannot be looked up.'%row.get('title',''));return
  quality=quality_key(drivelibrary.quality(row.get('name') or ''))
  xbmcgui.Window(10000).setProperty('KodiIOS.AvoidAV1','%s|%d'%(quality,int(time.time())))
  # Owner (build 185): once a replacement is picked, this one stops converting (elementum_cloud → 'replace').
  xbmcgui.Window(10000).setProperty('KodiIOS.Replacing','%s|%d'%(row.get('id',''),int(time.time())))
  if info.get('season'):
   args='kind=episode,tvshow.tmdb_id=%s,season=%s,episode=%s,replace=1'%(tmdb,info['season'],info.get('episode') or '')
  else:args='kind=movie,tmdb=%s,replace=1'%tmdb
  xbmc.log('Library status: looking for a version of %s without conversion (%s)'%(row.get('title',''),quality or 'any quality'),xbmc.LOGINFO)
  xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,download,%s)'%args)

 def play(row,tv):
  """A ready movie's sheet: Play (Kodi plays it from Drive) or Play on TV (the same, then the AirPlay picker)."""
  import navigation
  try:_,driveid=drivelibrary.client()
  except Exception:driveid=None
  if not driveid:dialog.notification('Library status','Sign in to Google Drive first',xbmcgui.NOTIFICATION_WARNING,3000);return
  page.finish()
  xbmc.executebuiltin('PlayMedia(%s)'%drivelibrary.play_url(driveid,row['id']))
  if tv:
   def picker():
    monitor=xbmc.Monitor()
    for _ in range(40):   # up to 20 s for playback to start, then Play on TV opens over it
     if xbmc.Player().isPlayingVideo():xbmc.executebuiltin(navigation.CAST_SCRIPT);return
     if monitor.waitForAbort(0.5):return
   threading.Thread(target=picker,daemon=True).start()
 page=Page(library_page.WINDOW,here,'Default','1080i')
 page.doModal()
 if hasattr(page,'stop'):page.stop.set()
 del page

if __name__=='__main__':run(sys.argv[1:])
