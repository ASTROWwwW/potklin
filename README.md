# Potklin

A local-first general-purpose AI agent research project, targeting consumer hardware. Potklin aims to complete real tasks quickly, autonomously and with verifiable evidence rather than merely generate answers.

**Status:** research and design; no working agent or GPT-5 parity claimed.

## Design principles

- Minimize time to verified completion, not just generation latency.
- Use deterministic tools for mechanical operations; adapt reasoning effort to uncertainty.
- Keep mission constraints, evidence and checkpoints outside the model context.
- Load skills and references on demand.
- Evaluate every change against quality, latency, memory and safety baselines.
- Keep model and runtime replaceable; prioritize local open-weight models, including abliterated candidates evaluated against their originals.

## Documentation

- [Architecture](docs/architecture.md)
- [Model and inference research](docs/inference.md)
- [Evaluation protocol](docs/evaluation.md)
- [Roadmap](docs/roadmap.md)
- [Security and reliability](docs/security.md)
- [Research provenance](docs/research.md)

Reference target: RTX 5080 16 GiB, 64 GiB RAM, Core Ultra 9 285K. Hardware-specific targets are experimental, not requirements for future users.

License: not yet selected. Do not assume permission to redistribute third-party model weights or source code.
