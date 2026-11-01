import struct,tempfile,unittest,zipfile,stat,os
from pathlib import Path
from build_unsigned_ipa import unsign,zip_tree,validate_staging
from inspect_ios_foundation import macho
from test_ios_foundation import image
class UnsignedTests(unittest.TestCase):
 def test_signature_removed_payload_preserved(self):
  cmd=struct.pack('<4I',0x1d,16,56,4)
  original=image(cmd,1)+b'PAYLOAD!SIGN'
  result,count=unsign(original)
  self.assertEqual(count,1);self.assertFalse(macho(result)['code_signature_commands'])
  self.assertEqual(result[48:56],b'PAYLOAD!');self.assertEqual(result[56:],b'\0'*4)
  self.assertEqual(len(result),len(original))
 def test_source_descendant_output_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   app=Path(d)/'Kodi.app';app.mkdir()
   with self.assertRaises(AssertionError):validate_staging(app,app/'new-output')
 def test_existing_output_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   app=Path(d)/'Kodi.app';app.mkdir();out=Path(d)/'out';out.mkdir()
   with self.assertRaises(AssertionError):validate_staging(app,out)
 def test_unsigned_unchanged(self):self.assertEqual(unsign(image()),(image(),0))
 def test_overlapping_signature_rejected(self):
  with self.assertRaises(AssertionError):unsign(image(struct.pack('<4I',0x1d,16,32,4),1))
 def test_reproducible_zip_and_executable_mode(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'root';root.mkdir();p=root/'Kodi';p.write_bytes(image());p.chmod(0o755)
   a=Path(d)/'a.zip';b=Path(d)/'b.zip';self.assertEqual(zip_tree(root,a),zip_tree(root,b))
   with zipfile.ZipFile(a) as z:self.assertEqual((z.getinfo('Kodi').external_attr>>16)&0o777,0o755)
 def test_symlink_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'root';root.mkdir();(root/'alias').symlink_to('target');out=Path(d)/'a.zip';zip_tree(root,out)
   with zipfile.ZipFile(out) as z:
    self.assertTrue(stat.S_ISLNK(z.getinfo('alias').external_attr>>16));self.assertEqual(z.read('alias'),b'target')
if __name__=='__main__':unittest.main()
