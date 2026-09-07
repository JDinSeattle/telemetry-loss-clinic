# Native ingestion readiness follow-up

The local `make verify` campaign passed **11** focused tests and both pinned Collector releases after replacing metrics-only readiness with an empty OTLP ingestion probe. The original ten scenarios and loss assertions remain intact.

[Full validation log](../evidence/native-ingestion-20260907/validation.log) · [0.160 summary](../evidence/native-ingestion-20260907/collector-0.160/summary.json) · [0.147 summary](../evidence/native-ingestion-20260907/collector-0.147/summary.json). Source export files are written before crash injection and scenario assertions. These local results do not conclusively reconstruct the unavailable transport errors in the original failed CI run.
