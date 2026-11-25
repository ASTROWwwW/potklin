# Prototype 0.5: consolidated validation

Added explicit scoped UIA actions, a read-only origin-scoped browser navigation loop, offline Windows Sandbox configuration generation, defensive AST leads and authorization matrix, recursive bounded decomposition, fast/deep retry, local Git branch/commit actions, observation context budgeting, OpenVINO measured dispatch, Ollama configuration matrix and offline LoRA training/smoke. Some modules are standalone Python APIs, not all are wired into the conversational CLI. No auto-granted capabilities.

## Validation

Offline tests cover boundaries, graph ordering, context, decomposition, synthetic static precision and fixture workflows. Browser fixture tests use loopback only. Complex model tests use exact oracles for shortest path, event replay, authorization, code diagnosis and data joins. Model security classification measures precision and recall on labeled synthetic snippets, not exploitability. No generated code executed.

## Remaining constraints

No general OS input driver, remote GitHub PR workflow, universal browser form automation, fully enforced OS isolation for the running agent, live OCR/vision integration, advanced offensive engine, production GPU scheduler under concurrent load, patched llama.cpp, or trained adapter for the main 35B model. Windows Sandbox configuration is not proof it was launched. OpenVINO selection measures an auxiliary synthetic model in isolation. LoRA requires compatible local HF safetensors weights and sufficient VRAM; GGUF alone is not a training checkpoint. Keep human review and separate approved execution for side effects. These additions are experimental and must not be presented as full implementation or verified on hardware until reports exist.
