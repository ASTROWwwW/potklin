# Hardware lab

Target: RTX 5080 16 GiB, Ultra 9 285K, 64 GiB DDR5, Z890. Primary CUDA model; CPU tools and possible MoE offload; iGPU display or auxiliary inference; NPU small supported models. Intel accelerators share system memory; they do not automatically add RTX VRAM. Benchmark before routing work to them.

Local lab evolution: diagnostic inventory and telemetry, initial Ollama sweep, V1 early exit, V2 process supervisor and scoring fixes, V3 extended context/placement and simulated multi-tool tasks. Unlimited V3 removes global budget but retains per-call timeouts. Scripts were generated for PowerShell 5.1; user runs provide evidence, not independent CI validation. Raw scripts and machine logs are not included in this documentation update.

Next lab: standard-user runtime tests, verified downloads, isolated dependencies, model hash inventory, matched repeated measurements, incremental result persistence, separate timeout/error/semantic/format scores, peak memory and integrated energy, real fixture-based agent tasks. Avoid executing newly downloaded code elevated. Never silently disable security or alter clocks, firmware or voltage. Keep thermal and stability gates; require manual approval for hardware changes.

Storage candidate: internal WD Blue SN5000 4TB for weights/caches, subject to sustained uncached testing. Current high-performance Windows plan is not evidence that further tuning helps. PSU and cooling remain unidentified.
