"""Crew's four remote modules: pinned lock, deterministic archive, build staging and the first-start seeding of Crew's disk fallback."""
import hashlib,io,json,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import fetch_crew_remote as f, bootstrap
ROOT=Path(__file__).resolve().parents[1]
LOCK=json.loads(f.LOCK.read_text())

class Lock(unittest.TestCase):
 def test_shape(self):
  self.assertEqual(sorted(m['path'] for m in LOCK['modules']),['crewproxy.xml','crewreplays.xml','crewschedule.xml','crewstreamer.xml'])
  for m in LOCK['modules']:self.assertRegex(m['sha256'],r'^[0-9a-f]{64}$');self.assertEqual(len(m['git_blob']),40)
  self.assertEqual(len(LOCK['commit']),40);self.assertEqual(LOCK['archive']['version'],LOCK['commit'][:8])
 def test_archive_is_deterministic_and_matches_the_lock(self):
  blobs={m['path']:(m['path']+'-body\n').encode() for m in LOCK['modules']};a=f.build_zip(LOCK,blobs);self.assertEqual(a,f.build_zip(LOCK,blobs))
  with zipfile.ZipFile(io.BytesIO(a)) as z:self.assertEqual(z.namelist(),sorted(z.namelist()));self.assertTrue(all(i.date_time==(1980,1,1,0,0,0) for i in z.infolist()))
 def test_the_committed_archive_is_the_pinned_one(self):
  p=ROOT/'migration/addon-preserve'/(LOCK['archive']['id']+'-'+LOCK['archive']['version']+'.zip')
  if p.stat().st_size>1000:self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),LOCK['archive']['sha256'])

class Stage(unittest.TestCase):
 def test_stage_extracts_verified_modules_and_skips_a_pointer(self):
  p=ROOT/'migration/addon-preserve'/(LOCK['archive']['id']+'-'+LOCK['archive']['version']+'.zip')
  if p.stat().st_size<1000:self.skipTest('Git LFS pointer in this checkout')
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(f.stage(d),4);self.assertEqual(sorted(x.name for x in (Path(d)/'crew_remote').iterdir()),['crewproxy.xml','crewreplays.xml','crewschedule.xml','crewstreamer.xml'])
   ptr=Path(d)/'ptr.zip';ptr.write_text('version https://git-lfs.github.com/spec/v1\n');self.assertEqual(f.stage(Path(d)/'x',ptr),0)
   bad=Path(d)/'bad.zip';bad.write_bytes(b'PK'+b'x'*2000)
   with self.assertRaises(ValueError):f.stage(Path(d)/'y',bad)

class Seed(unittest.TestCase):
 def test_seeds_only_missing_copies_and_never_overwrites(self):
  with tempfile.TemporaryDirectory() as d:
   profile=Path(d)/'p';src=Path(d)/'crew_remote';src.mkdir();(src/'crewproxy.xml').write_text('# pinned proxy\n');(src/'crewstreamer.xml').write_text('# pinned streamer\n')
   self.assertEqual(bootstrap.seed_crew_remote_cache(profile,src),['crewproxy','crewstreamer']);target=profile/'addon_data/plugin.video.thecrew'
   self.assertEqual((target/'crewproxy.py').read_text(),'# pinned proxy\n')
   (target/'crewproxy.py').write_text('# fresh download\n');self.assertEqual(bootstrap.seed_crew_remote_cache(profile,src),[]);self.assertEqual((target/'crewproxy.py').read_text(),'# fresh download\n')
   self.assertEqual(bootstrap.seed_crew_remote_cache(profile,Path(d)/'missing'),[])
 def test_housekeeping_seeds_once_from_the_bundled_folder(self):
  with tempfile.TemporaryDirectory() as d:
   profile=Path(d);calls=[]
   self.assertNotIn('crew_remote_cache',bootstrap.phone_housekeeping(profile,None,lambda m,p:calls.append(1) or {'result':'OK'}),'nothing bundled in a source checkout: nothing seeded')

if __name__=='__main__':unittest.main()
