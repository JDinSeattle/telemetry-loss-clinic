#!/usr/bin/env python3
"""Replay D's request audit log through the explicit source queue. This is replay traffic."""
import argparse, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from clinic import Source
from evidence import write

def main():
    p=argparse.ArgumentParser(); p.add_argument('service_log'); p.add_argument('collector_endpoint'); p.add_argument('--out',required=True); a=p.parse_args()
    source=Source(a.collector_endpoint)
    for index,line in enumerate(pathlib.Path(a.service_log).read_text().splitlines()):
        event=json.loads(line); source.publish(f"replay-{index}-{event['event_id']}")
    source.finish()
    write(a.out,{'traffic':'historical replay, not original real-time traffic','attempts':source.attempts,'exports':source.results})

if __name__=='__main__': main()
