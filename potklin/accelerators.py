"""Measured OpenVINO device selection for a trusted, preconverted local model."""
import time
from statistics import median
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Measurement:
    device: str
    median_ms: float
    samples: int
    correct: bool

class Engine:
    def __init__(self,model_path):
        import openvino as ov
        import numpy as np
        self.np=np
        self.core=ov.Core()
        self.model=self.core.read_model(str(Path(model_path).resolve(strict=True)))
        self.compiled={}
    def devices(self):
        return list(self.core.available_devices)
    def infer(self,device,inputs):
        if device not in self.devices():
            raise ValueError("unavailable device")
        if device not in self.compiled:
            self.compiled[device]=self.core.compile_model(self.model,device)
        result=self.compiled[device](inputs)
        return [self.np.array(x,copy=True) for x in result.values()]
    def measure(self,inputs,devices=None,repeats=20,atol=.02,rtol=.02):
        if not 2<=repeats<=1000:
            raise ValueError("repeat budget")
        baseline=self.infer("CPU",inputs)
        rows=[]
        for device in (devices or self.devices()):
            try:
                self.infer(device,inputs)
                times=[]
                correct=True
                for _ in range(repeats):
                    t=time.perf_counter_ns()
                    out=self.infer(device,inputs)
                    times.append((time.perf_counter_ns()-t)/1e6)
                    correct=correct and len(out)==len(baseline) and all(x.shape==y.shape and self.np.allclose(x,y,atol=atol,rtol=rtol) for x,y in zip(out,baseline))
                rows.append(Measurement(device,median(times),len(times),bool(correct)))
            except Exception:
                rows.append(Measurement(device,float("inf"),0,False))
        return rows
    def select(self,inputs,devices=None,repeats=20):
        rows=self.measure(inputs,devices,repeats)
        eligible=[r for r in rows if r.correct]
        if not eligible:
            raise RuntimeError("no verified device")
        return min(eligible,key=lambda x:x.median_ms).device,rows

    def dispatch(self,inputs,devices=None,repeats=20):
        device,measurements=self.select(inputs,devices,repeats)
        return {"device":device,"outputs":self.infer(device,inputs),"measurements":measurements}
