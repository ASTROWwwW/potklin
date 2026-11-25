# Prototype 0.1

Developer-authored fixed registry, explicit mod selection, typed string arguments, local Ollama proposal-only planner, SQLite metadata journal, bounded read-only filesystem and Python source-pattern audit, allowlisted Windows launch with explicit permission. Launch is intentionally unverified until UI observation exists. Audit findings are leads, never proof of exploitation. The audit verifier checks repeatability, not vulnerability validity. Workspace path checks are not an OS sandbox and do not defend against concurrent filesystem mutation; use a trusted disposable fixture workspace. No arbitrary shell execution, self-generated mods, autonomous red-team chain, external scanning, GUI automation, or automatic model-plan execution. Python 3.12 standard library only. Next: OS isolation, verified UI automation, mission-level multi-step planner, real fixture tests, structured model outputs, hardware scheduler. Model tag is configurable; use actual local tags from Ollama. No engine or hardware tuning applied.

## V4/V5 reported findings (not independently reproduced)

Model switching reported 9.77s to 35B and 4.69s to 9B vs warm 0.175/0.076s. Keep primary resident; avoid frequent swaps. OpenVINO CPU/iGPU/NPU validated in microbenchmarks. V5 embeddings latency CPU/iGPU/NPU 1.433/2.592/3.003 ms; OCR 3.336/12.495/4.005 ms. Concurrent 35B generation alone/iGPU/NPU/CPU/all 89.79/88.27/84.98/84.51/75.995 t/s. No scheduler implemented yet. Native operation medians Discord lookup 1.165ms, file fixture 4.580ms, process launch 19.118ms; 70/70 reported. Cyber classification 16/16, not a red-team audit. llama.cpp 14B batch 512 ~90.83 t/s; 30B CPU expert layer sweep best 16 at 102.12 t/s. 35B/9B GGUF RoPE array mismatch unresolved; no arbitrary metadata patch. No MTP tested. These are conversational aggregate summaries, not audited raw datasets.

## Usage

From repository root: python -m unittest discover -s tests -v
List tools: python -m potklin tools
Use plan with explicit --mods filesystem cyber and actual --model (global option before subcommand). Plans are printed, not executed. Direct run requires explicit tool and JSON arguments. Windows launch requires --allow-write and does not claim UI verification.
