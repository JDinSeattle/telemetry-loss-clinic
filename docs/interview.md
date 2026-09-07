# Interview preparation / 面试准备

Target: Observability · platform reliability · SDET.

Explain the code path and one retained failure before citing any metric. All numbers must link to the checked-in evidence and its hardware/software manifest. A GitHub CI pass demonstrates reproducibility, not production use.

可陈述：独立实现、真实本地测试、故障定位、可复现证据。不可陈述：企业客户、生产规模、未测硬件成绩、上游已合并贡献、独立用户验收。先按 README 完整复现，再练习解释每个边界和失败。

## Evidence-led talking points

- Explain three different ACKs: application queue acceptance, Collector transport acceptance, and receiver fsync. Show an actual acknowledged ID that is missing after memory-queue SIGKILL.
- Explain why the slow-ACK case duplicates after durable append. Exactly-once delivery cannot be inferred from a successful HTTP response.
- Walk through the EFBIG log and accepted/received set difference. Name the specific per-file capacity fault and avoid claiming a filesystem-full or power-loss test.
- Explain queue peak sampling, external observability-gap detection, original creation timestamps, and why recovered records are not real-time traffic.
- Explain the source choice: a bounded custom OTLP writer makes its queue/drop semantics explicit; it does not qualify a vendor SDK. Future SDK testing requires a separately pinned SDK and additional flush/shutdown cases.

Resume wording, after reproducing: “Built a real OTel Collector resilience lab with durable receiving oracle and event-ID reconciliation across 10 fault scenarios; demonstrated memory-vs-persistent crash recovery, duplicate delivery, queue overflow and storage-limit loss, retaining raw resource metrics and source instrumentation timings.” The experiment uses 30 events/scenario and is not a production scale claim.
