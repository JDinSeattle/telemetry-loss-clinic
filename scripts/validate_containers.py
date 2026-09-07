#!/usr/bin/env python3
"""Actual Docker bridges, volume recreation, process death and OTLP accounting."""
import argparse,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from clinic import reconcile
from evidence import fresh,write,seal
from scripts.container_support import Stack
from scripts.setup import PINS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='.runs/container');args=ap.parse_args();out=fresh(ROOT,args.out)
    stack=Stack(ROOT,out,'cc-telemetry');rows=[];environment=stack.environment();write(out/'environment.json',environment)
    def records():
        return json.loads(stack.execute('sink','python','-c','import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/records",timeout=2).read().decode())').stdout)
    def mode(value):stack.execute('sink','python','container/app.py','mode',value)
    def produce(name):
        p=stack.compose('run','--rm','--no-deps','-T','producer','python','container/app.py','produce','--prefix',name,timeout=30)
        source=json.loads(p.stdout);assert source['uid']==10001
        assert len(source['exports'])==30 and all(e['collector_accepted'] for e in source['exports']),source
        write(out/(name+'-source.json'),source);return source
    def settle(name,source):
        wanted={a['event_id'] for a in source['attempts']};end=time.monotonic()+20;seen=[]
        while time.monotonic()<end:
            seen=[r for r in records() if r['event_id'] in wanted]
            if {r['event_id'] for r in seen}==wanted:break
            time.sleep(.2)
        result=reconcile(source['attempts'],source['exports'],seen);assert not result['missing_all'],result
        write(out/(name+'-sink.json'),seen);result.update(scenario=name);rows.append(result);write(out/'scenarios-progress.json',rows);return result
    def assert_queued(source):
        wanted={a['event_id'] for a in source['attempts']}
        assert not wanted&{r['event_id'] for r in records()},'fault failed to block delivery'
    try:
        stack.compose('build','sink','collector',timeout=600)
        write(out/'resolved-compose.json',json.loads(stack.compose('config','--format','json').stdout))
        stack.compose('up','--detach','--wait','--wait-timeout','45','sink','collector',timeout=70)
        inspections={s:stack.inspect_summary(s) for s in ['sink','collector']}
        for i in inspections.values():
            assert i['user']=='10001:10001' and i['readonly_rootfs'] and not i['privileged']
            assert 'ALL' in i['cap_drop'] and 'no-new-privileges:true' in i['security_opt'] and i['pids_limit']==64
        write(out/'containers.json',inspections)
        hardened={service:json.loads(stack.execute(service,'python','container/app.py','hardening').stdout) for service in ['sink','collector']}
        for service,r in hardened.items():
            quota,period=map(int,r['cgroup']['cpu.max'].split());assert quota/period==.5
            assert int(r['cgroup']['memory.max'])==(512 if service=='collector' else 128)*1024*1024
            assert r['cgroup']['memory.swap.max']=='0' and r['cgroup']['pids.max']=='64'
        write(out/'hardening.json',hardened)
        metadata=stack.execute('collector','python','-c','import hashlib,json,subprocess; p="/usr/local/bin/otelcol-contrib"; print(json.dumps({"version":subprocess.check_output([p,"--version"],text=True).strip(),"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest()}))')
        write(out/'collector.json',json.loads(metadata.stdout));assert '0.160.0' in metadata.stdout
        assert json.loads(metadata.stdout)['sha256']==PINS['0.160.0'][1]
        source=produce('normal');settle('normal',source)
        collector=stack.cid('collector');network=stack.owned_network('delivery')
        stack.run(['docker','network','disconnect',network,collector])
        source=produce('network_partition');assert_queued(source)
        stack.run(['docker','network','connect','--alias','collector',network,collector])
        settle('network_partition',source)
        mode('outage');source=produce('collector_recreate');assert_queued(source)
        old=stack.inspect('collector');volume=next(m['Name'] for m in old['Mounts'] if m['Destination']=='/queue')
        stack.compose('kill','--signal','SIGKILL','collector')
        killed=stack.inspect('collector');assert killed['State']['ExitCode']==137 and not killed['State']['OOMKilled']
        stack.compose('up','--detach','--no-deps','--force-recreate','--wait','--wait-timeout','45','collector',timeout=70)
        new=stack.inspect('collector');assert new['Id']!=old['Id'];assert next(m['Name'] for m in new['Mounts'] if m['Destination']=='/queue')==volume
        mode('normal');settle('collector_recreate',source)
        write(out/'collector-recreation.json',{'old_id':old['Id'],'new_id':new['Id'],'same_volume':volume,'killed_state':killed['State']})
        before=records();old=stack.inspect('sink')
        stack.compose('up','--detach','--no-deps','--force-recreate','--wait','--wait-timeout','45','sink',timeout=70)
        new=stack.inspect('sink');assert old['Id']!=new['Id'] and records()==before
        write(out/'sink-recreation.json',{'old_id':old['Id'],'new_id':new['Id'],'records_preserved':len(before),'mounts':new['Mounts']})
        source=produce('sink_recreate');settle('sink_recreate',source)
        mode('slow');source=produce('delayed_ack');time.sleep(.6);mode('normal')
        result=settle('delayed_ack',source);assert result['duplicates']>0,result
        write(out/'summary.json',{'scenarios':rows,'scenario_count':len(rows),'attempted':sum(r['attempted'] for r in rows),'execution':'real local Docker container integration','performance_claim':None})
        print(json.dumps({'scenarios':len(rows),'attempted':sum(r['attempted'] for r in rows),'all_expected':True}),flush=True)
    finally:
        try:stack.close()
        finally:
            write(out/'cleanup.json',{'project':stack.project,'owned_resources_removed':stack.closed})
            seal(ROOT,out,{'execution':'Docker containers on local Linux CPU host','environment_file':'environment.json','source_changes':'no change to core source queue or reconciliation','cloud_deployment':False})
if __name__=='__main__':main()
