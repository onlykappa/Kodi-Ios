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

 def test_the_decks_working_3_3_34_proxy_is_accepted_and_still_compiles(self):
  # The real file (jetextractors 3.3.34, from the preserved archive) gets the same two changes; skipped when Git LFS content is not checked out.
  import zipfile
  archive=Path(__file__).resolve().parents[1]/'migration/addon-preserve/script.module.jetextractors-3.3.34.zip'
  try:z=zipfile.ZipFile(archive)
  except (zipfile.BadZipFile,OSError):self.skipTest('Git LFS archive not checked out')
  base='script.module.jetextractors/lib/jetextractors/util/'
  for name in ('proxy_server.py','manifest_rewriter.py'):
   data=z.read(base+name);out=compat.patched(name,data).decode()
   self.assertIn(compat.MARKER,out);compile(out,name,'exec');self.assertEqual(compat.patched(name,out.encode()),out.encode(),'patching twice changes nothing')
  proxy=compat.patched('proxy_server.py',z.read(base+'proxy_server.py')).decode()
  self.assertLess(proxy.index('kodi-loop-proxy-compat-v1'),proxy.index('import requests\n'),'the alias comes before the first use of quote')
if __name__=='__main__':unittest.main()
