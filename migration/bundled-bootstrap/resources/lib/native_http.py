"""HTTP through the system's networking (KodiAirPlay.framework kodi_http_send, ISSUE-167).

Build-229 log: Drive upload pieces crawled (~0.3 MB/s in total, one lane or two, on a 115 Mbps line) while nothing
played. Python's TLS sends a body 16 KB at a time and every step waits for the interpreter. The framework sends the
whole request with NSURLSession while this thread waits outside the interpreter (ctypes releases it)."""
import ctypes

HEADERS_MAX = 64 * 1024
BODY_MAX = 256 * 1024


def sender(lib):
    """send(method, url, body, headers, timeout) -> (status, headers, body), or None without the framework."""
    fn = getattr(lib, 'kodi_http_send', None) if lib is not None else None
    if fn is None:
        return None
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_longlong, ctypes.c_double,
                   ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    fn.restype = ctypes.c_int

    def send(method, url, body, headers, timeout):
        lines = ''.join('%s: %s\n' % (k, v) for k, v in (headers or {}).items() if '\n' not in str(v))
        out_headers = ctypes.create_string_buffer(HEADERS_MAX)
        out_body = ctypes.create_string_buffer(BODY_MAX)
        used = ctypes.c_int(0)
        status = fn(method.encode(), url.encode(), lines.encode(), body or None, len(body or b''), float(timeout),
                    out_headers, HEADERS_MAX, out_body, BODY_MAX, ctypes.byref(used))
        if status < 0:
            raise ConnectionError('System networking: ' + out_body.value.decode('utf-8', 'replace')[:200])
        parsed = {}
        for line in out_headers.value.decode('utf-8', 'replace').split('\n'):
            name, sep, value = line.partition(':')
            if sep:
                parsed[name.strip()] = value.strip()
        return status, parsed, out_body.raw[:used.value]
    return send
