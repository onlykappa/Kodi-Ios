"""Service-owned foreground HTTP source cache for AirPlay/TV; reuse Drive's byte-range engine.

Only the original resolved stream URL/headers are held in RAM. A per-launch authenticated
loopback control endpoint gives other Kodi interpreters a source URL that survives their exit.
One source at a time, at most 96 MiB cached, no Drive OAuth or media files.
"""
import http.server,ipaddress,json,secrets,threading,time,urllib.error,urllib.parse,urllib.request
import drive_stream,umbrella_recovery
PROPERTY='KodiIOS.RemoteMedia'
BLOCK=4*1024*1024;KEEP=24;AHEAD=4
# ISSUE-259: a video playing in Kodi has its first two blocks and its last block read once it has played steadily for
# WARM_AFTER seconds on Wi-Fi (12 MiB; Matroska usually keeps its index at the end), so Play on TV skips opening the source.
WARM_BLOCKS=2;WARM_AFTER=8
# ISSUE-280 (owner, build 430 log 72b62563: an Umbrella episode sat at "Getting ready to play… 0%" for 32 s, 19 s of it
# inside Kodi's own open of the MKV over one AllDebrid connection, about 0.7 MB/s each: ISSUE-163): Kodi's own player
# reads an Umbrella MKV / AVI / WebM through this cache too: four connections at once, and the file's first blocks and
# its last block (Matroska's tags and index) asked for the moment the link is known. Released after KODI_IDLE seconds
# with no read. False: Kodi reads the link itself, as before.
KODI_PLAYBACK=True;KODI_IDLE=120


def eligible(source):
 raw=source.partition('|')[0];p=urllib.parse.urlsplit(raw)
 if p.scheme not in ('http','https') or not p.hostname:return False
 if not p.path.lower().endswith(('.mkv','.avi','.webm')):return False
 if p.hostname.lower()=='localhost':return False
 try:return not ipaddress.ip_address(p.hostname).is_loopback
 except ValueError:return True


class Foreground(drive_stream.DriveStream):
 def __init__(self,source,context=None,open_url=None,clock=time.monotonic):
  raw,_,extra=source.partition('|');p=urllib.parse.urlsplit(raw)
  if p.scheme not in ('http','https') or not p.hostname:raise ValueError('Not an HTTP media source')
  self.remote_url=raw
  self.renew_lock=threading.Lock();self.renewal=None;self.renew_link=None;self.renewed=False;self.renewal_state='unavailable'
  self.renew_clock=clock;self.renew_after=0.0
  self.remote_headers={k:v for k,v in urllib.parse.parse_qsl(extra,keep_blank_values=True)
                       if k.lower() not in ('host','range','connection','content-length','transfer-encoding')}
  if not any(k.lower()=='user-agent' for k in self.remote_headers):self.remote_headers['User-Agent']='Kodi-iOS-AirPlay/1'
  opener=open_url or (lambda request,timeout:urllib.request.urlopen(request,timeout=timeout,context=context))
  def remote(request,timeout):
   headers=dict(self.remote_headers);headers['Range']=request.get_header('Range')
   attempted=self.remote_url
   try:response=opener(urllib.request.Request(attempted,headers=headers),timeout)
   except urllib.error.HTTPError as error:
    error.close()
    if error.code not in (401,403,404,410) or not self._renew(attempted):raise
    response=opener(urllib.request.Request(self.remote_url,headers=headers),timeout)
   span=drive_stream.SPAN.match(response.headers.get('Content-Range') or '')
   start=int(headers['Range'][6:].split('-')[0])
   if (getattr(response,'status',None) or response.getcode())==206 and (not span or int(span.group(1))!=start):
    response.close();raise ConnectionError('Stream server returned the wrong byte range')
   total=self.blocks.sizes.get('media') if hasattr(self,'blocks') else None
   if span and total and int(span.group(3))!=total:
    response.close();raise ConnectionError('The refreshed stream is a different file')
   return response
  # ISSUE-163 (build-224 log: 2 MiB blocks took 2.6-3 s each, about 0.7 MB/s, so reading the start of an episode took
  # 20-50 s): debrid links are slow per connection, not per phone. 4 MiB blocks with four fetched at once (about four
  # times the speed); 24 kept (96 MiB) so AirPlay's video and audio readers still share them.
  super().__init__(lambda:'',context=context,open_url=remote,block_size=BLOCK,keep=KEEP,playback=True)
  self.ahead_blocks=AHEAD
  # This is the playing movie, not a background download competing with it.
  self.gate=type('ForegroundGate',(),{'after':lambda *args,**kwargs:None})()
  self.media_url=self.url('media')

 def configure_renewal(self,record,renew):
  if record and record.get('source')==self.remote_url:
   self.renewal=record;self.renew_link=renew;self.renewal_state='ready'

 def _renew(self,attempted):
  with self.renew_lock:
   if attempted!=self.remote_url:return True  # another reader renewed this source already
   if self.renew_clock()<self.renew_after or not self.renewal or not self.renew_link:return False
   self.renew_after=self.renew_clock()+60   # bound rejected-link loops, not the lifetime of a long movie
   self.renewed=True;self.renewal_state='refreshing'
   try:
    fresh=self.renew_link(self.renewal)
    if not umbrella_recovery.web(fresh) or fresh==self.remote_url:raise ValueError('No fresh stream link')
    self.remote_url=fresh;self.renewal_state='refreshed';return True
   except Exception:
    self.renewal_state='failed';return False


