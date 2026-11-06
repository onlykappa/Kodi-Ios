"""Settings › Library › Library status (portrait/IOSLibraryStatus.xml, drawn by resources/lib/library_page.py).

Shows every video in Google Drive › Kodi Downloads: what is ready for Kodi and AirPlay, what is being prepared,
downloaded or uploaded, what waits (and why), and what is kept as it is. Refreshes every two seconds while open.
Check now (top right) asks the service to look at Google Drive again; a row opens that video's details sheet
(portrait/IOSLibraryItem.xml) with what can be done about it (prepare next, try again, keep as it is), which the
service applies on its next pass (prepare_downloads.request)."""
import os,shutil,sys,threading,time
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import library_page,library_rows,prepare_downloads

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

def usage(places):
 """{what: bytes} for [(what, path)], each file counted once (a folder inside an earlier one is not counted again)."""
 out={};seen=[]
 for what,path in places:
  try:real=os.path.realpath(str(path))
  except (OSError,ValueError):continue
  if not real or not os.path.isdir(real) or any(real==s or real.startswith(s+os.sep) for s in seen):continue
  seen.append(real)
  size=folder_size(real)
  if size:out[what]=out.get(what,0)+size
 return out

def places(profile,home,elementum_path=''):
 """Where Kodi keeps things on the phone, in the order they are counted (the most specific first)."""
 import updates
 data=os.path.join(profile,'addon_data')
 kept=updates.updates_folder(home)
 return [('preparing',str(prepare_downloads.location(profile).parent/'preparing-videos')),
         ('Elementum downloads',elementum_path or str(kept.with_name('Elementum Downloads'))),
         ('Elementum downloads',str(kept.with_name('Elementum Downloads'))),
         ('Elementum',os.path.join(data,'plugin.video.elementum')),
         ('videos on this iPhone',str(kept.with_name('Kodi Downloads'))),
         ('artwork',os.path.join(profile,'Thumbnails')),
         ('temporary files',os.path.join(home,'temp')),
         ('add-on downloads',os.path.join(home,'addons','packages')),
         ('add-on data',data)]

