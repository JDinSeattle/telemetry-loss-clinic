# Measured Docker results — 2026-09-07

Run completed 2026-09-07T23:37:24Z. Host: 13th Gen Intel(R) Core(TM) i9-13900K, Linux 7.0.0-29-generic; Docker 29.8.0, Compose 5.3.1, cgroup v2. Containers use digest-pinned Python 3.14.7 on Debian bookworm.

Single local Linux Docker Engine; other host activity was not controlled. Results are author-operated container evidence, not cloud service deployment or production capacity. CI repeats independently.

All **5 scenario contracts passed**, with **150 event attempts**. Each scenario has 30 actual projection computations and event IDs.

| Scenario | Collector ACK | Sink unique | Duplicates | ACK missing |
|---|---:|---:|---:|---:|
| normal | 30 | 30 | 0 | 0 |
| network_partition | 30 | 30 | 0 | 0 |
| collector_recreate | 30 | 30 | 0 | 0 |
| sink_recreate | 30 | 30 | 0 | 0 |
| delayed_ack | 30 | 30 | 4 | 0 |

The Collector container was SIGKILLed and recreated with the same named queue volume; all 30 queued scenario records were delivered after recovery. The sink container was also replaced and retained all 90 prior records before accepting its next batch. Delayed ACK duplicates are expected and reported. UID, no-new-privileges, zero effective capabilities, read-only root and actual cgroup limits were checked for sink and Collector.

[Raw summary](../evidence/containers-20260907/summary.json) · [hardening](../evidence/containers-20260907/hardening.json) · [Collector recreation](../evidence/containers-20260907/collector-recreation.json) · [sink recreation](../evidence/containers-20260907/sink-recreation.json). Source/sink records for each scenario are beside these files.

Both campaigns use scoped cleanup and confirmed their own containers, volumes and networks were removed. [Cleanup](../evidence/containers-20260907/cleanup.json) · [raw command journal](../evidence/containers-20260907/commands.jsonl) · [manifest](../evidence/containers-20260907/manifest.json). Historical native manifests retain their original source hashes.
