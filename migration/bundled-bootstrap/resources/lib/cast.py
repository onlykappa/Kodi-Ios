"""Play the current stream on a TV on the same Wi-Fi: Roku (External Control Protocol, port 8060), DLNA/UPnP
smart TVs (AVTransport), and Chromecast / Google TV (Cast protocol, Default Media Receiver). The TV fetches the
link itself, so the phone can sleep or switch apps. A link served by the phone (Elementum's local engine) is
rewritten to the phone's Wi-Fi address and only plays while Kodi keeps running. AirPlay goes through Apple's
player in KodiAirPlay.framework (see airplay.py)."""
import concurrent.futures,json,re,socket,ssl,struct,time,urllib.error,urllib.parse,urllib.request
from xml.sax.saxutils import escape
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

def launch_url(roku,url,title='',command='input'):
 # Roku's built-in "Play on Roku" receiver (channel 15985) takes a direct media link: `input` hands it to the
 # receiver, `launch` starts the receiver with it (some Roku OS versions only accept one of the two).
 ext=re.search(r'\.([a-z0-9]{2,4})$',urllib.parse.urlsplit(url).path.lower())
 query={'t':'v','u':url,'k':'(null)','videoName':title or 'Kodi'}
 if ext:query['videoFormat']=ext.group(1)
 return 'http://%s:%d/%s/15985?%s'%(roku,PORT,command,urllib.parse.urlencode(query,quote_via=urllib.parse.quote))

class TVRefused(Exception):
 """The TV answered but would not play; str() is what to tell the owner."""

def roku_reason(errors):
 codes=[e for e in errors if isinstance(e,int)]
 if 403 in codes:
  return ('The Roku refused the request (403). On the Roku: Settings › System › Advanced system settings › '
          'Control by mobile apps › Network access: Permissive, then try again.')
 if codes and all(c==404 for c in codes):
  return ('This Roku has no "Play on Roku" receiver (404). If the TV has AirPlay (Settings › Apple AirPlay and '
          'HomeKit), choose "Apple TV / AirPlay TV" instead.')
 if not codes:return 'The Roku did not answer (%s). Make sure it is on and on this Wi-Fi.'%', '.join(sorted(set(map(str,errors))))
 return 'The Roku answered %s.'%', '.join(map(str,errors))

def roku_play(host,url,title,post):
 """Hand the link to the Roku, trying both ways in. Returns the one it took; raises TVRefused with the reason."""
 errors=[]
 for command in ('input','launch'):
  try:post(launch_url(host,url,title,command));return command
  except urllib.error.HTTPError as error:errors.append(error.code)
  except OSError as error:errors.append(type(error).__name__)
 raise TVRefused(roku_reason(errors))

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


# --- Shared --------------------------------------------------------------------------------------------------

def media_type(url):
 path=urllib.parse.urlsplit(url).path.lower()
 if path.endswith('.m3u8'):return 'application/x-mpegURL'
 if path.endswith('.mkv'):return 'video/x-matroska'
 if path.endswith('.webm'):return 'video/webm'
 return 'video/mp4'

def network_hosts(phone_ip):
 if not phone_ip:return []
 prefix=phone_ip.rsplit('.',1)[0]+'.'
 return [prefix+str(i) for i in range(1,255) if prefix+str(i)!=phone_ip]

# --- DLNA / UPnP smart TVs -----------------------------------------------------------------------------------

SEARCH=('M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\n'
        'ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n').encode()

def ssdp_locations(hosts,wait=2.5,make_socket=None):
 """Asks each address directly (unicast M-SEARCH): sideloaded iOS apps may not send multicast."""
 sock=(make_socket or (lambda:socket.socket(socket.AF_INET,socket.SOCK_DGRAM)))()
 found={}
 try:
  sock.settimeout(0.2)
  for host in hosts:
   try:sock.sendto(SEARCH,(host,1900))
   except OSError:pass
  end=time.monotonic()+wait
  while time.monotonic()<end:
   try:data,(host,_)=sock.recvfrom(4096)
   except (socket.timeout,OSError):continue
   m=re.search(rb'(?im)^location:\s*(\S+)',data)
   if m:found.setdefault(host,m.group(1).decode('ascii','replace'))
 finally:sock.close()
 return found

def _text(node,name):
 for child in node.iter():
  if child.tag.split('}')[-1]==name:return (child.text or '').strip()
 return ''

def renderer(location,get):
 """(name, AVTransport control URL) from a UPnP device description, or None."""
 import xml.etree.ElementTree as ET
 try:root=ET.fromstring(get(location,3))
 except Exception:return None
 base=_text(root,'URLBase') or location
 for service in root.iter():
  if service.tag.split('}')[-1]!='service':continue
  if 'AVTransport' in _text(service,'serviceType'):
   name=_text(root,'friendlyName') or _text(root,'modelName') or 'TV'
   return name,urllib.parse.urljoin(base,_text(service,'controlURL'))
 return None

def didl(url,title):
 return ('<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" '
         'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"><item id="0" parentID="-1" restricted="1">'
         '<dc:title>%s</dc:title><upnp:class>object.item.videoItem</upnp:class>'
         '<res protocolInfo="http-get:*:%s:*">%s</res></item></DIDL-Lite>')%(escape(title or 'Kodi'),media_type(url),escape(url))

def soap(action,arguments):
 body=''.join('<%s>%s</%s>'%(k,v,k) for k,v in arguments)
 return ('<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
         's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:%s xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">'
         '%s</u:%s></s:Body></s:Envelope>')%(action,body,action)

