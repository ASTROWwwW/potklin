# Potklin

A local-first agent for code and file tasks, targeting consumer hardware. It runs on a local Ollama model, and success
is decided by checks **you** write, never by what the model claims.

**Status:** release candidate for one scope: bounded tasks in a workspace you trust. It is not a general autonomous
agent, and no GPT-5 parity is claimed.

## Quick start

Python 3.12 or newer, [Ollama](https://ollama.com) with a model that supports tool calling, no runtime dependency.

```sh
python -m pip install .
potklin doctor
potklin --workspace path/to/project mission "Where is the retry delay computed?"
```

Fix something and prove it:

```sh
potklin --workspace path/to/project mission "Fix the failing test" \
  --allow-write --only src --protect tests \
  --commands ~/commands.json --allow-exec --check command:test --rollback-on-failure
```

**Read [Using the agent](docs/agent.md) before you grant write or exec permissions.** Commands are not sandboxed, and
text inside your files can steer the model.

## What you get

- Tools to read, search, edit, create, move and (with its own flag) delete files, plus git status and diff.
- Commands you declare, which the model can start by name only.
- Acceptance checks, holdout checks the model never sees, read-only and write-only path lists.
- A diff of every mission and a rollback of its file writes.
- A SQLite journal of tool calls and outcomes.

## Develop

```sh
python -m unittest discover -s tests -v
python -m scripts.agent_eval --model <ollama-tag> --variants 7 31
```

`python -m potklin.commands --help` exposes the experimental commands (browser, memory, git, desktop automation).
Mods are authored by developers, never generated or installed by the model.

## Design principles

- Minimize time to verified completion, not just generation latency.
- Use deterministic tools for mechanical operations; adapt reasoning effort to uncertainty.
- Keep mission constraints, evidence and checkpoints outside the model context.
- Load skills and references on demand.
- Evaluate every change against quality, latency, memory and safety baselines.
- Keep model and runtime replaceable; prioritize local open-weight models, including abliterated candidates evaluated against their originals.

## Documentation

- [Using the agent](docs/agent.md)
- [Agent evaluation results](docs/agent-eval.md)
- [Architecture](docs/architecture.md)
- [Model and inference research](docs/inference.md)
- [Evaluation protocol](docs/evaluation.md)
- [Roadmap](docs/roadmap.md) and [current roadmap](docs/roadmap-current.md)
- [Security and reliability](docs/security.md)
- [Research provenance](docs/research.md)
- History: [benchmarks](docs/benchmarks-2026-11-25.md), [hardware lab](docs/hardware-lab.md),
  [early prototype](docs/prototype.md), [0.3.0 increment](docs/combined-release.md), [0.5 scope](docs/roadmap-v05.md)

Reference hardware: RTX 5080 16 GiB, 64 GiB RAM, Core Ultra 9 285K. Hardware-specific targets are experimental, not
requirements for future users.

License: not yet selected. Do not assume permission to redistribute third-party model weights or source code.
