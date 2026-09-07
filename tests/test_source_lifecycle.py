import concurrent.futures,pathlib,tempfile,threading,unittest,time
from clinic import Sink,Source,reconcile

class SourceLifecycleTests(unittest.TestCase):
    def test_reject_after_close_and_idempotent_close(self):
        s=Source('http://127.0.0.1:1');s.finish();s.finish()
        self.assertFalse(s.publish('late'));self.assertFalse(s.thread.is_alive())
        self.assertEqual(s.attempts[-1]['rejection_reason'],'source_closing_or_closed')
    def test_zero_capacity_cannot_create_unbounded_queue(self):
        for c in [0,-1,True]:
            with self.assertRaises(ValueError):Source('http://127.0.0.1:1',capacity=c)
    def test_close_deadline_is_retryable_and_rejects_late_work(self):
        with tempfile.TemporaryDirectory() as d:
            sink=Sink(('127.0.0.1',0),pathlib.Path(d)/'sink.jsonl');sink.mode='slow';sink.delay=.3
            t=threading.Thread(target=sink.serve_forever);t.start()
            s=Source(f'http://127.0.0.1:{sink.server_port}')
            try:
                self.assertTrue(s.publish('before-close'))
                with self.assertRaises(TimeoutError):s.finish(.02)
                self.assertFalse(s.publish('late'))
                s.finish(2);self.assertFalse(s.thread.is_alive())
                self.assertEqual(s.state,'closed');self.assertEqual(sink.arrivals[0]['event_id'],'before-close')
            finally:s.finish(3);sink.shutdown();sink.server_close();t.join()
    def test_real_concurrent_publish_and_close_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            sink=Sink(('127.0.0.1',0),pathlib.Path(d)/'sink.jsonl');t=threading.Thread(target=sink.serve_forever);t.start()
            try:
                s=Source(f'http://127.0.0.1:{sink.server_port}',capacity=32)
                self.assertTrue(s.publish('preclose'))
                barrier=threading.Barrier(5)
                def producer(i):
                    barrier.wait()
                    for j in range(25):s.publish(f'{i}-{j}')
                def closer():barrier.wait();s.finish()
                with concurrent.futures.ThreadPoolExecutor(5) as pool:
                    futures=[pool.submit(producer,i) for i in range(4)]+[pool.submit(closer)]
                    for f in futures:f.result(timeout=10)
                s.finish();r=reconcile(s.attempts,s.results,sink.arrivals)
                self.assertEqual(r['attempted'],101);self.assertFalse(r['acknowledged_missing'])
                self.assertEqual(r['source_accepted'],r['sink_unique']);self.assertEqual(s.state,'closed')
            finally:sink.shutdown();sink.server_close();t.join()
