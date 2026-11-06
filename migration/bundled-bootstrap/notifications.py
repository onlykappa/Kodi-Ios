"""Notification center page (the bell in the hub headers): live Elementum downloads, the Google Drive upload, then
earlier messages. The layout is portrait/IOSNotifications.xml, written by portrait.py; this fills it."""
import os,sys,threading
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import notice_page,notices,prepare_downloads,transfer_artwork,drivelibrary

ICON={'download':('download.png','330A84FF'),'drive':('circle-check.png','3330D158'),'problem':('triangle-exclamation.png','33FF453A'),
      'update':('circle-down.png','330A84FF'),'info':('circle-info.png','33FF9F0A'),'general':('bell.png','338E8E93')}
FILTER_KEYS=('all','general','downloads','problems')   # buttons 9101-9104
SLOTS,ROWS=4,15
BACK=(9,10,92,110)   # parent dir, previous menu, nav back, back

def card_properties(downloads,uploads):
 """Window properties for the Downloading and Uploading cards (only the first SLOTS downloads have a card)."""
 props={'has.dl':'true' if downloads else '','has.up':'true' if uploads else ''}
 running=[d for d in downloads if not d['paused']]
 props['dl.summary']=('%d active'%len(running)) if running else ('Paused' if downloads else '')
 for n in range(1,SLOTS+1):
  d=downloads[n-1] if n<=len(downloads) else {}
  for key in ('title','line','speed'):props['dl.%d.%s'%(n,key)]=d.get(key,'')
  props['dl.%d.pausetext'%n]=('Resume' if d.get('paused') else 'Pause') if d else ''
 u=uploads[0] if uploads else {}
 for key in ('title','line'):props['up.'+key]=u.get(key,'')
 props['up.summary']=' · '.join(x for x in (u.get('folder',''),'then off the phone') if x) if u else ''
 return props

def message_properties(items,filter_key,now=None):
 """Window properties for the Earlier rows under the chosen filter, and the empty state."""
 kinds=notices.FILTERS.get(filter_key,notices.KINDS);shown=[i for i in items if i.get('kind','info') in kinds][:ROWS]
 props={'has.msg':'true' if shown else ''}
 for n in range(1,ROWS+1):
  i=shown[n-1] if n<=len(shown) else {}
  glyph,tint=ICON.get(i.get('kind'),ICON['info']) if i else ('','')
  props.update({'msg.%d.title'%n:i.get('title',''),'msg.%d.text'%n:i.get('text',''),'msg.%d.ago'%n:notices.ago(i['time'],now) if i else '',
                'msg.%d.icon'%n:glyph,'msg.%d.tint'%n:tint,'msg.%d.unread'%n:'true' if i and not i.get('was_read') else ''})
 return props,shown

KIND_WORDS={'download':'Downloads','drive':'Google Drive','problem':'Problem','update':'Update','info':'Kodi iOS','general':'General'}
NO_LOG='Kodi wrote nothing else about this around that time.'

def short(text):
 """Log text for a phone screen: app folders cut to their last parts."""
 import re
 return re.sub(r'/(?:private/)?var/(?:mobile|containers)/\S*?/((?:[^/\s"]+/)?[^/\s"]+)(?=["\s,:)]|$)',r'…/\1',str(text))

def detail_properties(item,records,now=None):
 """Window properties for the details sheet (portrait/IOSNoticeDetail.xml) and its log rows [(label, label2, level)]."""
 import time as _time
 glyph,tint=ICON.get(item.get('kind'),ICON['info'])
 worst=next((r for level in ('error','fatal','warning') for r in reversed(records) if r['level']==level),None)
 props={'title':item.get('title',''),'text':item.get('text',''),'icon':glyph,'tint':tint,
        'ago':' · '.join(x for x in (KIND_WORDS.get(item.get('kind'),'Kodi iOS'),notices.ago(item['time'],now) if item.get('time') else '') if x),
        'summary':short(notices.plain_record(worst)) if worst else short(item.get('text','')),'nolog':'' if records else NO_LOG,
        'action.label':'Open' if item.get('action') else ''}
 rows=[]
 for r in reversed(records):     # newest first, as the messages are
  count=r.get('count',1)
  when=_time.strftime('%H:%M:%S',_time.localtime(r['time']))
  rows.append((short(notices.plain_record(r)),'%s · %s%s'%(when,r['level'].capitalize(),' · %d times'%count if count>1 else ''),
               r['level'] if r['level'] in ('error','warning') else 'info'))
 return props,rows

