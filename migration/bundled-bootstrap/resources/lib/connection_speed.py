"""How fast the phone's connection really delivers stream data, learned from what streams actually read (owner, 2026-11-28: "have it recommend the best based on wifi
speeds ... consistent for people, wifi speeds change depending on location"). Like Sports' source health it learns from real use rather than from a separate speed test:
every 4 MB block a stream's cache fetches is timed (remote_media._trace); the throughput while blocks were being fetched is kept per connection type and per network, with
newer samples counting more and a drop counting faster than a rise. The network is told apart by the connection type and a one-way hash of the phone's local subnet, so a
different Wi-Fi or a switch to cellular starts from "unknown", not from the home figure. Nothing but a number, the connection type and a hash is stored; no address.
Pure logic (no Kodi imports): the clock, the persistence path and the network key are passed in."""
import hashlib,json,os,time

STALE=6*3600.0        # a figure older than this says nothing about the line now
MIN_BYTES=2*1024*1024  # less than this has been read: too little to judge
MIN_BUSY=3.0          # seconds of fetching behind a figure
WINDOW=30.0           # the figure is the throughput over the last this many seconds of fetching
EVERY=10.0            # a stream records at most this often
HEADROOM=0.7          # a version may need at most this share of the measured rate (the rest is for stalls and the peaks above the average)
FLOOR,CAP,DEFAULT=4.0,20.0,10.0   # Mbit/s limits for versions listed first; DEFAULT while nothing is known
FILE='connection-speed.json'
STREAM_SUFFIX='#stream'   # the figure of what streams really got (the real path to the debrid server) is kept apart from the line's own speed (the live reading)
STREAM_TYPICAL=13.0       # what an AllDebrid stream usually gives (owner logs c703d50a, f821266d: 6.6 to 17.7 Mbit/s) until this network has a measured figure
PROBE_URL='https://speed.cloudflare.com/__down?bytes=4000000'   # a few MB from a fast public host; what the line to the internet gives right now
PROBE_BYTES,PROBE_SECONDS,PROBE_MIN_BYTES=4000000,3.0,400000

def probe(opener,clock=time.time,url=PROBE_URL):
    """ISSUE-503 (owner: "it doesn't seem to be reading live"): the Mbit/s the line gives right now, from reading up to PROBE_BYTES (or PROBE_SECONDS) of a public file, or None when
    it could not be read or too little came. `opener(url)` returns a file-like object. A short read under-reads a fast line (TCP is still ramping up), never over-reads it."""
    began=clock();got=0
    try:
        with opener(url) as response:
            while got<PROBE_BYTES and clock()-began<PROBE_SECONDS:
                chunk=response.read(65536)
                if not chunk:break
                got+=len(chunk)
    except Exception:return None
    took=clock()-began
    if got<PROBE_MIN_BYTES or took<=0.05:return None
    return round(got*8/took/1e6,2)

def network_key(kind,address):
    """'wifi:3f2a9c1b' for a connection type and a local address: only the first three parts of an IPv4 address (the subnet) go into the hash."""
    subnet='.'.join(str(address or '').split('.')[:3])
    return '%s:%s'%(kind or 'other',hashlib.sha1(subnet.encode()).hexdigest()[:8] if subnet else 'none')

class Meter:
    """Throughput of one stream while it was fetching: bytes over the merged busy time of its block fetches (parallel blocks are not counted twice)."""
    def __init__(self):self.items=[];self.last=0.0
    def add(self,nbytes,began,ended):
        if nbytes>0 and ended>began:self.items.append((began,ended,nbytes));del self.items[:-400]
    def rate(self,now):
        """(bytes per second, busy seconds, bytes) over the last WINDOW seconds, or None when there is too little."""
        recent=[(max(b,now-WINDOW),e,n) for b,e,n in self.items if e>now-WINDOW]
        total=sum(n for _,_,n in recent)
        busy=0.0;edge=None
        for b,e,_ in sorted(recent):
            if edge is None or b>edge:busy+=e-b;edge=e
            elif e>edge:busy+=e-edge;edge=e
        if total<MIN_BYTES or busy<MIN_BUSY:return None
        return total/busy,busy,total
    def due(self,now):
        if now-self.last<EVERY:return False
        self.last=now;return True

