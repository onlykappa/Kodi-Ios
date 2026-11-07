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

def phone_source(playing,fallback):
 """The link as Kodi plays it (headers after '|' dropped) when it is a web link, else `fallback`: what the phone itself
 reads for AirPlay conversion."""
 url=(playing or '').split('|',1)[0]
 return url if urllib.parse.urlsplit(url).scheme in {'http','https'} else fallback

def airplay_source(playing,url,converting):
 """What KodiAirPlay reads. A converting framework (r5+) always reads the video on the phone itself and serves the TV
 from its own endpoint, so it gets the link Kodi plays: Drive's and Elementum's helpers answer on 127.0.0.1 only.
 Owner build 157: prepared movies end in .mp4, were treated as Apple-playable and got the Wi-Fi address instead
 ("Connection refused"). An older framework hands the link to Apple's player, which needs the Wi-Fi address."""
 return phone_source(playing,url) if converting else url

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

# Apple's AirPlay player (AVPlayer) opens these containers only; an Elementum stream is usually MKV.
APPLE_FORMATS=('.mp4','.m4v','.mov','.m3u8')
MIRRORING=('Apple\'s AirPlay player can\'t play this video (%s). Use Screen Mirroring instead: Kodi keeps playing and '
           'your TV shows the picture with sound.\n'
           '1. Swipe down from the top-right corner of the screen.\n'
           '2. Tap Screen Mirroring and choose your TV.\n'
           'Turn the phone sideways for a full-size picture. To stop, open Screen Mirroring again and tap Stop Mirroring.')

CONVERTED_FORMATS=('.mkv','.mk3d','.avi','.webm','.ts','.m2ts','.mts')

def apple_playable(*names,converts=False):
 """Whether Apple's player can open the video: any of the names (stream link, Kodi's file name) ends in an Apple
 container. Kodi appends request headers after '|'. With converts (KodiAirPlay r5) MKV, AVI, WebM and MPEG-TS count
 too, and so do links without a file extension (the framework looks at the bytes)."""
 paths=[urllib.parse.urlsplit((name or '').split('|',1)[0]).path.lower() for name in names if name]
 if any(path.endswith(APPLE_FORMATS) for path in paths):return True
 if not converts or not paths:return False
 if any(path.endswith(CONVERTED_FORMATS) for path in paths):return True
 return not any(re.search(r'\.[a-z0-9]{2,4}$',path) for path in paths)

CONVERT_FAILED='%s\n\nYou can still use Screen Mirroring: swipe down from the top-right corner, tap Screen Mirroring and choose your TV.'

# Owner (build 160): a Ready (prepared) movie said "Apple's AirPlay player can't play this video (MP4)". That text is for
# formats Apple's player cannot open; when the player simply did not start, say what happened instead.
NOT_STARTED=('AirPlay didn\'t start on the TV: %s.\n\nMake sure the TV is on and on the same Wi-Fi as the phone, then '
             'try Play on TV again. Screen Mirroring also works: swipe down from the top-right corner, tap Screen '
             'Mirroring and choose your TV.')
PLAYER_ERRORS=((r'Code=-1004\b|Could not connect to the server','the TV could not connect to the phone'),
               (r'Code=-1001\b|timed out','the TV took too long to answer'),
               (r'Code=-1009\b|offline','the phone is not on Wi-Fi'),
               (r'Code=-11800\b|operation could not be completed','the TV stopped the video'))

def player_problem(lines):
 """What Apple's player said went wrong (KodiAirPlay's log lines), in everyday words, or ''."""
 for line in reversed(list(lines or ())):
  if 'could not open the stream:' in line or 'stopped:' in line or 'failed:' in line:
   for pattern,words in PLAYER_ERRORS:
    if re.search(pattern,line):return words
   return line.split(':',2)[-1].strip()[:120]
 return ''

BUSY='KodiIOS.PlayOnTV'   # Home window property while Play on TV is starting (a second press waits for it)
def busy(value,now,window=90):
 """Whether Play on TV is already starting: the property holds when it began (seconds)."""
 try:return now-float(value)<window
 except (TypeError,ValueError):return False

def format_name(*names):
 """MKV, AVI... for the Screen Mirroring message ('this format' when unknown)."""
 for name in names:
  m=re.search(r'\.([a-z0-9]{2,4})$',urllib.parse.urlsplit((name or '').split('|',1)[0]).path.lower())
  if m:return m.group(1).upper()
 return 'this format'

def retry_airplay(outcome,why):
 """Build 186: one more try when Apple's player gave up waiting for the first reads (a busy line), not otherwise."""
 return outcome=='failed' and 'timed out' in str(why or '').lower()

def airplay_outcome(state,wait,timeout=25):
 """Poll Apple's player (state(): 1 has the stream, -1 failed, 0 not yet) for up to `timeout` seconds; wait(s)
 sleeps and returns True if Kodi is closing. Returns 'playing', 'failed' or 'aborted'."""
 waited=0.0
 while waited<timeout:
  now=state()
  if now==1:return 'playing'
  if now<0:return 'failed'
  if wait(0.5):return 'aborted'
  waited+=0.5
 return 'failed'

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
 except Exception as error:_quiet('cast:203',error)
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

def _quiet(where,error,_seen=set()):
 """Log an error that is deliberately not shown on screen, once per place and kind (loops run every second)."""
 key=(where,type(error).__name__)
 if key in _seen:return
 _seen.add(key)
 try:
  import xbmc;xbmc.log('Kodi iOS %s: %s: %s'%(where,type(error).__name__,str(error)[:200]),xbmc.LOGWARNING)
 except Exception:pass
