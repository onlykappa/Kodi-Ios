"""Service-owned foreground HTTP source cache for AirPlay/TV; reuse Drive's byte-range engine.

Only the original resolved stream URL/headers are held in RAM. A per-launch authenticated
loopback control endpoint gives other Kodi interpreters a source URL that survives their exit.
One source at a time, at most 32 MiB cached, no Drive OAuth or media files.
"""
import http.server,ipaddress,json,secrets,threading,urllib.error,urllib.parse,urllib.request
import drive_stream,umbrella_recovery
PROPERTY='KodiIOS.RemoteMedia'


def eligible(source):
 raw=source.partition('|')[0];p=urllib.parse.urlsplit(raw)
 if p.scheme not in ('http','https') or not p.hostname:return False
 if not p.path.lower().endswith(('.mkv','.avi','.webm')):return False
 if p.hostname.lower()=='localhost':return False
 try:return not ipaddress.ip_address(p.hostname).is_loopback
 except ValueError:return True


class Foreground(drive_stream.DriveStream):
 def __init__(self,source,context=None,open_url=None):
  raw,_,extra=source.partition('|');p=urllib.parse.urlsplit(raw)
  if p.scheme not in ('http','https') or not p.hostname:raise ValueError('Not an HTTP media source')
  self.remote_url=raw
  self.renew_lock=threading.Lock();self.renewal=None;self.renew_link=None;self.renewed=False;self.renewal_state='unavailable'
  self.remote_headers={k:v for k,v in urllib.parse.parse_qsl(extra,keep_blank_values=True)
                       if k.lower() not in ('host','range','connection','content-length','transfer-encoding')}
  if not any(k.lower()=='user-agent' for k in self.remote_headers):self.remote_headers['User-Agent']='Kodi-iOS-AirPlay/1'
  opener=open_url or (lambda request,timeout:urllib.request.urlopen(request,timeout=timeout,context=context))
  def remote(request,timeout):
   headers=dict(self.remote_headers);headers['Range']=request.get_header('Range')
   attempted=self.remote_url
   try:response=opener(urllib.request.Request(attempted,headers=headers),timeout)
   except urllib.error.HTTPError as error:
    if error.code not in (401,403,404,410) or not self._renew(attempted):raise
    error.close()
    response=opener(urllib.request.Request(self.remote_url,headers=headers),timeout)
   span=drive_stream.SPAN.match(response.headers.get('Content-Range') or '')
   start=int(headers['Range'][6:].split('-')[0])
   if (getattr(response,'status',None) or response.getcode())==206 and (not span or int(span.group(1))!=start):
    response.close();raise ConnectionError('Stream server returned the wrong byte range')
   total=self.blocks.sizes.get('media') if hasattr(self,'blocks') else None
   if span and total and int(span.group(3))!=total:
    response.close();raise ConnectionError('The refreshed stream is a different file')
   return response
  super().__init__(lambda:'',context=context,open_url=remote,block_size=2*1024*1024,keep=16,playback=True)
  # This is the playing movie, not a background download competing with it.
  self.gate=type('ForegroundGate',(),{'after':lambda *args,**kwargs:None})()
  self.media_url=self.url('media')

 def configure_renewal(self,record,renew):
  if record and record.get('source')==self.remote_url:
   self.renewal=record;self.renew_link=renew;self.renewal_state='ready'

 def _renew(self,attempted):
  with self.renew_lock:
   if attempted!=self.remote_url:return True  # another reader renewed this source already
   if self.renewed or not self.renewal or not self.renew_link:return False
   self.renewed=True;self.renewal_state='refreshing'
   try:
    fresh=self.renew_link(self.renewal)
    if not umbrella_recovery.web(fresh) or fresh==self.remote_url:raise ValueError('No fresh stream link')
    self.remote_url=fresh;self.renewal_state='refreshed';return True
   except Exception:
    self.renewal_state='failed';return False


class Broker:
 def __init__(self,context=None,source_factory=None,renew_link=None):
  self.lock=threading.Lock();self.current=None;self.ident='';self.secret=secrets.token_urlsafe(24)
  self.factory=source_factory or (lambda source:Foreground(source,context=context))
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
       if broker.current:broker.current.close()
       broker.current=broker.factory(source);broker.ident=secrets.token_urlsafe(18)
       broker.current.configure_renewal(request.get('renewal'),broker.renew_link)
       answer={'url':broker.current.media_url,'id':broker.ident}
      elif action=='stats':
       answer={'stats':broker.current.stats() if broker.current else {}}
      elif action=='status':
       answer={'renewal':broker.current.renewal_state if broker.current and request.get('id')==broker.ident else 'closed'}
       if broker.current and request.get('id')==broker.ident:answer['stats']=broker.current.stats()
      elif action=='close':
       if request.get('id')==broker.ident:
        if broker.current:broker.current.close()
        broker.current=None;broker.ident=''
       answer={'closed':True}
      else:raise ValueError('Unknown action')
     body=json.dumps(answer).encode();self.send_response(200);self.send_header('Content-Length',str(len(body)))
     self.end_headers();self.wfile.write(body)
    except Exception:
     # Never print source URLs, provider cookies, or request bodies into Kodi's log.
     self.send_error(502,'Media source bridge unavailable')
  self.server=drive_stream._Server(('127.0.0.1',0),Handler)
  self.url='http://127.0.0.1:%d/%s'%(self.server.server_address[1],self.secret)
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def close(self):
  self.server.shutdown();self.server.server_close()
  with self.lock:
   if self.current:self.current.close();self.current=None


def start(monitor,window,context=None):
 """Register on Kodi's Home window (the service's `home` is a filesystem Path)."""
 broker=Broker(context=context)
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
  return answer['url'],Lease(endpoint,answer['id'])
 except Exception:return source,None


def stats(window):
 """Current source counters only, using the service-owned private loopback endpoint."""
 endpoint=window.getProperty(PROPERTY)
 return (_call(endpoint,{'action':'stats'}).get('stats') or {}) if endpoint else {}
