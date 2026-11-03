"""A tiny HTTP file server that answers Range requests (like Elementum's 127.0.0.1:65220 and Google Drive), for the
remuxer host tests. Prints its port, then serves DIR until killed. usage: range_server.py DIR
r8: paths under /slow/ serve the same files like a remote source (Drive through its loopback proxy): every request
waits SLOW_LATENCY seconds before answering and the bytes come at SLOW_RATE bytes/s (the latency host tests)."""
import http.server,os,re,sys,time
SLOW_LATENCY=0.1
SLOW_RATE=2*1024*1024

class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def send_head(self):
  self.slow=self.path.startswith('/slow/')
  if self.slow:self.path=self.path[5:];time.sleep(SLOW_LATENCY)
  path=self.translate_path(self.path)
  if not os.path.isfile(path):self.send_error(404);return None
  size=os.path.getsize(path);f=open(path,'rb')
  m=re.match(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
  if not m:
   self.send_response(200);self.send_header('Content-Length',str(size));self.send_header('Accept-Ranges','bytes');self.end_headers()
   return f
  a=int(m.group(1));b=int(m.group(2)) if m.group(2) else size-1
  if a>=size:self.send_error(416);f.close();return None
  b=min(b,size-1);f.seek(a)
  self.send_response(206);self.send_header('Content-Range','bytes %d-%d/%d'%(a,b,size))
  self.send_header('Content-Length',str(b-a+1));self.send_header('Accept-Ranges','bytes');self.end_headers()
  self.range_left=b-a+1
  return f
 def copyfile(self,src,dst):
  left=getattr(self,'range_left',None);step=16384 if self.slow else 65536
  while left is None or left>0:
   chunk=src.read(step if left is None else min(step,left))
   if not chunk:break
   try:dst.write(chunk)
   except (BrokenPipeError,ConnectionResetError):return
   if self.slow:time.sleep(len(chunk)/SLOW_RATE)
   if left is not None:left-=len(chunk)

if __name__=='__main__':
 os.chdir(sys.argv[1])
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
 print(server.server_address[1],flush=True)
 server.serve_forever()
