"""Play the current stream on a Roku through its External Control Protocol (port 8060): the Roku fetches the
link itself, so the phone can sleep or switch apps. A link served by the phone (Elementum's local engine) is
rewritten to the phone's Wi-Fi address and only plays while Kodi keeps running."""
import concurrent.futures,re,socket,urllib.parse,urllib.request
PORT=8060
LOCAL={'127.0.0.1','localhost','::1','0.0.0.0'}

def stream_url(playing,phone_ip):
 """The link the Roku should open, and whether it depends on the phone. Kodi appends request headers after '|'."""
 url=(playing or '').split('|',1)[0]
 parts=urllib.parse.urlsplit(url)
 if parts.scheme not in {'http','https'}:return None,False
 if (parts.hostname or '') in LOCAL:
  if not phone_ip:return None,True
  netloc=phone_ip+(':'+str(parts.port) if parts.port else '')
  return urllib.parse.urlunsplit(parts._replace(netloc=netloc)),True
 return url,False

def launch_url(roku,url,title=''):
 # Roku's built-in "Play on Roku" receiver (channel 15985) takes a direct media link.
 ext=re.search(r'\.([a-z0-9]{2,4})$',urllib.parse.urlsplit(url).path.lower())
 query={'t':'v','u':url,'k':'(null)','videoName':title or 'Kodi'}
 if ext:query['videoFormat']=ext.group(1)
 return 'http://%s:%d/input/15985?%s'%(roku,PORT,urllib.parse.urlencode(query,quote_via=urllib.parse.quote))

def phone_address():
 """The phone's Wi-Fi address (no packet is sent: connecting a UDP socket only picks a route)."""
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:s.connect(('192.168.0.1',9));return s.getsockname()[0]
 except OSError:return None
 finally:s.close()

def device_name(roku,get):
 try:info=get('http://%s:%d/query/device-info'%(roku,PORT),2).decode('utf-8','replace')
 except Exception:return None
 for tag in ('user-device-name','friendly-device-name','model-name'):
  m=re.search('<%s>([^<]+)</%s>'%(tag,tag),info)
  if m:return m.group(1).strip()
 return 'Roku' if '<device-info>' in info else None

def find_rokus(phone_ip,get,workers=64):
 """Every Roku answering on the phone's /24 network: (address, name). iOS blocks multicast discovery for
 sideloaded apps, so this asks each address directly; iOS shows its Local Network prompt the first time."""
 if not phone_ip:return []
 prefix=phone_ip.rsplit('.',1)[0]+'.'
 hosts=[prefix+str(i) for i in range(1,255) if prefix+str(i)!=phone_ip]
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  names=list(pool.map(lambda h:device_name(h,get),hosts))
 return [(h,n) for h,n in zip(hosts,names) if n]

def http_get(url,timeout):
 with urllib.request.urlopen(url,timeout=timeout) as r:return r.read()

def http_post(url,timeout=5):
 with urllib.request.urlopen(urllib.request.Request(url,data=b'',method='POST'),timeout=timeout) as r:return r.status
