#!/usr/bin/env python3
import argparse, contextlib, json, math, os, pathlib, resource, signal, socket, statistics, subprocess, sys, threading, time, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from clinic import Sink, Source, reconcile
from evidence import command, digest, fresh, seal, write
from scripts.setup import setup
from workload import ProjectionService

def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]

def get(url):
    with urllib.request.urlopen(url,timeout=.4) as r: return r.read().decode()

def config(path,receiver,sink,metrics,storage=None,capacity=128):
    data=f'''receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:{receiver}
exporters:
  otlp_http:
    endpoint: http://127.0.0.1:{sink}
    encoding: json
    compression: none
    timeout: 200ms
    retry_on_failure:
      initial_interval: 100ms
      max_interval: 200ms
      max_elapsed_time: 20s
    sending_queue:
      enabled: true
      num_consumers: 1
      queue_size: {capacity}
'''
    if storage: data+=f'      storage: file_storage\nextensions:\n  file_storage:\n    directory: {storage}\n'
    data+='service:\n'
    if storage: data+='  extensions: [file_storage]\n'
    data+=f'''  telemetry:
    logs:
      level: info
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 127.0.0.1
                port: {metrics}
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [otlp_http]
'''
    path.write_text(data)

def start(binary,cfg,log,limit=False):
    def limits():
        # Only the Collector child: simulate bounded persistent file capacity (EFBIG).
        signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE,(262144,262144))
    p=subprocess.Popen([str(binary),'--config',str(cfg)],stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits if limit else None)
    return p

def wait_ready(p,metrics):
    end=time.monotonic()+10
    while time.monotonic()<end:
        if p.poll() is not None: raise RuntimeError(f'collector exited {p.returncode}')
        try: get(f'http://127.0.0.1:{metrics}/metrics'); return
        except OSError: time.sleep(.05)
    raise TimeoutError('collector readiness')

