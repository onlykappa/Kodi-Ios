"""Service-owned foreground HTTP source cache for AirPlay/TV; reuse Drive's byte-range engine.

Only the original resolved stream URL/headers are held in RAM. A per-launch authenticated
loopback control endpoint gives other Kodi interpreters a source URL that survives their exit.
One source at a time, at most 96 MiB cached, no Drive OAuth or media files.
"""
import http.server,ipaddress,json,secrets,socket,threading,time,urllib.error,urllib.parse,urllib.request
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
# OFF (owner, build 442: no Umbrella stream plays, fresh or resumed from Continue Watching): Kodi reads the AllDebrid
# link itself again, as in build 430, until this route is proven on the phone. Play on TV still uses the cache.
KODI_IDLE=120
# ISSUE-300 (owner log 074adcd9, build 466: a resumed Umbrella episode took 23.5 s, 20.2 s of it Kodi opening the MKV over
# one AllDebrid connection): the route is back on. The build-442 failure came from the ISSUE-282 restart loop (a new
# cache every restart, Kodi pointed at an old one), fixed since; the fallback (FIRST_ANSWER) now sees the link's first
# answer at once. Desktop Kodi rig, 0.7 MB/s per connection, an MKV with 20 MB of fonts: 29 s direct, 7.3 s via the cache.
KODI_PLAYBACK=True
# ISSUE-281 (owner: stuck, then a crash on Resume): a paused player reads nothing, so the idle rule closed the source
# under it and Resume reopened a dead 127.0.0.1 address. While Kodi still has this source open (playing or paused) it
# is kept, up to KODI_CAP seconds with no read.
KODI_CAP=30*60
# ISSUE-281 (owner, build 442: an Umbrella episode sat at "Opening the video · 0 of 12 MB", then the app crashed on Resume):
# ISSUE-303: Kodi is handed the cache only after all opening blocks are complete within FIRST_ANSWER seconds;
# a size or one split piece is not enough. Otherwise cancel its reads and preserve the original direct source.
FIRST_ANSWER=5.0
_BROKER=[None]   # ISSUE-281: one cache per service run; a restarted Drive loop reuses it
# ISSUE-302 (owner, build 470, log 2979ea67: an Umbrella episode sat at "Opening the video · 4 of 12 MB, 33 %", AllDebrid
# "sending it slowly (0.2 MB/s)", no picture after 126 s, on Wi-Fi with nothing else copying): a 4 MiB block came over ONE
# connection and nothing is served until the whole block is here, so at 0.2 MB/s each block took 20 s, and the three
# opening blocks (the first two and the last) were fetched one after another: 60 s before the first picture. Debrid links
# are slow per connection, not per phone (ISSUE-163): each block is now fetched as SPLIT parallel ranges, and the opening
# blocks together. At most PIECES requests run at once, so a link that limits connections is not flooded.
SPLIT=4;PIECES=8;SPLIT_MIN=256*1024
TYPES={'mkv':'video/x-matroska','avi':'video/x-msvideo','webm':'video/webm'}
RACE=20          # ISSUE-315: a Kodi source replaced this soon after it was opened is kept beside the new one
KODI_AHEAD=4     # ISSUE-315: blocks after the opening ones fetched at once for Kodi (it reads the file's start next)
# ISSUE-317 (owner log d3c14036, build 482: the cache route with all three opening blocks ready in 4.3 s still took 31.3 s
# for Kodi to open; the direct link 19.6 s): every read Kodi makes through the cache (offset, length, time, how long it
# waited for blocks) and every block fetched, for READ_LOG_FOR seconds after the source opens (READ_LOG_MAX lines at most).
READ_LOG_FOR=90;READ_LOG_MAX=150
INTEGRITY=('wrong byte range','different file','complete range')   # ISSUE-344: a refused range (whole-file answer) is retried
REFUSED_FOR,REFUSED_PLACES=60,2   # ISSUE-344: after a ranged request answered with the whole file
CALM_FOR=30      # ISSUE-321: seconds of half the request places after an upstream failure
BLOCK_RETRIES=2  # ISSUE-317: more tries for a block a reader waits on (each try is up to 3 requests per piece)
OPEN_BLOCKS=2    # ISSUE-317: leading blocks a Kodi source must hold before Kodi is handed it (with the last block)
LOOP_WINDOW=90   # ISSUE-306: seconds in which a second hand-off after one Kodi never read means Umbrella is cycling its sources
_LAST=[0.0]


def eligible(source):
 raw=source.partition('|')[0];p=urllib.parse.urlsplit(raw)
 if p.scheme not in ('http','https') or not p.hostname:return False
 if not p.path.lower().endswith(('.mkv','.avi','.webm')):return False
 if p.hostname.lower()=='localhost':return False
 try:return not ipaddress.ip_address(p.hostname).is_loopback
 except ValueError:return True


