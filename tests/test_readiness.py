import concurrent.futures,http.server,json,threading,time,unittest
from scripts.validate import wait_ready

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'metrics_up 1\n')
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']));assert json.loads(raw)=={'resourceLogs':[]}
        self.server.probed.set();self.send_response(200 if self.server.ingestion_ready.is_set() else 503);self.end_headers();self.wfile.write(b'{}')
class Process:
    def poll(self):return None
class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.probed=threading.Event();self.server.ingestion_ready=threading.Event()
        self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def test_metrics_success_does_not_admit_work_before_ingestion(self):
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            f=pool.submit(wait_ready,Process(),self.server.server_port,self.server.server_port,2)
            try:
                self.assertTrue(self.server.probed.wait(1));self.assertFalse(f.done())
            finally:self.server.ingestion_ready.set()
            f.result(timeout=2)
    def test_ingestion_unavailable_is_a_bounded_readiness_failure(self):
        with self.assertRaisesRegex(TimeoutError,'OTLP ingestion'):
            wait_ready(Process(),self.server.server_port,self.server.server_port,.15)
        self.assertTrue(self.server.probed.is_set())