def measure(p,metrics):
    row={'unix_ns':time.time_ns(),'alive':p.poll() is None}
    try:
        status=pathlib.Path(f'/proc/{p.pid}/status').read_text()
        row['rss_kib']=int(next(l for l in status.splitlines() if l.startswith('VmRSS:')).split()[1])
        stat=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()
        row['cpu_seconds']=(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK')
    except (OSError,StopIteration): pass
    try: row['prometheus']=get(f'http://127.0.0.1:{metrics}/metrics'); row['observation_available']=True
    except OSError: row['observation_available']=False
    return row

def scenario(binary,out,name):
    directory=out/name; directory.mkdir(parents=True,exist_ok=True)
    sink=Sink(('127.0.0.1',0),directory/'sink.jsonl'); thread=threading.Thread(target=sink.serve_forever,daemon=True); thread.start()
    receiver,metrics=port(),port(); persistent=name in ['persistent_crash','storage_limit']
    store=directory/'queue'; store.mkdir(exist_ok=True)
    cfg=directory/'collector.yaml'; capacity=2 if name=='queue_full' else 128
    config(cfg,receiver,sink.server_port,metrics,store if persistent else None,capacity)
    if name in ['outage','memory_crash','persistent_crash','queue_full','storage_limit']: sink.mode='outage'
    if name=='rate_limit': sink.mode='rate_limit'
    if name=='disconnect': sink.mode='disconnect'
    if name=='slow_ack': sink.mode='slow'
    samples=[]; timeline=[]; p=None
    with (directory/'collector.log').open('w') as log:
      try:
        p=start(binary,cfg,log,name=='storage_limit'); wait_ready(p,metrics)
        components=command([str(binary),'components'])
        assert 'file_storage' in components and 'otlpreceiver' in components
        (directory/'components.txt').write_text(components)
        source=Source(f'http://127.0.0.1:{receiver}',capacity=1 if name=='source_queue_full' else 128,padding=20000 if name=='storage_limit' else 0)
        application=ProjectionService(source); business=[]
        count=30; started=time.monotonic(); cpu_before=measure(p,metrics)
        for i in range(count):
            business.append(application.handle(f'{name}-{i:04d}'))
            if i%5==0: samples.append(measure(p,metrics))
            if name!='source_queue_full': time.sleep(.01)  # 100 events/s target, or explicit unpaced overload
        source.finish(); timeline.append({'event':'source_drained','unix_ns':time.time_ns()})
        if name in ['memory_crash','persistent_crash']:
            p.kill(); p.wait(timeout=3); timeline.append({'event':'SIGKILL','unix_ns':time.time_ns()})
            samples.append(measure(p,metrics)); sink.mode='normal'
            p=start(binary,cfg,log); wait_ready(p,metrics)
        else: sink.mode='normal'
        recovered=time.time_ns(); timeline.append({'event':'sink_recovery','unix_ns':recovered})
        # Wait for acknowledged events or bounded stable quiescence; losses remain losses.
        deadline=time.monotonic()+5; last=-1; stable=time.monotonic()
        while time.monotonic()<deadline:
            samples.append(measure(p,metrics)); current=len(sink.arrivals)
            if current!=last: last=current; stable=time.monotonic()
            if time.monotonic()-stable>1.2: break
            time.sleep(.1)
        result=reconcile(source.attempts,source.results,sink.arrivals)
        latency=sorted((r['received_unix_ns']-r['created_unix_ns'])/1e6 for r in sink.arrivals)
        queue_values=[]
        for sample in samples:
            for line in sample.get('prometheus','').splitlines():
                if line.startswith('otelcol_exporter_queue_size{') or line.startswith('otelcol_exporter_queue_size '):
                    queue_values.append(float(line.rsplit(' ',1)[1]))
        result.update(scenario=name,mode='file_storage' if persistent else 'memory',source_target_rps=100 if name!='source_queue_full' else 'unpaced burst',
            elapsed_s=time.monotonic()-started,latency_p50_ms=statistics.median(latency) if latency else None,
            latency_p95_ms=latency[math.ceil(.95*len(latency))-1] if latency else None,
            rss_peak_kib=max((s.get('rss_kib',0) for s in samples),default=0),
            observation_gaps=sum(not s['observation_available'] for s in samples),
            recovery_ms=max([0]+[(r['received_unix_ns']-recovered)/1e6 for r in sink.arrivals if r['received_unix_ns']>=recovered]),
            late_replay_records=sum(r['received_unix_ns']>=recovered for r in sink.arrivals),
            queue_disk_bytes=sum(f.stat().st_size for f in store.rglob('*') if f.is_file()),
            queue_peak_observed=max(queue_values,default=None),queue_capacity=capacity,
            successful_delivery_rps=len({r['event_id'] for r in sink.arrivals})/(time.monotonic()-started),
            source_export_p50_ms=statistics.median(r['export_ms'] for r in source.results),
            cpu_seconds_samples=[s.get('cpu_seconds') for s in samples])
        if name in ['normal','outage','disconnect','rate_limit','persistent_crash']: assert not result['missing_all'],result
        if name=='memory_crash': assert result['acknowledged_missing'] and result['observation_gaps'],result
        if name in ['queue_full','storage_limit']: assert result['export_unacknowledged'],result
        if name=='slow_ack': assert result['duplicates']>0,result
        if name=='source_queue_full': assert result['source_dropped'],result
        for filename,rows in [('source-attempts.jsonl',source.attempts),('source-exports.jsonl',source.results),('resources.jsonl',samples)]:
            (directory/filename).write_text(''.join(json.dumps(r)+'\n' for r in rows))
        write(directory/'timeline.json',timeline); write(directory/'summary.json',result)
        write(directory/'business.json',business)
        # Local instrumentation cost: paired identical workload with/without enqueue.
        if name=='normal':
            sink.path=directory/'overhead-sink.jsonl'
            overhead=[]; plain=ProjectionService(); measured=Source(f'http://127.0.0.1:{receiver}'); instrumented=ProjectionService(measured)
            for i in range(60):
                for mode,app in ([('off',plain),('on',instrumented)] if i%2 else [('on',instrumented),('off',plain)]):
                    overhead.append({'mode':mode,'pair':i,**app.handle(f'overhead-{i}')})
            measured.finish(); write(directory/'instrumentation-overhead.json',overhead)
            write(directory/'overhead-source.json',{'attempts':measured.attempts,'exports':measured.results})
        return result
      finally:
        if p and p.poll() is None: p.terminate(); p.wait(timeout=5)
        sink.shutdown(); sink.server_close(); thread.join(timeout=5)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='.runs/latest'); args=ap.parse_args()
    out=fresh(ROOT,args.out)
    binary=setup(); version=command([str(binary),'--version']).strip()
    assert '0.147.0' in version,version
    rows=[]
    for name in ['normal','outage','disconnect','rate_limit','slow_ack','memory_crash','persistent_crash','queue_full','storage_limit','source_queue_full']:
        r=scenario(binary,out,name); rows.append(r); print(json.dumps(r),flush=True)
    write(out/'summary.json',rows)
    seal(ROOT,out,{'collector_version':version,'collector_binary_sha256':digest(binary),
        'signal':'OTLP logs only','source':'custom explicit bounded OTLP/HTTP writer, not official language SDK',
        'disk_fault':'per-process RLIMIT_FSIZE 256 KiB; EFBIG, not a filesystem ENOSPC or power-loss simulation',
        'ack_semantics':'source queue acceptance != Collector HTTP acceptance != receiver fsync; no exactly-once claim'})

if __name__=='__main__': main()