class Broker:
 def __init__(self,context=None,source_factory=None,renew_link=None,open_url=None):
  self.lock=threading.Lock();self.current=None;self.ident='';self.secret=secrets.token_urlsafe(24)
  self.warm=False;self.source=''   # ISSUE-259: current is a warmed source no TV has taken yet
  self.kodi=False;self.opened=0.0  # ISSUE-280: current is what Kodi's own player reads (released when idle)
  self.factory=source_factory or (lambda source:Foreground(source,context=context,open_url=open_url))
  self.renew_link=renew_link or (lambda record:umbrella_recovery.renew(record,context=context))
  broker=self
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    if self.path!='/'+broker.secret:self.send_error(404);return
    try:
     size=int(self.headers.get('Content-Length') or 0)
     if not 0<size<=32768:raise ValueError('Invalid request size')
     request=json.loads(self.rfile.read(size))
     with broker.lock:
      action=request.get('action')
      if action=='open':
       source=request.get('source','')
       if not eligible(source):raise ValueError('Not a remote file source')
       # ISSUE-280: the source Kodi's player already reads is shared too (Play on TV asks for the same link).
       warmed=bool(broker.current and (broker.warm or broker.kodi) and broker.source==source)
       shared=warmed and broker.kodi
       if not warmed:
        if broker.current:broker.current.close()
        broker.current=broker.factory(source)
       broker.ident=secrets.token_urlsafe(18);broker.warm=False;broker.source=source
       broker.current.configure_renewal(request.get('renewal'),broker.renew_link)
       broker.kodi=request.get('player')=='kodi' or shared;broker.opened=time.monotonic()
       if broker.kodi and not warmed:threading.Thread(target=prefetch,args=(broker.current,),daemon=True).start()
       answer={'url':broker.current.media_url,'id':broker.ident,'warmed':warmed}
      elif action=='warm':
       source=request.get('source','')
       if not eligible(source):raise ValueError('Not a remote file source')
       if broker.current and not broker.warm:answer={'busy':True}   # a TV is playing from it: never take it away
       elif broker.current and broker.source==source:answer={'id':broker.ident}
       else:
        if broker.current:broker.current.close()
        broker.current=broker.factory(source);broker.ident=secrets.token_urlsafe(18);broker.warm=True;broker.source=source
        broker.kodi=False
        threading.Thread(target=prefetch,args=(broker.current,),daemon=True).start()
        answer={'id':broker.ident}
      elif action=='cool':
       if broker.warm and request.get('id')==broker.ident:
        if broker.current:broker.current.close()
        broker.current=None;broker.ident='';broker.warm=False;broker.source=''
       answer={'closed':True}
      elif action=='stats':
       # ISSUE-280: the opening card also needs whose source it is and how much of it is in memory (no URL, no id).
       answer={'stats':dict(broker.current.stats(),kodi=broker.kodi,cached_blocks=len(broker.current.blocks.data),
                            block_size=broker.current.block_size) if broker.current else {}}
      elif action=='status':
       answer={'renewal':broker.current.renewal_state if broker.current and request.get('id')==broker.ident else 'closed'}
       if broker.current and request.get('id')==broker.ident:answer['stats']=broker.current.stats()
      elif action=='origin':
       # ISSUE-280: the real link behind the address Kodi plays (Play on TV gives TVs the real link, never 127.0.0.1).
       answer={'source':broker.source if broker.current and request.get('url')==broker.current.media_url else ''}
      elif action=='close':
       # A source Kodi's player reads stays until it is idle (reap), even when Play on TV lets go of it.
       if request.get('id')==broker.ident and not broker.kodi:
        if broker.current:broker.current.close()
        broker.current=None;broker.ident='';broker.warm=False;broker.source=''
       answer={'closed':True}
      else:raise ValueError('Unknown action')
     body=json.dumps(answer).encode();self.send_response(200);self.send_header('Content-Length',str(len(body)))
     self.end_headers();self.wfile.write(body)
    except Exception:
     # Never print source URLs, provider cookies, or request bodies into Kodi's log.
     self.send_error(502,'Media source bridge unavailable')
  self.server=drive_stream._Server(('127.0.0.1',0),Handler)
  self.url='http://127.0.0.1:%d/%s'%(self.server.server_address[1],self.secret)
  self.stopped=threading.Event()
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
  threading.Thread(target=self._reap,daemon=True).start()
 def reap(self,now=None):
  """ISSUE-280: a source Kodi's player opened is closed once nothing has read it for KODI_IDLE seconds (the video
  stopped, or the TV that took it over finished). Returns True when it closed one."""
  now=time.monotonic() if now is None else now
  with self.lock:
   if not (self.current and self.kodi):return False
   last=self.current.stats().get('last_read') or 0
   idle=time.time()-last if last else now-self.opened
   if idle<KODI_IDLE:return False
   self.current.close();self.current=None;self.ident='';self.kodi=False;self.source=''
   return True
 def _reap(self):
  while not self.stopped.wait(30):
   try:self.reap()
   except Exception:pass
 def close(self):
  self.stopped.set();self.server.shutdown();self.server.server_close()
  with self.lock:
   if self.current:self.current.close();self.current=None


