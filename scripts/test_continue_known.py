"""A subtitle search for an Umbrella episode knows the show, season and episode (owner, build 639 log 9f7b4ab2: Kodi's item said only 'Episode 8', so SubDL was asked
for 'Episode 8' with no season or episode and gave some other show's subtitle, which the owner found wrong)."""
import ast,json,sys,time,unittest
from pathlib import Path
SRC=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/tracks.py').read_text()
tree=ast.parse(SRC)
func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='continue_known')
space={'json':json,'time':time};exec(compile(ast.Module([func],[]),'tracks.py','exec'),space)
known=space['continue_known']

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
    def test_the_menu_asks_for_it_when_nothing_else_knows_the_title(self):
        self.assertIn('return continue_known(it, read, link=link)',SRC)
if __name__=='__main__':unittest.main()
