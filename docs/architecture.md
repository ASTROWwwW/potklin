# Architecture

## Execution model

User request → immutable mission contract → policy and complexity router → task executor → tool observation → verifier → completion or replan.

| Mode | Purpose |
|---|---|
| Instant | Known deterministic operations, no model if possible |
| Fast | Small edits or tool selections, bounded reasoning |
| Standard | Normal work with targeted retrieval and tests |
| Deep | Dependency graph, recursive decomposition, alternative strategies and evidence-driven backtracking |

Risk and difficulty are separate: a simple irreversible action still requires policy checks. Start with one resident model; introduce additional models only after measuring switching overhead. Independent tools can run concurrently; GPU inference concurrency is resource-budgeted.

## Contracts

- Mission: objective, hard constraints, acceptance criteria, budget, allowed capabilities.
- Task: parent, dependencies, input/output contracts, verifier, attempts, estimated cost, status.
- Action: typed tool name, arguments, authorization, idempotency key.
- Observation: exit status, timestamps, artifact references, output digest.
- Proof: criterion, evidence, verdict (pass/fail/unknown), verifier version.

Only observed, independently checked actions become verified. Never interpret model confidence as proof. The parent task completes only when its acceptance criteria are met, not merely when all children finish.

## Recursive planning

Decompose when a task exceeds measured capability, context or budget, or a previous approach failed. Require each child to narrow scope, expose dependencies and have observable completion criteria. Stop splitting when further division offers no expected benefit. Bound depth, attempts and total work; detect repeated failure signatures. Replan affected descendants and invalidate stale evidence. Validate the whole mission after integration.

## Memory and skills

Use an append-only event log, working state, artifact store, semantic/lexical index and versioned procedure store. Preserve original sources, hashes, timestamps and supersession. Stable prompt prefixes improve cache reuse; mutable observations follow them. Index source code by symbols and paths before semantic retrieval. Do not treat summaries as authoritative.

Skills use SKILL.md metadata, references and scripts. Retrieve domain then top-k candidates; load only relevant instructions. Validate scripts and permission manifests. Learned skills remain candidates until replay tests pass. Never grant skills authority beyond the mission.

## Proposed implementation

Python typed orchestration and SQLite for the first prototype; native runtime behind an adapter. Interfaces: ModelBackend.generate, Tool.execute, Verifier.verify, Memory.retrieve, Planner.replan, SkillRegistry.select. Use an explicit state machine and durable checkpoint transactions. No engine fork before profiling.

## Provisional routing experiment

35B-A3B for normal missions, 9B for fast work, 27B as a deep-mode comparison; Instant remains deterministic where possible. Thinking is conditional on measured difficulty, not mandatory. Use structured tool outputs and independent checks. Do not assume simultaneous residency or Intel acceleration. See [hardware lab](hardware-lab.md) and [campaign results](benchmarks-2026-11-25.md).