class Speeds:
    def __init__(self,path=None,clock=time.time):self.path=path;self.clock=clock
    def _load(self):
        try:
            with open(self.path,encoding='utf-8') as f:data=json.load(f)
            return data if isinstance(data,dict) else {}
        except (OSError,ValueError,TypeError):return {}
    def note(self,key,mbps):
        """Fold a measured Mbit/s into the figure for this network: new = 0.5 old + 0.5 sample, 0.3 + 0.7 when the line got slower."""
        if not self.path or not key or not 0<mbps<2000:return None
        data=self._load();now=self.clock()
        old=data.get(key) or {}
        if old and 0<=now-float(old.get('at') or 0)<STALE:
            before=float(old['mbps']);weight=0.7 if mbps<before else 0.5
            mbps=before*(1-weight)+mbps*weight
        data[key]={'mbps':round(float(mbps),2),'at':now}
        data={k:v for k,v in data.items() if isinstance(v,dict) and 0<=now-float(v.get('at') or 0)<STALE*4}
        try:
            os.makedirs(os.path.dirname(self.path),exist_ok=True)
            temp=self.path+'.tmp'
            with open(temp,'w',encoding='utf-8') as f:json.dump(data,f)
            os.replace(temp,self.path)
        except OSError:return None
        return data[key]['mbps']
    def estimate(self,key):
        """Mbit/s measured on this network in the last STALE seconds, or None."""
        found=self._load().get(key) or {}
        try:
            return float(found['mbps']) if 0<=self.clock()-float(found['at'])<STALE else None
        except (KeyError,TypeError,ValueError):return None

def stream_key(key):
    return (key or '')+STREAM_SUFFIX if key else ''

def delivery(stream):
    """What streams get here in Mbit/s: the measured figure, else the typical one for a debrid stream."""
    return float(stream) if stream and stream>0 else STREAM_TYPICAL

def allowed(stream,line=None):
    """The most a version may average, in Mbit/s, to be listed first: HEADROOM of what streams delivered (DEFAULT when that is unknown), between FLOOR and CAP, and never more than
    HEADROOM of the line's own speed when that is known (ISSUE-503: the line's speed alone says nothing about a stream, which the debrid server limits)."""
    limit=DEFAULT if not stream or stream<=0 else round(max(FLOOR,min(CAP,stream*HEADROOM)),1)
    if line and line>0:limit=min(limit,round(max(FLOOR,line*HEADROOM),1))
    return limit

def advice(estimate,limit,line=None):
    """One log line for the version list."""
    seen=' (line %.0f Mbit/s)'%line if line else ''
    if not estimate:return 'Kodi iOS stream advice: no stream speed measured on this network yet (typical %.0f); versions up to %.0f Mbit/s first%s'%(STREAM_TYPICAL,limit,seen)
    return 'Kodi iOS stream advice: streams delivered %.1f Mbit/s here; versions up to %.1f Mbit/s first%s'%(estimate,limit,seen)

def open_speeds(translate=None,clock=time.time):
    try:
        if translate is None:
            import xbmcvfs;translate=xbmcvfs.translatePath
        return Speeds(os.path.join(translate('special://profile/addon_data/service.kodi.ios.bootstrap'),FILE),clock)
    except Exception:return Speeds(None,clock)

def current_key():
    """The key of the network in use now, or '' when it cannot be told."""
    try:
        import cache_tune
        address=cache_tune.local_address()
        return network_key(cache_tune.link_kind(address),address)
    except Exception:return ''

def record(meter,now=None,speeds=None,key=None):
    """Called by a stream's cache after a block: store the throughput when there is enough of it, at most every EVERY seconds. Never raises."""
    try:
        now=time.monotonic() if now is None else now
        if not meter.due(now):return None
        got=meter.rate(now)
        if not got:return None
        speeds=speeds or open_speeds();key=key or current_key()
        return speeds.note(stream_key(key),got[0]*8/1e6) if key else None
    except Exception:return None
