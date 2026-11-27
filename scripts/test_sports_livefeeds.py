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

class Events(unittest.TestCase):
    """F1 (owner screenshot 2026-11-27: "Searching for sources" for Practice 2): a Grand Prix has one name and no two sides; the sessions of a weekend share it."""
    GP={'matches':[{'slug':'a','matchstr':'Qatar Grand Prix','team1':'Qatar Grand Prix','team2':None,'league':'Formula 1','startTimestamp':1795798800000,'channels':[{'name':'S','links':['https://s3.vertex.st/ch?id=7']}]},
                   {'slug':'b','matchstr':'Qatar Grand Prix','team1':'Qatar Grand Prix','team2':None,'league':'Formula 1','startTimestamp':1795872600000,'channels':[]}]}
    def test_sessions_with_one_name_are_all_listed_but_a_game_in_both_feeds_once(self):
        get=lambda url,ref:(url,json.dumps({'matches':[]} if 'cdnsport' in url else self.GP))
        items=lf.LiveFeeds(get=get).get_items()
        self.assertEqual([i.starttime is not None for i in items],[True,True])
    def test_a_one_name_event_becomes_a_record_and_matches_the_session_at_its_own_time(self):
        import sports_jet as sj,sports_merge as sm
        from types import SimpleNamespace as NS
        from datetime import datetime
        item=NS(title='Qatar Grand Prix',league='Formula 1',status='',links=[NS(address='https://topsurge.st/#a',name='',links=False,to_dict=lambda:{'address':'https://topsurge.st/#a'})],starttime=datetime.fromtimestamp(1795798800))
        rec=sj.records(item,'IndependentLiveFeeds',1795801200)[0]
        self.assertEqual((rec['league'],rec['away']['name'],rec['home']['name'],rec['state']),('F1','Qatar Grand Prix','','live'))
        espn={'league':'F1','start':1795798800,'away':{'name':'Qatar Airways Qatar Grand Prix'},'home':{'name':''}}
        self.assertTrue(sm.same_game(espn,rec))
        self.assertFalse(sm.same_game(dict(espn,start=1795798800+3*3600),rec),'another session of the weekend')
        self.assertFalse(sm.same_game(dict(espn,away={'name':'Abu Dhabi Grand Prix'}),rec))
        self.assertFalse(sm.same_game(dict(espn,league='MGP'),rec))
class ApiPlayer(unittest.TestCase):
    def test_channel_pages_that_ask_an_api_for_the_player_are_followed(self):
        page='<script>window.loadPlayerChannel = function(i){fetch("api/player.php?id=" + i)}; window.loadPlayerChannel(7);</script>'
        pages={'https://s3.example/ch?id=7':page,'https://s3.example/api/player.php?id=7':'{"url":"https:\\/\\/p.example\\/embed?c=1"}','https://p.example/embed?c=1':'<script>var s="https://h.example/x/index.m3u8";</script>','https://h.example/x/index.m3u8':'#EXTM3U'}
        url,headers=embed.resolve('https://s3.example/ch?id=7','https://r.example/',lambda u,r:(u,pages[u]))
        self.assertEqual(url,'https://h.example/x/index.m3u8')
    def test_json_url_only_takes_a_web_address(self):
        self.assertEqual(embed.json_url('{"url":"https://a.example/b"}'),'https://a.example/b')
        self.assertIsNone(embed.json_url('{"url":"javascript:x"}'));self.assertIsNone(embed.json_url('<html>'))
if __name__=='__main__':unittest.main()
