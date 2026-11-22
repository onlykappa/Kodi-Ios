"""A subtitle search for an Umbrella episode knows the show, season and episode (owner, build 639 log 9f7b4ab2: Kodi's item said only 'Episode 8', so SubDL was asked
for 'Episode 8' with no season or episode and gave some other show's subtitle, which the owner found wrong)."""
import ast,json,sys,time,unittest
from pathlib import Path
SRC=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/tracks.py').read_text()
tree=ast.parse(SRC)
func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='continue_known')
space={'json':json,'time':time};exec(compile(ast.Module([func],[]),'tracks.py','exec'),space)
pfunc=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='playing_known')
exec(compile(ast.Module([pfunc],[]),'tracks.py','exec'),space)
space['re']=__import__('re')
for _n in ('generic_title','tmdb_known'):
    exec(compile(ast.Module([next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==_n)],[]),'tracks.py','exec'),space)
known=space['continue_known'];playing_known=space['playing_known']

def store(**entry):
    base={'kind':'episode','tmdb_id':'73223','title':'Episode 8','tvshowtitle':'Black Clover','year':'2017','season':'2','episode':'8','played':time.time()}
    base.update(entry);return json.dumps({'current':'k','items':{'k':base}})

class Known(unittest.TestCase):
    def test_the_show_season_and_episode_come_from_what_continue_follows(self):
        got=known({'title':'Episode 8','showtitle':''},lambda path:store())
        self.assertEqual((got['show'],got['season'],got['episode'],got['tmdb']),('Black Clover','2','8','73223'))
    def test_another_title_or_an_old_entry_is_not_used(self):
        self.assertEqual(known({'title':'Something else'},lambda path:store()),{})
        self.assertEqual(known({'title':'Episode 8'},lambda path:store(played=time.time()-7*3600)),{})
        self.assertEqual(known({'title':'Episode 8'},lambda path:''),{});self.assertEqual(known({'title':'Episode 8'},lambda path:1/0),{})
    def test_a_movie_has_no_show(self):
        got=known({'title':'Heat'},lambda path:store(kind='movie',title='Heat',tvshowtitle='',season=None,episode=None,year='1995'))
        self.assertEqual((got['kind'],got['show'],got['year']),('movie','','1995'))
    def test_the_link_the_stream_is_read_from_counts_when_the_titles_differ(self):   # build 653 log d63069c3: the item's title need not be the entry's
        store=lambda **e:json.dumps({'current':'k','items':{'k':dict({'kind':'episode','title':'The Mage','tvshowtitle':'Black Clover','season':'2','episode':'8','played':time.time(),'stream':{'url':'https://dl.example.invalid/f.mkv'}},**e)}})
        got=known({'title':'Episode 8'},lambda p:store(),link='https://dl.example.invalid/f.mkv|User-Agent=Kodi')
        self.assertEqual((got['show'],got['season'],got['episode']),('Black Clover','2','8'))
        self.assertEqual(known({'title':'Episode 9'},lambda p:store(),link='https://dl.example.invalid/other.mkv'),{})
        self.assertEqual(known({'title':'Episode 9'},lambda p:store()),{})
    def test_a_recent_start_of_episode_n_counts_after_a_fallback_link(self):   # build 660 log dc74b76b: new link, entry titled 'The Mage'
        old=lambda **e:store(title='The Mage',**e)
        got=known({'title':'Episode 8'},lambda p:old(),link='https://other.example/f.mkv')
        self.assertEqual((got['show'],got['season'],got['episode']),('Black Clover','2','8'))
        self.assertEqual(known({'title':'Episode 9'},lambda p:old()),{})
        self.assertEqual(known({'title':'Episode 8'},lambda p:old(played=time.time()-7*3600)),{})
    def test_an_unset_playing_property_does_not_end_the_lookup(self):   # build 662 log 3173e72b: '' read as time 0 = stale, so Continue's record was never asked
        self.assertEqual(playing_known({'title':'Episode 8'},''),{});self.assertEqual(playing_known({'title':'Episode 8'},None),{})
        self.assertEqual(playing_known({'title':'Episode 8'},'{}'),{})
        fresh=json.dumps({'t':time.time(),'title':'Episode 8','show':'Black Clover','season':2,'episode':8})
        self.assertEqual(playing_known({'title':'Episode 8'},fresh)['show'],'Black Clover')
        self.assertEqual(playing_known({'title':'Other'},fresh),{})
        self.assertEqual(playing_known({'title':'Episode 8'},json.dumps({'t':time.time()-7*3600,'title':'Episode 8'})),{})
    def test_the_search_asks_continue_after_the_property(self):
        src=SRC[SRC.index('def played(self, it)'):SRC.index('def search(self)')]
        self.assertIn('playing_known(it,',src);self.assertLess(src.index('playing_known'),src.index('continue_known'))
    def test_a_bare_episode_label_names_no_show(self):
        g=space['generic_title']
        for t in ('Episode 8','episode 08','E8','Ep. 3','Part 2'):self.assertTrue(g(t),t)
        for t in ('Episode 8 The Mage','Black Clover','Heat',''):self.assertFalse(g(t),t)
        self.assertTrue(space['tmdb_known']({'uniqueid':{'tmdb':'1'}},None));self.assertFalse(space['tmdb_known']({},None))
    def test_the_menu_asks_for_it_when_nothing_else_knows_the_title(self):
        self.assertIn('return continue_known(it, read, link=link)',SRC)
if __name__=='__main__':unittest.main()
