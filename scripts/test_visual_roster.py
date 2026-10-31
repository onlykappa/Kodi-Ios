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
 def test_menu_slot_move_retains_original_id_and_failure(self):
  old=[{**self.row('youtube'),'id':'slot0','origin':'target','source':'menu','slot':0,'label':'YouTube'}, {**self.row('drive'),'id':'slot1','origin':'target','source':'menu','slot':1,'status':'FAILED','evidence':'private-failure'}]
  new=[{**self.row('drive'),'id':'slot0','origin':'target','source':'menu','slot':0}]
  out=preserve_evidence(new,old);self.assertEqual(len(out),2)
  drive=next(r for r in out if r['id']=='slot1');self.assertEqual(drive['status'],'FAILED');self.assertEqual(drive['slot'],0)
  yt=next(r for r in out if r['id']=='slot0');self.assertIn('owner_approved_exclusion',yt);self.assertIsNone(yt['evidence'])
if __name__=='__main__':unittest.main()
