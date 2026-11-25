# Evaluation

Primary endpoint: verified task success within a fixed time/resource budget. Report success rate and time to verified completion separately, including failed/time-out runs. Also report p50/p95, TTFT, prefill/decode throughput, model/tool calls, retries, peak RAM/VRAM and energy if available.

Record model hash, engine revision, driver, OS, context, KV format, template, seed, sampler, concurrency, cold/warm state and raw observations. Use matched workloads and repeated runs; distinguish cold load, cache reuse and tool latency. Avoid claiming p95 precision from tiny samples.

## Initial user-reported measurements (not reproduced)

Qwen3 14B Q4_K_M, Flash Attention, q8_0: short prompt ~80–82 tokens/s; ~13k prompt 62.27 tokens/s; ~26k prompt 52.65 tokens/s. The 30B-A3B reported two short runs of 101.02 and 90.13 tokens/s at 8K. These are preliminary, non-identical configurations; no quality parity established. Earlier no-thinking arithmetic failures motivate tool-backed checks and separate reasoning-mode tests.

## Targets (not measured)

| Workload | Target |
|---|---|
| Deterministic dispatch | <500 ms |
| Warm first token | <1 s |
| Git status interpretation | 1–2 s |
| Commit/push AI overhead | <5 s excluding network |
| Small edit | 5–15 s |
| Simple bug fix | 30–60 s, excluding unusually long tests |

Evaluate coding, terminal, browser, documents, data and GUI tasks. Build a private held-out suite with exact oracles where possible; use human rubrics for open-ended work. Compare public benchmarks only after verifying versions and contamination risks. Compare GPT-5 under equivalent tools, permissions and budgets; separately report native-product comparisons. Never claim general equivalence from isolated tasks.

Ablations: model original/abliterated, quantization, KV, context cache, MTP, planner, skills, memory, verifier, rollouts and OS. Keep changes only when benefits outweigh quality and complexity costs.

## Extended campaign

See [benchmark campaign](benchmarks-2026-11-25.md). Separate semantic correctness, format compliance, truncation, tool validity and end-to-end success. Report incomplete denominators and cold/warm conditions. Identical repeated requests are best-case cache tests, not conversation performance. Raw private data not published; aggregate transcription needs CSV audit.
