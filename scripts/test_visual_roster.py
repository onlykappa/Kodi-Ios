import copy,unittest
from build_visual_roster import preserve_evidence
class RosterTests(unittest.TestCase):
 def row(self,path='one'):return {'id':'fixture','route_sha256':path,'status':'AWAITING DEVICE TESTING','evidence':None}
 def test_same_route_preserves_recorded_failure(self):
  old={**self.row(),'status':'FAILED','evidence':'private-capture-sha256'}
  result=preserve_evidence([self.row()],[old]);self.assertEqual(result[0]['status'],'FAILED');self.assertEqual(result[0]['evidence'],'private-capture-sha256')
 def test_changed_route_keeps_history_and_requires_new_test(self):
  old={**self.row(),'status':'FAILED','evidence':'private-capture-sha256'}
  result=preserve_evidence([self.row('changed')],[copy.deepcopy(old)])
  self.assertIsNone(result[0]['evidence']);self.assertEqual(result[0]['previous_versions'][0],old)
 def test_removed_route_is_retained_for_owner_review(self):
  old={**self.row(),'status':'FAILED'}
  result=preserve_evidence([],[old]);self.assertTrue(result[0]['exclusion_review_required']);self.assertEqual(result[0]['status'],'FAILED')
if __name__=='__main__':unittest.main()
