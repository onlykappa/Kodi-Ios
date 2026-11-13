"""HTTP through the system's networking (KodiAirPlay.framework kodi_http_send, ISSUE-167).

Build-229 log: Drive upload pieces crawled (~0.3 MB/s in total, one lane or two, on a 115 Mbps line) while nothing
played. Python's TLS sends a body 16 KB at a time and every step waits for the interpreter. The framework sends the
whole request with NSURLSession while this thread waits outside the interpreter (ctypes releases it)."""
import ctypes,email.message,io,urllib.error,urllib.parse,urllib.request

HEADERS_MAX = 64 * 1024
BODY_MAX = 256 * 1024
READ_MAX = 8 * 1024 * 1024

def header_lines(headers):
    if any('\r' in str(x) or '\n' in str(x) for pair in (headers or {}).items() for x in pair):
        raise ValueError('Invalid HTTP header')
    return ''.join('%s: %s\n'%(k,v) for k,v in (headers or {}).items())

def parse_headers(text):
    out={}
    for line in text.split('\n'):
        name,sep,value=line.partition(':')
        if sep:out[name.strip()]=value.strip()
    return out


def sender(lib,body_max=BODY_MAX):
    """send(method, url, body, headers, timeout) -> (status, headers, body), or None without the framework."""
    fn = getattr(lib, 'kodi_http_send', None) if lib is not None else None
    if fn is None:
        return None
    if not 0<body_max<=READ_MAX:raise ValueError('Invalid native HTTP response limit')
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_longlong, ctypes.c_double,
                   ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    fn.restype = ctypes.c_int

    def send(method, url, body, headers, timeout):
        lines = header_lines(headers)
        out_headers = ctypes.create_string_buffer(HEADERS_MAX)
        out_body = ctypes.create_string_buffer(body_max)
        used = ctypes.c_int(0)
        status = fn(method.encode(), url.encode(), lines.encode(), body or None, len(body or b''), float(timeout),
                    out_headers, HEADERS_MAX, out_body, body_max, ctypes.byref(used))
        if status < 0:
            raise ConnectionError('System networking: ' + out_body.value.decode('utf-8', 'replace')[:200])
        if not 0<=used.value<=body_max:raise ConnectionError('Invalid native HTTP response length')
        parsed = parse_headers(out_headers.value.decode('utf-8','replace'))
        return status, parsed, out_body.raw[:used.value]
    return send

def copier(lib):
    fn=getattr(lib,'kodi_http_copy',None) if lib is not None else None
    if fn is None:return None
    fn.argtypes=[ctypes.c_char_p]*4+[ctypes.c_longlong,ctypes.c_int,ctypes.c_longlong,ctypes.c_double,
                 ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]
    fn.restype=ctypes.c_int
    # r50: the framework says how large a piece it takes (32 MB); older ones take 8 MB (READ_MAX).
    limit=getattr(lib,'kodi_http_copy_max',None)
    if limit is not None:
        limit.argtypes=[];limit.restype=ctypes.c_int
    largest=max(READ_MAX,int(limit())) if limit is not None else READ_MAX
    def copy(source,source_headers,target,target_headers,offset,count,total,timeout=20):
        if offset<0 or not 0<count<=largest or total<=0 or offset>total or count>total-offset:raise ValueError('Invalid copy bounds')
        # A larger piece gets more time: at least 1 MB/s before the piece counts as stalled.
        timeout=max(float(timeout),count/1048576.0)
        headers=ctypes.create_string_buffer(HEADERS_MAX);body=ctypes.create_string_buffer(BODY_MAX)
        used=ctypes.c_int();read_status=ctypes.c_int(-1)
        status=fn(source.encode(),header_lines(source_headers).encode(),target.encode(),header_lines(target_headers).encode(),
                  offset,count,total,float(timeout),headers,HEADERS_MAX,body,BODY_MAX,ctypes.byref(used),ctypes.byref(read_status))
        if read_status.value>=300:raise urllib.error.HTTPError(source,read_status.value,'Source request failed',{},None)
        if status<0:raise ConnectionError('Native copy did not finish; checking confirmed upload position')
        if not 0<=used.value<=BODY_MAX:raise ConnectionError('Invalid native copy receipt')
        return status,parse_headers(headers.value.decode('utf-8','replace')),body.raw[:used.value]
    copy.max=largest
    # r53 (ISSUE-201): the framework streams each piece (Drive PUT fed while the AllDebrid GET arrives).
    streams=getattr(lib,'kodi_http_copy_streams',None)
    if streams is not None:
        streams.argtypes=[];streams.restype=ctypes.c_int
    copy.streams=bool(streams is not None and streams()==1)
    return copy


class Response(io.BytesIO):
    def __init__(self,status,headers,body):
        super().__init__(body);self.status=status;self.headers=email.message.Message()
        for name,value in headers.items():self.headers[name]=str(value)
    def getcode(self):return self.status


def opener(lib):
    """Bounded range reads through NSURLSession, or None on an older framework. No full-film response buffering."""
    capability=getattr(lib,'kodi_http_reads',None) if lib is not None else None
    if capability is None or capability()!=1:return None
    send=sender(lib,READ_MAX)
    if send is None:return None
    def open_url(request,timeout=20):
        url=request.full_url;headers=dict(request.header_items())
        for _ in range(6):
            status,answer,body=send(request.get_method(),url,None,headers,timeout)
            if status in (301,302,303,307,308):
                location=next((v for k,v in answer.items() if k.lower()=='location'),None)
                if not location:break
                target=urllib.parse.urljoin(url,location);old=urllib.parse.urlsplit(url);new=urllib.parse.urlsplit(target)
                if new.scheme not in ('http','https') or (old.scheme=='https' and new.scheme!='https'):
                    raise ConnectionError('Refused unsafe media redirect')
                if (old.scheme,old.hostname,old.port)!=(new.scheme,new.hostname,new.port):
                    headers={k:v for k,v in headers.items() if k.lower() not in ('authorization','cookie','host')}
                url=target;continue
            if status>=300:raise urllib.error.HTTPError(url,status,'Media request failed',answer,io.BytesIO(body))
            return Response(status,answer,body)
        raise ConnectionError('Media redirect did not finish')
    return open_url
