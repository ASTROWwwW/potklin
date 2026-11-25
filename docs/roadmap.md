# Roadmap

All milestones are planned, not implemented.

- [ ] M0 — Benchmark schema, raw JSONL logging, repeatable baseline and model hashes. Gate: reproduce results within documented variance.
- [ ] M1 — Minimal local agent with typed file, terminal and Git tools. Gate: test sandbox, observed results, restart-safe state and no false success in fixtures.
- [ ] M2 — Compare candidate models and runtime configurations on actual agent tasks. Gate: choose a Pareto-optimal default with sufficient VRAM headroom.
- [ ] M3 — Adaptive routing and recursive task graph. Gate: improve held-out success without excessive simple-task latency; enforce budgets and backtracking.
- [ ] M4 — Memory and skills. Gate: source provenance, stale-evidence invalidation, skill qualification and long-mission constraint retention.
- [ ] M5 — Profile and optimize inference. Gate: end-to-end improvements with matched quality and rollback.
- [ ] M6 — Generalist tools: browser, documents, data and GUI. Gate: permission checks and verified task outcomes across domains.
- [ ] M7 — Offline learning and adapters. Gate: private holdout gains, non-regression and reversible promotion.
- [ ] M8 — Comparative evaluation against GPT-5. Gate: publish reproducible methods and limitations, including failed tasks.

First implementation: a single model backend, deterministic tool registry, mission state, evidence store and benchmark runner. Avoid building several engines or training pipelines before the first useful vertical slice.

## Current execution priorities

See [revised execution roadmap](roadmap-current.md) for completed research, outstanding verification and next actions. M0 is partially complete; implementation milestones remain open.