class _SourceClosed(RuntimeError):pass


class _Gate:
 """ISSUE-317: at most `size` requests at once, like the semaphore it replaces, but a free place goes to the most urgent
 waiter first: 0 a block Kodi is waiting on, 1 the opening blocks, 2 read-ahead nobody has asked for yet."""
 def __init__(self,size):
  self.free=size;self.size=size;self.cond=threading.Condition();self.waiting=[];self.calm_until=0.0;self.calm_places=size
 def calm(self,seconds=CALM_FOR,places=None):
  """ISSUE-321: after an upstream failure, half the places for a while (a debrid server that resets connections when
  too many arrive at once answers fewer, steadier ones). ISSUE-344: `places` sets a tighter limit (it never loosens one
  still running)."""
  with self.cond:
   limit=max(1,int(places)) if places else max(2,self.size//2)
   until=time.monotonic()+seconds
   if time.monotonic()<self.calm_until:limit=min(limit,self.calm_places)
   self.calm_until=max(self.calm_until,until);self.calm_places=limit
 def _room(self):
  used=self.size-self.free
  return used<(self.calm_places if time.monotonic()<self.calm_until else self.size)
 def acquire(self,timeout=None,priority=2,since=None):
  with self.cond:
   ticket=[priority,since or time.monotonic()];self.waiting.append(ticket)
   try:
    end=None if timeout is None else time.monotonic()+timeout
    while self.free<=0 or not self._room() or min(self.waiting)!=ticket:
     left=None if end is None else end-time.monotonic()
     if left is not None and left<=0:return False
     self.cond.wait(left if left is None else min(left,.05))
    self.free-=1;return True
   finally:
    self.waiting.remove(ticket);self.cond.notify_all()
 def release(self):
  with self.cond:self.free+=1;self.cond.notify_all()


class _Response:
 """A foreground read can be interrupted without changing Drive preparation's shared reader."""
 def __init__(self,owner,response):
  self.owner,self.response=owner,response;self.closed=False
 def __getattr__(self,name):return getattr(self.response,name)
 def read(self,size):
  if self.owner.cancelled.is_set():raise _SourceClosed('Stream cache closed')
  try:data=getattr(self.response,'read1',self.response.read)(size)
  except Exception:
   if self.owner.cancelled.is_set():raise _SourceClosed('Stream cache closed') from None
   raise
  if self.owner.cancelled.is_set():raise _SourceClosed('Stream cache closed')
  return data
 def close(self):
  with self.owner.response_lock:
   if self.closed:return
   self.closed=True;self.owner.responses.discard(self)
  try:self.response.close()
  finally:self.owner.pieces.release()
 def abort(self):
  # HTTPResponse.close alone can wait on a BufferedReader held by a stalled read. Interrupt its socket first.
  sock=getattr(getattr(getattr(self.response,'fp',None),'raw',None),'_sock',None)
  if sock is not None:
   try:sock.shutdown(socket.SHUT_RDWR)
   except OSError:pass
  threading.Thread(target=self.close,daemon=True).start()


class Foreground(drive_stream.DriveStream):
 def __init__(self,source,context=None,open_url=None,clock=time.monotonic):
  raw,_,extra=source.partition('|');p=urllib.parse.urlsplit(raw)
  if p.scheme not in ('http','https') or not p.hostname:raise ValueError('Not an HTTP media source')
  self.remote_url=raw
  # ISSUE-300: the file's size as soon as the link's first answer arrives (its Content-Range), not after the whole first
  # 4 MB block: at ~0.7 MB/s that block takes ~6 s, longer than for_kodi's FIRST_ANSWER, so Kodi always fell back.
  self.answered_size=0
  self.cancelled=threading.Event();self.response_lock=threading.Lock();self.responses=set()
  self.pieces=_Gate(PIECES);self.urgent=set();self.connect_timeout=20;self.opening_deadline=None
  self.renew_lock=threading.Lock();self.renewal=None;self.renew_link=None;self.renewed=False;self.renewal_state='unavailable'
  self.renew_clock=clock;self.renew_after=0.0
  self.remote_headers={k:v for k,v in urllib.parse.parse_qsl(extra,keep_blank_values=True)
                       if k.lower() not in ('host','range','connection','content-length','transfer-encoding')}
  if not any(k.lower()=='user-agent' for k in self.remote_headers):self.remote_headers['User-Agent']='Kodi-iOS-AirPlay/1'
  opener=open_url or (lambda request,timeout:urllib.request.urlopen(request,timeout=timeout,context=context))
  def remote(request,timeout):
   since=time.monotonic()   # ISSUE-317: its place in the queue is kept while it re-checks cancellation and urgency
   while not self.cancelled.is_set():
    if self.pieces.acquire(timeout=.05,priority=self._priority(request),since=since):break
   else:raise _SourceClosed('Stream cache closed')
   response=None;tracked=False
   try:
    if self.cancelled.is_set():raise _SourceClosed('Stream cache closed')
    # ISSUE-317 (owner log cf038697, build 482: three "Transferred a partial file" cuts while Kodi opened through the cache,
    # 31.3 s): the opening's budget (deadline, short timeouts) is for the blocks that decide the route, not for the next
    # blocks started at 4.3 s with under a second left, nor for Kodi's own reads or read-ahead.
    budgeted=self._priority(request)==1;deadline=self.opening_deadline if budgeted else None
    remaining=None if deadline is None else deadline-time.monotonic()
    if remaining is not None and remaining<=0:raise _SourceClosed('Stream opening budget expired')
    limit=timeout if deadline is None else min(timeout,self.connect_timeout,remaining)
    try:response=self._open_remote(request,limit,opener,budgeted=budgeted)
    except Exception:
     if self.cancelled.is_set():raise _SourceClosed('Stream cache closed') from None
     raise
    guarded=_Response(self,response)
    with self.response_lock:
     if self.cancelled.is_set():raise _SourceClosed('Stream cache closed')
     self.responses.add(guarded);tracked=True
    return guarded
   finally:
    if not tracked:
     self.pieces.release()
     if response is not None:response.close()
  # This is the playing movie, not a background download competing with it.
  super().__init__(lambda:'',context=context,open_url=remote,block_size=BLOCK,keep=KEEP,playback=True)
  self.ahead_blocks=AHEAD
  self.gate=type('ForegroundGate',(),{'after':lambda *args,**kwargs:None})()
  # ISSUE-306 (owner, build 475, log eadd0349: Umbrella handed six sources over one after another, the cache admitted each
  # (blocks 3/3, no errors), and none played): the address Kodi opens now ends in the file's own name and the reply names
  # its video type, as the Drive proxy's does (the one Kodi plays Drive copies from on the phone). It was ".../media/source"
  # with application/octet-stream, an address no Kodi video path had ever played on the phone.
  name=urllib.parse.unquote(urllib.parse.urlsplit(raw).path.rsplit('/',1)[-1]) or 'video.mkv'
  self.content_type=TYPES.get(name.rsplit('.',1)[-1].lower(),'video/x-matroska')
  self.served=0
  self.born=time.monotonic();self.reads=[];self.logged=0   # ISSUE-317: the read trace of the opening
  self.open_blocks=WARM_BLOCKS   # ISSUE-317: leading blocks the opening needs (OPEN_BLOCKS for Kodi's own player)
  self.block_retries=BLOCK_RETRIES   # ISSUE-317: a failed block is fetched again before a reader's read is cut
  self.media_url=self.url('media').rsplit('/',1)[0]+'/'+urllib.parse.quote(name,safe='')

 def _open_remote(self,request,timeout,opener,budgeted=True):
   headers=dict(self.remote_headers);headers['Range']=request.get_header('Range')
   attempted=self.remote_url
   def open_source(url):
    if self.cancelled.is_set():raise _SourceClosed('Stream cache closed')
    deadline=self.opening_deadline if budgeted else None   # read now: a renewal may have used up the budget
    remaining=timeout if deadline is None else min(timeout,deadline-time.monotonic())
    if remaining<=0:raise _SourceClosed('Stream opening budget expired')
    request=urllib.request.Request(url,headers=headers)
    # The system opener buffers a piece and may follow redirects internally; share the entire opening deadline.
    request._kodi_open_deadline=deadline;request._kodi_cancelled=self.cancelled.is_set
    return opener(request,remaining)
   try:response=open_source(attempted)
   except urllib.error.HTTPError as error:
    error.close()
    if error.code not in (401,403,404,410) or not self._renew(attempted):raise
    response=open_source(self.remote_url)
   span=drive_stream.SPAN.match(response.headers.get('Content-Range') or '')
   start=int(headers['Range'][6:].split('-')[0])
   if (getattr(response,'status',None) or response.getcode())==206 and (not span or int(span.group(1))!=start):
    response.close();raise ConnectionError('Stream server returned the wrong byte range')
   if span:
    with self.response_lock:
     total=self.answered_size or self.blocks.sizes.get('media')
     if total and int(span.group(3))!=total:
      response.close();raise ConnectionError('The refreshed stream is a different file')
     self.answered_size=int(span.group(3))
   return response

 def close(self):
  self.cancelled.set()
  with self.response_lock:responses=tuple(self.responses)
  for response in responses:response.abort()
  super().close()

 def _fetch(self,item,start,end):
  """ISSUE-302: the block as SPLIT ranges read at once (joined in order); small or single-piece ranges as before."""
  began=time.monotonic()
  try:
   result=self._fetch_block(item,start,end)
  except _SourceClosed:raise
  except Exception as error:
   # ISSUE-321 (owner log a30fb0aa: every block in flight failed with ConnectionError just after the picture, and Kodi's
   # reads waited 7-23 s): name the error, calm the request rate, and try the block once more over one connection.
   self._trace('block',start//self.block_size,began,error=describe(error))
   # ISSUE-344 (owner log a83e06c7, build 513: "Drive answered without the asked byte range" again and again while Kodi
   # and AirPlay read one AllDebrid link; most pieces in flight failed, single ones went through): the server answers
   # a ranged request with the whole file (200) when too many connections ask at once. Two places for a minute.
   if 'without the asked byte range' in str(error):self.pieces.calm(REFUSED_FOR,places=REFUSED_PLACES)
   else:self.pieces.calm()
   # Only a failed transfer is tried again; an answer that contradicts the file (a wrong range, another size, pieces
   # that do not make one block) never becomes a block (ISSUE-303 integrity).
   if self.cancelled.is_set() or any(w in str(error) for w in INTEGRITY):raise
   began=time.monotonic()
   # Preserve the previous retry budget for a server that continues refusing after the split requests. Without this,
   # stopping the split attempts early also removes up to eight opportunities for an upstream source to recover.
   fallback_limit=3 if isinstance(error,drive_stream.RangeRefused) else 1
   for fallback in range(fallback_limit):
    try:
     result=super()._fetch(item,start,end);break
    except drive_stream.RangeRefused as again:
     if self.cancelled.is_set() or fallback+1==fallback_limit:
      self._trace('block',start//self.block_size,began,error='retry '+describe(again));raise
     time.sleep(.25*(fallback+1))
    except Exception as again:
     self._trace('block',start//self.block_size,began,error='retry '+describe(again));raise
  self._trace('block',start//self.block_size,began,size=len(result[0]))
  return result

 def want(self,index):
  """ISSUE-317: a reader (Kodi) waits on this block now: its pieces go before read-ahead."""
  with self.response_lock:self.urgent.add(index)

 def _priority(self,request):
  try:index=int(request.get_header('Range')[6:].split('-')[0])//self.block_size
  except Exception:return 2
  if index in self.urgent:return 0
  total=self.answered_size or self.blocks.sizes.get('media') or 0
  if index<self.open_blocks or (total and index==(total-1)//self.block_size):return 1
  return 2

 def on_read(self,start,end,sent,took,waited,waits):
  """ISSUE-317: two lines per read Kodi makes through the cache: as it asks (sent is None) and as it ends."""
  at=time.monotonic()-took-self.born
  if sent is None:
   self._log('Kodi iOS cache read: at=+%.2fs offset=%d asked=%d'%(at,start,end-start+1));return
  self.reads.append((round(at,3),start,end,sent,round(took,3),round(waited,3)))
  self._log('Kodi iOS cache read done: at=+%.2fs offset=%d sent=%d took=%.2fs waited=%.2fs%s'%(
   at,start,sent,took,waited,(' waited_for=%s'%','.join(map(str,waits[:8]))) if waits else ''))

 def _trace(self,kind,index,began,size=0,error=''):
  now=time.monotonic()
  self._log('Kodi iOS cache %s: index=%d at=+%.2fs took=%.2fs %s'%(kind,index,began-self.born,now-began,
            ('error=%s'%error) if error else 'bytes=%d'%size))

 def _log(self,line):
  if time.monotonic()-self.born>READ_LOG_FOR or self.logged>=READ_LOG_MAX:return
  self.logged+=1
  try:
   import xbmc;xbmc.log(line,xbmc.LOGINFO)
  except Exception:pass

 def _fetch_block(self,item,start,end):
  if self.cancelled.is_set():raise _SourceClosed('Stream cache closed')
  total=self.blocks.sizes.get(item);stop=end if total is None else min(end,total-1)
  if stop-start+1<=SPLIT*SPLIT_MIN:return super()._fetch(item,start,end)
  step=-(-(stop-start+1)//SPLIT)
  spans=[(start+i*step,min(stop,start+(i+1)*step-1)) for i in range(SPLIT) if start+i*step<=stop]
  results=[None]*len(spans);errors=[]
  def piece(i,a,b):
   # A refused split range should yield to the existing single-connection fallback immediately. Retrying each piece
   # three times first can keep every reader waiting and flood a source that is already rejecting parallel requests.
   try:results[i]=super(Foreground,self)._fetch(item,a,b,fail_fast_range=True)
   except urllib.error.HTTPError as error:
    if error.code==416 and i>0:results[i]=(b'',None)   # the file ended inside the block
    else:errors.append(error)
   except Exception as error:errors.append(error)
  threads=[threading.Thread(target=piece,args=(i,a,b),daemon=True) for i,(a,b) in enumerate(spans)]
  for t in threads:t.start()
  for t in threads:t.join()
  if errors or any(r is None for r in results):raise errors[0] if errors else ConnectionError('Stream block was not read')
  size=next((r[1] for r in results if r[1]),total)
  body=b''.join(r[0] for r in results)
  if any(r[1] and r[1]!=size for r in results) or size is None or len(body)!=min(end,size-1)-start+1:
   raise ConnectionError('Stream block pieces do not describe one complete range')
  return body,size

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
 def __init__(self,context=None,source_factory=None,renew_link=None,open_url=None,playing=None):
  self.playing=playing or (lambda:'')   # ISSUE-281: the file Kodi has open ('' when none)
  self.lock=threading.Lock();self.current=None;self.ident='';self.secret=secrets.token_urlsafe(24)
  self.previous=None   # ISSUE-315: (ident, source, link, opened) of a Kodi source a second hand-off replaced just now
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
        # ISSUE-315 (owner log bdbdac02: two hand-offs 0.7 s apart for one play; the second closed the first's source, so
        # the first went direct after 1 s and Kodi opened it in 24 s): a Kodi source opened under RACE s ago stays open
        # beside the new one (one at most), so each hand-off finishes on its own source.
        old=broker.previous
        if broker.current and broker.kodi and time.monotonic()-broker.opened<RACE:
         broker.previous=(broker.ident,broker.current,broker.source,broker.opened)
        elif broker.current:broker.current.close()
        if old and old is not broker.previous:
         try:old[1].close()
         except Exception:pass
        broker.current=broker.factory(source)
       broker.ident=secrets.token_urlsafe(18);broker.warm=False;broker.source=source
       broker.current.configure_renewal(request.get('renewal'),broker.renew_link)
       broker.kodi=request.get('player')=='kodi' or shared;broker.opened=time.monotonic()
       if broker.kodi and not warmed:
        broker.current.connect_timeout=min(20,FIRST_ANSWER)
        broker.current.opening_deadline=broker.opened+FIRST_ANSWER
        broker.current.open_blocks=OPEN_BLOCKS
        resume=request.get('resume')
        resume=resume if isinstance(resume,(int,float)) and 0<resume<1 else None
        try:   # the opening kept from the last time this stream was played (resume_cache): in memory before Kodi reads, so the open and the resume seek need no network
         import resume_cache
         seeded=resume_cache.seed(broker.current,source)
         if seeded:
          import xbmc
          xbmc.log('Kodi iOS resume cache: %d kept blocks given to the opening'%seeded,xbmc.LOGINFO)
        except Exception:pass
        threading.Thread(target=prefetch,args=(broker.current,),kwargs={'blocks':OPEN_BLOCKS,'extra':KODI_AHEAD,'resume':resume},daemon=True).start()
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
       snapshot={}
       ident,current=broker.ident,broker.current
       prev=broker.previous
       if prev and request.get('id') and request.get('id')==prev[0]:ident,current=prev[0],prev[1]   # ISSUE-315
       if current:
        snapshot=current.stats()
        with current.blocks.lock:
         size=int(current.blocks.sizes.get('media') or current.answered_size or 0)
         wanted=set(range(getattr(current,'open_blocks',WARM_BLOCKS)))|{(size-1)//current.block_size} if size else set()
         wanted={i for i in wanted if size and i*current.block_size<size}
         complete=lambda index:len(current.blocks.data.get(('media',index),b''))==min(current.block_size,size-index*current.block_size)
         ready=bool(wanted) and all(complete(index) for index in wanted)
         snapshot.update(kodi=broker.kodi,cached_blocks=len(current.blocks.data),pending_blocks=len(current.blocks.pending),
                         block_size=current.block_size,size=size,source_id=fingerprint(ident),
                         first_block_ready=bool(size and complete(0)),first_block_bytes=len(current.blocks.data.get(('media',0),b'')),
                         opening_ready=ready,opening_blocks=len(wanted),opening_complete=sum(complete(i) for i in wanted),
                         served=int(getattr(current,'served',0)))   # ISSUE-306: bytes a reader (Kodi) really took
        if ready:current.connect_timeout=20;current.opening_deadline=None
       answer={'stats':snapshot}
      elif action=='status':
       answer={'renewal':broker.current.renewal_state if broker.current and request.get('id')==broker.ident else 'closed'}
       if broker.current and request.get('id')==broker.ident:answer['stats']=broker.current.stats()
      elif action=='origin':
       # ISSUE-280: the real link behind the address Kodi plays (Play on TV gives TVs the real link, never 127.0.0.1).
       answer={'source':broker.source if broker.current and request.get('url')==broker.current.media_url else
               (broker.previous[2] if broker.previous and request.get('url')==broker.previous[1].media_url else '')}
      elif action=='drop':
       # ISSUE-281: Kodi was given the real link after all (the cache had no answer in time): let the source go.
       if broker.previous and request.get('id')==broker.previous[0]:
        broker.previous[1].close();broker.previous=None
       elif (request.get('id')==broker.ident or request.get('any')) and broker.kodi:
        if broker.current:broker.current.close()
        broker.current=None;broker.ident='';broker.kodi=False;broker.source=''
       answer={'closed':True}
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
   prev=self.previous   # ISSUE-315: the kept source goes once Kodi has left it alone (or never read it) for a minute
   if prev and now-prev[3]>60:
    last=float(prev[1].stats().get('last_read') or 0)
    try:playing=prev[1].media_url in (self.playing() or '')
    except Exception:playing=True
    if not playing and (not last or time.time()-last>KODI_IDLE):
     try:prev[1].close()
     except Exception:pass
     self.previous=None
   if not (self.current and self.kodi):return False
   last=self.current.stats().get('last_read') or 0
   idle=time.time()-last if last else now-self.opened
   if idle<KODI_IDLE:return False
   try:open_in_kodi=self.current.media_url in (self.playing() or '')
   except Exception:open_in_kodi=True   # unsure: keep it (a dead address under the player is the worse failure)
   if open_in_kodi and idle<KODI_CAP:return False
   self.current.close();self.current=None;self.ident='';self.kodi=False;self.source=''
   return True
 def _reap(self):
  while not self.stopped.wait(30):
   try:self.reap()
   except Exception:pass
 def close(self):
  self.stopped.set();self.server.shutdown();self.server.server_close()
  with self.lock:
   if self.previous:
    try:self.previous[1].close()
    except Exception:pass
    self.previous=None
   if self.current:self.current.close();self.current=None


RESUME_BLOCKS=3   # Continue (owner, build 620 log 80ea6c76: 3.6 s from streams ready to the first picture, the resume seek reading cold): the
                  # block where playback resumes and its neighbours, asked for with the opening blocks

def resume_blocks(fraction,total,size):
 """The block indexes around `fraction` of a file of `total` bytes (a guess from time: bitrate varies), or [] when there is no resume point."""
 try:fraction=float(fraction)
 except (TypeError,ValueError):return []
 if not 0<fraction<1 or total<=0 or size<=0:return []
 at=int(fraction*total)//size;last=(total-1)//size
 return [i for i in range(at-1,at-1+RESUME_BLOCKS) if 0<i<last]

def prefetch(source,blocks=None,extra=0,resume=None):
 """ISSUE-259: the blocks a converter reads first, fetched once (the size comes with block 0). Failures only mean
 Play on TV reads them itself later."""
 try:
  cache=source.blocks;cache.get('media',0);total=cache.sizes['media'];size=cache.block_size
  last=(total-1)//size
  # ISSUE-302: together, not one after another (each is slow on its own on a debrid link)
  def one(index):
   try:cache.get('media',index)
   except Exception:pass
  threads=[threading.Thread(target=one,args=(i,),daemon=True) for i in sorted({i for i in range(1,blocks or WARM_BLOCKS) if i<=last}|{last}-{0})]
  # ISSUE-315: and the next blocks Kodi reads while it opens the file (an MKV's start: its tracks and attached fonts).
  # ISSUE-317: started with the opening ones, not after them: the request gate gives the opening blocks their places
  # first, and the rest use whatever places are left instead of waiting idle.
  first=blocks or WARM_BLOCKS
  # ISSUE-321 (owner log a30fb0aa): this Kodi seeks past an MKV's attached fonts, so the blocks after the opening ones
  # were font data it never read (it went from 6 MB straight to the first video at 22.6 MB), fetched just when it needed
  # the video. The file's own layout (in block 0) says where the video starts; the next blocks are fetched from there.
  begins=video_start(cache.data.get(('media',0),b''))
  if begins is not None:first=max(first,begins//size)
  more=[threading.Thread(target=one,args=(i,),daemon=True) for i in range(first,first+extra) if i<last]
  more+=[threading.Thread(target=one,args=(i,),daemon=True) for i in resume_blocks(resume,total,size)]
  for t in threads:t.start()
  # the opening blocks' requests queue first (the gate only orders waiters; a free place goes to whoever asks first)
  gate=getattr(source,'pieces',None);want=min(PIECES,SPLIT*len(threads))
  until=time.monotonic()+1
  while gate is not None and more and time.monotonic()<until and PIECES-gate.free+len(gate.waiting)<want:time.sleep(.01)
  for t in more:t.start()
  for t in threads:t.join()
 except Exception:pass


MKV_SEGMENT=0x18538067;MKV_CLUSTER=0x1F43B675


def video_start(data):
 """Where an MKV's first video data (its first Cluster) begins, from the start of the file, or None when it is not an
 MKV or its top-level elements cannot be followed that far. The headers before the video (tracks, attached fonts, tags)
 are walked by their sizes, so a Cluster beyond `data` is still found when the element before it begins inside it."""
 def vint(pos,keep_marker=False):
  if pos>=len(data):return None,0
  first=data[pos];length=1;mask=0x80
  while length<=8 and not first&mask:mask>>=1;length+=1
  if length>8 or pos+length>len(data):return None,0
  value=first if keep_marker else first&(mask-1)
  for byte in data[pos+1:pos+length]:value=(value<<8)|byte
  return value,length
 try:
  ident,n=vint(0,True)
  if ident!=0x1A45DFA3:return None
  size,m=vint(n);pos=n+m+size
  ident,n=vint(pos,True)
  if ident!=MKV_SEGMENT:return None
  size,m=vint(pos+n);pos+=n+m
  for _ in range(64):
   if pos>=len(data):return pos   # the element before ended past block 0: the next one starts here (the video, or tags)
   ident,n=vint(pos,True);size,m=vint(pos+n)
   if ident is None or size is None:return None
   if ident==MKV_CLUSTER:return pos
   pos+=n+m+size
 except Exception:return None
 return None


def start(monitor,window,context=None,open_url=None,playing=None):
 """Register on Kodi's Home window (the service's `home` is a filesystem Path).
 ISSUE-281 (log 6cf2a4c5): the Drive loop restarted every 30-600 s (ISSUE-282) and each start made a new cache and moved
 the Home property to it, so Kodi read one cache while the opening card counted another ("0 of 12 MB"). The cache made by
 the first start is kept for the whole run."""
 old=_BROKER[0]
 if old is not None and not old.stopped.is_set():
  window.setProperty(PROPERTY,old.url);return old
 broker=Broker(context=context,open_url=open_url,playing=playing);_BROKER[0]=broker
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


def _call(endpoint,payload,timeout=5):
 body=json.dumps(payload).encode()
 with urllib.request.urlopen(urllib.request.Request(endpoint,data=body,headers={'Content-Type':'application/json'}),timeout=timeout) as response:
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


SLOW_SKIP=1200   # seconds a server that did not answer the cache's opening in time is played directly without asking again
SLOW_PROPERTY='KodiIOS.CacheSlowHost'

def _host(source):
 try:return (urllib.parse.urlsplit(str(source).split('|',1)[0]).hostname or '').lower()
 except Exception:return ''

def _kept(source):
 try:
  import resume_cache
  return resume_cache.ready(source)
 except Exception:return False

def note_slow(home,source,now=time.time):
 """Remember (in the Home window, shared by every add-on) that this link's server was too slow for the cache's opening."""
 try:
  host=_host(source)
  if host:home.setProperty(SLOW_PROPERTY,'%s|%d'%(host,now()))
 except Exception:pass

def slow_recently(home,source,now=time.time):
 try:
  host,_,at=(home.getProperty(SLOW_PROPERTY) or '').partition('|')
  return bool(host) and host==_host(source) and 0<=now()-float(at)<SLOW_SKIP
 except Exception:return False

def for_kodi(source,home,wait=None,clock=time.monotonic,resume=None):
 """ISSUE-280: the address Kodi's own player should open for a link Umbrella just resolved: the service's cache when
 the link is a remote MKV / AVI / WebM and the service answers, else the link itself (nothing changes then)."""
 if not KODI_PLAYBACK or not eligible(source):return source
 began=clock();sample={}
 try:
  endpoint=_endpoint(home)
  if not endpoint:return source
  # Build 639 log 9f7b4ab2: both Umbrella opens waited 2 s for the cache's opening blocks (ready=False, 0 of 3) and then went direct. A server that
  # was too slow a moment ago is not asked again for SLOW_SKIP seconds: the link is played directly at once (the cache is tried again afterwards).
  if slow_recently(home,source) and not _kept(source):   # unless the opening of this very link is on the phone (resume_cache)
   opening_log('direct',0,{},reason='this server did not answer the cache in time a moment ago')
   return source
  # ISSUE-306: the source handed over last time is still here and Kodi took nothing from it, a moment ago: Umbrella went on
  # to its next source without playing this one. Whatever stops the cache route playing, more of it will not help: this
  # source (and the rest of the cycle) is played directly, as in the builds that played.
  try:before=_call(endpoint,{'action':'stats'},timeout=1).get('stats') or {}
  except Exception:before={}
  if before.get('kodi') and not before.get('served') and _LAST[0] and 0<clock()-_LAST[0]<LOOP_WINDOW:
   try:_call(endpoint,{'action':'drop','id':'','any':True},timeout=1)
   except Exception:pass
   opening_log('direct',clock()-began,before,reason='previous source never read by Kodi')
   return source
  request={'action':'open','source':source,'renewal':umbrella_recovery.selected(source,home),'player':'kodi'}
  if isinstance(resume,(int,float)) and 0<resume<1:request['resume']=resume   # Continue: where playback resumes, as a share of the file
  answer=_call(endpoint,request,timeout=min(1,FIRST_ANSWER))
  target=urllib.parse.urlsplit(answer['url'])
  if target.scheme!='http' or target.hostname!='127.0.0.1':return source
  # A Content-Range header is not video data. Admit only completed opening probes; otherwise preserve direct play.
  if not answered(endpoint,answer.get('id',''),wait=wait,clock=clock,
                  limit=max(0,FIRST_ANSWER-(clock()-began)),sample=sample.update):
   try:_call(endpoint,{'action':'drop','id':answer.get('id','')})
   except Exception:pass
   opening_log('direct',clock()-began,sample)
   note_slow(home,source)
   return source
  opening_log('cache',clock()-began,sample)
  _LAST[0]=clock()
  return answer['url']
 except Exception:return source


def opening_log(route,elapsed,stats,reason=''):
 """One useful, credential-free line per handoff, including failed/stalled probes."""
 try:
  import xbmc
  xbmc.log('Kodi iOS stream opening: route=%s wait_ms=%d ready=%s blocks=%d/%d pending=%d bytes=%d requests=%d errors=%d status=%d'%(
   route,max(0,int(elapsed*1000)),bool(stats.get('opening_ready')),int(stats.get('opening_complete') or 0),
   int(stats.get('opening_blocks') or 0),int(stats.get('pending_blocks') or 0),int(stats.get('read_bytes') or 0),
   int(stats.get('http_requests') or 0),int(stats.get('http_errors') or 0),int(stats.get('last_status') or 0))
   +(' served=%d'%int(stats.get('served') or 0))+((' reason=%s'%reason) if reason else '')+(' origin_answered=%s'%('yes' if int(stats.get('size') or 0)>0 else 'no')),xbmc.LOGINFO)   # origin_answered=no: the debrid server had not even said the file size, so the wait was its slow start, not ours
 except Exception:pass


def describe(error):
 """An error's type and words for the log, without any address in them (a link or a host can carry account tokens)."""
 import re
 text=re.sub(r'\S*://\S*','<address>',str(getattr(error,'reason',None) or error or ''))
 code=getattr(error,'code',None)
 return ('%s%s%s'%(type(error).__name__,' %s'%code if isinstance(code,int) else '',(': '+text[:90]) if text else '')).replace('\n',' ')


def fingerprint(ident):
 """Which source the stats are about, without giving the source's private id away."""
 import hashlib
 return hashlib.sha256(('kodi-ios:'+str(ident or '')).encode()).hexdigest()[:12] if ident else ''


# ISSUE-340 (owner log 218a6000: "route=direct wait_ms=5017 ready=False blocks=0/3 … bytes=3145728"; Umbrella took 15.8 s):
# the cache waited its whole 5 s for opening blocks that were arriving at ~0.6 MB/s and could not finish, then Kodi
# opened the link directly anyway. After EARLY_LOOK seconds the wait stops when, at the speed so far, the opening
# blocks cannot be complete within the budget (or nothing has arrived).
EARLY_LOOK=1.5

def hopeless(st,elapsed,limit):
 if elapsed<EARLY_LOOK:return False
 need=int(st.get('opening_blocks') or 0)*BLOCK-int(st.get('read_bytes') or 0)
 if need<=0:return False
 rate=int(st.get('read_bytes') or 0)/max(elapsed,.001)
 return rate<=0 or need/rate>(limit-elapsed)*1.2


def answered(endpoint,ident,wait=None,clock=time.monotonic,limit=None,sample=None):
 """True only when this source's first/second/tail probes contain validated bytes within the opening budget."""
 wait=wait or time.sleep;limit=FIRST_ANSWER if limit is None else limit
 began=clock()
 while True:
  remaining=limit-(clock()-began)
  if remaining<=0:return False
  try:
   st=_call(endpoint,{'action':'stats','id':ident},timeout=min(1,remaining)).get('stats') or {}
   if sample:sample(st)
   if clock()-began>=limit:return False
   if st.get('source_id')==fingerprint(ident) and st.get('opening_ready'):return True
   if st.get('source_id')!=fingerprint(ident):return False
   if hopeless(st,clock()-began,limit):return False
  except Exception:return False
  if clock()-began>=limit:return False
  if wait(min(.05,max(0,limit-(clock()-began)))):return False


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
