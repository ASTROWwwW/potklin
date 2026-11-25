# Local benchmark campaign — 2026-11-25

## Provenance and limitations
This is a transcription of the numerical summaries from the interactive research campaign, not an independent reproduction or a release-quality dataset. Raw private machine reports are not published. Model names below are local tags/labels, not verified upstream release identities. Pin exact digests, templates, runtime and driver before reproducing. Counts and aggregate results from V2/V3 should be checked against the original CSVs before scientific use. No GPT-5 equivalence is established.

Reference machine: RTX 5080 16 GiB (ZOTAC), Core Ultra 9 285K (8 P + 16 E cores), 64 GiB DDR5 configured at 6200 MT/s, ASUS ROG STRIX Z890-A GAMING WIFI BIOS 2201, Windows 11 Pro, Ollama 0.40.18, NVIDIA driver 610.88. Intel integrated graphics and NPU detected; their inference performance remains unmeasured.

## Initial sweeps
Qwen3 14B Q4_K_M, Flash Attention enabled, Q8 KV, one request:
| Context | Short decode t/s | Long decode t/s | Long prompt tokens |
|---|---:|---:|---:|
| 4K | 80.19 | 74.68 | 3196 |
| 8K | 80.58 | 72.00 | 6476 |
| 16K | 81.28 | 62.27 | 13038 |
| 32K | 75.65 | 52.65 | 26445 |

At 16K, FP16/Q8/Q4 KV short decode: 79.56/81.28/80.44 t/s; long decode: 67.77/62.27/63.68. Small samples, no quality equivalence established. Initial 30B-A3B two runs: 101.02 and 90.13 t/s at 8K. Initial four-model sweep reported 14B Q8 at 25.90 and 32B at 9.29 t/s. Partial CPU placement can dominate performance. A separate hardware diagnostic reported 14B peak 85.75 t/s, GPU 68 C, 328.2 W. SSD tests were cache-sensitive, not sustained storage benchmarks.

## Lab V1
Stopped early after about 3m16s. Native process exit codes were blank; exact crash cause unproven. 30B peaked at 120.69 t/s on a quality question, not a controlled throughput run. Strict score 2/8 without thinking and 0/8 with thinking; possible truncated final responses. One successful tool call. V2 introduced isolated workers, timeouts and richer result classification.

## Lab V2
Reported 56m42s, seven models, 91 quality results, 134 inference measurements, 1693 GPU samples.
| Local candidate | 8K short decode t/s (mean of two) | Strict non-thinking | Strict thinking |
|---|---:|---:|---:|
| Qwen3.5 9B | 134.94 | 5/8 | 5/8 |
| Qwen3 30B-A3B | 114.42 | 0/2 | 0/8 |
| Qwen3.6 35B-A3B | 90.08 | 8/8 | 8/8 |
| Qwen3 14B Q4 | 87.18 | 0/2 | 6/8 |
| Qwen3 14B V2 Q8 | 28.35 | 3/8 | 1/1 |
| Qwen3.8 27B | 22.86 | 6/8 | 7/8 |
| Qwen3 32B | 10.48 | 3/8 | 0/5 |

Incomplete denominators are not comparable full scores. Simple tool task succeeded on all seven in at least one tested condition; reported wall times 9B 0.73s, 35B 0.77s, 30B 1.65s, 14B Q4 2.93s, 32B 28.23s, 14B Q8 38.91s, 27B 51.81s. Mixed thinking and residency conditions prevent fair latency ranking. 35B reported loaded size 21.67 GiB, 12.88 GiB VRAM, 8.79 GiB outside VRAM; GPU power snapshot 117 W, not integrated energy. Peak sampled GPU temperature 74 C, power 361.31 W; no WHEA errors reported.

## Lab V3 Unlimited
Reported 45m50s, 320 quality tests, 40 simulated tool missions, zero worker crashes. No global deadline; individual timeouts retained.

| Candidate | Strict non-thinking /40 | Strict thinking /40 |
|---|---:|---:|
| 35B-A3B | 19 | 33 |
| 27B | 17 | 36 |
| 9B | 13 | 33 |
| 30B-A3B | 8 | 0 |

Strict format failures, timeouts and truncation must be separated from semantic errors. The 30B thinking failure requires diagnosis, not a claim that it cannot reason. Forty questions are insufficient for broad capability rankings.

### 35B placement sweep (decode t/s)
| Requested GPU layers | 8 CPU threads | 16 | 24 |
|---|---:|---:|---:|
| Auto | 87.746 | 78.896 | 83.402 |
| 8 | 30.201 | 30.979 | 23.265 |
| 16 | 35.915 | 37.849 | 30.247 |
| 24 | 50.796 | 52.784 | 44.823 |
| 32 | 12.558 | 12.202 | 11.935 |

Auto + 8 threads is the best observed configuration in this sweep. Requested placement is not proof of actual placement. Verify allocation and CPU affinity before attributing causes.

### 35B context sweep
| Configured context | Short decode t/s | Long decode t/s | Retrieval prompt tokens | First retrieval s | Repeated s |
|---|---:|---:|---:|---:|---:|
| 8K | 92.22 | 91.86 | 6382 | 11.93 | 0.40 |
| 16K | 91.83 | 90.02 | 12847 | 15.54 | 0.44 |
| 32K | 91.28 | 87.52 | 26501 | 21.25 | 0.51 |
| 64K | 86.37 | 76.58 | 54101 | 34.46 | 0.65 |
| 128K | 85.69 | 64.72 | 109285 | 65.37 | 0.95 |

Retrieval 10/10 on repeated simple needle tasks. Repeated identical requests are a best-case cache scenario, not evolving dialogue performance. Configured context is not evidence of full-context reasoning quality.

### Tools
Simple tool test without/with thinking: 9B 0.38/1.01s both pass; 30B 0.43/1.69s both pass; 35B 0.74s pass/2.88s fail; 27B 1.66/3.15s both pass. 35B multi-step: 0/8 strict without thinking (reported 8/8 numerically correct with extra prose), 8/8 with thinking (~2.6s warm). Simulated tools only; no real repository autonomy proven.

### Hardware and blockers
1368 GPU samples: max 66 C, 278.24 W, 2880 MHz core, 15001 MHz reported memory clock, 99% GPU utilization, 80% memory utilization, 15753 MiB VRAM. No WHEA events reported in the sampled diagnostic. V2 WinSAT RAM 134.71 GB/s is cache-sensitive; CPU compression 2994.81 MB/s. No overclock or BIOS changes applied. llama.cpp CUDA archive download and SHA256 check reported successful in V3; actual execution deferred because session elevated. OpenVINO setup also skipped. Verify archive source/checksum and driver/runtime compatibility before execution as a normal user. No measured alternative-engine or Intel accelerator speedup yet.

## Decisions
Provisional main candidate 35B-A3B, fast candidate 9B, deep comparison 27B. Keep 14B Q4 and 30B as controls. Start with a single resident model; prove routing benefits including switching costs. Prefer deterministic tools for calculations and known operations. Do not infer general intelligence from these synthetic suites.