def prefetch(source,blocks=None):
 """ISSUE-259: the blocks a converter reads first, fetched once (the size comes with block 0). Failures only mean
 Play on TV reads them itself later."""
 try:
  cache=source.blocks;cache.get('media',0);total=cache.sizes['media'];size=cache.block_size
  last=(total-1)//size
  for index in sorted({i for i in range(1,blocks or WARM_BLOCKS) if i<=last}|{last}-{0}):cache.get('media',index)
 except Exception:pass


def start(monitor,window,context=None,open_url=None):
 """Register on Kodi's Home window (the service's `home` is a filesystem Path)."""
 broker=Broker(context=context,open_url=open_url)
 try:
  window.setProperty(PROPERTY,broker.url)
  def close_sources():
   try:
    while not monitor.waitForAbort(30):pass
   finally:
    try:
     if window.getProperty(PROPERTY)==broker.url:window.clearProperty(PROPERTY)
    finally:broker.close()
  threading.Thread(target=close_sources,daemon=True).start()
 except Exception:
  broker.close();raise
 return broker


def _call(endpoint,payload):
 body=json.dumps(payload).encode()
 with urllib.request.urlopen(urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json'}),timeout=5) as response:
  return json.loads(response.read())


class Lease:
 warmed=False
 def __init__(self,endpoint,ident):self.endpoint,self.ident=endpoint,ident
 def status(self):return _call(self.endpoint,{'action':'status','id':self.ident})
 def close(self):
  if not self.ident:return
  try:_call(self.endpoint,{'action':'close','id':self.ident})
  except Exception:pass
  self.ident=''


def acquire(source,home):
 """Leave working Drive/Elementum loopback and HLS sources alone. Older services retain their direct route."""
 if not eligible(source):return source,None
 try:
  endpoint=home.getProperty(PROPERTY)
  p=urllib.parse.urlsplit(endpoint)
  if p.scheme!='http' or p.hostname!='127.0.0.1' or not p.port:return source,None
  answer=_call(endpoint,{'action':'open','source':source,'renewal':umbrella_recovery.selected(source,home)})
  target=urllib.parse.urlsplit(answer['url'])
  if target.scheme!='http' or target.hostname!='127.0.0.1':return source,None
  lease=Lease(endpoint,answer['id']);lease.warmed=bool(answer.get('warmed'))
  return answer['url'],lease
 except Exception:return source,None


def for_kodi(source,home):
 """ISSUE-280: the address Kodi's own player should open for a link Umbrella just resolved: the service's cache when
 the link is a remote MKV / AVI / WebM and the service answers, else the link itself (nothing changes then)."""
 if not KODI_PLAYBACK or not eligible(source):return source
 try:
  endpoint=_endpoint(home)
  if not endpoint:return source
  answer=_call(endpoint,{'action':'open','source':source,'renewal':umbrella_recovery.selected(source,home),'player':'kodi'})
  target=urllib.parse.urlsplit(answer['url'])
  if target.scheme!='http' or target.hostname!='127.0.0.1':return source
  return answer['url']
 except Exception:return source


def original(playing,home):
 """ISSUE-280: the link a TV or a file-name check should see for what Kodi plays: the real Umbrella link when Kodi reads
 it through this cache, else playing unchanged."""
 raw=(playing or '').split('|',1)[0]
 if not raw.startswith('http://127.0.0.1:'):return playing
 try:
  endpoint=_endpoint(home)
  source=_call(endpoint,{'action':'origin','url':raw}).get('source','') if endpoint else ''
  return source or playing
 except Exception:return playing


def stats(window):
 """Current source counters only, using the service-owned private loopback endpoint."""
 endpoint=window.getProperty(PROPERTY)
 return (_call(endpoint,{'action':'stats'}).get('stats') or {}) if endpoint else {}


def _endpoint(home):
 endpoint=home.getProperty(PROPERTY);p=urllib.parse.urlsplit(endpoint)
 return endpoint if p.scheme=='http' and p.hostname=='127.0.0.1' and p.port else ''


def watch(home,playing,steady,wifi,wait,clock=time.monotonic,log=None):
 """ISSUE-259: warm the video Kodi is playing so Play on TV starts sooner. playing() is the file Kodi has open ('' when
 none), steady() is true while it plays without buffering, wifi() is true on Wi-Fi. A video is warmed after WARM_AFTER
 steady seconds, once; a pause keeps it; a stop or another video releases it unless a TV took it (the broker ignores
 the release then). Nothing is read on cellular, for local or Drive links, or while a TV plays from the cache."""
 key='';ident='';since=None;tried=False
 while not wait(2):
  try:
   current=(playing() or '').split('|',1)[0]
   if current!=key:
    if ident:
     try:_call(_endpoint(home),{'action':'cool','id':ident})
     except Exception:pass
    key,ident,since,tried=current,'',None,False
   if not key or tried or not eligible(key):continue
   if not steady():since=None;continue
   since=clock() if since is None else since
   if clock()-since<WARM_AFTER or not wifi():continue
   tried=True;endpoint=_endpoint(home)
   if not endpoint:continue
   answer=_call(endpoint,{'action':'warm','source':key});ident=answer.get('id','')
   if log:log('Kodi iOS Play on TV: %s'%('the playing video is ready for the TV' if ident else 'not warmed, a TV is playing'))
  except Exception:tried=True
