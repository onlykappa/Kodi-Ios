"""Runs inside the phone namespace: asks the lab's echo service by the default route and straight out of eth0 (vpn_probe), then applies vpn_guard.decide()."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'migration', 'bundled-bootstrap', 'resources', 'lib'))
import vpn_guard as g, vpn_probe as p

URL = 'http://203.0.113.10:8080/ip'
out = {}
for label, interface in (('default_route', None), ('physical_eth0', 'eth0')):
    try:
        out[label] = g.parse_probe(p.get(URL, interface, 4))['ip']
    except Exception as error:
        out[label] = 'no answer (%s)' % type(error).__name__
answer = {'ip': out['default_route'], 'org': ''} if out['default_route'][0].isdigit() else None
direct = [out['physical_eth0']] if out['physical_eth0'][0].isdigit() else []
snap = {'tunnels': [('utun0', '10.8.0.2')], 'link': 'wifi'}
out['decision'] = g.decide(True, snap, answer, [], 'salt', (), direct)
print(json.dumps(out))
