"""Which layer stops a Sports source's website answering on the phone (owner, build 623 log 8c570737: Crew's embedsports host failed TLS)."""
import sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import host_check as hc

class Check(unittest.TestCase):
    def test_the_kind_of_address_shows_a_filters_answer(self):
        self.assertEqual([hc.kind(a) for a in ('104.21.4.5','10.0.0.2','192.168.1.1','127.0.0.1','0.0.0.0','::1','nope','2606:4700::1')],
                         ['public','private','private','loopback','unspecified','loopback','invalid','public'])
    def test_a_sinkhole_from_the_phones_dns_while_doh_gives_the_real_address_reads_as_such(self):
        line=hc.check_host('taifood-blog.asia',system=lambda h:['0.0.0.0'],doh=lambda h:['104.21.4.5'],tls=lambda h,a:'ok TLSv1.3' if a=='104.21.4.5' else 'tls refused (unknown error)',plain=lambda h,a:'tls refused (unknown error)')
        self.assertEqual(line,'taifood-blog.asia: phone DNS 1 address (unspecified), TLS tls refused (unknown error) | default roots: tls refused (unknown error) | DoH 1 address (public, not the phone\'s), TLS ok TLSv1.3')
    def test_the_same_address_both_ways_with_a_refused_handshake_points_at_the_site(self):
        line=hc.check_host('h.example',system=lambda h:['104.21.4.5'],doh=lambda h:['104.21.4.5'],tls=lambda h,a:'tls refused (unknown error)',plain=lambda h,a:'x')
        self.assertIn('DoH 1 address (public, same as the phone), TLS tls refused (unknown error)',line)
    def test_dns_failures_and_no_answers_are_words_not_crashes(self):
        def boom(h):raise OSError('nodename')
        self.assertEqual(hc.check_host('h.example',system=boom,doh=lambda h:[],tls=lambda h,a:'x'),'h.example: phone DNS failed (OSError) | DoH no answer')   # nothing found: no default-roots probe
        self.assertIn('DoH failed (RuntimeError)',hc.check_host('h.example',system=lambda h:[],doh=boom_runtime,tls=lambda h,a:'x'))
        self.assertIn('nothing to try',hc.check_host('h.example',system=lambda h:[],doh=lambda h:[],tls=lambda h,a:'x'))
    def test_no_path_or_header_reaches_the_line(self):
        line=hc.check_host('taifood-blog.asia',system=lambda h:['1.2.3.4'],doh=lambda h:[],tls=lambda h,a:'ok TLSv1.3')
        self.assertNotIn('://',line);self.assertNotIn('?',line)
    def test_the_default_roots_are_told_from_certifi_on_the_same_address(self):
        line=hc.check_host('h.example',system=lambda h:['104.21.4.5'],doh=lambda h:[],tls=lambda h,a:'ok TLSv1.3',plain=lambda h,a:'tls refused (unknown error)')
        self.assertIn('TLS ok TLSv1.3 | default roots: tls refused (unknown error)',line)

def boom_runtime(host):raise RuntimeError('x')

class Later(unittest.TestCase):
    def setUp(self):hc._last[0]=0.0;self.addCleanup(hc._last.__setitem__,0,0.0)
    def test_once_every_ten_minutes_in_a_thread(self):
        logs=[];clock=[1000.0]
        t=hc.check_later(logs.append,hosts=('a.example','b.example'),now=lambda:clock[0],system=lambda h:['1.1.1.1'],doh=lambda h:[],tls=lambda h,a:'ok TLSv1.3');t.join(5)
        self.assertEqual(len(logs),2);self.assertTrue(logs[0].startswith('host check: a.example: phone DNS'))
        clock[0]+=60;self.assertIsNone(hc.check_later(logs.append,hosts=('a.example',),now=lambda:clock[0]))
        clock[0]+=hc.EVERY;t=hc.check_later(logs.append,hosts=('c.example',),now=lambda:clock[0],system=lambda h:['1.1.1.1'],doh=lambda h:[],tls=lambda h,a:'ok');t.join(5);self.assertEqual(len(logs),3)
    def test_a_failing_host_is_logged_not_raised(self):
        logs=[]
        def bad(h):raise ValueError('x')
        t=hc.check_later(logs.append,hosts=('a.example',),now=lambda:5.0,system=bad,doh=bad,tls=lambda h,a:'x');t.join(5)
        self.assertEqual(len(logs),1)
    def test_a_failed_source_triggers_it(self):
        text=(ROOT/'migration/bundled-bootstrap/resources/lib/sports_loop_router.py').read_text()
        self.assertIn('host_check.check_later(logger)',text);self.assertLess(text.index('host_check.check_later(logger)'),text.index("raise RuntimeError('native queue exhausted')"))
if __name__=='__main__':unittest.main()
