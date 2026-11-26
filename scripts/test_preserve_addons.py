"""Preserved add-on archives: scanner rules on synthetic archives, and every committed archive verifies against its lock."""
import hashlib,io,json,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import preserve_addons as pa
ROOT=Path(__file__).resolve().parents[1]

def make(files,id='plugin.video.x'):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  for n,body in files.items():z.writestr(n,body)
 return b.getvalue()
def spec_for(data,id='plugin.video.x',reviewed=None,**k):
 s={'id':id,'version':'1','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'lock':'x','notice':id+'/LICENSE.txt'}
 s.update(k)
 if reviewed:s['reviewed_secret_shaped']=reviewed
 return s
RX=pa.patterns()
KEY='api_'+'key = '+"'"+'abcdEFGH1234'+'567890abcdefgh'+"'"      # built at run time so this file holds no secret-shaped literal

class Scanner(unittest.TestCase):
 def run_check(self,files,reviewed=None,pinned=True,**k):
  data=make(files);spec=spec_for(data,reviewed=reviewed,**k)
  orig=pa.locked;pa.locked=lambda s:(s['sha256'],s['bytes']) if pinned else None
  try:pa.check(spec,data,RX)
  finally:pa.locked=orig
 def test_clean_archive_passes(self):self.run_check({'plugin.video.x/LICENSE.txt':'GPL','plugin.video.x/a.py':'print(1)\n','plugin.video.x/i.png':b'\x89PNG'})
 def test_unpinned_native_traversal_and_missing_notice_are_refused(self):
  base={'plugin.video.x/LICENSE.txt':'GPL'}
  with self.assertRaisesRegex(ValueError,'pinned'):self.run_check(base,pinned=False)
  with self.assertRaisesRegex(ValueError,'native'):self.run_check(dict(base,**{'plugin.video.x/lib.so':b'\x7fELF'}))
  with self.assertRaisesRegex(ValueError,'native'):self.run_check(dict(base,**{'plugin.video.x/a.pyc':b'x'}))
  with self.assertRaisesRegex(ValueError,'path'):self.run_check(dict(base,**{'../evil.py':'x'}))
  with self.assertRaisesRegex(ValueError,'path'):self.run_check(dict(base,**{'other.addon/a.py':'x'}))
  with self.assertRaisesRegex(ValueError,'notice'):self.run_check({'plugin.video.x/a.py':'x'})
 def test_a_secret_shaped_match_needs_a_review_for_that_exact_member_content(self):
  files={'plugin.video.x/LICENSE.txt':'GPL','plugin.video.x/k.py':KEY+'\n'}
  with self.assertRaisesRegex(ValueError,'unreviewed'):self.run_check(files)
  body=files['plugin.video.x/k.py'].encode()
  ok=[{'member':'plugin.video.x/k.py','pattern':'assigned-secret','member_sha256':hashlib.sha256(body).hexdigest()}]
  self.run_check(files,reviewed=ok)
  with self.assertRaisesRegex(ValueError,'unreviewed'):self.run_check(dict(files,**{'plugin.video.x/k.py':KEY+'\n# changed\n'}),reviewed=ok)
  with self.assertRaisesRegex(ValueError,'unreviewed'):self.run_check(dict(files,**{'plugin.video.x/second.py':KEY+'\n'}),reviewed=ok)
 def test_wrong_digest_and_private_values_are_refused(self):
  data=make({'plugin.video.x/LICENSE.txt':'GPL'});s=spec_for(data);s['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'digest'):pa.check(s,data,RX)
  files={'plugin.video.x/LICENSE.txt':'GPL','plugin.video.x/p.py':'x = "owner-private-value"\n'};data=make(files);s=spec_for(data)
  orig=pa.locked;pa.locked=lambda s_:(s['sha256'],s['bytes'])
  try:
   with self.assertRaisesRegex(ValueError,'private'):pa.check(s,data,RX,needles={'owner-private-value'})
  finally:pa.locked=orig

class Committed(unittest.TestCase):
 def test_manifest_matches_the_locks_and_every_archive_verifies(self):
  m=json.loads(pa.MANIFEST.read_text())['archives'];self.assertGreaterEqual(len(m),16)
  ids=[a['id'] for a in m];self.assertEqual(len(ids),len(set(ids)));self.assertIn('plugin.video.umbrella',ids);self.assertIn('plugin.video.the-loop',ids);self.assertNotIn('plugin.video.youtube',ids)
  for a in m:
   self.assertEqual(pa.locked(a),(a['sha256'],a['bytes']),a['id'])
   p=ROOT/a['path']
   if p.exists() and p.stat().st_size>200:pa.verify(a['path'])      # a checkout without Git LFS holds pointer files: the digest check then needs `git lfs pull`
 def test_reviewed_matches_are_only_third_party_embedded_keys(self):
  for a in json.loads(pa.MANIFEST.read_text())['archives']:
   for r in a.get('reviewed_secret_shaped',[]):self.assertIn(a['id'],('plugin.video.umbrella','plugin.video.the-loop'));self.assertTrue(r['member'].startswith(a['id']+'/'))

if __name__=='__main__':unittest.main()
