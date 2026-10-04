# Experience Bank implementation map

Result provenance: owner-confirmed separate cloud-hosted test results. The README reproduces the current selected bullets. Commands below exercise this checkout; new outcomes must be recorded separately from those supplied results.

| Result | Implementation and regression evidence | Reproduce | Scope / source difference |
|---|---|---|---|
| 1 | [clinic.py](../clinic.py) · [tests/test_reconciliation.py](../tests/test_reconciliation.py) | `make verify` | Admission, exporter acknowledgement and durable sink receipt are separate sets. |
| 2 | [clinic.py](../clinic.py) · [tests/test_source_lifecycle.py](../tests/test_source_lifecycle.py) | `make test` | Lifecycle lock orders publish versus finish; exact race counts belong to the supplied run. |
| 3 | [scripts/validate.py](../scripts/validate.py) · [scripts/validate_containers.py](../scripts/validate_containers.py) | `make container-verify` | Memory and persistent queue failure behavior are checked separately. |
| 4 | [scripts/container_support.py](../scripts/container_support.py) · [tests/test_readiness.py](../tests/test_readiness.py) | `make test` | OTLP ingestion readiness is an actual event probe; EFBIG is not disk-full. |
| 5 | [scripts/validate.py](../scripts/validate.py) · [Makefile](../Makefile) | `make verify evidence-check` | Two native releases and Docker scenarios have separate manifests. |
| 6 | [tests/test_source_lifecycle.py](../tests/test_source_lifecycle.py) · [clinic.py](../clinic.py) | `make test` | Timeout preserves closing state while the in-flight network request finishes. |

## Measurement boundaries

- The 20 scenario-runs / 600 attempts across two releases and the separate Docker 5-scenario / 150-attempt campaign must not be accumulated into one unique event set; the latest native focused suite is 11 tests.
- The 30-record recovery holds only for the tested SIGKILL plus same named volume path; storage write failure, corruption, and physical power loss are different boundaries and are not covered.
- Two clean-storage runs (0.160.0 container, 0.147.0 native) do not validate in-place migration of one persistent database across versions.
- finish's timeout cannot preempt the current urllib request; it returns timeout and permits a retryable drain while closing keeps rejecting new events.
- EFBIG is a per-file size fault, not ENOSPC or power loss; sink_total=32 with sink_unique=30 shows duplicate handling, so neither exactly-once nor universal zero-loss may be claimed.
- Source success means only admission into the bounded queue and the network request may not have started; readiness was confirmed with a real small OTLP event, not process presence or a healthy port.
- Recovery timing of 2.4 seconds is a single observation measured from actual OTLP ingestion readiness, not a benchmark.

## Local verification

See `docs/alignment-verification.json` for commands and outcomes from this checkout. Supplied cloud numbers, historical checked-in artifacts and new local checks are separate evidence sets. A skipped dependency test is not a pass.
