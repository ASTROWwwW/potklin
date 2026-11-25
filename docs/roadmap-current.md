# Execution roadmap — revision 2026-11-25

Companion to the original milestone roadmap. Research completed is not product implementation.

## Phase A — baseline (partially complete)
- [x] Collect initial Ollama context/KV sweeps and compare seven local candidates.
- [x] Run V3 placement, long-context, strict reasoning and simulated tool tests.
- [ ] Archive sanitized raw CSV/JSONL, exact model digests and harness revisions; audit scoring and reproduce controlled baselines.
- [ ] Investigate 30B thinking failures, truncation, strict formatting and inconsistent samples.

## Phase B — next: inference and first agent vertical slice
- [ ] Run downloaded official llama.cpp as standard user after verifying integrity and runtime compatibility; compare identical GGUF/model, context, sampling and cold/warm conditions against Ollama.
- [ ] Install OpenVINO in isolated environment; benchmark CPU/iGPU/NPU separately, then concurrently with RTX inference. Measure correctness, latency, shared RAM contention and energy; no assumed acceleration.
- [ ] Test 35B quantizations, expert-level CPU/GPU placement, thread affinity, KV precision, batch and prefix reuse. Record actual allocation, not requested layers only.
- [ ] Test supported MTP/speculation with acceptance rates and quality controls; fall back when slower.
- [ ] Measure model switching, warm residency, VRAM headroom and evolving conversation cache.
- [ ] Build Python/SQLite mission runner with typed file/terminal/Git tools, sandbox, checkpoints and independent verification. Start with one resident model. Test real local fixture repositories before external writes.

## Phase C — hardware tuning (parallel, supervised)
- [ ] Establish sustained baseline and recoverable BIOS/GPU profiles; identify PSU and CPU cooler, record CPU temperatures and RAM timings.
- [ ] Evaluate display on iGPU, background load, Windows/WSL/Linux and storage placement.
- [ ] Test GPU power limit, memory and core changes one variable at a time; no firmware bypass, unattended voltage changes or security disablement. Stress-test correctness, WHEA, driver stability and rollback.
- [ ] Evaluate Intel 200S Boost and DDR5 tuning only after compatibility and cooling checks. No guaranteed gains.

## Phase D — agent quality
- [ ] Independent held-out tests: hundreds of diverse tasks, code edits, debugging, Git, documents, browser, data and GUI. Measure verified outcomes, not format alone.
- [ ] Adaptive Instant/Fast/Standard/Deep routing, bounded recursive plans, recovery and evidence invalidation.
- [ ] Persistent memory and versioned skills, provenance, cache-aware context management and security boundaries.
- [ ] Hardware-aware scheduler only when independent accelerator experiments justify it.
- [ ] Offline learning/adapters from verified trajectories with holdout gates; no automatic self-modification of production policy.
- [ ] Matched-tool/budget comparison against GPT-5; publish failures and limitations.

Acceptance: improvements must reduce time to verified completion or increase success at matched budgets without unacceptable regressions. Retain reversible baselines. No working agent or parity claim yet.