def dlna_play(control,url,title,post):
 def call(action,arguments):
  post(control,soap(action,arguments).encode('utf-8'),{'Content-Type':'text/xml; charset="utf-8"','SOAPAction':'"urn:schemas-upnp-org:service:AVTransport:1#%s"'%action})
 try:call('Stop',[('InstanceID','0')])
 except Exception:pass
 call('SetAVTransportURI',[('InstanceID','0'),('CurrentURI',escape(url)),('CurrentURIMetaData',escape(didl(url,title)))])
 call('Play',[('InstanceID','0'),('Speed','1')])

# --- Chromecast / Google TV ----------------------------------------------------------------------------------

MEDIA_RECEIVER='CC1AD845'

def _varint(n):
 out=b''
 while True:
  byte=n&0x7f;n>>=7
  out+=bytes([byte|(0x80 if n else 0)])
  if not n:return out

def _field(number,wire,value):
 key=_varint(number<<3|wire)
 return key+_varint(value) if wire==0 else key+_varint(len(value))+value

def cast_frame(source,destination,namespace,payload):
 message=(_field(1,0,0)+_field(2,2,source.encode())+_field(3,2,destination.encode())+_field(4,2,namespace.encode())
          +_field(5,0,0)+_field(6,2,json.dumps(payload).encode()))
 return struct.pack('>I',len(message))+message

def cast_parse(message):
 """namespace and JSON payload of one CastMessage."""
 fields={};i=0
 def varint():
  nonlocal i
  shift=value=0
  while True:
   byte=message[i];i+=1;value|=(byte&0x7f)<<shift;shift+=7
   if not byte&0x80:return value
 while i<len(message):
  key=varint();number,wire=key>>3,key&7
  if wire==0:fields[number]=varint()
  elif wire==2:
   length=varint();fields[number]=message[i:i+length];i+=length
  else:break
 return fields.get(4,b'').decode(),json.loads(fields.get(6,b'{}') or b'{}')

def chromecast_name(host,get):
 try:return json.loads(get('http://%s:8008/setup/eureka_info?params=name'%host,2)).get('name') or 'Chromecast'
 except Exception:return None

def chromecast_play(host,url,title,connect=None,timeout=20):
 sock=(connect or _cast_socket)(host)
 send=lambda dst,ns,payload:sock.sendall(cast_frame('sender-0',dst,ns,payload))
 def read():
  head=_recv(sock,4);return cast_parse(_recv(sock,struct.unpack('>I',head)[0]))
 try:
  send('receiver-0','urn:x-cast:com.google.cast.tp.connection',{'type':'CONNECT'})
  send('receiver-0','urn:x-cast:com.google.cast.receiver',{'type':'LAUNCH','appId':MEDIA_RECEIVER,'requestId':1})
  transport=None;loaded=False;end=time.monotonic()+timeout
  while time.monotonic()<end:
   namespace,payload=read()
   if payload.get('type')=='PING':send('receiver-0','urn:x-cast:com.google.cast.tp.heartbeat',{'type':'PONG'});continue
   if payload.get('type')=='RECEIVER_STATUS' and not transport:
    for app in payload.get('status',{}).get('applications',[]):
     if app.get('appId')==MEDIA_RECEIVER and app.get('transportId'):
      transport=app['transportId']
      send(transport,'urn:x-cast:com.google.cast.tp.connection',{'type':'CONNECT'})
      send(transport,'urn:x-cast:com.google.cast.media',{'type':'LOAD','requestId':2,'autoplay':True,'currentTime':0,
           'media':{'contentId':url,'streamType':'BUFFERED','contentType':'video/mp4' if media_type(url)=='video/x-matroska' else media_type(url),
                    'metadata':{'metadataType':0,'title':title or 'Kodi'}}})
   elif payload.get('type') in {'LOAD_FAILED','LOAD_CANCELLED','INVALID_REQUEST','LAUNCH_ERROR'}:
    raise RuntimeError(payload.get('type'))
   elif payload.get('type')=='MEDIA_STATUS' and transport:
    loaded=True;break
  if not loaded:raise RuntimeError('Chromecast did not start the video')
 finally:sock.close()

def _cast_socket(host):
 # Cast devices present self-signed certificates.
 context=ssl.create_default_context();context.check_hostname=False;context.verify_mode=ssl.CERT_NONE
 raw=socket.create_connection((host,8009),timeout=10)
 return context.wrap_socket(raw,server_hostname=host)

def _recv(sock,size):
 data=b''
 while len(data)<size:
  chunk=sock.recv(size-len(data))
  if not chunk:raise ConnectionError('Chromecast closed the connection')
  data+=chunk
 return data

# --- Discovery of everything ---------------------------------------------------------------------------------

def find_tvs(phone_ip,get,workers=128,locations=None):
 """[{'kind':'roku'|'dlna'|'chromecast','host','name','control'?}] on the phone's /24 network."""
 hosts=network_hosts(phone_ip)
 if not hosts:return []
 # The three searches run together: one pass of direct probes plus the SSDP replies, a few seconds in all.
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers+1) as pool:
  pending=pool.submit(ssdp_locations,hosts) if locations is None else None
  probes=list(pool.map(lambda h:(device_name(h,get),chromecast_name(h,get)),hosts))
  if pending:locations=pending.result()
 rokus=[p[0] for p in probes];casts=[p[1] for p in probes]
 tvs=[{'kind':'roku','host':h,'name':n} for h,n in zip(hosts,rokus) if n]
 tvs+=[{'kind':'chromecast','host':h,'name':n} for h,n in zip(hosts,casts) if n]
 seen={t['host'] for t in tvs}
 for host,location in sorted(locations.items()):
  if host in seen:continue
  found=renderer(location,get)
  if found:tvs.append({'kind':'dlna','host':host,'name':found[0],'control':found[1]})
 return tvs

def http_post_body(url,body,headers,timeout=8):
 with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers,method='POST'),timeout=timeout) as r:return r.status
