"""Actual OpenVINO model inference on available devices, with CPU oracle."""
import argparse
import json
import math
import tempfile
from dataclasses import asdict
from pathlib import Path
from potklin.accelerators import Engine

def main():
    import numpy as np
    import openvino as ov
    from openvino import opset13 as ops
    p=argparse.ArgumentParser()
    p.add_argument("--repeats",type=int,default=30)
    a=p.parse_args()
    rng=np.random.default_rng(42)
    x=ops.parameter([1,128],np.float32,name="features")
    w=ops.constant(rng.normal(0,.03,(128,64)).astype(np.float32))
    y=ops.relu(ops.matmul(x,w,False,False))
    model=ov.Model([y],[x],"fixture")
    sample=rng.normal(0,1,(1,128)).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"fixture.xml"
        ov.save_model(model,str(path),compress_to_fp16=False)
        engine=Engine(path)
        device,measurements=engine.select([sample],repeats=a.repeats)
        rows=[asdict(m) for m in measurements]
        for row in rows:
            if not math.isfinite(row["median_ms"]):
                row["median_ms"]=None
        print(json.dumps({"suite":"openvino","devices":engine.devices(),"selected":device,"measurements":rows,"model":"synthetic dense layer; not LLM"}))
        # Unsupported devices are reported, CPU verification is mandatory.
        return int(not any(m.device=="CPU" and m.correct for m in measurements))
if __name__=="__main__":
    raise SystemExit(main())
