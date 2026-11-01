import hashlib,tempfile,unittest
from pathlib import Path
from compare_skin_source import compare
class SkinComparisonTests(unittest.TestCase):
 def test_matching_changed_missing_and_extra(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'same.xml').write_bytes(b'fixture');(root/'changed.xml').write_bytes(b'changed');(root/'extra.xml').write_bytes(b'extra')
   blob=hashlib.sha1(b'blob 7\0fixture').hexdigest()
   tree={'commit':'fixture','truncated':False,'files':[{'path':n,'git_blob_sha':blob} for n in ('same.xml','changed.xml','missing.xml')]}
   r=compare(root,tree);self.assertEqual(r['matching_files'],1);self.assertEqual(r['changed_upstream_files'][0]['path'],'changed.xml');self.assertEqual(r['absent_upstream_files'],['missing.xml']);self.assertEqual(r['additional_installed_file_count'],1)
 def test_truncated_tree_rejected(self):
  with self.assertRaises(AssertionError):compare(Path('/tmp'),{'truncated':True})
 def test_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(AssertionError):compare(Path(d),{'commit':'fixture','truncated':False,'files':[{'path':'../escape','git_blob_sha':'fixture'}]})
if __name__=='__main__':unittest.main()
