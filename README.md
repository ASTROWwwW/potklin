# Potklin

A local-first general-purpose AI agent research project, targeting consumer hardware. Potklin aims to complete real tasks quickly, autonomously and with verifiable evidence rather than merely generate answers.

**Status:** early executable prototype; no general autonomous agent or GPT-5 parity claimed.

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

## Research update (2026-11-25)

Local benchmark campaign completed through V3; provisional 35B-A3B main candidate and 9B fast candidate. See [benchmark findings](docs/benchmarks-2026-11-25.md), [current execution roadmap](docs/roadmap-current.md) and [hardware lab](docs/hardware-lab.md). No working agent yet.

## Prototype

See [prototype scope and V4/V5 findings](docs/prototype.md). Python 3.12, standard library only. Run `python -m unittest discover -s tests -v` and `python -m potklin tools` from the checkout. Mods are authored by developers, never generated or installed by the model.

## Combined increment (0.3.0)

See [current implementation and limitations](docs/combined-release.md). Run `python -m scripts.expanded_probe` for offline DAG regressions. This is not a stable V1.0 release.
