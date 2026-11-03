"""A tiny HTTP file server that answers Range requests (like Elementum's 127.0.0.1:65220 and Google Drive), for the
remuxer host tests. Prints its port, then serves DIR until killed. usage: range_server.py DIR"""
import http.server,os,re,sys

class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
 def send_head(self):
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
  left=getattr(self,'range_left',None)
  while left is None or left>0:
   chunk=src.read(65536 if left is None else min(65536,left))
   if not chunk:break
   try:dst.write(chunk)
   except (BrokenPipeError,ConnectionResetError):return
   if left is not None:left-=len(chunk)

if __name__=='__main__':
 os.chdir(sys.argv[1])
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
 print(server.server_address[1],flush=True)
 server.serve_forever()
