# Maintenance validation — 2026-09-07

**9 focused tests passed**, followed by the real integration campaign. [Raw log](../evidence/refresh-20260907/validation.log) · [manifest](../evidence/refresh-20260907/manifest.json).

Run: 2026-09-07T22:42:32Z; Python 3.14.4, 13th Gen Intel(R) Core(TM) i9-13900K, Linux 7.0.0-29-generic. Single author-operated Linux CPU host. Hosted CI execution is separate.

Both checksum-pinned Collector versions ran all 10 scenarios with 30 event attempts each: **20 scenario-runs and 600 event attempts**, excluding the 60 paired handler instrumentation trials per version. Explicit batching is disabled. Each campaign starts clean storage.

| Version | Scenario | ACK | Unique delivered | Duplicates | ACK missing |
|---|---|---:|---:|---:|---:|
| 0.160.0 | normal | 30 | 30 | 0 | 0 |
| 0.160.0 | outage | 30 | 30 | 0 | 0 |
| 0.160.0 | disconnect | 30 | 30 | 0 | 0 |
| 0.160.0 | rate_limit | 30 | 30 | 0 | 0 |
| 0.160.0 | slow_ack | 30 | 30 | 1 | 0 |
| 0.160.0 | memory_crash | 30 | 0 | 0 | 30 |
| 0.160.0 | persistent_crash | 30 | 30 | 0 | 0 |
| 0.160.0 | queue_full | 2 | 2 | 0 | 0 |
| 0.160.0 | storage_limit | 9 | 3 | 0 | 6 |
| 0.160.0 | source_queue_full | 7 | 7 | 0 | 0 |
| 0.147.0 | normal | 30 | 30 | 0 | 0 |
| 0.147.0 | outage | 30 | 30 | 0 | 0 |
| 0.147.0 | disconnect | 30 | 30 | 0 | 0 |
| 0.147.0 | rate_limit | 30 | 30 | 0 | 0 |
| 0.147.0 | slow_ack | 30 | 30 | 1 | 0 |
| 0.147.0 | memory_crash | 30 | 0 | 0 | 30 |
| 0.147.0 | persistent_crash | 30 | 30 | 0 | 0 |
| 0.147.0 | queue_full | 2 | 2 | 0 | 0 |
| 0.147.0 | storage_limit | 9 | 3 | 0 | 6 |
| 0.147.0 | source_queue_full | 7 | 7 | 0 | 0 |

Each version loses 30 acknowledged records after memory-queue SIGKILL and recovers all 30 in the persistent-queue crash case. A 256 KiB RLIMIT_FSIZE fault still exposes acknowledged loss. No zero-loss, exactly-once, database-format migration or comparative performance claim follows. The source tests exercise four concurrent producers plus close (101 attempts), post-close rejection and retry after a close deadline.

[0.160 summary](../evidence/refresh-20260907/summary.json) · [0.147 summary](../evidence/refresh-baseline-20260907/summary.json). Every scenario retains configuration, event IDs, Collector logs, resource samples and recovery timeline.
