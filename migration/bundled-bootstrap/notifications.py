"""Notification center page (the bell in the hub headers): live Elementum downloads, the Google Drive upload, then
earlier messages. The layout is portrait/IOSNotifications.xml, written by portrait.py; this fills it."""
import os,sys,threading
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import notices

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

def run():
 import xbmc,xbmcgui,xbmcvfs
 profile=xbmcvfs.translatePath('special://profile/')
 home=os.path.dirname(os.path.abspath(__file__))

 class Page(xbmcgui.WindowXMLDialog):
  def onInit(self):
   items=notices.load(profile)
   # The blue dot marks what was new when the page opened; everything counts as read from now on.
   self.items=[dict(i,was_read=i.get('read',False)) for i in items];notices.mark_all_read(profile)
   xbmcgui.Window(10000).setProperty('Notices.Unread','')
   self.filter='all';self.shown=[];self.downloads=[];self.lock=threading.Lock();self.stop=threading.Event()
   self.show_messages();self.refresh()
   threading.Thread(target=self.loop,daemon=True).start()
  def set_all(self,props):
   for key,value in props.items():self.setProperty(key,value)
  def show_messages(self):
   props,self.shown=message_properties(self.items,self.filter)
   props['filter']=self.filter;self.set_all(props);self.update_empty()
  def update_empty(self):
   live=self.filter in ('all','downloads') and (self.getProperty('has.dl') or self.getProperty('has.up'))
   self.setProperty('empty','' if (self.shown or live) else 'true')
  def refresh(self):
   with self.lock:
    show_live=self.filter in ('all','downloads')
    self.downloads=notices.downloads() if show_live else [];ups=notices.uploads(profile) if show_live else []
    self.set_all(card_properties(self.downloads,ups))
    for n in range(1,SLOTS+1):
     if n<=len(self.downloads):self.percent(9400+n,self.downloads[n-1]['progress'])
    if ups:self.percent(9430,ups[0]['progress'])
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
    n=control-9500
    if n<=len(self.shown) and self.shown[n-1].get('action'):
     self.finish();xbmc.executebuiltin(self.shown[n-1]['action'])

 page=Page('IOSNotifications.xml',home,'Default','1080i')
 page.doModal();page.stop.set() if hasattr(page,'stop') else None
 del page

if __name__=='__main__':run()

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass
