"""Notification center page (the bell in the hub headers): live Elementum downloads, the Google Drive upload, then
earlier messages. The layout is portrait/IOSNotifications.xml, written by portrait.py; this fills it."""
import os,sys,threading
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import notice_page,notices,prepare_downloads,transfer_artwork,drivelibrary,library_tools,transfer_control

ICON={'download':('download.png','330A84FF'),'drive':('circle-check.png','3330D158'),'problem':('triangle-exclamation.png','33FF453A'),
      'update':('circle-down.png','330A84FF'),'info':('circle-info.png','33FF9F0A'),'general':('bell.png','338E8E93')}
FILTER_KEYS=('all','general','downloads','problems')   # buttons 9101-9104
SLOTS,ROWS=4,15
BACK=(9,10,92,110)   # parent dir, previous menu, nav back, back
# The touch keymap makes a long press a right click (navigation.TOUCH); a right click no control takes becomes
# previous menu (10), which closed the page (owner, build 185). On a transfer card both open its menu instead.
LONG=(101,117)       # right click, context menu

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

def transfer_card(job, running_id=''):
 """Control metadata stays with the model card so its long-press menu can cancel the right job."""
 card=dict(job,progress=job.get('pct') or 0,paused=job.get('state')=='paused_by_you')
 if job.get('kind') in ('conv','repack'):card['id']=job.get('id') or running_id
 if job.get('kind')=='copy':card.update(source='debrid',hash=job.get('hash') or '')
 return card


def model_cards(state,running_id=''):
 """Build 193: the Preparing and Uploading cards from the status model (work_state), the same words as Library status,
 Transfers and the bell. Returns (prepare card or {}, upload line or '')."""
 import work_state
 conv=work_state.job(state,'conv');copy=work_state.job(state,'up');card={}
 if conv:
  card={'title':conv['title'],'line':conv['line'],'progress':conv['pct'],'indeterminate':conv['indeterminate'] or conv['state'] not in work_state.MOVING,
        'running':conv['state'] in work_state.MOVING,'paused':conv['state']==work_state.PAUSED,'id':running_id}
 elif state and state.get('next'):
  first=state['next'][0]
  card={'title':first['title'],'progress':0,'indeterminate':False,'running':False,'id':first['id'],
        'line':'Paused by you' if first.get('paused') else (state.get('wait') or 'Up next · #1')}
 if card:card['queued']=len((state or {}).get('next') or [])
 return card,(copy['line'] if copy else '')

def next_text(titles,room=60):   # Kodi cuts the line short of the link (notifications_skin.LINK_W)
 """Board 5: 'Up next: Scary Movie, then Fall 2 Deadpoint ·' with the titles cut short, so the Library status link
 after it always shows."""
 if not titles:return ''
 import re
 cut=lambda t,n:t if len(t)<=n else t[:max(1,n-1)].rstrip()+'…'
 shown=[re.sub(r'\s*\((19|20)\d\d\)$','',t) for t in titles[:2]]
 budget=max(8*len(shown),room-len('Up next: ')-(len(', then ') if len(shown)>1 else 0))
 # Each title gets an even share; room one title does not need goes to the other.
 share=budget//len(shown);spare=sum(max(0,share-len(t)) for t in shown)
 return 'Up next: '+', then '.join(cut(t,share+spare) for t in shown)+' ·'

def message_properties(items,filter_key,now=None):
 """Window properties for the Earlier rows under the chosen filter, and the empty state."""
 kinds=notices.FILTERS.get(filter_key,notices.KINDS);shown=[i for i in items if i.get('kind','info') in kinds][:ROWS]
 props={'has.msg':'true' if shown else ''}
 for n in range(1,ROWS+1):
  i=shown[n-1] if n<=len(shown) else {}
  glyph,tint=ICON.get(i.get('kind'),ICON['info']) if i else ('','')
  # Build 194 (board 5): one grouped card; the tile is the kind's colour at 18 %, its glyph the full colour.
  pos='' if not i else 'only' if len(shown)==1 else 'first' if n==1 else 'last' if n==len(shown) else 'mid'
  props.update({'msg.%d.title'%n:i.get('title',''),'msg.%d.text'%n:i.get('text',''),'msg.%d.ago'%n:notices.ago(i['time'],now) if i else '',
                'msg.%d.icon'%n:glyph,'msg.%d.tint'%n:('2E'+tint[2:]) if tint else '','msg.%d.glyph'%n:('FF'+tint[2:]) if tint else '',
                'msg.%d.pos'%n:pos,'msg.%d.unread'%n:'true' if i and not i.get('was_read') else ''})
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
   import live_window
   self.guard=live_window.Guard(self)   # ISSUE-123: controls only while this page is open
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
    import work_state
    model=work_state.load(profile) if show_live else None
    jobs=(model or {}).get('jobs') or []
    self.downloads=[transfer_card(j) for j in jobs if j['kind']=='down']
    ups=[transfer_card(j) for j in jobs if j['kind'] in ('copy','upload')]
    conv=work_state.job(model,'conv')
    current=transfer_card(conv,prepare_downloads.running_id(prepare_downloads.load(profile))) if conv else {}
    self.ups,self.current=ups,current
    self.setProperty('live','true' if jobs else '')
    self.setProperty('has.prepare','true' if current else '')
    self.setProperty('has.dl','true' if self.downloads else '')
    self.setProperty('has.up','true' if ups else '')
    cache=drivelibrary.load_json(transfer_artwork.cache_path(profile),{})
    pairs=[('dl.%d.'%(n+1),self.downloads[n] if n<len(self.downloads) else {}) for n in range(SLOTS)]
    pairs += [('up.',ups[0] if ups else {}),('prepare.',current)]
    self.artnames=[j.get('name') or j['title'] for j in jobs]
    import notifications_skin
    bars={'prepare.':notifications_skin.BARS,'up.':notifications_skin.BARS+1}
    bars.update({'dl.%d.'%k:notifications_skin.BARS+1+k for k in range(1,SLOTS+1)})
    for pre,j in pairs:
     for key in ('title','line'):self.setProperty(pre+key,str(j.get(key,'')))
     self.setProperty(pre+'pct',str(j.get('pct') or 0))
     if pre in bars:self.percent(bars[pre],j.get('pct') or 0)
     self.setProperty(pre+'tint',j.get('tint','') if j.get('state')=='slowed' else j.get('tint_now',''))   # board 5: slowed still moves
     self.setProperty(pre+'poster',transfer_artwork.describe(j.get('name') or j.get('title',''),cache)['poster'] if j else '')
    titles=[j['title'] for j in (model or {}).get('next') or []]
    self.setProperty('next.text',next_text(titles))
    self.update_empty()
  def percent(self,control,value):
   self.guard.percent(control,value or 0)
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
   import time
   code=action.getId()
   if code in LONG or code==10:
    card=transfer_control.card_of(self.getFocusId(),SLOTS)
    if card:
     # One long press can arrive as both actions: the second one, just after the menu, does nothing.
     if time.time()-getattr(self,'menu_done',0)<1.5:return
     if self.long_press(*card):self.menu_done=time.time();return
   if code in BACK:self.finish()
  def long_press(self,kind,n):
   """The menu for a held transfer card: pause / resume, cancel, the speed graph. False when the card is empty."""
   if kind=='down':item=self.downloads[n] if n<len(self.downloads) else None
   elif kind=='up':item=self.ups[0] if getattr(self,'ups',None) else None
   else:item=getattr(self,'current',None) or None
   if not item:return False
   rows=transfer_control.menu(kind,item,transfer_control.paused(profile,'up'),transfer_control.paused(profile,'conv'))
   pick=xbmcgui.Dialog().contextmenu([label for label,_ in rows])
   if 0<=pick<len(rows):self.act(kind,item,rows[pick][1])
   return True
  def act(self,kind,item,action):
   import transfers
   title=item.get('title','') or 'this video'
   if action=='speed':transfers.run([kind]);return
   if kind=='down':
    if action=='toggle':command='resume' if item.get('paused') else 'pause'
    elif xbmcgui.Dialog().yesno('Cancel download','Stop downloading %s and delete what has downloaded so far?'%title):command='cancel'
    else:return
    if not notices.engine_action(command,item['id']):xbmcgui.Dialog().notification('Elementum','The download engine did not answer',xbmcgui.NOTIFICATION_WARNING,3000)
   elif action=='toggle':
    now=not transfer_control.paused(profile,kind);transfer_control.set_paused(profile,kind,now)
    words={'up':('Uploads paused','Uploads resumed'),'conv':('Converting paused','Converting resumed')}[kind]
    xbmcgui.Dialog().notification('Kodi iOS',words[0] if now else words[1],xbmcgui.NOTIFICATION_INFO,2500)
   elif kind=='up':
    if xbmcgui.Dialog().yesno('Cancel download','Stop copying %s from AllDebrid to Google Drive? What has been copied so far is dropped.'%title):
     transfer_control.cancel_copy(profile,item['hash'])
   elif kind=='conv':
    if xbmcgui.Dialog().yesno('Cancel conversion','Stop converting %s? It stays in your library as it is and plays on this iPhone. Library status can convert it later for Play on TV.'%title):
     prepare_downloads.request(profile,'keep',item['id'])
   self.refresh()
  def finish(self):
   self.stop.set();self.guard.close()
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
   elif control==9440:
    import library_status;library_status.run()
   elif 9460<=control<=9465:
    if control==9460:self.long_press('conv',0)
    elif control==9461:self.long_press('up',0)
    else:self.long_press('down',control-9462)
   elif control in (9432,9433) or 9436<=control<=9435+SLOTS:
    # Owner: the speed graph shows only when a transfer card is tapped.
    import transfers;transfers.run(['up' if control==9432 else 'conv' if control==9433 else 'down'])
   elif 9501<=control<=9500+ROWS:
    # Owner (build 159): a message opens its details and its part of kodi.log; its own action (if any) is a button there.
    n=control-9500
    if n>len(self.shown):return
    item=self.shown[n-1]
    if library_tools.airplay_notice(item):
     # An AirPlay message opens the AirPlay check: the last Play on TV as steps, and what to try.
     import tool_windows;tool_windows.open_airplay(profile);return
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