def records_for(profile,item,log_path=None):
 """The kodi.log records kept for a message; for one from before they were kept, read now from this launch's log."""
 if 'log' in item:return notices.log_of(profile,item)
 if not log_path:return []
 try:
  with open(log_path,'rb') as handle:
   handle.seek(0,2);size=handle.tell();handle.seek(max(0,size-2*1024*1024))
   return notices.excerpt(notices.parse_log(handle.read().decode('utf-8','replace')),item.get('time',0),item.get('title',''))
 except OSError:return []

def run():
 import xbmc,xbmcgui,xbmcvfs,xbmcaddon
 profile=xbmcvfs.translatePath('special://profile/')
 home=os.path.dirname(os.path.abspath(__file__))
 log_path=os.path.join(xbmcvfs.translatePath('special://logpath/'),'kodi.log')

 class Detail(xbmcgui.WindowXMLDialog):
  def setup(self,props,rows):
   self.props,self.rows,self.chosen=props,rows,False
  def onInit(self):
   for key,value in self.props.items():self.setProperty(key,value)
   items=[]
   for label,label2,level in self.rows:
    li=xbmcgui.ListItem(label,label2);li.setProperty('level',level);items.append(li)
   try:
    listing=self.getControl(notice_page.LOG);listing.reset();listing.addItems(items)
   except Exception as error:_quiet('notifications:detail',error)
  def onAction(self,action):
   if action.getId() in BACK:self.close()
  def onClick(self,control):
   if control==notice_page.ACTION and self.props.get('action.label'):self.chosen=True;self.close()
   elif control==notice_page.LOG:
    index=self.getControl(notice_page.LOG).getSelectedPosition()
    if 0<=index<len(self.rows):xbmcgui.Dialog().textviewer(self.rows[index][1],self.rows[index][0])
   elif control in (notice_page.CLOSE,notice_page.DIM):self.close()

 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   items=notices.load(profile)
   # The blue dot marks what was new when the page opened; everything counts as read from now on.
   self.items=[dict(i,was_read=i.get('read',False)) for i in items];notices.mark_all_read(profile)
   xbmcgui.Window(10000).setProperty('Notices.Unread','')
   self.filter='all';self.shown=[];self.downloads=[];self.lock=threading.Lock();self.stop=threading.Event()
   self.attempted=set()
   try:self.artkey=drivelibrary.tmdb_key(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.themoviedb.helper').getAddonInfo('path')))
   except Exception:self.artkey=''
   self.show_messages();self.refresh()
   threading.Thread(target=self.loop,daemon=True).start()
   threading.Thread(target=self.art_loop,daemon=True).start()
  def set_all(self,props):
   for key,value in props.items():self.setProperty(key,value)
  def show_messages(self):
   props,self.shown=message_properties(self.items,self.filter)
   props['filter']=self.filter;self.set_all(props);self.update_empty()
  def update_empty(self):
   live=self.filter in ('all','downloads') and (self.getProperty('has.dl') or self.getProperty('has.up') or self.getProperty('has.prepare'))
   self.setProperty('empty','' if (self.shown or live) else 'true')
  def refresh(self):
   with self.lock:
    show_live=self.filter in ('all','downloads')
    self.downloads=notices.downloads() if show_live else [];ups=notices.uploads(profile) if show_live else []
    self.set_all(card_properties(self.downloads,ups))
    preparing=prepare_downloads.cards(profile) if show_live else []
    current=preparing[0] if preparing else {}
    self.setProperty('has.prepare','true' if preparing else '')
    self.setProperty('prepare.indeterminate','1' if current.get('indeterminate') else '')
    for key in ('title','line'):self.setProperty('prepare.'+key,str(current.get(key,'')))
    queued=current.get('queued',0)
    self.setProperty('prepare.summary',('Download → Drive → Prepare'+(' · %d remaining'%queued if queued else '')) if preparing else '')
    self.percent(9431,current.get('progress',0))
    for n in range(1,SLOTS+1):
     if n<=len(self.downloads):self.percent(9400+n,self.downloads[n-1]['progress'])
    if ups:self.percent(9430,ups[0]['progress'])
    self.artnames=[d.get('title','') for d in self.downloads]+[u.get('title','') for u in ups]+[current.get('title','')]
    cache=drivelibrary.load_json(transfer_artwork.cache_path(profile),{})
    for pre,name in [('dl.%d.'%(n+1),d.get('title','')) for n,d in enumerate(self.downloads[:SLOTS])]+[('up.',ups[0].get('title','') if ups else ''),('prepare.',current.get('title',''))]:
     self.setProperty(pre+'poster',transfer_artwork.describe(name,cache)['poster'] if name else '')
    self.update_empty()
  def percent(self,control,value):
   try:self.getControl(control).setPercent(float(value))
   except Exception as error:_quiet('notifications:70',error)
  def loop(self):
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(1):
    if self.stop.is_set():break
    try:self.refresh()
    except Exception as error:_quiet('notifications:76',error)
  def art_loop(self):
   import urllib.request
   def get(url):
    with urllib.request.urlopen(url,timeout=8) as response:return response.read(1024*1024)
   monitor=xbmc.Monitor()
   while not self.stop.is_set() and not monitor.waitForAbort(2):
    try:transfer_artwork.hydrate(profile,list(self.artnames),self.artkey,get,lambda:not self.stop.is_set(),self.attempted)
    except Exception as error:_quiet('notifications:artwork',error)
  def onAction(self,action):
   if action.getId() in BACK:self.finish()
  def finish(self):
   self.stop.set();self.close()
  def onClick(self,control):
   if control==9001:self.finish()
   elif control==9002:
    notices.clear(profile);self.items=[];self.show_messages()
   elif 9101<=control<9101+len(FILTER_KEYS):
    self.filter=FILTER_KEYS[control-9101];self.show_messages();self.refresh()
   elif 9411<=control<=9410+SLOTS or 9421<=control<=9420+SLOTS:
    n=control%10
    if n>len(self.downloads):return
    d=self.downloads[n-1]
    if control<9420:command='resume' if d['paused'] else 'pause'
    elif xbmcgui.Dialog().yesno('Cancel download','Stop downloading %s and delete what has downloaded so far?'%d['title']):command='cancel'
    else:return
    if not notices.engine_action(command,d['id']):xbmcgui.Dialog().notification('Elementum','The download engine did not answer',xbmcgui.NOTIFICATION_WARNING,3000)
    self.refresh()
   elif 9501<=control<=9500+ROWS:
    # Owner (build 159): a message opens its details and its part of kodi.log; its own action (if any) is a button there.
    n=control-9500
    if n>len(self.shown):return
    item=self.shown[n-1]
    sheet=Detail(notice_page.SHEET,home,'Default','1080i')
    sheet.setup(*detail_properties(item,records_for(profile,item,log_path)))
    sheet.doModal();chosen=sheet.chosen;del sheet
    if chosen and item.get('action'):
     self.finish();xbmc.executebuiltin(item['action'])

 page=Page('IOSNotifications.xml',home,'Default','1080i')
 page.doModal();page.stop.set() if hasattr(page,'stop') else None
 del page

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass

if __name__=='__main__':run()
