"""OTLP/HTTP logs producer, durable receiving oracle, and loss reconciliation."""
import collections
import http.server
import json
import os
import queue
import socket
import threading
import time
import urllib.error
import urllib.request

def envelope(identifier, timestamp, padding=0):
    return {'resourceLogs':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'gemm-integration-clinic'}}]},
        'scopeLogs':[{'scope':{'name':'clinic.explicit-otlp-writer','version':'1'},'logRecords':[{
            'timeUnixNano':str(timestamp),'severityNumber':9,'body':{'stringValue':identifier},
            'attributes':[{'key':'event_id','value':{'stringValue':identifier}},
                          {'key':'padding','value':{'stringValue':'x'*padding}}]}]}]}]}

def send(endpoint, identifier, padding=0, created=None):
    created=time.time_ns() if created is None else created; start=time.monotonic_ns()
    req=urllib.request.Request(endpoint+'/v1/logs',json.dumps(envelope(identifier,created,padding)).encode(),{'Content-Type':'application/json'})
    record={'event_id':identifier,'created_unix_ns':created,'collector_accepted':False}
    try:
        with urllib.request.urlopen(req,timeout=2) as r:
            result=json.loads(r.read() or '{}'); record['http_status']=r.status
            rejected=int(result.get('partialSuccess',{}).get('rejectedLogRecords','0'))
            record['collector_accepted']=r.status==200 and rejected==0
            record['rejected_log_records']=rejected
    except urllib.error.HTTPError as e:
        with e: record.update(http_status=e.code,error=e.read().decode(errors='replace'))
    except OSError as e: record.update(http_status=None,error=type(e).__name__)
    except (ValueError,TypeError,AttributeError) as e: record.update(error='malformed collector acknowledgement: '+type(e).__name__)
    record['export_ms']=(time.monotonic_ns()-start)/1e6
    return record

class Source:
    """Explicit bounded application export queue; intentionally no hidden SDK retries."""
    def __init__(self,endpoint,capacity=128,padding=0):
        if type(capacity) is not int or capacity<1: raise ValueError('positive bounded capacity required')
        self.endpoint=endpoint; self.padding=padding; self.queue=queue.Queue(capacity)
        self.state='open'; self.state_lock=threading.Lock();self.finish_lock=threading.Lock();self.stop_sent=False
        self.attempts=[]; self.results=[]; self.thread=threading.Thread(target=self.run,daemon=True); self.thread.start()
    def publish(self,identifier):
        created=time.time_ns()
        with self.state_lock:
            reason=None;accepted=False
            if self.state!='open': reason='source_closing_or_closed'
            else:
                try: self.queue.put_nowait((identifier,created)); accepted=True
                except queue.Full: reason='source_queue_full'
            self.attempts.append({'event_id':identifier,'source_accepted':accepted,'unix_ns':created,'rejection_reason':reason})
            return accepted
    def run(self):
        while True:
            identifier=self.queue.get()
            try:
                if identifier is None: return
                event_id,created=identifier
                try: result=send(self.endpoint,event_id,self.padding,created)
                except Exception as e:
                    result={'event_id':event_id,'collector_accepted':False,'error':'exporter_exception:'+type(e).__name__}
                with self.state_lock: self.results.append(result)
            finally: self.queue.task_done()
    def finish(self,timeout=15):
        if timeout<=0: raise ValueError('positive finish timeout required')
        deadline=time.monotonic()+timeout
        if not self.finish_lock.acquire(timeout=timeout): raise TimeoutError('concurrent source close deadline')
        try:
            with self.state_lock:
                if self.state=='closed': return
                self.state='closing'
            if not self.stop_sent:
                try: self.queue.put(None,timeout=max(0,deadline-time.monotonic()))
                except queue.Full as e: raise TimeoutError('source queue drain deadline') from e
                self.stop_sent=True
            self.thread.join(timeout=max(0,deadline-time.monotonic()))
            if self.thread.is_alive(): raise TimeoutError('source export drain deadline')
            with self.state_lock: self.state='closed'
        finally: self.finish_lock.release()

class Sink(http.server.ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,path):
        self.path=path; self.mode='normal'; self.delay=.4; self.lock=threading.Lock(); self.arrivals=[]
        super().__init__(address,SinkHandler)

class SinkHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        body=self.rfile.read(int(self.headers['Content-Length']))
        if self.server.mode=='disconnect':
            self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
        if self.server.mode in ['outage','rate_limit']:
            self.send_response(503 if self.server.mode=='outage' else 429)
            self.send_header('Retry-After','1'); self.end_headers(); return
        try:
            payload=json.loads(body); rows=[]
            for resource in payload['resourceLogs']:
              for scope in resource['scopeLogs']:
                for log in scope['logRecords']:
                    rows.append({'event_id':log['body']['stringValue'],'created_unix_ns':int(log['timeUnixNano']),
                        'received_unix_ns':time.time_ns(),'sink_mode':self.server.mode})
            with self.server.lock:
                with open(self.server.path,'a') as f:
                    for row in rows: f.write(json.dumps(row)+'\n')
                    f.flush(); os.fsync(f.fileno())
                self.server.arrivals.extend(rows)
            # Delaying the ACK after fsync intentionally creates ambiguous delivery.
            if self.server.mode=='slow': time.sleep(self.server.delay)
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
            try: self.wfile.write(b'{}')
            except (BrokenPipeError,ConnectionResetError): pass
        except (ValueError,KeyError): self.send_error(400)

def reconcile(attempts, exports, arrivals):
    ids=[a['event_id'] for a in attempts]
    if len(ids)!=len(set(ids)): raise ValueError('source event IDs must be unique')
    attempted=set(ids); accepted={a['event_id'] for a in attempts if a['source_accepted']}
    acknowledged={e['event_id'] for e in exports if e['collector_accepted']}
    count=collections.Counter(a['event_id'] for a in arrivals); received=set(count)
    if not acknowledged<=accepted or not received<=attempted: raise ValueError('foreign or impossible IDs')
    return {'attempted':len(attempted),'source_accepted':len(accepted),'collector_acknowledged':len(acknowledged),
            'sink_unique':len(received),'sink_total':sum(count.values()),'duplicates':sum(v-1 for v in count.values()),
            'source_dropped':sorted(attempted-accepted),'export_unacknowledged':sorted(accepted-acknowledged),
            'acknowledged_missing':sorted(acknowledged-received),'delivered_without_ack':sorted(received-acknowledged),
            'missing_all':sorted(attempted-received)}
