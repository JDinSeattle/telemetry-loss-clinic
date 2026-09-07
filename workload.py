"""Small Python application workload; logs describe real completed projections."""
import hashlib
import json
import math
import time

class ProjectionService:
    def __init__(self,source=None): self.source=source
    def handle(self,event_id):
        started=time.perf_counter_ns()
        a=[float(i%7-3) for i in range(8*16)]
        b=[float(i%5-2) for i in range(16*8)]
        result=[math.fsum(a[i*16+k]*b[k*8+j] for k in range(16)) for i in range(8) for j in range(8)]
        computation_end=time.perf_counter_ns()
        accepted=self.source.publish(event_id) if self.source else None
        end=time.perf_counter_ns()
        return {'event_id':event_id,'result_sha256':hashlib.sha256(json.dumps(result).encode()).hexdigest(),
            'kernel_us':(computation_end-started)/1000,'enqueue_us':(end-computation_end)/1000,
            'handler_us':(end-started)/1000,'source_accepted':accepted}
