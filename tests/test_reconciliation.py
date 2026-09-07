import unittest
from clinic import reconcile

class ReconciliationTests(unittest.TestCase):
    def test_ack_is_not_durability(self):
        r=reconcile([{'event_id':'x','source_accepted':True}],[{'event_id':'x','collector_accepted':True}],[])
        self.assertEqual(r['acknowledged_missing'],['x'])
    def test_duplicates_and_unacknowledged_delivery(self):
        r=reconcile([{'event_id':'x','source_accepted':True}],[],[{'event_id':'x'}]*2)
        self.assertEqual(r['duplicates'],1); self.assertEqual(r['delivered_without_ack'],['x'])
    def test_source_drop(self):
        r=reconcile([{'event_id':'x','source_accepted':False}],[],[])
        self.assertEqual(r['source_dropped'],['x'])
    def test_foreign_and_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError): reconcile([],[],[{'event_id':'foreign'}])
        with self.assertRaises(ValueError): reconcile([{'event_id':'a','source_accepted':True}]*2,[],[])

if __name__=='__main__': unittest.main()
