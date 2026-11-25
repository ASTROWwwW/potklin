"""Conservative measured accelerator policy, not an accelerator backend."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Sample:
    device: str
    latency_ms: float
    main_slowdown: float
    validated: bool=True

def select(samples,concurrent=False,slowdown_budget=.05):
    eligible=[s for s in samples if s.validated and s.latency_ms>0 and 0<=s.main_slowdown<=1 and (not concurrent or s.main_slowdown<=slowdown_budget)]
    if not eligible:
        return None
    return min(eligible,key=lambda s:(s.latency_ms,s.main_slowdown,s.device)).device

def reference_samples():
    # V5 observations, illustrative; never substitute for per-machine validation.
    return [Sample("CPU",1.433,.059),Sample("iGPU",2.592,.017),Sample("NPU",3.003,.054)]
