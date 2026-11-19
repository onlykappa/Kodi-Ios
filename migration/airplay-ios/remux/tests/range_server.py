"""A tiny HTTP file server that answers Range requests (like Elementum's 127.0.0.1:65220 and Google Drive), for the
remuxer host tests. Prints its port, then serves DIR until killed. usage: range_server.py DIR
r8: paths under /slow/ serve the same files like a remote source (Drive through its loopback proxy): every request
waits SLOW_LATENCY seconds before answering and the bytes come at SLOW_RATE bytes/s (the latency host tests).
ISSUE-335: /quiet/ sends the first chunk of one ranged answer per file and then nothing for 25 s."""
import http.server,json,os,re,sys,time,threading
SLOW_LATENCY=0.1
SLOW_RATE=2*1024*1024
RECOVERED=set()
QUIETED=set()   # ISSUE-335: /quiet/ goes silent once per file mid-body
BUSY=set()      # r13: /busy/ refuses a second concurrent connection to the same path (a server's per-resource limit)
RECOVER_LOCK=threading.Lock()
STATS={'requests':0,'bytes':0}
STATS_LOCK=threading.Lock()
CUE_DELAY=False

class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def handle(self):
  try:super().handle()
  except (BrokenPipeError,ConnectionResetError):pass  # expected when the native cancellation test interrupts open
 def send_head(self):
  global CUE_DELAY
  if self.path=='/__cue_delay':
   self.protocol_version='HTTP/1.1';self.close_connection=True
   with STATS_LOCK:CUE_DELAY=True
   import io
   self.send_response(200);self.send_header('Content-Length','2');self.end_headers();return io.BytesIO(b'OK')
  if self.path.startswith('/cue-delay/'):
   self.path=self.path[len('/cue-delay'):]
   with STATS_LOCK:delay=CUE_DELAY;CUE_DELAY=False
   if delay:time.sleep(10) # only the first read after arming; the demuxer must retain its in-flight work
  self.indexed=False;self.slow=False
  if self.path.startswith('/__stats'):
   with STATS_LOCK:
    if self.path.endswith('/reset'):STATS.update(requests=0,bytes=0)
    data=json.dumps(STATS).encode()
   import io
   self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers()
   return io.BytesIO(data)
  self.indexed=self.path.startswith('/indexed/')
  if self.indexed:
   self.path=self.path[len('/indexed'):]
   with STATS_LOCK:STATS['requests']+=1
   time.sleep(0.1)
  if self.path.startswith('/open-stall/'):
   self.path=self.path[len('/open-stall'):];time.sleep(8)
  self.fault=None
  for mode in ('bounded','recover','stall','quiet','busy'):
   if self.path.startswith('/'+mode+'/'):
    self.fault=mode;self.path=self.path[len(mode)+1:];break
  self.slow=self.path.startswith('/slow/')
  if self.slow:self.path=self.path[5:];time.sleep(SLOW_LATENCY)
  path=self.translate_path(self.path)
  if not os.path.isfile(path):self.send_error(404);return None
  size=os.path.getsize(path);f=open(path,'rb')
  m=re.match(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
  if self.fault=='bounded' and (not m or not m.group(2) or int(m.group(2))-int(m.group(1))+1>1048576):
   self.send_error(400,'test requires finite ranges no larger than 1 MiB');f.close();return None
  if not m:
   self.send_response(200);self.send_header('Content-Length',str(size));self.send_header('Accept-Ranges','bytes');self.end_headers()
   return f
  a=int(m.group(1));b=int(m.group(2)) if m.group(2) else size-1
  if a>=size:self.send_error(416);f.close();return None
  if a>262144 and self.fault=='busy':
   with RECOVER_LOCK:
    if path in BUSY:f.close();self.send_error(503,'too many connections to this resource');return None
    BUSY.add(path)
   self.busy_path=path;time.sleep(1)  # held just long enough for a concurrent second request to arrive and be refused
  b=min(b,size-1);f.seek(a)
  self.send_response(206);self.send_header('Content-Range','bytes %d-%d/%d'%(a,b,size))
  self.send_header('Content-Length',str(b-a+1));self.send_header('Accept-Ranges','bytes');self.end_headers()
  self.range_left=b-a+1
  if a>262144 and self.fault=='recover':
   with RECOVER_LOCK:
    if path not in RECOVERED:RECOVERED.add(path);self.drop=True
  if a>262144 and self.fault=='stall':time.sleep(2)
  if a>262144 and self.fault=='quiet':
   with RECOVER_LOCK:
    if path not in QUIETED:QUIETED.add(path);self.quiet=True
  return f
 def copyfile(self,src,dst):
  try:
   if getattr(self,'drop',False):return # headers promised bytes, but this connection dies before its body
   left=getattr(self,'range_left',None);step=16384 if self.slow else 65536
   while left is None or left>0:
    chunk=src.read(step if left is None else min(step,left))
    if not chunk:break
    try:dst.write(chunk)
    except (BrokenPipeError,ConnectionResetError):return
    if getattr(self,'quiet',False):  # a connection that stops sending (owner log 65cca4ce: 31.7 s on one read)
     try:dst.flush()
     except OSError:pass
     time.sleep(25);return
    if self.indexed:
     with STATS_LOCK:STATS['bytes']+=len(chunk)
    if self.slow:time.sleep(len(chunk)/SLOW_RATE)
    if left is not None:left-=len(chunk)
  finally:
   busy_path=getattr(self,'busy_path',None)
   if busy_path:
    with RECOVER_LOCK:BUSY.discard(busy_path)

if __name__=='__main__':
 os.chdir(sys.argv[1])
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
 print(server.server_address[1],flush=True)
 server.serve_forever()
