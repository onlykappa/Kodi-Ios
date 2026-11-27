import base64,json,sys,unittest
from pathlib import Path
from urllib.parse import parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_p720 as p
LIST='<a class="match-card" href="/live/nfl/buffalo-bills"><div class="match-time"><span>2026-11-27 01:20:00 UTC</span></div><span class="live-badge"></span><div class="match-teams"><b>Buffalo Bills</b> VS <b>Kansas City Chiefs</b></div></a><a class="match-card" href="/live/x"><div class="match-time"><span>24/7</span></div><div class="match-teams">Replay channel</div></a>'
EMBED='<script>var siteConfig = {"csrf":"c","csrf_ip":"i","sec_expires":"9","sec_hash":"h"};</script><script async src="https://sts.p.me/scripts/v2/embedv4.min.js" data-pldm="p.me" data-pid="6" data-play="abc" data-player="jw" data-gc="football"></script>'
CFG={'urlSource':'https://cdn.example/m/manifest.ts?u_id=old','csrf_token':base64.b64encode(b'tok').decode(),'secTokenUrl':base64.b64encode(b'https://auth.example/').decode(),'sCode':'s','strUnqId':'u','expireTs':'1','session_id':'x','device_id':'d0','edgeHostId':'e'}
PLAYER='<script>window.SecKeyPlayerConfig["a"]=%s;</script>'%json.dumps(CFG)
class Fake:
    def __init__(self,**o):self.calls=[];self.o=o
    def __call__(self,url,headers=None,data=None,timeout=8):
        self.calls.append((url,headers or {},data))
        if '/vimpl/' in url:return 200,url,PLAYER
        if url.startswith('https://auth.example/'):return 200,url,json.dumps({'device_id':'fresh'})
        if url.startswith('https://cdn.example/'):return self.o.get('manifest',(200,url,'#EXTM3U\n'))
        if url.startswith('https://sportsframe.me/'):return 200,url,EMBED
        if url.startswith('https://720pstream.cx/live/'):return 200,url,'<iframe src="https://sportsframe.me/nfl/buffalo-bills-stream-1"></iframe>'
        return 404,url,''
class P720(unittest.TestCase):
    def test_listing(self):
        get=lambda url,headers=None:(200,url,LIST)
        items=p.P720Stream(get=get,slugs=['nfl-online']).get_items()
        self.assertEqual([(i.title,i.status,i.league) for i in items],[('Buffalo Bills VS Kansas City Chiefs','LIVE','NFL')])
        self.assertEqual(items[0].links[0].address,'https://720pstream.cx/live/nfl/buffalo-bills');self.assertIsNotNone(items[0].starttime)
    def test_site_down_raises(self):
        def get(url,headers=None):raise OSError('down')
        with self.assertRaises(RuntimeError):p.P720Stream(get=get,slugs=['nfl-online']).get_items()
    def test_v4_player_posts_payload_and_uses_fresh_device(self):
        fake=Fake();url,headers=p.resolve('https://720pstream.cx/live/nfl/buffalo-bills',get=fake)
        self.assertIn('u_id=fresh',url);self.assertEqual(headers['Origin'],'https://p.me')
        post=[c for c in fake.calls if '/vimpl/' in c[0]][0]
        payload=json.loads(base64.b64decode(parse_qs(post[2].decode())['payload'][0]))
        self.assertEqual(payload,{'pid':'6','vimg':'abc','player':'jw','csrf':'c','csrf_ip':'i','expires':'9','sec_hash':'h'})
        auth=[c for c in fake.calls if c[0].startswith('https://auth.example/')][0]
        self.assertEqual(auth[1]['X-CSRF-Auth'],'tok')
    def test_a_playlist_that_is_not_hls_is_not_reported(self):
        with self.assertRaises(RuntimeError):p.resolve('https://720pstream.cx/live/nfl/buffalo-bills',get=Fake(manifest=(200,'u','<html>no</html>')))
        with self.assertRaises(RuntimeError):p.resolve('https://720pstream.cx/live/nfl/buffalo-bills',get=Fake(manifest=(403,'u','')))
    def test_other_hosts_are_refused(self):
        with self.assertRaises(ValueError):p.resolve('https://evil.example/live/x',get=Fake())
if __name__=='__main__':unittest.main()
