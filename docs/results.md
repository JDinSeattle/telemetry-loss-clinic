# Measured local results

Execution date: 2026-09-07T21:43:59Z. 5 focused unit/regression tests passed, followed by the real integration campaign. See [validation log](../evidence/local/validation.log) and [manifest](../evidence/local/manifest.json).

CPU: 13th Gen Intel(R) Core(TM) i9-13900K. Kernel: 7.0.0-29-generic. All results are author-operated local measurements; cloud CI is a separate reproducibility check.

| Scenario | Source accepted | Collector ACK | Sink unique | Duplicates | ACK missing | RSS peak KiB | Queue observed peak |
|---|---:|---:|---:|---:|---:|---:|---:|
| normal | 30 | 30 | 30 | 0 | 0 | 196748 | 4.0 |
| outage | 30 | 30 | 30 | 0 | 0 | 199132 | 30.0 |
| disconnect | 30 | 30 | 30 | 0 | 0 | 199560 | 30.0 |
| rate_limit | 30 | 30 | 30 | 0 | 0 | 200484 | 30.0 |
| slow_ack | 30 | 30 | 30 | 2 | 0 | 198984 | 30.0 |
| memory_crash | 30 | 30 | 0 | 0 | 30 | 194636 | 26.0 |
| persistent_crash | 30 | 30 | 30 | 0 | 0 | 198984 | 29.0 |
| queue_full | 30 | 2 | 2 | 0 | 0 | 195756 | 2.0 |
| storage_limit | 30 | 9 | 3 | 0 | 6 | 208188 | 30.0 |
| source_queue_full | 7 | 7 | 7 | 0 | 0 | 196256 | 6.0 |

60 paired local handler trials: instrumentation-off median 80.72 µs; on median 82.40 µs. This describes enqueue-path overhead on this host; asynchronous network and Collector work are retained separately in export/resource records. No universal overhead percentage is claimed.

Each scenario has 30 attempted events. Source overflow is unpaced; other scenarios target 100 events/s. Recovery observation is included in the reported delivery-rate denominator. See [complete summary](../evidence/local/summary.json) for latency, recovery, CPU tick samples and exact missing IDs. The stored EFBIG fault is a 256 KiB per-file limit; acknowledged loss remains visible rather than discounted.

Collector/storage-limit counter cross-check: receiver accepted **9**, refused **21**, exporter enqueue failures **21**, exporter sent **3**, and final queue size **0**. This independently agrees with source 9 ACKs, sink 3 unique arrivals and 6 ACKed missing IDs. After restart, Collector counters belong to a new epoch; the source ID ledger supplies the cross-epoch total. [Counter reconciliation](../evidence/local/collector-counter-reconciliation.json).
