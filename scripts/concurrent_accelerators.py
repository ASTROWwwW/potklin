"""Measured concurrent auxiliary compute while the resident local LLM generates."""
import argparse
import json
import threading
import tempfile
import time
from pathlib import Path
from statistics import median
from potklin.accelerators import Engine
from potklin.ollama import Ollama

def main():
    import numpy as np
    import openvino as ov
    from openvino import opset13 as ops
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--repeats",type=int,default=3)
    a=p.parse_args()
    if not 1<=a.repeats<=10:
        p.error("invalid repeats")
    rng=np.random.default_rng(78)
    x=ops.parameter([1,512],np.float32,name="features")
    w=ops.constant(rng.normal(0,.03,(512,512)).astype(np.float32))
    m=ov.Model([ops.relu(ops.matmul(x,w,False,False))],[x],"fixture")
    inputs=[rng.normal(0,1,(1,512)).astype(np.float32)]
    client=Ollama(a.model)
    def llm():
        r=client.chat([{"role":"user","content":"Explain the purpose of unit and integration testing in a technical essay of at least 300 words."}],think=False,tokens=512)
        n=r.get("eval_count",0)
        d=r.get("eval_duration",0)
        if n<128 or d<=0:
            raise RuntimeError("short generation")
        return n*1e9/d
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"fixture.xml"
        ov.save_model(m,str(path),compress_to_fp16=False)
        engine=Engine(path)
        ref=engine.infer("CPU",inputs)
        llm()
        baseline=median(llm() for _ in range(a.repeats))
        print(json.dumps({"baseline_tps":baseline}),flush=True)
        measurements=[]
        for device in engine.devices():
            try:
                engine.infer(device,inputs)
                stop=threading.Event()
                ready=threading.Event()
                aux={"count":0,"correct":True,"error":None}
                def worker():
                    try:
                        while not stop.is_set():
                            values=engine.infer(device,inputs)
                            aux["correct"]=aux["correct"] and len(values)==len(ref) and all(np.allclose(v,b,atol=.02,rtol=.02) for v,b in zip(values,ref))
                            aux["count"]+=1
                            ready.set()
                    except Exception as e:
                        aux["error"]=type(e).__name__
                        ready.set()
                t=threading.Thread(target=worker,daemon=True)
                t.start()
                start=time.perf_counter()
                try:
                    if not ready.wait(10) or aux["error"]:
                        raise RuntimeError("auxiliary initialization failed")
                    speed=median(llm() for _ in range(a.repeats))
                finally:
                    stop.set()
                    t.join(15)
                elapsed=time.perf_counter()-start
                if t.is_alive():
                    raise RuntimeError("auxiliary worker did not stop")
                row={"device":device,"main_tps":speed,"slowdown":max(0,1-speed/baseline),"aux_per_s":aux["count"]/elapsed,"correct":aux["correct"] and not aux["error"]}
                measurements.append(row)
                print(json.dumps(row),flush=True)
            except Exception as e:
                print(json.dumps({"device":device,"error":str(e)}),flush=True)
        eligible=[r for r in measurements if r["correct"] and r["slowdown"]<=.05]
        selected=max(eligible,key=lambda x:x["aux_per_s"])["device"] if eligible else None
        print(json.dumps({"summary":"concurrent_dispatch","selected_under_5_percent_budget":selected,"workload":"synthetic auxiliary layer; no production policy update"}),flush=True)
        return int(not any(x["correct"] for x in measurements))
if __name__=="__main__":
    raise SystemExit(main())
