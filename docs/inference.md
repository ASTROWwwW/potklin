# Model and inference research

## Candidates, not selections

- Qwen3-14B Abliterated: initial dense baseline.
- Qwen3-30B-A3B: initial MoE comparison.
- Qwen3.8-27B and Qwen3.6-35B-A3B: candidates named in the supplied research; verify official model cards, revisions, licenses and derivative provenance before download or adoption.
- GPT-OSS-20B: alternate architecture control; verify variant availability if abliterated is required.

Compare original and abliterated checkpoints using identical templates and samplers. Model size, active parameters and theoretical context do not establish achievable quality or VRAM fit.

## Runtime

Start with Ollama baseline and llama.cpp reference backend. Compare native Windows, WSL2 and Linux where available. Evaluate alternative backends only after confirming SM120 kernel support. Profile weights, KV/recurrent state, buffers, display reservations and CPU/GPU transfer separately. Admission controller must leave measured VRAM headroom.

Priorities: stable prefix caching, Flash Attention, KV precision sweep, mixed weight precision, adaptive speculative decoding/MTP where supported, expert cache and CPU placement for MoE. Use measured acceptance rates and total latency to enable/disable speculation. Profile prefill and decode independently. Pin engine revisions and retain fallbacks. Do not multiply unrelated published speedups.

## Training

First collect verified trajectories with failure labels and immutable train/holdout splits. Test conditional adapters on feasible small models before attempting 27B training. Estimate peak memory empirically. Compare SFT, preference tuning and reward-based training only where verifiers are meaningful. Pruning and expert surgery are later experiments with non-regression gates. No full fine-tuning promise on 16 GiB.
