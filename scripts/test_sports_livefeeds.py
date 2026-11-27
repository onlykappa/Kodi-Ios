import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_embed as embed,sports_livefeeds as lf
PACKED="eval(function(p,a,c,k,e,d){while(c--)if(k[c])p=p.replace(new RegExp('\\\\b'+c.toString(a)+'\\\\b','g'),k[c]);return p}('0 1=\\'2://3.4/5.6\\';',7,7,'var|u|https|a|b|c|m3u8'.split('|'),0,{}))"
CDN={'matches':[{'id':'g1','team1':'Kansas City Chiefs','team2':'Buffalo Bills','status':'live','league':'NFL','datetime_utc':'2026-11-27T01:20:00Z','channels':[{'name':'A','language':'EN','links':['https://one.example/e1']}]}]}
TOP={'matches':[{'slug':'s1','matchstr':'Buffalo Bills vs Kansas City Chiefs','team1':'Kansas City Chiefs','team2':'Buffalo Bills','channels':[{'name':'B','links':['https://two.example/e2','https://one.example/e1']}]}]}
def feeds(url,referer):
    return url,json.dumps(CDN if 'cdnsport' in url else TOP)
class Embed(unittest.TestCase):
    def test_unpack(self):self.assertEqual(embed.unpack(PACKED),"var u='https://a.b/c.m3u8';")
    def test_playlist_in_packed_script_and_atob(self):
        self.assertEqual(embed.find_playlists('<script>'+PACKED+'</script>','https://x.example/p'),['https://a.b/c.m3u8'])
        import base64
        b=base64.b64encode(b'https://cdn.example/live/x.m3u8?t=1').decode()
        self.assertEqual(embed.find_playlists('<script>play(atob("%s"))</script>'%b,'https://x.example/'),['https://cdn.example/live/x.m3u8?t=1'])
    def test_hops_through_iframes_and_verifies_playlist(self):
        pages={'https://a.example/':'<iframe src="//b.example/e"></iframe><iframe src="https://doubleclick.net/x"></iframe>',
               'https://b.example/e':'<script>var file="https://c.example/s.m3u8";</script>','https://c.example/s.m3u8':'#EXTM3U\n#EXT-X-VERSION:3'}
        calls=[]
        def get(url,ref):calls.append(url);return url,pages[url]
        url,headers=embed.resolve('https://a.example/','https://r.example/',get)
        self.assertEqual(url,'https://c.example/s.m3u8');self.assertEqual(headers['Referer'],'https://b.example/e')
        self.assertNotIn('https://doubleclick.net/x',calls)
    def test_a_page_that_is_not_a_playlist_is_not_reported(self):
        pages={'https://a.example/':'<script>var file="https://c.example/s.m3u8";</script>','https://c.example/s.m3u8':'<html>blocked</html>'}
        self.assertIsNone(embed.resolve('https://a.example/','',lambda u,r:(u,pages[u])))
    def test_depth_and_loops_end(self):
        self.assertIsNone(embed.resolve('https://a.example/','',lambda u,r:(u,'<iframe src="%s"></iframe>'%u)))
class Feeds(unittest.TestCase):
    def test_items_and_candidates(self):
        feed=lf.LiveFeeds(get=feeds);items=feed.get_items()
        self.assertEqual([i.title for i in items],['Kansas City Chiefs vs Buffalo Bills'])
        self.assertEqual(items[0].status,'LIVE');self.assertEqual(items[0].links[0].address,'https://cdnsport.ru/#g1')
        self.assertEqual(feed.candidates('https://cdnsport.ru/#g1'),['https://one.example/e1','https://two.example/e2'])
    def test_one_feed_down_still_works_and_both_down_fails(self):
        def only_top(url,ref):
            if 'cdnsport' in url:raise OSError('down')
            return url,json.dumps(TOP)
        self.assertEqual(lf.LiveFeeds(get=only_top).get_items()[0].links[0].address,'https://topsurge.st/#s1')
        def none(url,ref):raise OSError('down')
        with self.assertRaises(RuntimeError):lf.LiveFeeds(get=none).get_items()
    def test_resolve_takes_first_verified_embed(self):
        pages={'https://one.example/e1':'nothing','https://two.example/e2':'<script>x="https://v.example/a.m3u8"</script>','https://v.example/a.m3u8':'#EXTM3U'}
        get=lambda u,r:(u,pages[u])
        feed=lf.LiveFeeds(get=feeds)
        self.assertEqual(lf.resolve('https://cdnsport.ru/#g1',feed=feed,get=get)[0],'https://v.example/a.m3u8')
        with self.assertRaises(RuntimeError):lf.resolve('https://cdnsport.ru/#g1',feed=feed,get=lambda u,r:(u,'nothing'))
if __name__=='__main__':unittest.main()
