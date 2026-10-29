import struct,unittest,plistlib
from inspect_ios_foundation import macho,signature_entitlements

def image(commands=b'',count=0,cpu=0x100000c):return struct.pack('<8I',0xfeedfacf,cpu,0,2,count,len(commands),0,0)+commands
class FoundationTests(unittest.TestCase):
 def test_arm64_ios_platform(self):
  command=struct.pack('<6I',0x32,24,2,11<<16,18<<16,0)
  self.assertEqual(macho(image(command,1))['platforms'][0]['platform'],2)
 def test_other_cpu_rejected(self):
  with self.assertRaises(AssertionError):macho(image(cpu=0x1000007))
 def test_truncated_header_rejected(self):
  with self.assertRaises(AssertionError):macho(b'bad')
 def test_invalid_command_rejected(self):
  with self.assertRaises(AssertionError):macho(image(struct.pack('<2I',0x32,64),1))
 def test_signature_command_recorded(self):
  command=struct.pack('<4I',0x1d,16,48,4)
  self.assertEqual(macho(image(command,1)+b'test')['code_signature_commands'][0]['bytes'],4)
 def test_signature_outside_file_rejected(self):
  with self.assertRaises(AssertionError):macho(image(struct.pack('<4I',0x1d,16,900,20),1))
 def test_simulator_not_misreported_as_device(self):
  command=struct.pack('<6I',0x32,24,7,18<<16,18<<16,0)
  self.assertEqual(macho(image(command,1))['platforms'][0]['platform'],7)
 def test_encryption_reported(self):
  command=struct.pack('<6I',0x2c,24,32,0,1,0)
  self.assertTrue(macho(image(command,1))['encrypted'])
class EntitlementTests(unittest.TestCase):
 def test_unsigned_has_no_entitlements(self):self.assertEqual(signature_entitlements(image()),[])
 def test_xml_entitlements_parsed(self):
  xml=plistlib.dumps({'get-task-allow':True})
  member=struct.pack('>II',0xfade7171,len(xml)+8)+xml
  blob=struct.pack('>III',0xfade0cc0,20+len(member),1)+struct.pack('>II',5,20)+member
  data=image(struct.pack('<4I',0x1d,16,48,len(blob)),1)+blob
  self.assertTrue(signature_entitlements(data)[0]['values']['get-task-allow'])
 def test_corrupt_superblob_rejected(self):
  data=image(struct.pack('<4I',0x1d,16,48,12),1)+b'bad-signatur'
  with self.assertRaises(AssertionError):signature_entitlements(data)
if __name__=='__main__':unittest.main()
