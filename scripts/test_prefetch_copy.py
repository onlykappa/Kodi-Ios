"""A copy that may play next is prefetched by the proxy (next episode, the most likely movie, the first two Continue Watching items)."""
import sys,types,unittest,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import ios_library as lib

class Win:
    def __init__(self,port):self.port=port
    def getProperty(self,key):return self.port if key=='KodiIOS.DriveProxy' else ''

class Prefetch(unittest.TestCase):
    def run_with(self,port,path,asked):
        gui=types.SimpleNamespace(Window=lambda ident:Win(port))
        saved=sys.modules.get('xbmcgui');sys.modules['xbmcgui']=gui
        try:
            ok=lib.prefetch_copy(path,ask=lambda p,f:asked.append((p,f)))
            time.sleep(0.1)
            return ok
        finally:
            if saved is None:sys.modules.pop('xbmcgui',None)
            else:sys.modules['xbmcgui']=saved
    def test_a_drive_copy_is_prefetched_through_the_proxy_on_a_thread(self):
        asked=[]
        path='plugin://plugin.googledrive/?action=play&content_type=video&driveid=D&item_id=FILE1'
        self.assertTrue(self.run_with('8123',path,asked));self.assertEqual(asked,[(8123,'FILE1')])
    def test_nothing_happens_without_a_proxy_or_for_a_phone_file(self):
        asked=[]
        self.assertFalse(self.run_with('','plugin://plugin.googledrive/?action=play&driveid=D&item_id=F',asked))
        self.assertFalse(self.run_with('8123','/var/mobile/Kodi Downloads/TV Shows/x.mp4',asked));self.assertEqual(asked,[])
if __name__=='__main__':unittest.main()
