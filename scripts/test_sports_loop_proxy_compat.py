import sys,unittest,urllib.parse,threading,uuid,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_loop_proxy_compat as compat
class Tests(unittest.TestCase):
 def test_opaque_alias_preserves_exact_signed_and_relative_paths(self):
  env={'quote':urllib.parse.quote,'unquote':urllib.parse.unquote,'urlparse':urllib.parse.urlparse,'threading':threading,'uuid':uuid}
  exec(compat.ALIAS,env)
  for value in ['seg.ts?token=fixture','https://source.invalid/sub/seg.ts?token=fixture','https://source.invalid/key?token=fixture']:
   alias=env['quote'](value,safe='');self.assertTrue(alias.endswith('.ts'));self.assertNotIn('fixture',alias);self.assertEqual(env['unquote'](alias),value)
 def test_child_segments_and_keys_use_child_playlist_base(self):
  env={'child_body':'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:6,\nsegment.ts?token=fixture\n','best_variant_url':'https://source.invalid/sub/live.m3u8','urljoin':urllib.parse.urljoin,'re':__import__('re')}
  # Execute the actual inserted block in a function so original indentation is retained.
  import textwrap
  exec(textwrap.dedent(compat.REBASE),env)
  self.assertIn('https://source.invalid/sub/segment.ts?token=fixture',env['child_body']);self.assertIn('https://source.invalid/sub/key',env['child_body'])
 def test_rejects_unknown_source(self):
  with self.assertRaises(ValueError):compat.patched('proxy_server.py',b'import requests\n')
if __name__=='__main__':unittest.main()
