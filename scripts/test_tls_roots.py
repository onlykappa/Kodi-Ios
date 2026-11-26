"""Every add-on gets CA roots on the phone (build 623 log 8c570737: Crew's streamers failed TLS with the "unknown error" the default context gives there)."""
import sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import tls_roots as t

class Roots(unittest.TestCase):
    def test_certifis_bundle_is_set_when_nothing_usable_is_set(self):
        env={};self.assertEqual(t.apply(env,lambda:'/certs/cacert.pem',lambda p:True),'/certs/cacert.pem');self.assertEqual(env['SSL_CERT_FILE'],'/certs/cacert.pem')
        env={'SSL_CERT_FILE':'/gone.pem'};self.assertEqual(t.apply(env,lambda:'/certs/cacert.pem',lambda p:p=='/certs/cacert.pem'),'/certs/cacert.pem')   # a stale path is replaced
    def test_an_existing_file_is_left_alone(self):
        env={'SSL_CERT_FILE':'/mine.pem'};self.assertEqual(t.apply(env,lambda:'/certs/cacert.pem',lambda p:True),'');self.assertEqual(env['SSL_CERT_FILE'],'/mine.pem')
    def test_no_certifi_or_a_missing_file_changes_nothing_and_never_raises(self):
        env={};self.assertEqual(t.apply(env,lambda:'/certs/cacert.pem',lambda p:False),'');self.assertEqual(env,{})
        def boom():raise ImportError('certifi')
        self.assertEqual(t.apply(env,boom,lambda p:True),'');self.assertEqual(env,{})
    def test_the_service_applies_it_before_anything_else_and_says_so(self):
        text=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
        self.assertLess(text.index('import tls_roots;_TLS_ROOTS=tls_roots.apply()'),text.index('from bootstrap import'))
        self.assertIn("Kodi iOS startup: TLS roots",text)
    def test_openssl_honours_the_variable_for_a_new_default_context(self):
        # the mechanism itself: a context made after SSL_CERT_FILE is set loads that file (checked with the real ssl module and a throwaway bundle)
        import os,ssl,tempfile,subprocess
        code="import ssl,sys;c=ssl.create_default_context();print(c.cert_store_stats()['x509_ca'])"
        try:
            import certifi;bundle=certifi.where()
        except Exception:
            self.skipTest('certifi not installed here')
        env=dict(os.environ,SSL_CERT_FILE=bundle);env.pop('SSL_CERT_DIR',None)
        out=subprocess.run([sys.executable,'-I','-c',code],env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(out.returncode,0,out.stderr);self.assertGreater(int(out.stdout.strip()),50)   # certifi's roots are loaded
if __name__=='__main__':unittest.main()