def snapshot(profile,downloads,uploads):
 """library_view() for the page right now (never raises: an empty library on any error)."""
 # Choices not yet applied by the service show at once (it applies them before its next video).
 state=prepare_downloads.apply_to(prepare_downloads.snapshot(profile),prepare_downloads.pending_requests(profile),time.time())
 work=prepare_downloads.location(profile).parent/'preparing-videos'
 import phone_space
 try:free=phone_space.free(str(work if work.exists() else work.parent))
 except OSError:free=None
 try:down=downloads() or []
 except Exception:down=[]
 try:up=uploads() or []
 except Exception:up=[]
 return state,prepare_downloads.library_view(state,down,up,free,folder_size(work) if work.exists() else 0)

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
  def setup(self,sheet,row):
   self.sheet,self.row,self.chosen=sheet,row,None
  def onInit(self):
   s=self.sheet
   for k in ('title','status','tone','quality'):self.setProperty(k,s[k])
   self.setProperty('poster',poster(self.row))
   for n in range(4):
    label,value=s['facts'][n] if n<len(s['facts']) else ('','')
    self.setProperty('fact%d.label'%n,label);self.setProperty('fact%d.value'%n,value)
   for n in range(2):
    self.setProperty('action%d.label'%(n+1),s['actions'][n][0] if n<len(s['actions']) else '')
   if not s['actions']:
    try:self.setFocusId(9200)
    except Exception:pass
  def onAction(self,action):
   if action.getId() in BACK:self.close()
  def onClick(self,control):
   if control in (9201,9202) and len(self.sheet['actions'])>control-9201:
    self.chosen=self.sheet['actions'][control-9201];self.close()
   elif control in (9200,9099):self.close()

 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   self.filter=getattr(self,'filter','all');self.checking=0;self.shown=None;self.view=None
   self.stop=threading.Event();self.busy=threading.Lock()
   self.setProperty('filter',self.filter);self.setProperty('title',library_rows.TITLES.get(self.filter,'Library status'))
   self.refresh(force=True)
   threading.Thread(target=self.loop,daemon=True).start()
   self.measure()
  def measure(self):
   """What Kodi keeps on the phone, for the Phone space card (in the background: walking the folders takes a while)."""
   def run():
    try:
     try:engine=xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.elementum').getSetting('download_path') or '')
     except Exception:engine=''
     self.used=usage(places(profile,xbmcvfs.translatePath('special://home/'),engine))
     if not self.stop.is_set():self.refresh()
    except Exception as error:xbmc.log('Library status: phone space not measured: %s'%error,xbmc.LOGWARNING)
   threading.Thread(target=run,daemon=True).start()
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
    props=library_rows.page_properties(view,bool(self.checking),getattr(self,'used',None))
    for k,v in props.items():self.setProperty(k,v)
    try:self.getControl(library_page.SPACE).setPercent(float(props['space_pct']))
    except Exception:pass
    items=library_rows.list_items(view,self.filter)
    shape=[(i['kind'],i['props'].get('id',''),i['props'].get('state',''),i['label']) for i in items]
    listing=self.getControl(library_page.LIST)
    if force or shape!=self.shown:
     keep=listing.getSelectedPosition() if self.shown is not None and not force else 0
     made=[]
     for i in items:
      li=xbmcgui.ListItem(i['label'],i.get('label2',''))
      for k,v in i['props'].items():li.setProperty(k,str(v))
      if i['kind']=='row':li.setArt({'poster':poster(i['row'])})
      made.append(li)
     listing.reset();listing.addItems(made)
     if made:listing.selectItem(max(0,min(keep,len(made)-1)))
     self.shown=shape;self.items=items
    else:
     # Same rows: only percentages, lines and posters change, without moving the selection.
     for n,i in enumerate(items):
      li=listing.getListItem(n)
      li.setLabel2(i.get('label2',''))
      for k in ('pct','ring','warn'):
       if k in i['props']:li.setProperty(k,str(i['props'][k]))
      if i['kind']=='row' and not li.getArt('poster'):
       art=poster(i['row'])
       if art:li.setArt({'poster':art})
     self.items=items
  def set_filter(self,key):
   # A folder (Waiting, Ready, Kept) or a filter: the page's title says which; Back returns to All.
   self.filter=key;self.setProperty('filter',key);self.setProperty('title',library_rows.TITLES.get(key,'Library status'))
   self.refresh(force=True)
  def finish(self):
   self.stop.set();self.close()
  def go_back(self):
   if self.filter!='all':self.set_filter('all')
   else:self.finish()
  def onAction(self,action):
   if action.getId() in BACK:self.go_back()
  def onClick(self,control):
   if control==library_page.BACK:self.go_back()
   elif control==library_page.CHECK:self.check()
   elif FILTER_BASE<=control<FILTER_BASE+len(library_page.FILTERS):self.set_filter(library_page.FILTERS[control-FILTER_BASE][0])
   elif control==library_page.LIST:self.open_row(self.getControl(library_page.LIST).getSelectedPosition())
  def check(self):
   if not addon.getSettingBool('prepare_downloads'):
    if not dialog.yesno('Library status','Preparing videos for Kodi and AirPlay is turned off. Turn it on and check now?',
                        nolabel='Cancel',yeslabel='Turn on'):return
    addon.setSettingBool('prepare_downloads',True)
   self.checking=time.time();prepare_downloads.request_check(profile);self.refresh();self.measure()
  def open_row(self,position):
   items=getattr(self,'items',[])
   if not 0<=position<len(items):return
   item=items[position]
   if item['kind']=='folder':self.set_filter(item['props']['folder']);return
   if item['kind']!='row':return
   sheet=Details(library_page.ITEM,here,'Default','1080i')
   sheet.setup(library_rows.details(item['row'],self.view),item['row'])
   sheet.doModal()
   chosen=sheet.chosen;del sheet
   if chosen:
    label,action=chosen
    if not addon.getSettingBool('prepare_downloads'):
     if not dialog.yesno('Library status','Preparing videos for Kodi and AirPlay is turned off. Turn it on so this can happen?',
                         nolabel='Cancel',yeslabel='Turn on'):return
     addon.setSettingBool('prepare_downloads',True)
    prepare_downloads.request(profile,action,item['row']['id'])
    dialog.notification('Library status','%s: %s'%(label,item['row']['title']),xbmcgui.NOTIFICATION_INFO,2500)
    self.refresh(force=True)

 page=Page(library_page.WINDOW,here,'Default','1080i')
 page.doModal()
 if hasattr(page,'stop'):page.stop.set()
 del page

if __name__=='__main__':run(sys.argv[1:])
