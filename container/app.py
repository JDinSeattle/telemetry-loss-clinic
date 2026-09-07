"""Container-only test producer and durable oracle. Fault control is exec-only."""
import argparse,errno,json,os,pathlib,sys,threading,time,urllib.request
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from clinic import Sink,SinkHandler,Source
from workload import ProjectionService
MODE=pathlib.Path('/tmp/sink-mode')
class ContainerSink(Sink):
    @property
    def mode(self):return MODE.read_text().strip() if MODE.exists() else 'normal'
    @mode.setter
    def mode(self,value):MODE.write_text(value)
class Handler(SinkHandler):
    def do_GET(self):
        if self.path=='/health':data={'ready':True}
        elif self.path=='/records':
            with self.server.lock:data=list(self.server.arrivals)
        else:return self.send_error(404)
        payload=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='op',required=True)
    sub.add_parser('sink');sub.add_parser('hardening');h=sub.add_parser('health');h.add_argument('url')
    m=sub.add_parser('mode');m.add_argument('value',choices=['normal','outage','slow','rate_limit','disconnect'])
    p=sub.add_parser('produce');p.add_argument('--prefix',required=True);p.add_argument('--count',type=int,default=30);p.add_argument('--endpoint',default='http://collector:4318')
    args=ap.parse_args()
    if args.op=='hardening':
        try:fd=os.open('/app/readonly-probe',os.O_WRONLY);os.close(fd);raise AssertionError('rootfs writable')
        except OSError as e:assert e.errno==errno.EROFS
        fields={k:v.strip() for k,v in (line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)}
        assert os.geteuid()==10001 and fields['CapEff']=='0000000000000000' and fields['NoNewPrivs']=='1'
        print(json.dumps({'uid':os.geteuid(),'write_errno':errno.EROFS,'cap_eff':fields['CapEff'],'no_new_privs':fields['NoNewPrivs'],'cgroup':{name:pathlib.Path('/sys/fs/cgroup',name).read_text().strip() for name in ['cpu.max','memory.max','memory.swap.max','pids.max']}}));return
    if args.op=='health':
        with urllib.request.urlopen(args.url,timeout=1) as r:assert r.status==200
    elif args.op=='mode':
        temporary=MODE.with_suffix('.pending');temporary.write_text(args.value);temporary.replace(MODE)
    elif args.op=='sink':
        path=pathlib.Path('/data/sink.jsonl');sink=ContainerSink(('0.0.0.0',8080),path);sink.RequestHandlerClass=Handler
        if path.exists():sink.arrivals=[json.loads(line) for line in path.read_text().splitlines()]
        try:sink.serve_forever()
        finally:sink.server_close()
    else:
        if not 1<=args.count<=100:ap.error('count must be in 1..100')
        source=Source(args.endpoint,capacity=128);app=ProjectionService(source);business=[]
        try:
            for i in range(args.count):business.append(app.handle(f'{args.prefix}-{i:04d}'));time.sleep(.01)
        finally:source.finish()
        print(json.dumps({'uid':os.geteuid(),'attempts':source.attempts,'exports':source.results,'business':business}))
if __name__=='__main__':main()
