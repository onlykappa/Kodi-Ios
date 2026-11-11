"""Roadmap 2.13: the subtitle site failed with Errno 8 on the owner's phone (its DNS refuses the name)."""
import io,json,socket,sys,unittest,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import doh_fetch,track_menu

class Resp:
    def __init__(self,status,body=b'',location=None):self.status=status;self._b=body;self.reason='x';self.headers={};self._l=location
    def read(self):return self._b
    def getheader(self,k):return self._l if k=='Location' else None

class Conn:
    def __init__(self,log,answers):self.log=log;self.answers=answers
    def request(self,method,path,headers):self.log.append((path,headers['Host']))
    def getresponse(self):return self.answers.pop(0)
    def close(self):pass

def refusing_dns(req,timeout):raise urllib.error.URLError(socket.gaierror(8,'nodename nor servname provided, or not known'))

class Fallback(unittest.TestCase):
    def test_dns_refusal_retries_through_dns_over_https_and_follows_redirects(self):
        log=[];answers=[Resp(302,location='/subtitles/abc/download?x=1'),Resp(200,b'ZIP')]
        conns=[]
        def connect(host,ip):conns.append((host,ip));return Conn(log,answers)
        body=doh_fetch.get('https://www.podnapisi.net/subtitles/search/advanced?keywords=phony',opener=refusing_dns,
                           resolver=lambda host:['1.2.3.4'],connect=connect)
        self.assertEqual(body,b'ZIP')
        self.assertEqual(conns,[('www.podnapisi.net','1.2.3.4')]*2)   # SNI/Host keep the name; only the IP comes from DoH
        self.assertEqual(log[1],('/subtitles/abc/download?x=1','www.podnapisi.net'))
    def test_other_errors_are_not_retried(self):
        def http_error(req,timeout):raise urllib.error.HTTPError(req.full_url,500,'x',{},None)
        with self.assertRaises(urllib.error.HTTPError):doh_fetch.get('https://a.example/',opener=http_error,resolver=lambda h:self.fail('no DoH'))
    def test_no_answer_raises_the_original_error(self):
        with self.assertRaises(urllib.error.URLError):doh_fetch.get('https://a.example/',opener=refusing_dns,resolver=lambda h:[])
    def test_resolve_reads_a_records(self):
        class R(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*a):pass
        answer=json.dumps({'Answer':[{'type':5,'data':'cname.'},{'type':1,'data':'5.6.7.8'}]}).encode()
        self.assertEqual(doh_fetch.resolve('www.podnapisi.net',opener=lambda req,timeout:R(answer)),['5.6.7.8'])

class Release(unittest.TestCase):
    def test_release_names(self):
        self.assertEqual(track_menu.from_release('phony.s01e01.1080p.web.h264-cakes[EZTVx.to].mp4'),{'title':'phony','season':1,'episode':1})
        self.assertEqual(track_menu.from_release('The.Last.of.Us.S02E07.2160p.mkv')['title'],'The Last of Us')
        self.assertIsNone(track_menu.from_release('Home Alone'))

if __name__=='__main__':unittest.main()
